"""İpucu, anlatım ve sohbetin hazırlığını gerçek Postgres'le, sahte aramayla test eder.

Claude'a ve embedding modeline gidilmez: hybrid_search yerine testin verdiği sırayla blok dönen
sahte arama konur. Testler kendi program, ünite, kaynak, soru, paragraf, öğrenci ve sohbet
satırlarını yazar; her şey test bitince geri alınır.
"""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, NamedTuple

import psycopg
import pytest
import pytest_asyncio
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from app.db.queries.tutor import fetch_question
from app.schemas.search import SearchFilters, SearchHit
from app.schemas.tutor import ChatRequest, ExplainStyle, ExplanationRequest
from app.tutor import hint, stream
from app.tutor.chat import NoUserMessageError, prepare_chat
from app.tutor.explanation import prepare_explanation

Connection = psycopg.AsyncConnection[TupleRow]

SEED = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('ANLATIM', 'Anlatım Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Anlatım Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), group_row AS (
    INSERT INTO learning_outcome_group (curriculum_id, code, name)
    SELECT id, 'A.2', 'Öyküleyici' FROM curriculum_row
    RETURNING id
), outcome_rows AS (
    INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
    SELECT group_row.id, code, 'Kazanım ' || code, code
    FROM group_row, unnest(ARRAY['A.2.15', 'A.2.3']) AS code
    RETURNING id
), unit_row AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT id, 12, 1, 'Roman' FROM curriculum_row
    RETURNING id
), user_row AS (
    INSERT INTO app_user (tenant_id, display_name, explain_style)
    SELECT min(id), 'Anlatım Testi', 'STEP_BY_STEP' FROM tenant
    RETURNING id
), other_user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Başka Öğrenci' FROM tenant
    RETURNING id
), document_row AS (
    INSERT INTO source_document (title, sha256, file_path, uploaded_by)
    SELECT 'TDE 12 Ders Kitabı', repeat('f', 64), '/data/sources/0.pdf', id FROM user_row
    RETURNING id
), page_row AS (
    INSERT INTO source_page (source_document_id, page_no)
    SELECT id, 174 FROM document_row
    RETURNING id
)
SELECT page_row.id, unit_row.id, user_row.id, other_user_row.id,
    (SELECT array_agg(id ORDER BY id) FROM outcome_rows)
FROM page_row, unit_row, user_row, other_user_row
"""

INSERT_QUESTION = """
INSERT INTO question (source_page_id, curriculum_unit_id, origin, content, correct_option,
    status, content_hash)
VALUES (
    %(page_id)s, %(unit_id)s, 'SOURCE', %(content)s, 'B', %(status)s,
    md5(%(content)s::text || %(status)s) || md5(%(content)s::text)
)
RETURNING id
"""

LINK_OUTCOMES = """
INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
SELECT %(question_id)s, unnest(%(outcome_ids)s::bigint[]), 'MODEL'
"""

INSERT_BLOCK = """
INSERT INTO content_block (source_page_id, block_type, position, title_path, markdown,
    search_text, status)
VALUES (%(page_id)s, %(block_type)s, %(position)s, 'Roman › Türler', %(markdown)s, %(markdown)s,
    %(status)s)
RETURNING id
"""

INSERT_CONVERSATION = """
INSERT INTO tutor_conversation (user_id, question_id)
VALUES (%(user_id)s, %(question_id)s)
RETURNING id
"""

INSERT_MESSAGE = """
INSERT INTO tutor_message (tutor_conversation_id, role, content)
VALUES (%(conversation_id)s, %(role)s, %(content)s)
"""

CONTENT = {
    "stem": [{"type": "paragraph", "md": "Hangisi tarihî roman örneğidir?"}],
    "options": [
        {"label": label, "blocks": [{"type": "paragraph", "md": title}]}
        for label, title in zip(
            "ABCDE",
            ["Eylül", "Küçük Ağa", "Aylak Adam", "Bereketli Topraklar Üzerinde", "Tutunamayanlar"],
            strict=True,
        )
    ],
}


class Seed(NamedTuple):
    """Testin kurduğu sayfa, ünite, iki öğrenci ve iki kazanım."""

    page_id: int
    unit_id: int
    user_id: int
    other_user_id: int
    outcome_ids: list[int]


class FakeSearch:
    """Aramayı kaydeden ve hazır blok sırasını dönen sahte hybrid_search."""

    def __init__(self, block_ids: list[int]) -> None:
        """Dönülecek blok sırasını saklar."""
        self.block_ids = block_ids
        self.calls: list[Mapping[str, Any]] = []

    async def __call__(
        self,
        connection: Connection,
        query: str,
        filters: SearchFilters,
        top_k: int,
        rerank: bool,
    ) -> list[SearchHit]:
        """Çağrıyı kaydeder ve blokları verilen sırayla döner."""
        self.calls.append({"query": query, "filters": filters, "top_k": top_k, "rerank": rerank})
        return [SearchHit(id=block_id, text="", score=0.0) for block_id in self.block_ids]


@pytest_asyncio.fixture
async def seed(db: Connection) -> Seed:
    """Program, ünite, öğrenciler, kaynak ve sayfayı yazar."""
    row = await (await db.execute(SEED)).fetchone()
    assert row is not None
    return Seed(*row)


async def fetch_id(db: Connection, query: str, values: dict[str, object]) -> int:
    """Sorgunun döndürdüğü kimliği okur."""
    row = await (await db.execute(query, values)).fetchone()
    assert row is not None
    return int(row[0])


async def add_question(db: Connection, seed: Seed, status: str = "PUBLISHED") -> int:
    """Kazanımlarına bağlı bir soru yazar."""
    values = {
        "page_id": seed.page_id,
        "unit_id": seed.unit_id,
        "content": Jsonb(CONTENT),
        "status": status,
    }
    question_id = await fetch_id(db, INSERT_QUESTION, values)
    await db.execute(LINK_OUTCOMES, {"question_id": question_id, "outcome_ids": seed.outcome_ids})
    return question_id


async def add_block(
    db: Connection, seed: Seed, block_type: str, position: int, status: str = "PUBLISHED"
) -> int:
    """Kaynak sayfaya bir paragraf yazar."""
    values = {
        "page_id": seed.page_id,
        "block_type": block_type,
        "position": position,
        "markdown": f"Paragraf {position}",
        "status": status,
    }
    return await fetch_id(db, INSERT_BLOCK, values)


async def add_conversation(
    db: Connection, user_id: int, question_id: int | None, *turns: tuple[str, str]
) -> int:
    """Mesajlarıyla bir sohbet yazar."""
    values = {"user_id": user_id, "question_id": question_id}
    conversation_id = await fetch_id(db, INSERT_CONVERSATION, values)
    for role, content in turns:
        values = {"conversation_id": conversation_id, "role": role, "content": content}
        await db.execute(INSERT_MESSAGE, values)
    return conversation_id


def use_search(monkeypatch: pytest.MonkeyPatch, block_ids: list[int]) -> FakeSearch:
    """hybrid_search yerine sahte aramayı koyar."""
    fake = FakeSearch(block_ids)
    monkeypatch.setattr(stream, "hybrid_search", fake)
    return fake


@pytest.mark.asyncio
async def test_draft_question_is_not_read(db: Connection, seed: Seed) -> None:
    """Yayında olmayan soru okunmaz."""
    question_id = await add_question(db, seed, status="DRAFT")

    assert await fetch_question(db, question_id) is None


@pytest.mark.asyncio
async def test_explanation_collects_context(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anlatım soruyu, iki şıkkı, bütün kazanımları ve öğrencinin tarzını taşır."""
    question_id = await add_question(db, seed)
    use_search(monkeypatch, [])
    request = ExplanationRequest(user_id=seed.user_id, question_id=question_id, selected_option="A")

    prepared = await prepare_explanation(db, request)

    assert prepared is not None
    assert prepared.user_id == seed.user_id
    assert prepared.variables["selected_option"] == "A"
    assert prepared.variables["correct_option"] == "B"
    assert prepared.variables["style"] == ExplainStyle.STEP_BY_STEP
    assert "B) Küçük Ağa" in str(prepared.variables["question"])
    outcomes = prepared.variables["outcomes"]
    assert isinstance(outcomes, list)
    assert [outcome.code for outcome in outcomes] == ["A.2.15", "A.2.3"]


@pytest.mark.asyncio
async def test_explanation_searches_question_outcomes_with_correct_option(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arama sorunun kazanımlarında, kök ve doğru şıkla, reranker açık yapılır."""
    question_id = await add_question(db, seed)
    fake = use_search(monkeypatch, [])
    request = ExplanationRequest(user_id=seed.user_id, question_id=question_id, selected_option="A")

    await prepare_explanation(db, request)

    call = fake.calls[0]
    assert call["query"] == "Hangisi tarihî roman örneğidir?\nKüçük Ağa"
    assert call["filters"].learning_outcome_ids == seed.outcome_ids
    assert call["rerank"] is True


@pytest.mark.asyncio
async def test_sources_are_published_text_blocks_in_rank_order(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Taslak, etkinlik ve başlık blokları atlanır; kalanlar arama sırasıyla, en fazla dört tane."""
    question_id = await add_question(db, seed)
    draft = await add_block(db, seed, "BILGI", 0, status="DRAFT")
    activity = await add_block(db, seed, "ETKINLIK", 1)
    quote = await add_block(db, seed, "ALINTI", 2)
    heading = await add_block(db, seed, "BASLIK", 3)
    text = await add_block(db, seed, "METIN", 4)
    infos = [await add_block(db, seed, "BILGI", position) for position in range(5, 9)]
    use_search(monkeypatch, [draft, activity, quote, heading, text, *infos])
    request = ExplanationRequest(user_id=seed.user_id, question_id=question_id, selected_option="A")

    prepared = await prepare_explanation(db, request)

    assert prepared is not None
    assert [source.block_id for source in prepared.sources] == [quote, text, *infos[:2]]
    first = prepared.sources[0]
    assert (first.source_title, first.page_no, first.markdown) == (
        "TDE 12 Ders Kitabı",
        174,
        "Paragraf 2",
    )


@pytest.mark.asyncio
async def test_explanation_of_draft_question_is_none(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yayında olmayan soru için anlatım hazırlanmaz."""
    question_id = await add_question(db, seed, status="DRAFT")
    use_search(monkeypatch, [])
    request = ExplanationRequest(user_id=seed.user_id, question_id=question_id, selected_option="A")

    assert await prepare_explanation(db, request) is None


@pytest.mark.asyncio
async def test_chat_reads_history_and_searches_last_message(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sohbet geçmişi okunur; arama son mesajla ve sorunun kazanımlarında yapılır."""
    question_id = await add_question(db, seed)
    conversation_id = await add_conversation(
        db,
        seed.user_id,
        question_id,
        ("ASSISTANT", "Küçük Ağa tarihî romandır."),
        ("USER", "Devlet Ana da tarihî roman mı?"),
    )
    fake = use_search(monkeypatch, [])

    prepared = await prepare_chat(
        db, ChatRequest(conversation_id=conversation_id, user_id=seed.user_id)
    )

    assert prepared is not None
    assert prepared.variables["message"] == "Devlet Ana da tarihî roman mı?"
    history = prepared.variables["history"]
    assert isinstance(history, list)
    assert [turn.role for turn in history] == ["ASSISTANT"]
    assert prepared.variables["correct_option"] == "B"
    assert fake.calls[0]["query"] == "Devlet Ana da tarihî roman mı?"
    assert fake.calls[0]["filters"].learning_outcome_ids == seed.outcome_ids


@pytest.mark.asyncio
async def test_chat_without_question_searches_everywhere(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Soru için açılmamış sohbette arama kazanımla daraltılmaz."""
    conversation_id = await add_conversation(db, seed.user_id, None, ("USER", "Roman nedir?"))
    fake = use_search(monkeypatch, [])

    prepared = await prepare_chat(
        db, ChatRequest(conversation_id=conversation_id, user_id=seed.user_id)
    )

    assert prepared is not None
    assert prepared.variables["question"] == ""
    assert fake.calls[0]["filters"].learning_outcome_ids is None


@pytest.mark.asyncio
async def test_chat_of_another_student_is_none(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Başka öğrencinin sohbeti okunmaz."""
    conversation_id = await add_conversation(db, seed.user_id, None, ("USER", "Roman nedir?"))
    use_search(monkeypatch, [])
    request = ChatRequest(conversation_id=conversation_id, user_id=seed.other_user_id)

    assert await prepare_chat(db, request) is None


@pytest.mark.asyncio
async def test_chat_without_new_student_message_fails(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Son mesajı öğrenciden olmayan sohbet hata verir."""
    conversation_id = await add_conversation(db, seed.user_id, None, ("ASSISTANT", "Merhaba"))
    use_search(monkeypatch, [])
    request = ChatRequest(conversation_id=conversation_id, user_id=seed.user_id)

    with pytest.raises(NoUserMessageError):
        await prepare_chat(db, request)


@pytest.mark.asyncio
async def test_hint_is_generated_for_published_question(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İpucu yayındaki soru için doğru şıkkın harfiyle birlikte HINT'e gider."""
    question_id = await add_question(db, seed)
    calls: list[Mapping[str, object]] = []

    async def fake_run_task(task: object, variables: Mapping[str, object]) -> str:
        """Çağrıyı kaydeder ve hazır ipucunu döner."""
        calls.append(variables)
        return "Romanın konusunu nereden aldığına bak."

    monkeypatch.setattr(hint, "get_pool", lambda: FakePool(db))
    monkeypatch.setattr(hint, "run_task", fake_run_task)

    assert await hint.generate_hint(question_id) == "Romanın konusunu nereden aldığına bak."
    assert calls[0]["correct_option"] == "B"


@pytest.mark.asyncio
async def test_hint_of_draft_question_is_none(
    db: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yayında olmayan soru için ipucu üretilmez."""
    question_id = await add_question(db, seed, status="DRAFT")
    monkeypatch.setattr(hint, "get_pool", lambda: FakePool(db))

    assert await hint.generate_hint(question_id) is None


class FakePool:
    """Testin transaction'ındaki bağlantıyı veren sahte havuz."""

    def __init__(self, connection: Connection) -> None:
        """Verilen bağlantıyı saklar."""
        self._connection = connection

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Connection]:
        """Saklanan bağlantıyı verir."""
        yield self._connection
