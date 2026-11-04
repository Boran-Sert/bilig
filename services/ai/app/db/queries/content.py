"""Ders kitabı bloklarını content_block tablosuna yazan sorgular (hazırlık hattı A5, #129).

Blok (source_page_id, position) anahtarıyla upsert edilir; adım tekrar çalışınca kopya satır
oluşmaz. Değişmeyen satıra dokunulmaz; arama metni değişen satırın embedding'i silinir. Durum
(status) ve kazanım bağları yazılmaz: onları sonraki adımlar ve inceleme belirler. Tablolar
core'un Flyway migration'larıyla kurulur.
"""

from collections.abc import Sequence

from psycopg import AsyncConnection

from app.schemas.textbook import TextbookBlock

SELECT_PAGE_IDS = """
SELECT page_no, id FROM source_page WHERE source_document_id = %(source_id)s
"""

UPSERT_CONTENT_BLOCK = """
INSERT INTO content_block (source_page_id, block_type, position, title_path, markdown, search_text)
VALUES (%(source_page_id)s, %(block_type)s, %(position)s, %(title_path)s, %(markdown)s,
        %(search_text)s)
ON CONFLICT ON CONSTRAINT uq_content_block_source_page_id_position DO UPDATE SET
    block_type = EXCLUDED.block_type,
    title_path = EXCLUDED.title_path,
    markdown = EXCLUDED.markdown,
    embedding = CASE
        WHEN content_block.search_text IS DISTINCT FROM EXCLUDED.search_text THEN NULL
        ELSE content_block.embedding
    END,
    search_text = EXCLUDED.search_text,
    updated_at = now()
WHERE (content_block.block_type, content_block.title_path, content_block.markdown,
       content_block.search_text)
    IS DISTINCT FROM (EXCLUDED.block_type, EXCLUDED.title_path, EXCLUDED.markdown,
                      EXCLUDED.search_text)
"""


async def save_content_blocks(
    connection: AsyncConnection, source_id: int, blocks: Sequence[TextbookBlock]
) -> None:
    """Blokları ilk sayfalarının satırına ekler; varsa değişen alanları günceller."""
    cursor = await connection.execute(SELECT_PAGE_IDS, {"source_id": source_id})
    page_ids = {int(page_no): int(page_id) for page_no, page_id in await cursor.fetchall()}
    rows = []
    for block in blocks:
        if block.page_no not in page_ids:
            raise LookupError(f"Source {source_id} has no page {block.page_no}")
        rows.append(
            {
                "source_page_id": page_ids[block.page_no],
                "block_type": block.block_type,
                "position": block.position,
                "title_path": block.title_path,
                "markdown": block.markdown,
                "search_text": block.search_text,
            }
        )
    async with connection.cursor() as writer:
        await writer.executemany(UPSERT_CONTENT_BLOCK, rows)
