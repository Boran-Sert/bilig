"""Sohbetin okuma tool'larını gerçek Postgres'le, sahte aramayla test eder.

Embedding modeline gidilmez: hybrid_search yerine testin verdiği sırayla not dönen sahte arama
konur. Testler kendi kaynak, sayfa, paragraf, not, bağ ve kazanım satırlarını yazar; her şey test
bitince geri alınır.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import NamedTuple

import psycopg
import pytest
import pytest_asyncio
from psycopg.rows import TupleRow

from app.llm.prompts import get_tool_prompts
from app.schemas.search import SearchFilters, SearchHit, SearchTarget
from app.tutor import tools

Connection = psycopg.AsyncConnection[TupleRow]

SEED = """
WITH user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Tool Testi' FROM tenant
    RETURNING id
), document_row AS (
    INSERT INTO source_document (title, sha256, file_path, uploaded_by)
    SELECT 'TDE 12 Ders Kitabı', repeat('e', 64), '/data/sources/1.pdf', id FROM user_row
    RETURNING id
)
INSERT INTO source_page (source_document_id, page_no)
SELECT id, 88 FROM document_row
RETURNING id
"""

INSERT_BLOCK = """
INSERT INTO content_block (source_page_id, block_type, position, title_path, markdown,
    search_text, status)
VALUES (%(page_id)s, %(block_type)s, %(position)s, 'Roman › Yazarlar', %(markdown)s, %(markdown)s,
    %(status)s)
RETURNING id
"""

INSERT_NODE = """
INSERT INTO knowledge_node (node_type, name, note_md, status, search_text)
VALUES (%(node_type)s, %(name)s, %(note_md)s, %(status)s, %(name)s)
RETURNING id
"""

INSERT_EDGE = """
INSERT INTO knowledge_edge (from_node_id, to_node_id, relation, evidence_content_block_id, status)
VALUES (%(from_id)s, %(to_id)s, %(relation)s, %(block_id)s, %(status)s)
"""

INSERT_OUTCOME = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('TOOL', 'Tool Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Tool Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), group_row AS (
    INSERT INTO learning_outcome_group (curriculum_id, code, name)
    SELECT id, 'Z.9', 'Tool Grubu' FROM curriculum_row
    RETURNING id
)
INSERT INTO learning_outcome (learning_outcome_group_id, code, title, meb_explanation, search_text)
SELECT id, 'Z.9.1', 'Romanın türünü belirler.', 'Tarihî ve psikolojik roman.', 'Z.9.1'
FROM group_row
"""


class Notes(NamedTuple):
    """Testin kurduğu notlar ve paragraflar."""

    author: int
    work: int
    draft: int
    lonely: int
    evidence: int
    activity: int
    draft_block: int


class FakeSearch:
    """Aramayı kaydeden ve hazır not sırasını dönen sahte hybrid_search."""

    def __init__(self, node_ids: list[int]) -> None:
        """Dönülecek not sırasını saklar."""
        self.node_ids = node_ids
        self.calls: list[tuple[str, SearchFilters, int, bool]] = []

    async def __call__(
        self, connection: Connection, query: str, filters: SearchFilters, top_k: int, rerank: bool
    ) -> list[SearchHit]:
        """Çağrıyı kaydeder ve notları verilen sırayla döner."""
        self.calls.append((query, filters, top_k, rerank))
        return [SearchHit(id=node_id, text="", score=0.0) for node_id in self.node_ids]


class FakePool:
    """Testin transaction'ındaki bağlantıyı veren sahte havuz."""

    def __init__(self, connection: Connection) -> None:
        """Verilen bağlantıyı saklar."""
        self._connection = connection

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Connection]:
        """Saklanan bağlantıyı verir."""
        yield self._connection


async def fetch_id(db: Connection, query: str, values: dict[str, object]) -> int:
    """Sorgunun döndürdüğü kimliği okur."""
    row = await (await db.execute(query, values)).fetchone()
    assert row is not None
    return int(row[0])


async def add_block(
    db: Connection, page_id: int, block_type: str, position: int, status: str = "PUBLISHED"
) -> int:
    """Kaynak sayfaya bir paragraf yazar."""
    values = {
        "page_id": page_id,
        "block_type": block_type,
        "position": position,
        "markdown": f"Kanıt {position}",
        "status": status,
    }
    return await fetch_id(db, INSERT_BLOCK, values)


async def add_node(
    db: Connection, node_type: str, name: str, status: str = "PUBLISHED", note: str | None = None
) -> int:
    """Bir not yazar."""
    values = {"node_type": node_type, "name": name, "note_md": note, "status": status}
    return await fetch_id(db, INSERT_NODE, values)


async def add_edge(
    db: Connection,
    from_id: int,
    to_id: int,
    relation: str,
    block_id: int | None,
    status: str = "PUBLISHED",
) -> None:
    """İki not arasına bir bağ yazar."""
    values = {
        "from_id": from_id,
        "to_id": to_id,
        "relation": relation,
        "block_id": block_id,
        "status": status,
    }
    await db.execute(INSERT_EDGE, values)


@pytest_asyncio.fixture
async def notes(db: Connection) -> Notes:
    """Yazar, eser, taslak ve bağsız notları; bağları ve kanıt paragraflarını yazar."""
    page_id = await fetch_id(db, SEED, {})
    activity = await add_block(db, page_id, "ETKINLIK", 0)
    draft_block = await add_block(db, page_id, "BILGI", 1, status="DRAFT")
    evidence = await add_block(db, page_id, "BILGI", 2)
    author = await add_node(db, "AUTHOR", "Deneme Yazarı", note="Tarihî romanlarıyla bilinir.")
    work = await add_node(db, "WORK", "Deneme Romanı")
    draft = await add_node(db, "WORK", "Taslak Eser", status="DRAFT")
    lonely = await add_node(db, "CONCEPT", "Bağsız Kavram")
    await add_edge(db, author, work, "WROTE", activity)
    await add_edge(db, author, draft, "WROTE", evidence)
    await add_edge(db, work, author, "RELATED", draft_block)
    await add_edge(db, author, lonely, "RELATED", evidence, status="DRAFT")
    await add_edge(db, author, work, "RELATED", evidence)
    return Notes(author, work, draft, lonely, evidence, activity, draft_block)


def use_search(monkeypatch: pytest.MonkeyPatch, node_ids: list[int]) -> FakeSearch:
    """hybrid_search yerine sahte aramayı koyar."""
    fake = FakeSearch(node_ids)
    monkeypatch.setattr(tools, "hybrid_search", fake)
    return fake


@pytest.mark.asyncio
async def test_search_notes_returns_published_notes_in_rank_order(
    db: Connection, notes: Notes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Taslak not atlanır; kalanlar arama sırasıyla alıntılanmayan düz metin olarak döner."""
    fake = use_search(monkeypatch, [notes.work, notes.draft, notes.author])

    output = await tools.search_notes(db, "Deneme Yazarı romanları")

    assert (output.sources, output.is_error) == ([], False)
    headers = [line for line in output.text.splitlines() if " · id " in line]
    assert headers == [
        f"WORK · Deneme Romanı · id {notes.work}",
        f"AUTHOR · Deneme Yazarı · id {notes.author}",
    ]
    query, filters, top_k, rerank = fake.calls[0]
    assert query == "Deneme Yazarı romanları"
    assert filters == SearchFilters(target=SearchTarget.KNOWLEDGE_NODE)
    assert (top_k, rerank) == (5, True)


@pytest.mark.asyncio
async def test_note_text_has_type_note_and_published_links(
    db: Connection, notes: Notes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not metni türü, notu ve sadece iki ucu da yayında olan yayındaki bağları taşır."""
    use_search(monkeypatch, [notes.author])

    text = (await tools.search_notes(db, "Deneme Yazarı")).text

    assert text == (
        f"AUTHOR · Deneme Yazarı · id {notes.author}\n"
        "Tarihî romanlarıyla bilinir.\n"
        f"- Deneme Yazarı (AUTHOR, id {notes.author}) WROTE "
        f"Deneme Romanı (WORK, id {notes.work})\n"
        f"- Deneme Romanı (WORK, id {notes.work}) RELATED "
        f"Deneme Yazarı (AUTHOR, id {notes.author})\n"
        f"- Deneme Yazarı (AUTHOR, id {notes.author}) RELATED "
        f"Deneme Romanı (WORK, id {notes.work})"
    )


@pytest.mark.asyncio
async def test_note_card_is_first_published_evidence_paragraph(
    db: Connection, notes: Notes
) -> None:
    """Notun kartı, etkinlik ve taslak atlanarak bağlarının dayandığı ilk paragraftır."""
    author = (await tools.open_note(db, notes.author)).sources[0]
    lonely = await tools.open_note(db, notes.lonely)

    assert author.source == f"kb://note/{notes.author}"
    assert author.block is not None
    assert (author.block.block_id, author.block.source_title, author.block.page_no) == (
        notes.evidence,
        "TDE 12 Ders Kitabı",
        88,
    )
    assert [source.block for source in lonely.sources] == [None]


@pytest.mark.asyncio
async def test_search_without_notes_says_so(
    db: Connection, notes: Notes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not bulunmazsa sonuç hata değil, düz metin mesajıdır."""
    use_search(monkeypatch, [notes.draft])

    output = await tools.search_notes(db, "Yok")

    assert (output.sources, output.is_error) == ([], False)
    assert output.text == get_tool_prompts().messages.no_notes


@pytest.mark.asyncio
async def test_open_note_returns_note_and_its_evidence_paragraphs(
    db: Connection, notes: Notes
) -> None:
    """Önce not, sonra bağlarının dayandığı yayındaki, etkinlik olmayan paragraflar gelir."""
    output = await tools.open_note(db, notes.work)

    assert output.sources[0].title == "Deneme Romanı"
    assert [source.block.block_id for source in output.sources if source.block] == [
        notes.evidence,
        notes.evidence,
    ]
    paragraph = output.sources[1]
    assert (paragraph.source, paragraph.title, paragraph.text) == (
        "TDE 12 Ders Kitabı · s. 88",
        "Roman › Yazarlar",
        "Kanıt 2",
    )


@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.asyncio
async def test_open_unknown_or_draft_note_is_error(
    db: Connection, notes: Notes, missing: bool
) -> None:
    """Bulunmayan ya da yayında olmayan not hata sonucu döner."""
    note_id = notes.draft + 1000 if missing else notes.draft

    output = await tools.open_note(db, note_id)

    assert (output.sources, output.is_error) == ([], True)
    assert output.text == get_tool_prompts().messages.note_not_found


@pytest.mark.asyncio
async def test_get_outcome_returns_code_title_and_explanation(db: Connection) -> None:
    """Kazanım kodu, başlığı ve MEB açıklamasıyla düz metin olarak döner."""
    await db.execute(INSERT_OUTCOME)

    output = await tools.get_outcome(db, " Z.9.1 ")

    assert (output.sources, output.is_error) == ([], False)
    assert output.text == "Z.9.1: Romanın türünü belirler.\nTarihî ve psikolojik roman."


@pytest.mark.asyncio
async def test_unknown_outcome_is_error(db: Connection) -> None:
    """Bulunmayan kazanım kodu hata sonucu döner."""
    output = await tools.get_outcome(db, "Q.0.0")

    assert output.is_error
    assert output.text == get_tool_prompts().messages.outcome_not_found


@pytest.mark.asyncio
async def test_execute_tool_runs_named_tool_on_pool_connection(
    db: Connection, notes: Notes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tool adına göre çalışır ve girdisini şemasından okur."""
    monkeypatch.setattr(tools, "get_pool", lambda: FakePool(db))

    output = await tools.execute_tool("open_note", {"note_id": notes.author})

    assert output.sources[0].title == "Deneme Yazarı"
