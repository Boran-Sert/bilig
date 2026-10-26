"""Ünitelerin ve ünite-kazanım bağlarının yazılmasını gerçek Postgres'te test eder (A1, #108).

Testler kendi ders koduyla (TST) yazar; veritabanında gerçek program yüklü olsa da sonuç
değişmez. Kazanımlar önce save_program ile yazılır.
"""

import psycopg
import pytest
from psycopg.rows import TupleRow

from app.db.queries.program import save_program, save_units
from app.schemas.program import (
    Curriculum,
    CurriculumUnit,
    LearningOutcome,
    LearningOutcomeGroup,
    Program,
    Subject,
    UnitSaveSummary,
)

Connection = psycopg.AsyncConnection[TupleRow]

CURRICULUM_NAME = "Test Programı 2018"
PROGRAM = Program(
    subject=Subject(code="TST", name="Test Dersi"),
    curriculum=Curriculum(name=CURRICULUM_NAME, model="LEGACY", year=2018),
    groups=[
        LearningOutcomeGroup(
            code="A.1",
            name="Şiir",
            outcomes=[LearningOutcome(code="A.1.1", title="Yorumlar.", meb_explanation=None)],
        ),
        LearningOutcomeGroup(
            code="A.2",
            name="Öyküleyici",
            outcomes=[
                LearningOutcome(code="A.2.1", title="Okur.", meb_explanation=None),
                LearningOutcome(code="A.2.2", title="Belirler.", meb_explanation=None),
            ],
        ),
    ],
)

LINKS = """
SELECT curriculum_unit.grade, curriculum_unit.unit_no, curriculum_unit.title,
    learning_outcome.code
FROM curriculum_unit
JOIN curriculum ON curriculum.id = curriculum_unit.curriculum_id
LEFT JOIN curriculum_unit_outcome
    ON curriculum_unit_outcome.curriculum_unit_id = curriculum_unit.id
LEFT JOIN learning_outcome ON learning_outcome.id = curriculum_unit_outcome.learning_outcome_id
WHERE curriculum.name = 'Test Programı 2018'
ORDER BY 1, 2, 4
"""


def unit(unit_no: int, title: str, group_codes: list[str], grade: int = 12) -> CurriculumUnit:
    """Ünite kurar."""
    return CurriculumUnit(grade=grade, unit_no=unit_no, title=title, group_codes=group_codes)


async def links(db: Connection) -> list[tuple[int, int, str, str | None]]:
    """Test programının ünitelerini ve bağlı kazanım kodlarını döner."""
    cursor = await db.execute(LINKS)
    return [
        (grade, unit_no, title, code) for grade, unit_no, title, code in await cursor.fetchall()
    ]


@pytest.mark.asyncio
async def test_units_are_linked_to_their_group_outcomes(db: Connection) -> None:
    """Her ünite gruplarındaki bütün kazanımlara bağlanır; grubu olmayan ünite bağsız kalır."""
    await save_program(db, PROGRAM)

    summary = await save_units(
        db, "TST", CURRICULUM_NAME, [unit(1, "Giriş", []), unit(2, "Hikâye", ["A.2"])]
    )

    assert summary == UnitSaveSummary(units=2, linked=2, unlinked=0)
    assert await links(db) == [
        (12, 1, "Giriş", None),
        (12, 2, "Hikâye", "A.2.1"),
        (12, 2, "Hikâye", "A.2.2"),
    ]


@pytest.mark.asyncio
async def test_second_save_creates_no_duplicates(db: Connection) -> None:
    """Aynı üniteler ikinci kez yazılınca kopya ünite ya da bağ oluşmaz."""
    await save_program(db, PROGRAM)
    units = [unit(1, "Şiir", ["A.1"]), unit(1, "Şiir", ["A.1"], grade=11)]
    await save_units(db, "TST", CURRICULUM_NAME, units)

    summary = await save_units(db, "TST", CURRICULUM_NAME, units)

    assert summary == UnitSaveSummary(units=2, linked=0, unlinked=0)
    assert await links(db) == [(11, 1, "Şiir", "A.1.1"), (12, 1, "Şiir", "A.1.1")]


@pytest.mark.asyncio
async def test_changed_rule_replaces_links_and_title(db: Connection) -> None:
    """Ünitenin grubu ya da adı değişince eski bağ kaldırılır, yenisi eklenir, ad güncellenir."""
    await save_program(db, PROGRAM)
    await save_units(db, "TST", CURRICULUM_NAME, [unit(1, "Şiir", ["A.1"])])

    summary = await save_units(db, "TST", CURRICULUM_NAME, [unit(1, "Roman", ["A.2"])])

    assert summary == UnitSaveSummary(units=1, linked=2, unlinked=1)
    assert await links(db) == [(12, 1, "Roman", "A.2.1"), (12, 1, "Roman", "A.2.2")]


@pytest.mark.asyncio
async def test_links_stay_inside_the_curriculum(db: Connection) -> None:
    """Aynı grup kodu başka programda da olsa ünite sadece kendi programının kazanımına bağlanır."""
    other = PROGRAM.model_copy(
        update={"curriculum": Curriculum(name="Test Programı 2024", model="MAARIF", year=2024)}
    )
    await save_program(db, other)
    await save_program(db, PROGRAM)

    summary = await save_units(db, "TST", CURRICULUM_NAME, [unit(1, "Şiir", ["A.1"])])

    assert summary.linked == 1
    assert await links(db) == [(12, 1, "Şiir", "A.1.1")]


@pytest.mark.asyncio
async def test_missing_curriculum_is_an_error(db: Connection) -> None:
    """Kazanımları yüklenmemiş program için ünite yazılmaz, hata verir."""
    with pytest.raises(ValueError, match="import the program first"):
        await save_units(db, "TST", "Olmayan Program", [unit(1, "Şiir", ["A.1"])])


@pytest.mark.asyncio
async def test_unit_without_groups_loses_old_links(db: Connection) -> None:
    """Grubu kalmayan ünitenin eski bütün bağları kaldırılır."""
    await save_program(db, PROGRAM)
    await save_units(db, "TST", CURRICULUM_NAME, [unit(1, "Şiir", ["A.1"])])

    summary = await save_units(db, "TST", CURRICULUM_NAME, [unit(1, "Giriş", [])])

    assert summary == UnitSaveSummary(units=1, linked=0, unlinked=1)
    assert await links(db) == [(12, 1, "Giriş", None)]


@pytest.mark.asyncio
async def test_curriculum_is_found_by_subject_and_name(db: Connection) -> None:
    """Aynı adlı program başka derste de varsa ünite verilen dersin programına yazılır."""
    other_subject = PROGRAM.model_copy(update={"subject": Subject(code="TS2", name="İkinci Ders")})
    await save_program(db, other_subject)

    with pytest.raises(ValueError, match="import the program first"):
        await save_units(db, "TST", CURRICULUM_NAME, [unit(1, "Şiir", ["A.1"])])


@pytest.mark.asyncio
async def test_group_without_outcomes_is_an_error(db: Connection) -> None:
    """Kuralın verdiği grupta hiç kazanım yoksa (eksik yükleme) bağ yazılmaz, hata verir."""
    await save_program(db, PROGRAM)

    with pytest.raises(ValueError, match=r"No outcomes in groups \['A.3'\]"):
        await save_units(db, "TST", CURRICULUM_NAME, [unit(1, "Tiyatro", ["A.3"])])


@pytest.mark.asyncio
async def test_failed_save_rolls_back_every_unit(db: Connection) -> None:
    """Ünitelerden biri yazılamazsa önceki üniteler de yazılmaz."""
    await save_program(db, PROGRAM)

    with pytest.raises(psycopg.errors.CheckViolation):
        await save_units(
            db, "TST", CURRICULUM_NAME, [unit(1, "Şiir", ["A.1"]), unit(1, "Roman", [], grade=13)]
        )

    assert await links(db) == []
