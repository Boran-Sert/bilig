"""İndeksleme adımının sorguları (hazırlık hattı A9, INDEX).

Kaynağın vektörü olmayan blokları ve soruları okunur, vektörleri yazılır. Kazanım eşleştirmenin
aldığı içerik alınır: BILGI, ALINTI ve METIN blokları ile sorular; reddedilen içerik alınmaz.
Vektörü olan içerik okunmaz, böylece adım tekrar çalışınca model ikinci kez çalışmaz. Tablolar
core'un Flyway migration'larıyla kurulur.
"""

from typing import LiteralString

from pgvector import Vector
from psycopg import AsyncConnection

from app.schemas.question import QuestionContent

SELECT_BLOCKS_WITHOUT_EMBEDDING = """
SELECT content_block.id, content_block.search_text
FROM content_block
JOIN source_page ON source_page.id = content_block.source_page_id
WHERE source_page.source_document_id = %(source_id)s
    AND content_block.block_type IN ('BILGI', 'ALINTI', 'METIN')
    AND content_block.status <> 'REJECTED'
    AND content_block.embedding IS NULL
ORDER BY content_block.id
"""

SELECT_QUESTIONS_WITHOUT_EMBEDDING = """
SELECT question.id, question.content
FROM question
JOIN source_page ON source_page.id = question.source_page_id
WHERE source_page.source_document_id = %(source_id)s
    AND question.status <> 'REJECTED'
    AND question.embedding IS NULL
ORDER BY question.id
"""

UPDATE_BLOCK_EMBEDDING = "UPDATE content_block SET embedding = %(embedding)s WHERE id = %(id)s"

UPDATE_QUESTION_EMBEDDING = "UPDATE question SET embedding = %(embedding)s WHERE id = %(id)s"


async def fetch_blocks_without_embedding(
    connection: AsyncConnection, source_id: int
) -> list[tuple[int, str]]:
    """Kaynağın vektörü olmayan bloklarının kimliğini ve arama metnini döner."""
    cursor = await connection.execute(SELECT_BLOCKS_WITHOUT_EMBEDDING, {"source_id": source_id})
    return [(row[0], row[1]) for row in await cursor.fetchall()]


async def fetch_questions_without_embedding(
    connection: AsyncConnection, source_id: int
) -> list[tuple[int, str]]:
    """Kaynağın vektörü olmayan sorularının kimliğini ve düz metnini döner."""
    cursor = await connection.execute(SELECT_QUESTIONS_WITHOUT_EMBEDDING, {"source_id": source_id})
    return [
        (row[0], QuestionContent.model_validate(row[1]).to_text())
        for row in await cursor.fetchall()
    ]


async def save_block_embeddings(
    connection: AsyncConnection, embeddings: list[tuple[int, list[float]]]
) -> None:
    """Blokların vektörlerini yazar."""
    await _save(connection, UPDATE_BLOCK_EMBEDDING, embeddings)


async def save_question_embeddings(
    connection: AsyncConnection, embeddings: list[tuple[int, list[float]]]
) -> None:
    """Soruların vektörlerini yazar."""
    await _save(connection, UPDATE_QUESTION_EMBEDDING, embeddings)


async def _save(
    connection: AsyncConnection, query: LiteralString, embeddings: list[tuple[int, list[float]]]
) -> None:
    """Verilen güncelleme sorgusunu her kimlik ve vektör için çalıştırır."""
    async with connection.cursor() as cursor:
        await cursor.executemany(
            query, [{"id": item_id, "embedding": Vector(vector)} for item_id, vector in embeddings]
        )
