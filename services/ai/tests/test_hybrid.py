"""Ortak aramayı (vektör, BM25, RRF ve reranker) sahte embedding ve gerçek Postgres'le test eder.

Testler kendi ders, ünite, kaynak ve sayfa satırlarını yazar ve sonucu bunlarla sınırlar;
veritabanında gerçek içerik olsa da sonuç değişmez. Vektörler elle kurulan 1024 boyutlu
normalize vektörlerdir.
"""

import math
from typing import NamedTuple

import psycopg
import pytest
import pytest_asyncio
from pgvector import Vector
from pgvector.psycopg import register_vector_async
from psycopg.rows import TupleRow
from pydantic import ValidationError

from app.schemas.search import SearchFilters, SearchTarget
from app.search.vector import search_vector

Connection = psycopg.AsyncConnection[TupleRow]

DIMENSIONS = 1024

SEED = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('ARAMA', 'Arama Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Arama Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), group_row AS (
    INSERT INTO learning_outcome_group (curriculum_id, code, name)
    SELECT id, 'A.2', 'Öyküleyici' FROM curriculum_row
    RETURNING id
), unit_rows AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT curriculum_row.id, 12, unit.unit_no, unit.title
    FROM curriculum_row, (VALUES (1, 'Roman'), (2, 'Hikâye')) AS unit (unit_no, title)
    RETURNING id, unit_no
), user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Arama Testi' FROM tenant
    RETURNING id
), document_row AS (
    INSERT INTO source_document (title, sha256, file_path, uploaded_by)
    SELECT 'TDE 12 Ders Kitabı', repeat('a', 64), '/data/sources/0.pdf', id FROM user_row
    RETURNING id
), page_row AS (
    INSERT INTO source_page (source_document_id, page_no)
    SELECT id, 1 FROM document_row
    RETURNING id
)
SELECT group_row.id, roman.id, story.id, page_row.id
FROM group_row, page_row, unit_rows AS roman, unit_rows AS story
WHERE roman.unit_no = 1 AND story.unit_no = 2
"""

INSERT_BLOCK = """
INSERT INTO content_block (
    source_page_id, curriculum_unit_id, block_type, position, title_path, markdown, status,
    search_text, embedding
)
VALUES (
    %(page_id)s, %(unit_id)s, 'BILGI',
    (SELECT count(*) FROM content_block WHERE source_page_id = %(page_id)s),
    '', %(text)s, %(status)s, %(text)s, %(embedding)s
)
RETURNING id
"""

INSERT_OUTCOME = """
WITH outcome AS (
    INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text, embedding)
    VALUES (%(group_id)s, %(code)s, %(text)s, %(text)s, %(embedding)s)
    RETURNING id
), unit_link AS (
    INSERT INTO curriculum_unit_outcome (curriculum_unit_id, learning_outcome_id)
    SELECT %(unit_id)s, id FROM outcome
)
SELECT id FROM outcome
"""

INSERT_NODE = """
INSERT INTO knowledge_node (node_type, name, status, search_text, embedding)
VALUES ('CONCEPT', %(text)s, %(status)s, %(text)s, %(embedding)s)
RETURNING id
"""


class Seed(NamedTuple):
    """Testin kurduğu kazanım grubu, iki ünite ve sayfanın kimlikleri."""

    group_id: int
    unit_id: int
    other_unit_id: int
    page_id: int


def vector(*weights: float) -> list[float]:
    """İlk boyutları verilen ağırlıklarla, kalanı sıfır olan normalize vektör kurar."""
    norm = math.hypot(*weights)
    return [weight / norm for weight in weights] + [0.0] * (DIMENSIONS - len(weights))


@pytest_asyncio.fixture
async def connection(db: Connection) -> Connection:
    """Test bağlantısına vector tipini tanıtır."""
    await register_vector_async(db)
    return db


@pytest_asyncio.fixture
async def seed(connection: Connection) -> Seed:
    """Ders, program, kazanım grubu, iki ünite, kaynak ve sayfa yazar."""
    cursor = await connection.execute(SEED)
    row = await cursor.fetchone()
    assert row is not None
    return Seed(*row)


async def insert_returning_id(connection: Connection, query: str, values: dict[str, object]) -> int:
    """Ekleme sorgusunu çalıştırıp yeni kaydın kimliğini döner."""
    cursor = await connection.execute(query, values)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def add_block(
    connection: Connection,
    seed: Seed,
    unit_id: int,
    text: str,
    embedding: list[float] | None,
    status: str = "PUBLISHED",
) -> int:
    """Sayfanın sonuna blok yazar."""
    values = {
        "page_id": seed.page_id,
        "unit_id": unit_id,
        "text": text,
        "status": status,
        "embedding": Vector(embedding) if embedding else None,
    }
    return await insert_returning_id(connection, INSERT_BLOCK, values)


async def add_outcome(
    connection: Connection,
    seed: Seed,
    unit_id: int,
    code: str,
    text: str,
    embedding: list[float] | None,
) -> int:
    """Kazanımı yazar ve üniteye bağlar."""
    values = {
        "group_id": seed.group_id,
        "unit_id": unit_id,
        "code": code,
        "text": text,
        "embedding": Vector(embedding) if embedding else None,
    }
    return await insert_returning_id(connection, INSERT_OUTCOME, values)


async def link_block(connection: Connection, block_id: int, outcome_id: int) -> None:
    """Bloğu kazanıma bağlar."""
    await connection.execute(
        "INSERT INTO content_block_outcome (content_block_id, learning_outcome_id, mapped_by)"
        " VALUES (%s, %s, 'HUMAN')",
        (block_id, outcome_id),
    )


async def add_node(
    connection: Connection, text: str, embedding: list[float], status: str = "PUBLISHED"
) -> int:
    """Bilgi düğümü yazar."""
    values = {"text": text, "status": status, "embedding": Vector(embedding)}
    return await insert_returning_id(connection, INSERT_NODE, values)


def test_knowledge_node_search_rejects_filters() -> None:
    """knowledge_node aramasına verilen ünite filtresi reddedilir."""
    with pytest.raises(ValidationError):
        SearchFilters(target=SearchTarget.KNOWLEDGE_NODE, curriculum_unit_id=1)


@pytest.mark.asyncio
async def test_vector_search_orders_by_distance_and_skips_missing_embedding(
    connection: Connection, seed: Seed
) -> None:
    """Bloklar sorgu vektörüne uzaklık sırasıyla döner; vektörü olmayan blok dönmez."""
    far = await add_block(connection, seed, seed.unit_id, "uzak", vector(0, 1))
    middle = await add_block(connection, seed, seed.unit_id, "orta", vector(1, 1))
    near = await add_block(connection, seed, seed.unit_id, "yakın", vector(1, 0))
    await add_block(connection, seed, seed.unit_id, "vektörsüz", None)
    filters = SearchFilters(target=SearchTarget.CONTENT_BLOCK, curriculum_unit_id=seed.unit_id)

    hits = await search_vector(connection, vector(1, 0), filters)

    assert [hit.id for hit in hits] == [near, middle, far]
    assert hits[0].score < hits[1].score < hits[2].score


@pytest.mark.asyncio
async def test_vector_search_returns_only_published_blocks_inside_filters(
    connection: Connection, seed: Seed
) -> None:
    """Taslak, başka ünitedeki ve kazanıma bağlı olmayan blok, vektörü aynı olsa da dönmez."""
    query = vector(1, 0)
    outcome = await add_outcome(connection, seed, seed.unit_id, "A.2.1", "kazanım", None)
    linked = await add_block(connection, seed, seed.unit_id, "bağlı", query)
    draft = await add_block(connection, seed, seed.unit_id, "taslak", query, status="DRAFT")
    other_unit = await add_block(connection, seed, seed.other_unit_id, "başka ünite", query)
    await add_block(connection, seed, seed.unit_id, "bağsız", query)
    for block_id in (linked, draft, other_unit):
        await link_block(connection, block_id, outcome)
    filters = SearchFilters(
        target=SearchTarget.CONTENT_BLOCK,
        curriculum_unit_id=seed.unit_id,
        learning_outcome_ids=[outcome],
    )

    hits = await search_vector(connection, query, filters)

    assert [hit.id for hit in hits] == [linked]


@pytest.mark.asyncio
async def test_vector_search_returns_learning_outcomes_of_unit(
    connection: Connection, seed: Seed
) -> None:
    """Kazanım araması ünite filtresiyle sadece o ünitenin kazanımlarını döner."""
    query = vector(1, 0)
    inside = await add_outcome(connection, seed, seed.unit_id, "A.2.1", "roman", query)
    await add_outcome(connection, seed, seed.other_unit_id, "A.2.2", "hikâye", query)
    filters = SearchFilters(target=SearchTarget.LEARNING_OUTCOME, curriculum_unit_id=seed.unit_id)

    hits = await search_vector(connection, query, filters)

    assert [hit.id for hit in hits] == [inside]


@pytest.mark.asyncio
async def test_vector_search_skips_draft_knowledge_nodes(connection: Connection) -> None:
    """Taslak bilgi düğümü vektörü aynı olsa da dönmez."""
    published = await add_node(connection, "Arama Testi Yayında", vector(1, 0))
    draft = await add_node(connection, "Arama Testi Taslak", vector(1, 0), status="DRAFT")

    hits = await search_vector(
        connection, vector(1, 0), SearchFilters(target=SearchTarget.KNOWLEDGE_NODE)
    )

    ids = [hit.id for hit in hits]
    assert published in ids
    assert draft not in ids
