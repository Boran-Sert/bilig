"""Kazanım ağacını veritabanına yazan sorgular (hazırlık hattı A1).

Ders, program, kazanım grubu ve kazanım benzersiz anahtarlarıyla upsert edilir; komut ikinci
kez çalışınca kopya satır oluşmaz. Kazanımın arama metni değişirse eski embedding silinir,
çünkü artık o metne ait değildir; kazanım vektörleri ayrı adımda yeniden hesaplanır (#123).
Değişmeyen kazanım güncellenmez. Programda kayıtlı olup PDF'te artık olmayan kazanımlar
silinmez (soru bağları olabilir), sadece sayılır. Tablolar core'un Flyway migration'larıyla kurulur.
"""

from psycopg import AsyncConnection

from app.constants import SEARCH_PATH_SEPARATOR
from app.schemas.program import LearningOutcome, Program, ProgramSaveSummary

UPSERT_SUBJECT = """
INSERT INTO subject (code, name)
VALUES (%(code)s, %(name)s)
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
RETURNING id
"""

UPSERT_CURRICULUM = """
INSERT INTO curriculum (subject_id, name, model, year)
VALUES (%(subject_id)s, %(name)s, %(model)s, %(year)s)
ON CONFLICT (subject_id, name) DO UPDATE SET model = EXCLUDED.model, year = EXCLUDED.year
RETURNING id
"""

UPSERT_LEARNING_OUTCOME_GROUP = """
INSERT INTO learning_outcome_group (curriculum_id, code, name)
VALUES (%(curriculum_id)s, %(code)s, %(name)s)
ON CONFLICT (curriculum_id, code) DO UPDATE SET name = EXCLUDED.name
RETURNING id
"""

UPSERT_LEARNING_OUTCOME = """
INSERT INTO learning_outcome (learning_outcome_group_id, code, title, meb_explanation, search_text)
VALUES (%(group_id)s, %(code)s, %(title)s, %(meb_explanation)s, %(search_text)s)
ON CONFLICT (learning_outcome_group_id, code) DO UPDATE SET
    title = EXCLUDED.title,
    meb_explanation = EXCLUDED.meb_explanation,
    search_text = EXCLUDED.search_text,
    embedding = CASE
        WHEN learning_outcome.search_text = EXCLUDED.search_text THEN learning_outcome.embedding
    END
WHERE (learning_outcome.title, learning_outcome.meb_explanation, learning_outcome.search_text)
    IS DISTINCT FROM (EXCLUDED.title, EXCLUDED.meb_explanation, EXCLUDED.search_text)
RETURNING (xmax = 0) AS inserted
"""

COUNT_MISSING_LEARNING_OUTCOMES = """
SELECT count(*)
FROM learning_outcome
JOIN learning_outcome_group
    ON learning_outcome_group.id = learning_outcome.learning_outcome_group_id
WHERE learning_outcome_group.curriculum_id = %(curriculum_id)s
    AND NOT EXISTS (
        SELECT 1
        FROM unnest(%(group_codes)s::text[], %(outcome_codes)s::text[]) AS saved(group_code, code)
        WHERE saved.group_code = learning_outcome_group.code AND saved.code = learning_outcome.code
    )
"""


async def save_program(connection: AsyncConnection, program: Program) -> ProgramSaveSummary:
    """Ağacı tek transaction'da yazar; değişen ve PDF'te olmayan kazanımları sayıp döner."""
    inserted = updated = unchanged = 0
    async with connection.transaction():
        subject_id = await _fetch_id(connection, UPSERT_SUBJECT, program.subject.model_dump())
        curriculum_id = await _fetch_id(
            connection,
            UPSERT_CURRICULUM,
            {"subject_id": subject_id, **program.curriculum.model_dump()},
        )
        for group in program.groups:
            group_id = await _fetch_id(
                connection,
                UPSERT_LEARNING_OUTCOME_GROUP,
                {"curriculum_id": curriculum_id, "code": group.code, "name": group.name},
            )
            for outcome in group.outcomes:
                values = {
                    "group_id": group_id,
                    **outcome.model_dump(),
                    "search_text": build_search_text(program.subject.name, group.name, outcome),
                }
                cursor = await connection.execute(UPSERT_LEARNING_OUTCOME, values)
                row = await cursor.fetchone()
                if row is None:
                    unchanged += 1
                elif row[0]:
                    inserted += 1
                else:
                    updated += 1
        missing = await _count_missing(connection, curriculum_id, program)
    return ProgramSaveSummary(
        inserted=inserted, updated=updated, unchanged=unchanged, missing=missing
    )


def build_search_text(subject_name: str, group_name: str, outcome: LearningOutcome) -> str:
    """Kazanımın arama metnini ders › grup › başlık yolu ve MEB açıklamasından kurar."""
    path = SEARCH_PATH_SEPARATOR.join([subject_name, group_name, outcome.title])
    return f"{path}\n{outcome.meb_explanation}" if outcome.meb_explanation else path


async def _fetch_id(connection: AsyncConnection, query: str, values: dict[str, object]) -> int:
    """Upsert sorgusunu çalıştırıp dönen satırın kimliğini verir."""
    cursor = await connection.execute(query, values)
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError("Upsert returned no id")
    return int(row[0])


async def _count_missing(connection: AsyncConnection, curriculum_id: int, program: Program) -> int:
    """Programda kayıtlı olup okunan ağaçta bulunmayan kazanımları sayar."""
    pairs = [(group.code, outcome.code) for group in program.groups for outcome in group.outcomes]
    values = {
        "curriculum_id": curriculum_id,
        "group_codes": [group_code for group_code, _ in pairs],
        "outcome_codes": [outcome_code for _, outcome_code in pairs],
    }
    cursor = await connection.execute(COUNT_MISSING_LEARNING_OUTCOMES, values)
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError("Count returned no row")
    return int(row[0])
