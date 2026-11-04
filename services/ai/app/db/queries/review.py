"""Kaynağa bağlı inceleme kaydı açan sorgu (hazırlık hattı, #130, #269).

Cevap anahtarı bulunamayan ya da kontrolden geçemeyen test soruları yazılmaz; bunun yerine kaynak
için bir inceleme kaydı açılır ve kaynak REVIEW durumuna geçer. Kaydın ayrıntısında (detail) her
sorun sayfası, sayfanın kaydı, testi ve soru numarasıyla durur. Aynı nedenle açık kayıt varsa
ikincisi açılmaz, ayrıntısı son okumayla değiştirilir; böylece adım tekrar çalışınca kopya
oluşmaz. Tablolar core'un Flyway migration'larıyla kurulur.
"""

from collections.abc import Sequence
from typing import Literal

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.db.queries.source import fetch_page_ids
from app.schemas.review import SourceProblem

SourceReviewReason = Literal["NO_ANSWER_KEY", "VALIDATION_FAILED"]

UPSERT_SOURCE_REVIEW = """
WITH updated AS (
    UPDATE review_item SET detail = %(detail)s
    WHERE source_document_id = %(source_id)s AND reason = %(reason)s AND status = 'OPEN'
    RETURNING id
)
INSERT INTO review_item (reason, source_document_id, detail)
SELECT %(reason)s, %(source_id)s, %(detail)s
WHERE NOT EXISTS (SELECT 1 FROM updated)
"""

SET_REVIEW_STATUS = """
UPDATE source_document SET status = 'REVIEW', updated_at = now() WHERE id = %(source_id)s
"""


async def open_source_review(
    connection: AsyncConnection,
    source_id: int,
    reason: SourceReviewReason,
    problems: Sequence[SourceProblem],
) -> None:
    """Kaynak için ayrıntılı açık inceleme kaydı açar ya da günceller ve kaynağı REVIEW yapar."""
    page_ids = await fetch_page_ids(connection, source_id)
    items = [
        problem.model_copy(update={"page_id": page_ids.get(problem.page_no or 0)})
        for problem in problems
    ]
    detail = {"problems": [item.model_dump(by_alias=True, exclude_none=True) for item in items]}
    params = {"source_id": source_id, "reason": reason, "detail": Jsonb(detail)}
    await connection.execute(UPSERT_SOURCE_REVIEW, params)
    await connection.execute(SET_REVIEW_STATUS, {"source_id": source_id})
