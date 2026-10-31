"""Vektör araması: sorgu vektörüne kosinüs uzaklığı en küçük ilk kayıtlar (plan 13.11).

Her hedef tablonun kendi sorgusu vardır. Embedding'i henüz hesaplanmamış kayıt atlanır.
content_block ve knowledge_node'da sadece PUBLISHED kayıt döner. HNSW filtreyi taramadan sonra
uyguladığı için hnsw.iterative_scan açılır; dar filtrede de liste dolana kadar tarama sürer.
Skor kosinüs uzaklığıdır; küçük olan önce gelir.
"""

from pgvector import Vector
from psycopg import AsyncConnection

from app.constants import SEARCH_CANDIDATE_LIMIT
from app.schemas.search import SearchFilters, SearchHit, SearchTarget

ENABLE_ITERATIVE_SCAN = "SET LOCAL hnsw.iterative_scan = strict_order"

CONTENT_BLOCK_QUERY = """
SELECT id, search_text, embedding <=> %(embedding)s AS distance
FROM content_block
WHERE embedding IS NOT NULL
    AND status = 'PUBLISHED'
    AND (%(curriculum_unit_id)s::bigint IS NULL OR curriculum_unit_id = %(curriculum_unit_id)s)
    AND (%(learning_outcome_ids)s::bigint[] IS NULL OR EXISTS (
        SELECT 1
        FROM content_block_outcome
        WHERE content_block_outcome.content_block_id = content_block.id
            AND content_block_outcome.learning_outcome_id = ANY(%(learning_outcome_ids)s)
    ))
ORDER BY distance
LIMIT %(limit)s
"""

LEARNING_OUTCOME_QUERY = """
SELECT id, search_text, embedding <=> %(embedding)s AS distance
FROM learning_outcome
WHERE embedding IS NOT NULL
    AND (%(curriculum_unit_id)s::bigint IS NULL OR EXISTS (
        SELECT 1
        FROM curriculum_unit_outcome
        WHERE curriculum_unit_outcome.learning_outcome_id = learning_outcome.id
            AND curriculum_unit_outcome.curriculum_unit_id = %(curriculum_unit_id)s
    ))
    AND (%(learning_outcome_ids)s::bigint[] IS NULL OR id = ANY(%(learning_outcome_ids)s))
ORDER BY distance
LIMIT %(limit)s
"""

KNOWLEDGE_NODE_QUERY = """
SELECT id, search_text, embedding <=> %(embedding)s AS distance
FROM knowledge_node
WHERE embedding IS NOT NULL AND status = 'PUBLISHED'
ORDER BY distance
LIMIT %(limit)s
"""

QUERIES = {
    SearchTarget.CONTENT_BLOCK: CONTENT_BLOCK_QUERY,
    SearchTarget.LEARNING_OUTCOME: LEARNING_OUTCOME_QUERY,
    SearchTarget.KNOWLEDGE_NODE: KNOWLEDGE_NODE_QUERY,
}


async def search_vector(
    connection: AsyncConnection, embedding: list[float], filters: SearchFilters
) -> list[SearchHit]:
    """Sorgu vektörüne en yakın ilk kayıtları uzaklık sırasıyla döner."""
    values = {
        "embedding": Vector(embedding),
        "curriculum_unit_id": filters.curriculum_unit_id,
        "learning_outcome_ids": filters.learning_outcome_ids,
        "limit": SEARCH_CANDIDATE_LIMIT,
    }
    async with connection.transaction():
        await connection.execute(ENABLE_ITERATIVE_SCAN)
        cursor = await connection.execute(QUERIES[filters.target], values)
        rows = await cursor.fetchall()
    return [SearchHit(id=row[0], text=row[1], score=row[2]) for row in rows]
