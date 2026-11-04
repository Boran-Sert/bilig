"""Yüklenen kaynağın durumunu ve sayfa kayıtlarını yazan sorgular (hazırlık hattı).

Sayfa kaydı (source_document_id, page_no) anahtarıyla upsert edilir; adım tekrar çalışınca kopya
satır oluşmaz, görüntü yolu güncellenir. İş başlarken PROCESSING, son denemedeki hatada FAILED
yazılır. Bütün adımlar bitince kaynağın, sorularının ya da bloklarının açık inceleme kaydı varsa
REVIEW, yoksa PUBLISHED yazılır. Tablolar core'un Flyway migration'larıyla kurulur.
"""

from psycopg import AsyncConnection

UPSERT_SOURCE_PAGE = """
INSERT INTO source_page (source_document_id, page_no, image_path)
VALUES (%(source_id)s, %(page_no)s, %(image_path)s)
ON CONFLICT (source_document_id, page_no) DO UPDATE SET image_path = EXCLUDED.image_path
"""

SELECT_PAGE_IDS = """
SELECT page_no, id FROM source_page WHERE source_document_id = %(source_id)s
"""

SELECT_SOURCE_TITLE = "SELECT title FROM source_document WHERE id = %(source_id)s"

SELECT_SOURCE_KIND = "SELECT kind FROM source_document WHERE id = %(source_id)s"

SET_SOURCE_STATUS = """
UPDATE source_document
SET status = %(status)s, updated_at = now()
WHERE id = %(source_id)s
"""

SET_FINISHED_STATUS = """
UPDATE source_document
SET status = CASE
        WHEN EXISTS (
            SELECT 1
            FROM review_item
            WHERE review_item.status = 'OPEN'
                AND (
                    review_item.source_document_id = source_document.id
                    OR review_item.question_id IN (
                        SELECT question.id
                        FROM question
                        JOIN source_page ON source_page.id = question.source_page_id
                        WHERE source_page.source_document_id = source_document.id
                    )
                    OR review_item.content_block_id IN (
                        SELECT content_block.id
                        FROM content_block
                        JOIN source_page ON source_page.id = content_block.source_page_id
                        WHERE source_page.source_document_id = source_document.id
                    )
                )
        ) THEN 'REVIEW'
        ELSE 'PUBLISHED'
    END,
    updated_at = now()
WHERE id = %(source_id)s
"""


async def save_source_pages(
    connection: AsyncConnection, source_id: int, image_paths: list[str]
) -> None:
    """Sayfaların kayıtlarını tek seferde ekler; varsa görüntü yollarını günceller."""
    async with connection.cursor() as cursor:
        await cursor.executemany(
            UPSERT_SOURCE_PAGE,
            [
                {"source_id": source_id, "page_no": page_no, "image_path": image_path}
                for page_no, image_path in enumerate(image_paths, start=1)
            ],
        )


async def fetch_page_ids(connection: AsyncConnection, source_id: int) -> dict[int, int]:
    """Kaynağın sayfa numaralarını sayfa kayıtlarının kimliğine eşler."""
    cursor = await connection.execute(SELECT_PAGE_IDS, {"source_id": source_id})
    return {int(page_no): int(page_id) for page_no, page_id in await cursor.fetchall()}


async def fetch_source_title(connection: AsyncConnection, source_id: int) -> str:
    """Kaynağın başlığını verir; kaynak yoksa LookupError fırlatır."""
    cursor = await connection.execute(SELECT_SOURCE_TITLE, {"source_id": source_id})
    row = await cursor.fetchone()
    if row is None:
        raise LookupError(f"Source {source_id} not found")
    return str(row[0])


async def fetch_source_kind(connection: AsyncConnection, source_id: int) -> str:
    """Kaynağın türünü verir; kaynak yoksa LookupError fırlatır."""
    cursor = await connection.execute(SELECT_SOURCE_KIND, {"source_id": source_id})
    row = await cursor.fetchone()
    if row is None:
        raise LookupError(f"Source {source_id} not found")
    return str(row[0])


async def mark_processing(connection: AsyncConnection, source_id: int) -> None:
    """Kaynağı PROCESSING yapar."""
    await connection.execute(SET_SOURCE_STATUS, {"source_id": source_id, "status": "PROCESSING"})


async def mark_failed(connection: AsyncConnection, source_id: int) -> None:
    """Kaynağı FAILED yapar."""
    await connection.execute(SET_SOURCE_STATUS, {"source_id": source_id, "status": "FAILED"})


async def mark_finished(connection: AsyncConnection, source_id: int) -> None:
    """Kaynağın açık inceleme kaydı varsa REVIEW, yoksa PUBLISHED yapar."""
    await connection.execute(SET_FINISHED_STATUS, {"source_id": source_id})
