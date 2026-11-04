"""Kaynağa bağlı inceleme kaydı açan sorgu (hazırlık hattı, #130).

Cevap anahtarı bulunamayan ya da kontrolden geçemeyen test soruları yazılmaz; bunun yerine kaynak
için bir inceleme kaydı açılır ve kaynak REVIEW durumuna geçer. Aynı nedenle açık kayıt varsa
ikincisi açılmaz, böylece adım tekrar çalışınca kopya oluşmaz. Tablolar core'un Flyway
migration'larıyla kurulur.
"""

from typing import Literal

from psycopg import AsyncConnection

SourceReviewReason = Literal["NO_ANSWER_KEY", "VALIDATION_FAILED"]

INSERT_SOURCE_REVIEW = """
INSERT INTO review_item (reason, source_document_id)
SELECT %(reason)s, %(source_id)s
WHERE NOT EXISTS (
    SELECT 1 FROM review_item
    WHERE source_document_id = %(source_id)s AND reason = %(reason)s AND status = 'OPEN'
)
"""

SET_REVIEW_STATUS = """
UPDATE source_document SET status = 'REVIEW', updated_at = now() WHERE id = %(source_id)s
"""


async def open_source_review(
    connection: AsyncConnection, source_id: int, reason: SourceReviewReason
) -> None:
    """Kaynak için açık bir inceleme kaydı açar (yoksa) ve kaynağı REVIEW yapar."""
    params = {"source_id": source_id, "reason": reason}
    await connection.execute(INSERT_SOURCE_REVIEW, params)
    await connection.execute(SET_REVIEW_STATUS, {"source_id": source_id})
