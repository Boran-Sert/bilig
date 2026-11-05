"""Bilgi katmanı adımını sahte run_task ve gerçek Postgres'le test eder.

Claude'a çağrı yapılmaz: sahte run_task gelen paragrafı kaydeder ve testin o paragraf için
verdiği çıkarımı döner. Testler kendi kaynak, sayfa ve paragraf satırlarını yazar; her şey test
bitince geri alınır. Adlar gerçek verideki notlarla karışmasın diye uydurmadır.
"""

from collections.abc import Mapping
from typing import Any, NamedTuple

import psycopg
import pytest
import pytest_asyncio
from pgvector.psycopg import register_vector_async
from psycopg.rows import TupleRow
from pydantic import BaseModel

from app.db.queries.knowledge import open_node_review
from app.ingest import entities
from app.ingest.entities import check_evidence, extract_source_entities, save_extraction
from app.llm.tasks import LlmTask
from app.schemas.entity_extract import (
    EntityExtraction,
    ExtractedEdge,
    ExtractedNode,
    NodeType,
    PageEdge,
    PageExtraction,
    Relation,
)

Connection = psycopg.AsyncConnection[TupleRow]

SEED = """
WITH user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Bilgi Testi' FROM tenant
    RETURNING id
), document_row AS (
    INSERT INTO source_document (title, sha256, file_path, uploaded_by)
    SELECT 'Bilgi Testi Kitabı', repeat('k', 64), '/data/sources/0.pdf', id FROM user_row
    RETURNING id
), page_row AS (
    INSERT INTO source_page (source_document_id, page_no)
    SELECT id, 1 FROM document_row
    RETURNING id
)
SELECT document_row.id, page_row.id FROM document_row, page_row
"""

INSERT_BLOCK = """
INSERT INTO content_block (source_page_id, block_type, position, title_path, markdown, status,
    search_text)
VALUES (%(page_id)s, %(block_type)s, %(position)s, 'Kitap › Roman', %(text)s, %(status)s,
    %(text)s)
RETURNING id
"""

READ_EDGES = """
SELECT source.name, edge.relation, target.name, edge.status, edge.evidence_content_block_id
FROM knowledge_edge AS edge
JOIN knowledge_node AS source ON source.id = edge.from_node_id
JOIN knowledge_node AS target ON target.id = edge.to_node_id
WHERE edge.evidence_content_block_id = ANY(%(ids)s::bigint[])
ORDER BY edge.relation, source.name
"""

READ_NODE = """
SELECT id, status, note_md, search_text, embedding IS NULL
FROM knowledge_node WHERE node_type = %(node_type)s AND name = %(name)s
"""

READ_REVIEWS = """
SELECT review_item.reason, node.name, review_item.detail
FROM review_item
JOIN knowledge_node AS node ON node.id = review_item.knowledge_node_id
WHERE node.name = ANY(%(names)s::text[])
ORDER BY review_item.id
"""

READ_EDGE_REVIEW_COUNT = """
SELECT count(*)
FROM review_item
JOIN knowledge_edge AS edge ON edge.id = review_item.knowledge_edge_id
WHERE edge.evidence_content_block_id = ANY(%(ids)s::bigint[])
"""

READ_ALIAS_COUNTS = """
SELECT node.name, count(alias.knowledge_node_id)
FROM knowledge_node AS node
JOIN knowledge_node_alias AS alias ON alias.knowledge_node_id = node.id
WHERE node.name = ANY(%(names)s::text[])
GROUP BY node.name
ORDER BY node.name
"""

SET_EMBEDDING = "UPDATE knowledge_node SET embedding = %(vector)s WHERE id = %(id)s"

INSERT_PAGE = """
INSERT INTO source_page (source_document_id, page_no) VALUES (%(document_id)s, %(page_no)s)
RETURNING id
"""

READ_PAGE_MARK = "SELECT entities_extracted_at IS NOT NULL FROM source_page WHERE id = %(id)s"

NOVEL = "*Zümrüt Ağa* (Tarık Zümrütoğlu) bir tarihî romandır ve Cumhuriyet Dönemi eseridir."


class Seed(NamedTuple):
    """Testin kurduğu kaynak ve sayfa."""

    document_id: int
    page_id: int


class FakeRunTask:
    """ENTITY_EXTRACT sayfa çağrılarını kaydeden ve paragraflara göre hazır çıkarım dönen görev."""

    def __init__(
        self, results: Mapping[str, EntityExtraction], extra_edges: list[PageEdge] | None = None
    ) -> None:
        """Paragraf metnine göre dönülecek çıkarımları ve eklenecek bağları saklar."""
        self.results = results
        self.extra_edges = extra_edges or []
        self.pages: list[list[str]] = []

    async def __call__(
        self, task: LlmTask, variables: Mapping[str, Any], *, output_model: type[BaseModel]
    ) -> PageExtraction:
        """Çağrıyı kaydeder; sayfadaki paragrafların çıkarımlarını numaralarıyla birleştirir."""
        assert task is LlmTask.ENTITY_EXTRACT
        assert output_model is PageExtraction
        self.pages.append([block["markdown"] for block in variables["blocks"]])
        nodes: list[ExtractedNode] = []
        edges = list(self.extra_edges)
        for block in variables["blocks"]:
            found = self.results.get(block["markdown"], EntityExtraction(nodes=[], edges=[]))
            nodes += found.nodes
            edges += [PageEdge(**edge.model_dump(), block_id=block["id"]) for edge in found.edges]
        return PageExtraction(nodes=nodes, edges=edges)


def node(node_type: NodeType, name: str, note: str | None = None) -> ExtractedNode:
    """Çıkarılmış not kurar."""
    return ExtractedNode(node_type=node_type, name=name, note=note)


def edge(source: ExtractedNode, relation: Relation, target: ExtractedNode) -> ExtractedEdge:
    """İki not arasında çıkarılmış bağ kurar."""
    return ExtractedEdge(
        from_type=source.node_type,
        from_name=source.name,
        relation=relation,
        to_type=target.node_type,
        to_name=target.name,
    )


def novel_extraction() -> EntityExtraction:
    """Roman paragrafı için iki dayanaklı ve bir dayanaksız bağ içeren çıkarım kurar."""
    work = node(NodeType.WORK, "Zümrüt Ağa", "Kurtuluş Savaşı yıllarını anlatır.")
    genre = node(NodeType.GENRE, "tarihî roman")
    period = node(NodeType.PERIOD, "Cumhuriyet Dönemi")
    stranger = node(NodeType.AUTHOR, "Kemal Zümrütoğlu")
    return EntityExtraction(
        nodes=[work, genre, period, stranger],
        edges=[
            edge(work, Relation.HAS_GENRE, genre),
            edge(work, Relation.IN_PERIOD, period),
            edge(stranger, Relation.WROTE, work),
        ],
    )


@pytest_asyncio.fixture
async def connection(db: Connection) -> Connection:
    """Test bağlantısına vector tipini tanıtır."""
    await register_vector_async(db)
    return db


@pytest_asyncio.fixture
async def seed(connection: Connection) -> Seed:
    """Kullanıcı, kaynak ve sayfayı yazar."""
    cursor = await connection.execute(SEED)
    row = await cursor.fetchone()
    assert row is not None
    return Seed(*row)


async def add_block(
    connection: Connection,
    seed: Seed,
    text: str,
    position: int,
    block_type: str = "BILGI",
    status: str = "DRAFT",
) -> int:
    """Sayfaya paragraf yazar."""
    values = {
        "page_id": seed.page_id,
        "block_type": block_type,
        "position": position,
        "text": text,
        "status": status,
    }
    cursor = await connection.execute(INSERT_BLOCK, values)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def fetch_rows(connection: Connection, query: str, values: dict[str, object]) -> list[Any]:
    """Sorgunun bütün satırlarını döner."""
    cursor = await connection.execute(query, values)
    return list(await cursor.fetchall())


async def read_node(connection: Connection, node_type: NodeType, name: str) -> Any:
    """Notun kimliğini, durumunu, notunu, arama metnini ve vektörünün boşluğunu döner."""
    rows = await fetch_rows(connection, READ_NODE, {"node_type": node_type, "name": name})
    return rows[0] if rows else None


def use_results(
    monkeypatch: pytest.MonkeyPatch,
    results: Mapping[str, EntityExtraction],
    extra_edges: list[PageEdge] | None = None,
) -> FakeRunTask:
    """run_task yerine verilen çıkarımları dönen sahte görevi koyar."""
    fake = FakeRunTask(results, extra_edges)
    monkeypatch.setattr(entities, "run_task", fake)
    return fake


async def add_page(connection: Connection, seed: Seed, page_no: int) -> Seed:
    """Kaynağa yeni sayfa ekler ve o sayfayı gösteren tohumu döner."""
    values = {"document_id": seed.document_id, "page_no": page_no}
    cursor = await connection.execute(INSERT_PAGE, values)
    row = await cursor.fetchone()
    assert row is not None
    return Seed(seed.document_id, int(row[0]))


@pytest.mark.asyncio
async def test_step_publishes_supported_links_once(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kural ve dayanaklı model bağları yayına girer, inceleme açılmaz, kopya olmaz."""
    fake = use_results(monkeypatch, {NOVEL: novel_extraction()})
    block_id = await add_block(connection, seed, NOVEL, 1)
    await add_block(connection, seed, "Etkinlik metni", 2, block_type="ETKINLIK")
    await add_block(connection, seed, "Reddedilen metin", 3, status="REJECTED")

    await extract_source_entities(connection, seed.document_id)
    await extract_source_entities(connection, seed.document_id)

    assert await fetch_rows(connection, READ_EDGES, {"ids": [block_id]}) == [
        ("Zümrüt Ağa", "HAS_GENRE", "tarihî roman", "PUBLISHED", block_id),
        ("Zümrüt Ağa", "IN_PERIOD", "Cumhuriyet Dönemi", "PUBLISHED", block_id),
        ("Tarık Zümrütoğlu", "WROTE", "Zümrüt Ağa", "PUBLISHED", block_id),
    ]
    assert await fetch_rows(connection, READ_EDGE_REVIEW_COUNT, {"ids": [block_id]}) == [(0,)]
    assert fake.pages == [[NOVEL]]
    assert await fetch_rows(connection, READ_PAGE_MARK, {"id": seed.page_id}) == [(True,)]
    assert await read_node(connection, NodeType.AUTHOR, "Kemal Zümrütoğlu") is None
    work = await read_node(connection, NodeType.WORK, "Zümrüt Ağa")
    assert work[1:] == (
        "PUBLISHED",
        "Kurtuluş Savaşı yıllarını anlatır.",
        "Zümrüt Ağa Kurtuluş Savaşı yıllarını anlatır.",
        True,
    )


@pytest.mark.asyncio
async def test_same_key_spelling_joins_note_and_new_note_clears_embedding(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anahtarı aynı yazım aynı nota gider; nota metin eklenince arama metni ve vektör yenilenir."""
    mention = "*Kambur Zümrüt* (Victor Zümrütyan) çok okundu."
    noted = node(NodeType.AUTHOR, "Victor Zümrütyan", "Fransız romancı.")
    use_results(monkeypatch, {mention: EntityExtraction(nodes=[noted], edges=[])})
    await add_block(connection, seed, "*Sefil Zümrüt* (Victor Zumrutyan)", 1)
    await extract_source_entities(connection, seed.document_id)
    first = await read_node(connection, NodeType.AUTHOR, "Victor Zumrutyan")
    vector = [1.0] + [0.0] * 1023
    await connection.execute(SET_EMBEDDING, {"id": first[0], "vector": vector})

    await add_block(connection, await add_page(connection, seed, 2), mention, 1)
    await extract_source_entities(connection, seed.document_id)

    assert await read_node(connection, NodeType.AUTHOR, "Victor Zümrütyan") is None
    merged = await read_node(connection, NodeType.AUTHOR, "Victor Zumrutyan")
    assert merged[0] == first[0]
    assert merged[2:] == ("Fransız romancı.", "Victor Zumrutyan Fransız romancı.", True)


@pytest.mark.asyncio
async def test_similar_spelling_opens_published_note_and_one_merge_review(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Benzer yazım yeni yayında not açar ve benzer notu gösteren tek NAME_MERGE kaydı düşer."""
    fake = use_results(monkeypatch, {})
    await add_block(connection, seed, "*İnce Zümrüt* (Orhan Zumrutkemaloglu)", 1)
    await add_block(connection, seed, "*Zümrüt Yolu* (Orhan Zumrutkemal) da okundu.", 2)

    await extract_source_entities(connection, seed.document_id)
    await extract_source_entities(connection, seed.document_id)

    assert len(fake.pages) == 1
    original = await read_node(connection, NodeType.AUTHOR, "Orhan Zumrutkemaloglu")
    added = await read_node(connection, NodeType.AUTHOR, "Orhan Zumrutkemal")
    assert (original[1], added[1]) == ("PUBLISHED", "PUBLISHED")
    names = ["Orhan Zumrutkemaloglu", "Orhan Zumrutkemal"]
    reviews = await fetch_rows(connection, READ_REVIEWS, {"names": names})
    assert [(reason, name) for reason, name, _ in reviews] == [("NAME_MERGE", "Orhan Zumrutkemal")]
    assert reviews[0][2]["candidateNodeId"] == original[0]
    assert reviews[0][2]["score"] >= 80
    counts = await fetch_rows(connection, READ_ALIAS_COUNTS, {"names": names})
    assert counts == [("Orhan Zumrutkemal", 1), ("Orhan Zumrutkemaloglu", 1)]


@pytest.mark.asyncio
async def test_page_without_links_is_marked_and_not_sent_again(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sonucu boş sayfa da işaretlenir; adım tekrar çalışınca modele ikinci kez gitmez."""
    fake = use_results(monkeypatch, {})
    await add_block(connection, seed, "Bu paragrafta ad geçmez.", 1)

    await extract_source_entities(connection, seed.document_id)
    await extract_source_entities(connection, seed.document_id)

    assert fake.pages == [["Bu paragrafta ad geçmez."]]
    assert await fetch_rows(connection, READ_PAGE_MARK, {"id": seed.page_id}) == [(True,)]


@pytest.mark.asyncio
async def test_link_citing_block_outside_page_is_dropped(
    connection: Connection, seed: Seed, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Modelin sayfada olmayan paragrafa dayandırdığı bağ ve yalnız ona bağlı notlar yazılmaz."""
    text = "Zümrüt Ağa bir tarihî romandır."
    outside = PageEdge(
        from_type=NodeType.WORK,
        from_name="Zümrüt Ağa",
        relation=Relation.HAS_GENRE,
        to_type=NodeType.GENRE,
        to_name="tarihî roman",
        block_id=-1,
    )
    use_results(monkeypatch, {}, extra_edges=[outside])
    block_id = await add_block(connection, seed, text, 1)

    await extract_source_entities(connection, seed.document_id)

    assert await fetch_rows(connection, READ_EDGES, {"ids": [block_id]}) == []
    assert await read_node(connection, NodeType.WORK, "Zümrüt Ağa") is None


@pytest.mark.asyncio
async def test_saving_same_extraction_twice_adds_no_copies(
    connection: Connection, seed: Seed
) -> None:
    """Aynı paragrafın çıkarımı ikinci kez yazılınca not, yazım ve bağ kopyalanmaz."""
    block_id = await add_block(connection, seed, NOVEL, 1)
    extraction = check_evidence(novel_extraction(), NOVEL)

    first = await save_extraction(connection, block_id, extraction)
    second = await save_extraction(connection, block_id, extraction)

    assert (first, second) == (2, 0)
    edges = await fetch_rows(connection, READ_EDGES, {"ids": [block_id]})
    assert [row[1] for row in edges] == ["HAS_GENRE", "IN_PERIOD"]
    names = ["Zümrüt Ağa", "tarihî roman", "Cumhuriyet Dönemi"]
    counts = await fetch_rows(connection, READ_ALIAS_COUNTS, {"names": names})
    assert [count for _, count in counts] == [1, 1, 1]


@pytest.mark.asyncio
async def test_open_merge_review_is_not_opened_twice(connection: Connection, seed: Seed) -> None:
    """Açık NAME_MERGE incelemesi varken aynı not için ikinci kayıt açılmaz."""
    block_id = await add_block(connection, seed, NOVEL, 1)
    await save_extraction(connection, block_id, check_evidence(novel_extraction(), NOVEL))
    work = await read_node(connection, NodeType.WORK, "Zümrüt Ağa")
    genre = await read_node(connection, NodeType.GENRE, "tarihî roman")

    await open_node_review(connection, work[0], genre[0], 85.0)
    await open_node_review(connection, work[0], genre[0], 85.0)

    reviews = await fetch_rows(connection, READ_REVIEWS, {"names": ["Zümrüt Ağa"]})
    assert [(reason, name) for reason, name, _ in reviews] == [("NAME_MERGE", "Zümrüt Ağa")]
