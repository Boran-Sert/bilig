"""Kaynağın müfredatındaki üniteyi adıyla bulan sorgu (hazırlık hattı, #130).

Ünite adı Türkçe harflerle karşılaştırılır (SQL lower() İ ve I'yı yanlış çevirdiği için eşitlik
Python'da kurulur). Kaynağın müfredatı yoksa ya da ad hiçbir üniteyle uyuşmazsa boş döner.
Tablolar core'un Flyway migration'larıyla kurulur.
"""

from psycopg import AsyncConnection

from app.text.turkish import tr_lower

SELECT_CURRICULUM_UNITS = """
SELECT curriculum_unit.id, curriculum_unit.title
FROM curriculum_unit
JOIN source_document ON source_document.curriculum_id = curriculum_unit.curriculum_id
WHERE source_document.id = %(source_id)s
ORDER BY curriculum_unit.grade, curriculum_unit.unit_no
"""


async def fetch_unit_id(connection: AsyncConnection, source_id: int, unit_title: str) -> int | None:
    """Kaynağın müfredatında adı uyan ilk ünitenin numarasını verir; yoksa boş döner."""
    cursor = await connection.execute(SELECT_CURRICULUM_UNITS, {"source_id": source_id})
    wanted = tr_lower(unit_title)
    for unit_id, title in await cursor.fetchall():
        if tr_lower(title) == wanted:
            return int(unit_id)
    return None
