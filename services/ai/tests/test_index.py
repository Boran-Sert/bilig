"""İndeksleme adımını sahte embedding ve gerçek Postgres'le test eder (A9).

Sahte embedding aldığı metinleri kaydeder ve her metne aynı vektörü verir; model yüklenmez.
Testler kendi kaynak, sayfa, blok ve soru satırlarını yazar; her şey test bitince geri alınır.
"""

from pathlib import Path

import pytest
import pytest_asyncio
from pgvector.psycopg import register_vector_async
from psycopg.types.json import Jsonb

from app.ingest import index
from app.ingest.index import index_source
from app.schemas.question import Block, QuestionContent, QuestionOption
from tests.test_pipeline import make_context, make_source
from tests.test_postgres_queue import Connection

DIMENSIONS = 1024

INSERT_PAGE = """
INSERT INTO source_page (source_document_id, page_no) VALUES (%s, 1) RETURNING id
"""

INSERT_BLOCK = """
INSERT INTO content_block (source_page_id, block_type, position, title_path, markdown,
    search_text, status)
VALUES (%s, %s, %s, '', %s, %s, %s)
RETURNING id
"""

INSERT_QUESTION = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('INDEKS', 'İndeks Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'İndeks Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), unit_row AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT id, 12, 1, 'Roman' FROM curriculum_row
    RETURNING id
)
INSERT INTO question (source_page_id, curriculum_unit_id, origin, content, correct_option,
    content_hash)
SELECT %s, id, 'SOURCE', %s, 'A', repeat('c', 64) FROM unit_row
RETURNING id
"""

READ_EMBEDDED = """
SELECT id FROM content_block WHERE source_page_id = %(page_id)s AND embedding IS NOT NULL
UNION ALL
SELECT id FROM question WHERE source_page_id = %(page_id)s AND embedding IS NOT NULL
ORDER BY id
"""

QUESTION = QuestionContent(
    passage=[Block(type="paragraph", md="Ortak parça")],
    stem=[Block(type="paragraph", md="Hangisi doğrudur?")],
    options=[
        QuestionOption(label=label, blocks=[Block(type="paragraph", md=f"Şık {label}")])
        for label in "ABCDE"
    ],
)


class FakeEmbedding:
    """Aldığı metinleri kaydeden ve her metne aynı vektörü veren embedding."""

    def __init__(self) -> None:
        """Kayıt listesini kurar."""
        self.texts: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Metinleri kaydeder ve her biri için ilk boyutu 1 olan vektör döner."""
        self.texts.extend(texts)
        return [[1.0] + [0.0] * (DIMENSIONS - 1) for _ in texts]


@pytest_asyncio.fixture
async def connection(db: Connection) -> Connection:
    """Test bağlantısına vector tipini tanıtır."""
    await register_vector_async(db)
    return db


@pytest.fixture
def embedding(monkeypatch: pytest.MonkeyPatch) -> FakeEmbedding:
    """Adımın modelini sahte embedding'le değiştirir."""
    fake = FakeEmbedding()
    monkeypatch.setattr(index, "get_embedding_provider", lambda: fake)
    return fake


async def add_block(
    db: Connection, page_id: int, block_type: str, position: int, status: str = "DRAFT"
) -> int:
    """Sayfaya verilen tür ve durumda blok ekler; arama metni türü ve sırasıdır."""
    text = f"{block_type} {position}"
    cursor = await db.execute(INSERT_BLOCK, (page_id, block_type, position, text, text, status))
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def seed(db: Connection) -> tuple[int, int, list[int], int]:
    """Kaynağı, sayfasını, indekslenecek iki bloğu ve bir soruyu ekler."""
    source_id = await make_source(db)
    cursor = await db.execute(INSERT_PAGE, (source_id,))
    row = await cursor.fetchone()
    assert row is not None
    page_id = int(row[0])
    blocks = [await add_block(db, page_id, "BILGI", 0), await add_block(db, page_id, "METIN", 1)]
    cursor = await db.execute(INSERT_QUESTION, (page_id, Jsonb(QUESTION.model_dump(mode="json"))))
    row = await cursor.fetchone()
    assert row is not None
    return source_id, page_id, blocks, int(row[0])


@pytest.mark.asyncio
async def test_index_writes_vectors_of_blocks_and_questions(
    connection: Connection, tmp_path: Path, embedding: FakeEmbedding
) -> None:
    """Blok arama metninden, soru ortak parça, kök ve şıklarından vektöre çevrilir."""
    source_id, page_id, blocks, question_id = await seed(connection)

    await index_source(source_id, make_context(connection, tmp_path))

    assert embedding.texts == ["BILGI 0", "METIN 1", QUESTION.to_text()]
    cursor = await connection.execute(READ_EMBEDDED, {"page_id": page_id})
    assert [row[0] for row in await cursor.fetchall()] == sorted([*blocks, question_id])


@pytest.mark.asyncio
async def test_index_skips_headings_and_rejected_content(
    connection: Connection, tmp_path: Path, embedding: FakeEmbedding
) -> None:
    """Başlık bloğu ve reddedilen içerik indekslenmez."""
    source_id, page_id, blocks, question_id = await seed(connection)
    await add_block(connection, page_id, "BASLIK", 2)
    await add_block(connection, page_id, "METIN", 3, status="REJECTED")

    await index_source(source_id, make_context(connection, tmp_path))

    cursor = await connection.execute(READ_EMBEDDED, {"page_id": page_id})
    assert [row[0] for row in await cursor.fetchall()] == sorted([*blocks, question_id])


@pytest.mark.asyncio
async def test_index_twice_does_not_encode_again(
    connection: Connection, tmp_path: Path, embedding: FakeEmbedding
) -> None:
    """Adım iki kez çalışınca vektörü olan içerik modele ikinci kez gitmez."""
    source_id, _, _, _ = await seed(connection)
    context = make_context(connection, tmp_path)

    await index_source(source_id, context)
    await index_source(source_id, context)

    assert len(embedding.texts) == 3


@pytest.mark.asyncio
async def test_index_without_content_does_not_load_model(
    connection: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İndekslenecek içerik yoksa model yüklenmez."""

    def fail() -> None:
        """Model yüklenmeye çalışılırsa testi düşürür."""
        raise AssertionError("model loaded")

    monkeypatch.setattr(index, "get_embedding_provider", fail)
    source_id = await make_source(connection)

    await index_source(source_id, make_context(connection, tmp_path))
