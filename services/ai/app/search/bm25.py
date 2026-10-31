"""BM25 araması: sorgu kelimeleriyle en iyi eşleşen ilk kayıtlar (plan 13.11).

pg_textsearch arama metnini Türkçe kök bulmayla puanlar; puan negatiftir, küçük olan önce gelir.
Sorgu parametreyle gittiği için index adı to_bm25query'de açıkça verilir; verilmezse eklenti
index'i bulamaz. Filtre varken Postgres tam taramaya geçebilir ve kelimesi geçmeyen satıra 0 puan
verir; bu yüzden sadece puanı sıfırdan küçük satırlar alınır. content_block ve knowledge_node'da
sadece PUBLISHED kayıt döner.
"""

from psycopg import AsyncConnection

from app.constants import SEARCH_CANDIDATE_LIMIT
from app.schemas.search import SearchFilters, SearchHit, SearchTarget

CONTENT_BLOCK_QUERY = """
SELECT id, search_text,
    search_text <@> to_bm25query(%(query)s, 'idx_content_block_bm25') AS score
FROM content_block
WHERE status = 'PUBLISHED'
    AND search_text <@> to_bm25query(%(query)s, 'idx_content_block_bm25') < 0
    AND (%(curriculum_unit_id)s::bigint IS NULL OR curriculum_unit_id = %(curriculum_unit_id)s)
    AND (%(learning_outcome_ids)s::bigint[] IS NULL OR EXISTS (
        SELECT 1
        FROM content_block_outcome
        WHERE content_block_outcome.content_block_id = content_block.id
            AND content_block_outcome.learning_outcome_id = ANY(%(learning_outcome_ids)s)
    ))
ORDER BY score
LIMIT %(limit)s
"""

LEARNING_OUTCOME_QUERY = """
SELECT id, search_text,
    search_text <@> to_bm25query(%(query)s, 'idx_learning_outcome_bm25') AS score
FROM learning_outcome
WHERE search_text <@> to_bm25query(%(query)s, 'idx_learning_outcome_bm25') < 0
    AND (%(curriculum_unit_id)s::bigint IS NULL OR EXISTS (
        SELECT 1
        FROM curriculum_unit_outcome
        WHERE curriculum_unit_outcome.learning_outcome_id = learning_outcome.id
            AND curriculum_unit_outcome.curriculum_unit_id = %(curriculum_unit_id)s
    ))
    AND (%(learning_outcome_ids)s::bigint[] IS NULL OR id = ANY(%(learning_outcome_ids)s))
ORDER BY score
LIMIT %(limit)s
"""

KNOWLEDGE_NODE_QUERY = """
SELECT id, search_text,
    search_text <@> to_bm25query(%(query)s, 'idx_knowledge_node_bm25') AS score
FROM knowledge_node
WHERE status = 'PUBLISHED'
    AND search_text <@> to_bm25query(%(query)s, 'idx_knowledge_node_bm25') < 0
ORDER BY score
LIMIT %(limit)s
"""

QUERIES = {
    SearchTarget.CONTENT_BLOCK: CONTENT_BLOCK_QUERY,
    SearchTarget.LEARNING_OUTCOME: LEARNING_OUTCOME_QUERY,
    SearchTarget.KNOWLEDGE_NODE: KNOWLEDGE_NODE_QUERY,
}


async def search_bm25(
    connection: AsyncConnection, query: str, filters: SearchFilters
) -> list[SearchHit]:
    """Sorgu kelimeleriyle en iyi eşleşen ilk kayıtları puan sırasıyla döner."""
    values = {
        "query": query,
        "curriculum_unit_id": filters.curriculum_unit_id,
        "learning_outcome_ids": filters.learning_outcome_ids,
        "limit": SEARCH_CANDIDATE_LIMIT,
    }
    cursor = await connection.execute(QUERIES[filters.target], values)
    rows = await cursor.fetchall()
    return [SearchHit(id=row[0], text=row[1], score=row[2]) for row in rows]
