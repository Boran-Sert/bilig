"""Kazanım ağacının upsert'ünü gerçek Postgres'te test eder (hazırlık hattı A1, #104).

Tablolar core'un migration'larıyla (#93) kurulur. Sahte bağlantılı testler (test_program_queries.py)
sorgu sırasını ölçer; bunlar upsert'ün veritabanındaki etkisini ölçer: tekrar çalıştırmada kopya
satır oluşmaması, değişmeyen satırın hiç güncellenmemesi, arama metni değişince embedding'in
silinmesi ve PDF'te artık olmayan kazanımın silinmeden sayılması. Testler kendi ders koduyla
(TST) yazar ve sadece onu okur; veritabanında gerçek program yüklü olsa da sonuç değişmez.
"""

import psycopg
import pytest
from psycopg.rows import TupleRow

from app.db.queries.program import save_program
from app.schemas.program import (
    Curriculum,
    LearningOutcome,
    LearningOutcomeGroup,
    Program,
    ProgramSaveSummary,
    Subject,
)

Connection = psycopg.AsyncConnection[TupleRow]
RowState = dict[str, tuple[str, bool, str | None]]

SUBJECT = Subject(code="TST", name="Test Dersi")
CURRICULUM = Curriculum(name="Test Programı 2018", model="LEGACY", year=2018)
OTHER_CURRICULUM = Curriculum(name="Test Programı 2024", model="MAARIF", year=2024)

TEST_OUTCOMES = """
FROM learning_outcome
JOIN learning_outcome_group
    ON learning_outcome_group.id = learning_outcome.learning_outcome_group_id
JOIN curriculum ON curriculum.id = learning_outcome_group.curriculum_id
JOIN subject ON subject.id = curriculum.subject_id
WHERE subject.code = 'TST'
"""

COUNT_OUTCOMES = "SELECT count(*)" + TEST_OUTCOMES

SET_EMBEDDINGS = (
    "UPDATE learning_outcome SET embedding = array_fill(0.5, ARRAY[1024])::vector"
    " WHERE id IN (SELECT learning_outcome.id" + TEST_OUTCOMES + ")"
)

ROW_STATE = (
    "SELECT learning_outcome.code, learning_outcome.xmin::text,"
    " learning_outcome.embedding IS NOT NULL, learning_outcome.meb_explanation"
    + TEST_OUTCOMES
    + " AND curriculum.name = 'Test Programı 2018'"
)

READ_TEXTS = (
    "SELECT learning_outcome.title, learning_outcome.search_text"
    + TEST_OUTCOMES
    + " AND curriculum.name = 'Test Programı 2018'"
)


def build_program(
    *,
    curriculum: Curriculum = CURRICULUM,
    poem_group_name: str = "Şiir",
    poem_title: str = "Şiiri yorumlar.",
    theme_explanation: str | None = None,
    dropped: frozenset[str] = frozenset(),
) -> Program:
    """İki gruplu küçük bir kazanım ağacı kurar; alanlar değiştirilebilir, kazanım çıkarılabilir."""
    trees = {
        ("A.1", poem_group_name): [
            LearningOutcome(code="A.1.1", title=poem_title, meb_explanation="a. Not."),
            LearningOutcome(
                code="A.1.2", title="Temayı belirler.", meb_explanation=theme_explanation
            ),
        ],
        ("B", "Yazma"): [LearningOutcome(code="B.1", title="Metin yazar.", meb_explanation=None)],
    }
    groups = []
    for (code, name), outcomes in trees.items():
        kept = [outcome for outcome in outcomes if outcome.code not in dropped]
        if kept:
            groups.append(LearningOutcomeGroup(code=code, name=name, outcomes=kept))
    return Program(subject=SUBJECT, curriculum=curriculum, groups=groups)


async def count_outcomes(db: Connection) -> int:
    """Test dersinin bütün programlarındaki kazanım satırlarını sayar."""
    cursor = await db.execute(COUNT_OUTCOMES)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def row_state(db: Connection) -> RowState:
    """Varsayılan programdaki her kazanımın xmin'ini, embedding doluluğunu ve açıklamasını döner."""
    cursor = await db.execute(ROW_STATE)
    rows = await cursor.fetchall()
    return {code: (version, embedded, explanation) for code, version, embedded, explanation in rows}


async def save_with_embeddings(db: Connection) -> RowState:
    """Varsayılan ağacı yazar, kazanımlara embedding koyar ve satırların durumunu döner."""
    await save_program(db, build_program())
    await db.execute(SET_EMBEDDINGS)
    return await row_state(db)


def changed_codes(before: RowState, after: RowState) -> set[str]:
    """Satır sürümü (xmin) değişen kazanımları döner."""
    return {code for code in after if after[code][0] != before[code][0]}


@pytest.mark.asyncio
async def test_first_save_inserts_whole_tree(db: Connection) -> None:
    """İlk yazmada bütün ağaç eklenir ve kazanım sayısı doğru raporlanır."""
    summary = await save_program(db, build_program())

    assert summary == ProgramSaveSummary(inserted=3, updated=0, unchanged=0, missing=0)
    assert await count_outcomes(db) == 3


@pytest.mark.asyncio
async def test_second_save_creates_no_duplicates_and_touches_no_outcome(db: Connection) -> None:
    """Aynı ağaç ikinci kez yazılınca kopya satır oluşmaz, kazanım satırları hiç güncellenmez."""
    before = await save_with_embeddings(db)

    summary = await save_program(db, build_program())

    assert summary == ProgramSaveSummary(inserted=0, updated=0, unchanged=3, missing=0)
    assert await count_outcomes(db) == 3
    assert await row_state(db) == before


@pytest.mark.asyncio
async def test_changed_title_clears_only_that_embedding(db: Connection) -> None:
    """Başlığı değişen kazanım güncellenir ve embedding'i silinir; diğerleri olduğu gibi kalır."""
    before = await save_with_embeddings(db)

    summary = await save_program(db, build_program(poem_title="Şiiri bütün yönleriyle yorumlar."))

    after = await row_state(db)
    assert summary == ProgramSaveSummary(inserted=0, updated=1, unchanged=2, missing=0)
    assert changed_codes(before, after) == {"A.1.1"}
    assert after["A.1.1"][1] is False
    cursor = await db.execute(READ_TEXTS + " AND learning_outcome.code = 'A.1.1'")
    assert await cursor.fetchone() == (
        "Şiiri bütün yönleriyle yorumlar.",
        "Test Dersi › Şiir › Şiiri bütün yönleriyle yorumlar.\na. Not.",
    )


@pytest.mark.asyncio
async def test_changed_explanation_updates_column_and_clears_embedding(db: Connection) -> None:
    """Sadece MEB açıklaması değişen kazanımın açıklaması yazılır, embedding'i silinir."""
    before = await save_with_embeddings(db)

    summary = await save_program(db, build_program(theme_explanation="a. Yeni not."))

    after = await row_state(db)
    assert summary == ProgramSaveSummary(inserted=0, updated=1, unchanged=2, missing=0)
    assert changed_codes(before, after) == {"A.1.2"}
    assert after["A.1.2"][1:] == (False, "a. Yeni not.")


@pytest.mark.asyncio
async def test_change_without_search_text_change_keeps_embedding(db: Connection) -> None:
    """Açıklama yoktan boş metne geçince satır güncellenir; arama metni aynı, embedding kalır."""
    before = await save_with_embeddings(db)

    summary = await save_program(db, build_program(theme_explanation=""))

    after = await row_state(db)
    assert summary == ProgramSaveSummary(inserted=0, updated=1, unchanged=2, missing=0)
    assert changed_codes(before, after) == {"A.1.2"}
    assert after["A.1.2"][1:] == (True, "")


@pytest.mark.asyncio
async def test_renamed_group_clears_embeddings_of_its_outcomes(db: Connection) -> None:
    """Grup adı arama yolunda olduğu için adı değişen grubun bütün kazanımları güncellenir."""
    before = await save_with_embeddings(db)

    summary = await save_program(db, build_program(poem_group_name="Şiir Okuma"))

    after = await row_state(db)
    assert summary == ProgramSaveSummary(inserted=0, updated=2, unchanged=1, missing=0)
    assert changed_codes(before, after) == {"A.1.1", "A.1.2"}
    assert {code: state[1] for code, state in after.items()} == {
        "A.1.1": False,
        "A.1.2": False,
        "B.1": True,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("dropped", ["B.1", "A.1.2"], ids=["whole-group", "inside-group"])
async def test_outcome_missing_from_pdf_is_counted_not_deleted(
    db: Connection, dropped: str
) -> None:
    """PDF'te artık olmayan kazanım, grubu kalsa da kalmasa da silinmez, eksik olarak sayılır."""
    await save_program(db, build_program())

    summary = await save_program(db, build_program(dropped=frozenset({dropped})))

    assert summary == ProgramSaveSummary(inserted=0, updated=0, unchanged=2, missing=1)
    assert await count_outcomes(db) == 3


@pytest.mark.asyncio
async def test_missing_count_ignores_other_curricula(db: Connection) -> None:
    """Eksik sayımı sadece yazılan programın kazanımlarına bakar, diğer programı saymaz."""
    await save_program(db, build_program(curriculum=OTHER_CURRICULUM))
    await save_program(db, build_program())

    summary = await save_program(db, build_program(dropped=frozenset({"B.1"})))

    assert summary.missing == 1
    assert await count_outcomes(db) == 6


def build_same_code_program(group_codes: list[str]) -> Program:
    """Her grubunda "1" kodlu tek kazanım olan ağaç kurar."""
    outcome = LearningOutcome(code="1", title="Dinler.", meb_explanation=None)
    groups = [
        LearningOutcomeGroup(code=code, name=code, outcomes=[outcome]) for code in group_codes
    ]
    return Program(subject=SUBJECT, curriculum=CURRICULUM, groups=groups)


@pytest.mark.asyncio
async def test_missing_count_matches_outcome_code_within_its_group(db: Connection) -> None:
    """Aynı kodlu kazanım iki grupta varsa, birinden çıkanı diğerindeki gizlemez."""
    await save_program(db, build_same_code_program(["C", "D"]))

    summary = await save_program(db, build_same_code_program(["C"]))

    assert summary.missing == 1
