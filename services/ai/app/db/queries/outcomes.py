"""Kazanım eşleştirme adımının sorguları (hazırlık hattı A8).

Kaynağın eşlenmemiş soruları ve paragrafları okunur: kazanım bağı ya da LOW_CONFIDENCE inceleme
kaydı olan içerik eşlenmiş sayılır. Etkinlik ve başlık blokları eşlenmez. Bağlar MODEL olarak
yazılır; aynı bağ ve aynı inceleme kaydı ikinci kez eklenmez. İncelemeye düşmeyen taslak
içerik yayına alınır. Vektörü olmayan kazanımlar da
buradan okunup yazılır. Tablolar core'un Flyway migration'larıyla kurulur.
"""

from pgvector import Vector
from psycopg import AsyncConnection

from app.schemas.outcome_match import ItemKind, MatchItem, OutcomeCandidate
from app.schemas.question import QuestionContent

SELECT_OUTCOMES_WITHOUT_EMBEDDING = """
SELECT id, search_text FROM learning_outcome WHERE embedding IS NULL ORDER BY id
"""

UPDATE_OUTCOME_EMBEDDING = """
UPDATE learning_outcome SET embedding = %(embedding)s WHERE id = %(id)s
"""

SELECT_CANDIDATES = """
SELECT id, code, title, meb_explanation FROM learning_outcome WHERE id = ANY(%(ids)s)
"""

SELECT_UNMATCHED_QUESTIONS = """
SELECT question.id, question.content, question.correct_option, question.curriculum_unit_id
FROM question
JOIN source_page ON source_page.id = question.source_page_id
WHERE source_page.source_document_id = %(source_document_id)s
    AND question.status <> 'REJECTED'
    AND NOT EXISTS (
        SELECT 1 FROM question_outcome WHERE question_outcome.question_id = question.id
    )
    AND NOT EXISTS (
        SELECT 1
        FROM review_item
        WHERE review_item.question_id = question.id AND review_item.reason = 'LOW_CONFIDENCE'
    )
ORDER BY question.id
"""

SELECT_UNMATCHED_BLOCKS = """
SELECT content_block.id, content_block.search_text, content_block.curriculum_unit_id
FROM content_block
JOIN source_page ON source_page.id = content_block.source_page_id
WHERE source_page.source_document_id = %(source_document_id)s
    AND content_block.block_type IN ('BILGI', 'ALINTI', 'METIN')
    AND content_block.status <> 'REJECTED'
    AND NOT EXISTS (
        SELECT 1
        FROM content_block_outcome
        WHERE content_block_outcome.content_block_id = content_block.id
    )
    AND NOT EXISTS (
        SELECT 1
        FROM review_item
        WHERE review_item.content_block_id = content_block.id
            AND review_item.reason = 'LOW_CONFIDENCE'
    )
ORDER BY content_block.id
"""

INSERT_LINKS = {
    ItemKind.QUESTION: """
INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
SELECT %(item_id)s, outcome_id, 'MODEL' FROM unnest(%(outcome_ids)s::bigint[]) AS outcome_id
ON CONFLICT DO NOTHING
""",
    ItemKind.PARAGRAPH: """
INSERT INTO content_block_outcome (content_block_id, learning_outcome_id, mapped_by)
SELECT %(item_id)s, outcome_id, 'MODEL' FROM unnest(%(outcome_ids)s::bigint[]) AS outcome_id
ON CONFLICT DO NOTHING
""",
}

PUBLISH_ITEMS = {
    ItemKind.QUESTION: """
UPDATE question SET status = 'PUBLISHED', updated_at = now()
WHERE id = %(item_id)s AND status = 'DRAFT'
""",
    ItemKind.PARAGRAPH: """
UPDATE content_block SET status = 'PUBLISHED', updated_at = now()
WHERE id = %(item_id)s AND status = 'DRAFT'
""",
}

INSERT_REVIEWS = {
    ItemKind.QUESTION: """
INSERT INTO review_item (reason, question_id)
SELECT 'LOW_CONFIDENCE', %(item_id)s
WHERE NOT EXISTS (
    SELECT 1 FROM review_item
    WHERE question_id = %(item_id)s AND reason = 'LOW_CONFIDENCE' AND status = 'OPEN'
)
""",
    ItemKind.PARAGRAPH: """
INSERT INTO review_item (reason, content_block_id)
SELECT 'LOW_CONFIDENCE', %(item_id)s
WHERE NOT EXISTS (
    SELECT 1 FROM review_item
    WHERE content_block_id = %(item_id)s AND reason = 'LOW_CONFIDENCE' AND status = 'OPEN'
)
""",
}


async def fetch_outcomes_without_embedding(connection: AsyncConnection) -> list[tuple[int, str]]:
    """Vektörü olmayan kazanımların kimliğini ve arama metnini döner."""
    cursor = await connection.execute(SELECT_OUTCOMES_WITHOUT_EMBEDDING)
    return [(row[0], row[1]) for row in await cursor.fetchall()]


async def save_outcome_embeddings(
    connection: AsyncConnection, embeddings: list[tuple[int, list[float]]]
) -> None:
    """Kazanımların vektörlerini yazar."""
    async with connection.cursor() as cursor:
        await cursor.executemany(
            UPDATE_OUTCOME_EMBEDDING,
            [{"id": outcome_id, "embedding": Vector(vector)} for outcome_id, vector in embeddings],
        )


async def fetch_candidates(connection: AsyncConnection, ids: list[int]) -> list[OutcomeCandidate]:
    """Kazanımları verilen kimlik sırasıyla döner."""
    cursor = await connection.execute(SELECT_CANDIDATES, {"ids": ids})
    found = {
        row[0]: OutcomeCandidate(id=row[0], code=row[1], title=row[2], meb_explanation=row[3])
        for row in await cursor.fetchall()
    }
    return [found[outcome_id] for outcome_id in ids]


async def fetch_unmatched_items(
    connection: AsyncConnection, source_document_id: int
) -> list[tuple[int, MatchItem]]:
    """Kaynağın eşlenmemiş sorularını ve paragraflarını kimlikleriyle döner."""
    values = {"source_document_id": source_document_id}
    cursor = await connection.execute(SELECT_UNMATCHED_QUESTIONS, values)
    questions = [
        (row[0], question_item(QuestionContent.model_validate(row[1]), row[2], row[3]))
        for row in await cursor.fetchall()
    ]
    cursor = await connection.execute(SELECT_UNMATCHED_BLOCKS, values)
    blocks = [
        (row[0], MatchItem(kind=ItemKind.PARAGRAPH, text=row[1], curriculum_unit_id=row[2]))
        for row in await cursor.fetchall()
    ]
    return questions + blocks


def question_item(
    content: QuestionContent, correct_option: str, curriculum_unit_id: int | None
) -> MatchItem:
    """Sorunun ortak parçası, kökü ve şıklarından eşleştirme metnini kurar."""
    return MatchItem(
        kind=ItemKind.QUESTION,
        text=content.to_text(),
        curriculum_unit_id=curriculum_unit_id,
        correct_option=correct_option,
    )


async def save_links(
    connection: AsyncConnection, kind: ItemKind, item_id: int, outcome_ids: list[int]
) -> None:
    """İçeriği kazanımlara MODEL olarak bağlar; var olan bağı tekrar eklemez."""
    values = {"item_id": item_id, "outcome_ids": outcome_ids}
    await connection.execute(INSERT_LINKS[kind], values)


async def publish_item(connection: AsyncConnection, kind: ItemKind, item_id: int) -> None:
    """Taslak durumdaki içeriği yayına alır."""
    await connection.execute(PUBLISH_ITEMS[kind], {"item_id": item_id})


async def open_review(connection: AsyncConnection, kind: ItemKind, item_id: int) -> None:
    """İçerik için açık LOW_CONFIDENCE inceleme kaydı yoksa açar."""
    await connection.execute(INSERT_REVIEWS[kind], {"item_id": item_id})
