"""Kazanım eşleştirme adımını sahte run_task, sahte embedding ve gerçek Postgres'le test eder.

Claude'a çağrı yapılmaz: sahte run_task gelen adayları kaydeder ve testin verdiği seçimi döner.
Sahte embedding, testin işaret kelimesini taşıyan metne aynı vektörü verir; böylece veritabanında
gerçek kazanımlar olsa da adayların başında testin kazanımları gelir. Testler kendi program,
ünite, kaynak, soru ve paragraf satırlarını yazar; her şey test bitince geri alınır.
"""

from collections.abc import Mapping
from typing import Any, NamedTuple

import psycopg
import pytest
import pytest_asyncio
from pgvector.psycopg import register_vector_async
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from app.ingest import outcomes
from app.ingest.outcomes import check_match, match_source_outcomes
from app.llm.tasks import LlmTask
from app.schemas.outcome_match import (
    Confidence,
    MatchedOutcome,
    OutcomeCandidate,
    OutcomeMatch,
)
from app.search import hybrid

Connection = psycopg.AsyncConnection[TupleRow]

DIMENSIONS = 1024
MARKER = "zümrüdüankatest"
CODES = ("A.2.3", "A.2.7", "A.2.8")

SEED = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('ESLESME', 'Eşleşme Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Eşleşme Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), group_row AS (
    INSERT INTO learning_outcome_group (curriculum_id, code, name)
    SELECT id, 'A.2', 'Öyküleyici' FROM curriculum_row
    RETURNING id
), outcome_rows AS (
    INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
    SELECT group_row.id, code, 'Kazanım ' || code, %(marker)s || ' ' || code
    FROM group_row, unnest(%(codes)s::text[]) AS code
    RETURNING id
), unit_rows AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT curriculum_row.id, 12, unit.unit_no, unit.title
    FROM curriculum_row, (VALUES (1, 'Roman'), (2, 'Giriş')) AS unit (unit_no, title)
    RETURNING id, unit_no
), unit_link AS (
    INSERT INTO curriculum_unit_outcome (curriculum_unit_id, learning_outcome_id)
    SELECT unit_rows.id, outcome_rows.id
    FROM unit_rows, outcome_rows
    WHERE unit_rows.unit_no = 1
), user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Eşleşme Testi' FROM tenant
    RETURNING id
), document_row AS (
    INSERT INTO source_document (title, sha256, file_path, uploaded_by)
    SELECT 'ÖDSGM Roman Testi', repeat('e', 64), '/data/sources/0.pdf', id FROM user_row
    RETURNING id
), page_row AS (
    INSERT INTO source_page (source_document_id, page_no)
    SELECT id, 1 FROM document_row
    RETURNING id
)
SELECT document_row.id, page_row.id, roman.id, intro.id
FROM document_row, page_row, unit_rows AS roman, unit_rows AS intro
WHERE roman.unit_no = 1 AND intro.unit_no = 2
"""

INSERT_QUESTION = """
INSERT INTO question (source_page_id, curriculum_unit_id, origin, content, correct_option,
    content_hash)
VALUES (
    %(page_id)s, %(unit_id)s, 'SOURCE', %(content)s, 'E',
    md5(%(content)s::text) || md5(%(content)s::text || 'x')
)
RETURNING id
"""

INSERT_BLOCK = """
INSERT INTO content_block (source_page_id, curriculum_unit_id, block_type, position, title_path,
    markdown, search_text)
VALUES (%(page_id)s, %(unit_id)s, %(block_type)s, %(position)s, '', %(text)s, %(text)s)
RETURNING id
"""

READ_LINKS = """
SELECT learning_outcome.code, question_outcome.mapped_by
FROM question_outcome
JOIN learning_outcome ON learning_outcome.id = question_outcome.learning_outcome_id
WHERE question_outcome.question_id = %(id)s
ORDER BY learning_outcome.code
"""

COUNT_REVIEWS = """
SELECT count(*) FROM review_item
WHERE reason = 'LOW_CONFIDENCE' AND question_id = %(id)s
"""

COUNT_EMBEDDED = """
SELECT count(*) FROM learning_outcome WHERE search_text LIKE %(marker)s AND embedding IS NOT NULL
"""


class Seed(NamedTuple):
    """Testin kurduğu kaynak, sayfa, Roman ünitesi ve kazanımsız Giriş ünitesi."""

    document_id: int
    page_id: int
    unit_id: int
    intro_unit_id: int


def axis(index: int) -> list[float]:
    """Sadece verilen boyutu 1 olan normalize vektör kurar."""
    return [1.0 if position == index else 0.0 for position in range(DIMENSIONS)]


class FakeEmbedding:
    """İşaret kelimesini taşıyan metne bir eksen, diğerlerine başka bir eksen veren embedding."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Her metin için işaret kelimesine göre sabit bir vektör döner."""
        return [axis(0) if MARKER in text else axis(1) for text in texts]


class FakeRunTask:
    """OUTCOME_MATCH çağrılarını kaydeden ve hazır seçimi dönen sahte run_task."""

    def __init__(self, picks: list[tuple[str, Confidence]]) -> None:
        """Her çağrıda dönülecek kodları ve güvenleri saklar."""
        self.picks = picks
        self.calls: list[Mapping[str, Any]] = []

    async def __call__(
        self, task: LlmTask, variables: Mapping[str, Any], *, output_model: type[BaseModel]
    ) -> OutcomeMatch:
        """Çağrıyı kaydeder ve hazır seçimi döner."""
        assert task is LlmTask.OUTCOME_MATCH
        self.calls.append(variables)
        picked = [MatchedOutcome(code=code, confidence=level) for code, level in self.picks]
        return OutcomeMatch(outcomes=picked)


def candidate(code: str) -> OutcomeCandidate:
    """Kodu verilen aday kazanım kurar."""
    return OutcomeCandidate(id=int(code[-1]), code=code, title=code, meb_explanation=None)


@pytest_asyncio.fixture
async def connection(db: Connection) -> Connection:
    """Test bağlantısına vector tipini tanıtır."""
    await register_vector_async(db)
    return db


@pytest_asyncio.fixture
async def seed(connection: Connection, monkeypatch: pytest.MonkeyPatch) -> Seed:
    """Program, ünite, kaynak ve sayfayı yazar; sahte embedding kullandırır."""
    monkeypatch.setattr(hybrid, "get_embedding_provider", FakeEmbedding)
    monkeypatch.setattr(outcomes, "get_embedding_provider", FakeEmbedding)
    cursor = await connection.execute(SEED, {"marker": MARKER, "codes": list(CODES)})
    row = await cursor.fetchone()
    assert row is not None
    return Seed(*row)


def use_picks(monkeypatch: pytest.MonkeyPatch, *picks: tuple[str, Confidence]) -> FakeRunTask:
    """run_task yerine verilen seçimi dönen sahte görevi koyar."""
    fake = FakeRunTask(list(picks))
    monkeypatch.setattr(outcomes, "run_task", fake)
    return fake


async def fetch_value(connection: Connection, query: str, values: dict[str, object]) -> Any:
    """Sorgunun ilk satırının ilk değerini döner."""
    cursor = await connection.execute(query, values)
    row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def add_question(connection: Connection, seed: Seed, unit_id: int) -> int:
    """İşaret kelimesini taşıyan bir soru yazar."""
    content = {
        "stem": [{"type": "paragraph", "md": f"{MARKER} romanında anlatıcı kimdir?"}],
        "options": [
            {"label": label, "blocks": [{"type": "paragraph", "md": f"Şık {label}"}]}
            for label in "ABCDE"
        ],
    }
    values = {
        "page_id": seed.page_id,
        "unit_id": unit_id,
        "content": Jsonb(content),
    }
    return int(await fetch_value(connection, INSERT_QUESTION, values))


async def add_block(connection: Connection, seed: Seed, block_type: str, position: int) -> int:
    """İşaret kelimesini taşıyan bir blok yazar."""
    values = {
        "page_id": seed.page_id,
        "unit_id": seed.unit_id,
        "block_type": block_type,
        "position": position,
        "text": f"{MARKER} romanında zaman ve mekân",
    }
    return int(await fetch_value(connection, INSERT_BLOCK, values))


async def read_links(connection: Connection, question_id: int) -> list[tuple[str, str]]:
    """Sorunun kazanım kodlarını ve bağı kuranı döner."""
    cursor = await connection.execute(READ_LINKS, {"id": question_id})
    return [(row[0], row[1]) for row in await cursor.fetchall()]


def test_check_keeps_every_high_confidence_outcome() -> None:
    """Yüksek güvenli birden çok kazanım tutulur ve inceleme gerekmez."""
    match = OutcomeMatch(
        outcomes=[
            MatchedOutcome(code="A.2.3", confidence=Confidence.HIGH),
            MatchedOutcome(code="A.2.7", confidence=Confidence.HIGH),
        ]
    )

    choice = check_match(match, [candidate(code) for code in CODES])

    assert [outcome.code for outcome in choice.outcomes] == ["A.2.3", "A.2.7"]
    assert not choice.needs_review


@pytest.mark.parametrize("level", [Confidence.MEDIUM, Confidence.LOW])
def test_check_sends_medium_or_low_confidence_to_review(level: Confidence) -> None:
    """Herhangi bir kazanımın güveni orta ya da düşükse kazanım tutulur, inceleme açılır."""
    match = OutcomeMatch(
        outcomes=[
            MatchedOutcome(code="A.2.3", confidence=Confidence.HIGH),
            MatchedOutcome(code="A.2.8", confidence=level),
        ]
    )

    choice = check_match(match, [candidate(code) for code in CODES])

    assert [outcome.code for outcome in choice.outcomes] == ["A.2.3", "A.2.8"]
    assert choice.needs_review


def test_check_drops_codes_outside_candidates_and_duplicates() -> None:
    """Aday listesinde olmayan kod atılır, tekrar eden kod bir kez sayılır, inceleme açılır."""
    match = OutcomeMatch(
        outcomes=[
            MatchedOutcome(code="A.2.3", confidence=Confidence.HIGH),
            MatchedOutcome(code="A.2.3", confidence=Confidence.HIGH),
            MatchedOutcome(code="A.1.5", confidence=Confidence.HIGH),
        ]
    )

    choice = check_match(match, [candidate(code) for code in CODES])

    assert [outcome.code for outcome in choice.outcomes] == ["A.2.3"]
    assert choice.needs_review


def test_check_sends_empty_result_to_review() -> None:
    """Hiç kazanım seçilmezse sonuç incelemeye düşer."""
    choice = check_match(OutcomeMatch(outcomes=[]), [candidate(code) for code in CODES])

    assert choice.outcomes == []
    assert choice.needs_review


@pytest.mark.asyncio
async def test_question_is_linked_to_several_outcomes_once(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Soru birden çok kazanıma MODEL olarak bağlanır; adım iki kez çalışınca kopya bağ olmaz."""
    fake = use_picks(monkeypatch, ("A.2.7", Confidence.HIGH), ("A.2.8", Confidence.HIGH))
    question_id = await add_question(connection, seed, seed.unit_id)

    await match_source_outcomes(connection, seed.document_id)
    await match_source_outcomes(connection, seed.document_id)

    assert await read_links(connection, question_id) == [("A.2.7", "MODEL"), ("A.2.8", "MODEL")]
    assert await fetch_value(connection, COUNT_REVIEWS, {"id": question_id}) == 0
    assert len(fake.calls) == 1
    assert {item.code for item in fake.calls[0]["candidates"]} == set(CODES)
    assert fake.calls[0]["correct_option"] == "E"


@pytest.mark.asyncio
async def test_low_confidence_result_goes_to_review_once(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Düşük güvenli sonuç bağlanır ve inceleme listesine bir kez düşer."""
    fake = use_picks(monkeypatch, ("A.2.3", Confidence.LOW))
    question_id = await add_question(connection, seed, seed.unit_id)

    await match_source_outcomes(connection, seed.document_id)
    await match_source_outcomes(connection, seed.document_id)

    assert await read_links(connection, question_id) == [("A.2.3", "MODEL")]
    assert await fetch_value(connection, COUNT_REVIEWS, {"id": question_id}) == 1
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_result_without_valid_code_is_reviewed_without_links(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aday dışı kod bağlanmaz, soru incelemeye düşer ve ikinci çalışmada tekrar sorulmaz."""
    fake = use_picks(monkeypatch, ("A.1.5", Confidence.HIGH))
    question_id = await add_question(connection, seed, seed.unit_id)

    await match_source_outcomes(connection, seed.document_id)
    await match_source_outcomes(connection, seed.document_id)

    assert await read_links(connection, question_id) == []
    assert await fetch_value(connection, COUNT_REVIEWS, {"id": question_id}) == 1
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_missing_outcome_vectors_are_computed_first(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Vektörü olmayan kazanımların vektörü model çağrılmadan önce yazılmış olur."""
    fake = use_picks(monkeypatch, ("A.2.3", Confidence.HIGH))
    embedded_at_call: list[int] = []

    async def count_then_pick(
        task: LlmTask, variables: Mapping[str, Any], *, output_model: type[BaseModel]
    ) -> OutcomeMatch:
        """Model çağrıldığı anda vektörü yazılmış kazanımları sayar."""
        values = {"marker": f"{MARKER}%"}
        embedded_at_call.append(await fetch_value(connection, COUNT_EMBEDDED, values))
        return await fake(task, variables, output_model=output_model)

    monkeypatch.setattr(outcomes, "run_task", count_then_pick)
    await add_question(connection, seed, seed.unit_id)

    await match_source_outcomes(connection, seed.document_id)

    assert embedded_at_call == [len(CODES)]


@pytest.mark.asyncio
async def test_unit_without_outcomes_searches_all_outcomes(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kazanıma bağlı olmayan ünitenin sorusunda adaylar bütün kazanımlardan gelir."""
    fake = use_picks(monkeypatch, ("A.2.3", Confidence.HIGH))
    await add_question(connection, seed, seed.intro_unit_id)

    await match_source_outcomes(connection, seed.document_id)

    assert set(CODES) <= {item.code for item in fake.calls[0]["candidates"]}


@pytest.mark.asyncio
async def test_paragraphs_are_matched_but_activities_are_not(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bilgi bloğu kazanıma bağlanır, etkinlik bloğu modele hiç gitmez."""
    fake = use_picks(monkeypatch, ("A.2.7", Confidence.HIGH))
    info_id = await add_block(connection, seed, "BILGI", 0)
    await add_block(connection, seed, "ETKINLIK", 1)

    await match_source_outcomes(connection, seed.document_id)

    links = await fetch_value(
        connection,
        "SELECT count(*) FROM content_block_outcome WHERE content_block_id = %(id)s",
        {"id": info_id},
    )
    assert links == 1
    assert len(fake.calls) == 1
    assert fake.calls[0]["kind"] == "PARAGRAPH"
    assert len(fake.calls[0]["candidates"]) == len(CODES)
