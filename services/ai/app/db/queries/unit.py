"""Kaynağın sınıfındaki üniteyi adıyla bulan sorgu (hazırlık hattı, #130).

Ünite kaynağın müfredatında aranır; yüklemede müfredat seçilmediği için boşsa öğretim
programının (PROGRAM_CURRICULUM_NAME) üniteleri kullanılır. Aynı adlı ünite her sınıfta
bulunduğu için sadece kaynağın sınıfındaki üniteler aranır; sınıf boşsa SOURCE_DEFAULT_GRADE.
Ünite adı Türkçe harflerle karşılaştırılır (SQL lower() İ ve I'yı yanlış çevirdiği için eşitlik
Python'da kurulur). Ad hiçbir üniteyle uyuşmazsa boş döner. Tablolar core'un Flyway
migration'larıyla kurulur.
"""

from psycopg import AsyncConnection

from app.constants import PROGRAM_CURRICULUM_NAME, PROGRAM_SUBJECT_CODE, SOURCE_DEFAULT_GRADE
from app.text.turkish import tr_lower

SELECT_SOURCE_UNITS = """
SELECT curriculum_unit.id, curriculum_unit.title
FROM source_document
JOIN curriculum_unit ON curriculum_unit.curriculum_id = coalesce(
    source_document.curriculum_id,
    (SELECT curriculum.id
     FROM curriculum
     JOIN subject ON subject.id = curriculum.subject_id
     WHERE subject.code = %(subject_code)s AND curriculum.name = %(curriculum_name)s)
)
WHERE source_document.id = %(source_id)s
    AND curriculum_unit.grade = coalesce(source_document.grade, %(default_grade)s)
ORDER BY curriculum_unit.unit_no
"""


async def fetch_unit_id(connection: AsyncConnection, source_id: int, unit_title: str) -> int | None:
    """Kaynağın sınıfında adı uyan ilk ünitenin numarasını verir; yoksa boş döner."""
    values = {
        "source_id": source_id,
        "subject_code": PROGRAM_SUBJECT_CODE,
        "curriculum_name": PROGRAM_CURRICULUM_NAME,
        "default_grade": SOURCE_DEFAULT_GRADE,
    }
    cursor = await connection.execute(SELECT_SOURCE_UNITS, values)
    wanted = tr_lower(unit_title)
    for unit_id, title in await cursor.fetchall():
        if tr_lower(title) == wanted:
            return int(unit_id)
    return None
