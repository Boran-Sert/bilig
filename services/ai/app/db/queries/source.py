"""Yüklenen kaynağın durumunu ve sayfa kayıtlarını yazan sorgular (hazırlık hattı).

Sayfa kaydı (source_document_id, page_no) anahtarıyla upsert edilir; adım tekrar çalışınca kopya
satır oluşmaz, görüntü yolu güncellenir. Durum sadece PROCESSING ve FAILED yazılır: PUBLISHED'ı
içerik bazında yayın kuralı belirler. Tablolar core'un Flyway migration'larıyla kurulur.
"""

from psycopg import AsyncConnection

UPSERT_SOURCE_PAGE = """
INSERT INTO source_page (source_document_id, page_no, image_path)
VALUES (%(source_id)s, %(page_no)s, %(image_path)s)
ON CONFLICT (source_document_id, page_no) DO UPDATE SET image_path = EXCLUDED.image_path
"""

SET_SOURCE_STATUS = """
UPDATE source_document
SET status = %(status)s, updated_at = now()
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


async def mark_processing(connection: AsyncConnection, source_id: int) -> None:
    """Kaynağı PROCESSING yapar."""
    await connection.execute(SET_SOURCE_STATUS, {"source_id": source_id, "status": "PROCESSING"})


async def mark_failed(connection: AsyncConnection, source_id: int) -> None:
    """Kaynağı FAILED yapar."""
    await connection.execute(SET_SOURCE_STATUS, {"source_id": source_id, "status": "FAILED"})
