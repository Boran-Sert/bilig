"""Hazırlık bitince testlerin yayını ve kaynağın son durumu gerçek Postgres'te test edilir.

Adımlar boş geçilir; testler kendi ünite, kaynak, sayfa, test, soru ve inceleme satırlarını yazar.
Her şey db fixture'ının geri alınan transaction'ında yaşar (#262).
"""

from pathlib import Path

import pytest

from app.ingest.pipeline import IngestContext, run_steps
from app.ingest.steps import IngestStep
from tests.test_pipeline import READ_SOURCE_STATUS, make_context, make_job, make_source
from tests.test_postgres_queue import Connection

INSERT_UNIT_AND_PAGE = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('BITIS', 'Bitiş Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Bitiş Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), unit_row AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT id, 12, 1, 'Roman' FROM curriculum_row
    RETURNING id
), page_row AS (
    INSERT INTO source_page (source_document_id, page_no) VALUES (%(source_id)s, 1) RETURNING id
)
SELECT unit_row.id, page_row.id FROM unit_row, page_row
"""

INSERT_EXAM = """
INSERT INTO exam (curriculum_unit_id, source_document_id, title)
VALUES (%(unit_id)s, %(source_id)s, %(title)s)
RETURNING id
"""

INSERT_QUESTION = """
WITH question_row AS (
    INSERT INTO question (source_page_id, curriculum_unit_id, origin, content, correct_option,
        content_hash, status)
    VALUES (%(page_id)s, %(unit_id)s, 'SOURCE', '{}', 'A', md5(%(key)s) || md5(%(key)s || 'x'),
        %(status)s)
    RETURNING id
)
INSERT INTO exam_question (exam_id, question_id, position)
SELECT %(exam_id)s, id, %(position)s FROM question_row
RETURNING question_id
"""

INSERT_SOURCE_REVIEW = """
INSERT INTO review_item (reason, source_document_id, status) VALUES ('NO_ANSWER_KEY', %s, %s)
"""

INSERT_QUESTION_REVIEW = (
    "INSERT INTO review_item (reason, question_id) VALUES ('LOW_CONFIDENCE', %s)"
)

READ_EXAM_STATUS = "SELECT status FROM exam WHERE id = %s"


async def seed_page(db: Connection, source_id: int) -> tuple[int, int]:
    """Bir ünite ve kaynağın ilk sayfasını ekler; ünite ve sayfa numarasını döner."""
    cursor = await db.execute(INSERT_UNIT_AND_PAGE, {"source_id": source_id})
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0]), int(row[1])


async def seed_exam(
    db: Connection, source_id: int, page: tuple[int, int], title: str, statuses: list[str]
) -> list[int]:
    """Kaynağa verilen durumlarda sorusu olan test ekler; test ve soru numaralarını döner."""
    unit_id, page_id = page
    values = {"unit_id": unit_id, "source_id": source_id, "title": title}
    cursor = await db.execute(INSERT_EXAM, values)
    exam_row = await cursor.fetchone()
    assert exam_row is not None
    ids = [int(exam_row[0])]
    for position, status in enumerate(statuses, start=1):
        question = {
            "page_id": page_id,
            "unit_id": unit_id,
            "key": f"{title}-{position}",
            "status": status,
            "exam_id": ids[0],
            "position": position,
        }
        cursor = await db.execute(INSERT_QUESTION, question)
        question_row = await cursor.fetchone()
        assert question_row is not None
        ids.append(int(question_row[0]))
    return ids


async def read_status(db: Connection, query: str, item_id: int) -> str:
    """Satırın durumunu okur."""
    cursor = await db.execute(query, (item_id,))
    row = await cursor.fetchone()
    assert row is not None
    return str(row[0])


async def finish(db: Connection, source_id: int, tmp_path: Path) -> None:
    """Kaynağın işini adımsız çalıştırıp bitirir."""
    await run_steps(await make_job(db, source_id), make_context(db, tmp_path), {})


@pytest.mark.asyncio
async def test_exam_with_published_question_is_published(db: Connection, tmp_path: Path) -> None:
    """En az bir yayındaki sorusu olan test yayına girer, olmayan taslak kalır."""
    source_id = await make_source(db)
    page = await seed_page(db, source_id)
    [published_exam, *_] = await seed_exam(db, source_id, page, "Test 1", ["PUBLISHED", "DRAFT"])
    [draft_exam, *_] = await seed_exam(db, source_id, page, "Test 2", ["DRAFT", "REJECTED"])

    await finish(db, source_id, tmp_path)

    assert await read_status(db, READ_EXAM_STATUS, published_exam) == "PUBLISHED"
    assert await read_status(db, READ_EXAM_STATUS, draft_exam) == "DRAFT"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("review_status", "expected"), [("OPEN", "REVIEW"), ("APPROVED", "PUBLISHED")]
)
async def test_source_with_open_source_review_goes_to_review(
    db: Connection, tmp_path: Path, review_status: str, expected: str
) -> None:
    """Kaynağın açık inceleme kaydı varsa kaynak REVIEW, karar verilmişse PUBLISHED olur."""
    source_id = await make_source(db)
    await db.execute(INSERT_SOURCE_REVIEW, (source_id, review_status))

    await finish(db, source_id, tmp_path)

    assert await read_status(db, READ_SOURCE_STATUS, source_id) == expected


@pytest.mark.asyncio
async def test_source_with_open_question_review_goes_to_review(
    db: Connection, tmp_path: Path
) -> None:
    """Kaynağın bir sorusu incelemedeyse kaynak REVIEW olur."""
    source_id = await make_source(db)
    page = await seed_page(db, source_id)
    [_, question_id] = await seed_exam(db, source_id, page, "Test 1", ["DRAFT"])
    await db.execute(INSERT_QUESTION_REVIEW, (question_id,))

    await finish(db, source_id, tmp_path)

    assert await read_status(db, READ_SOURCE_STATUS, source_id) == "REVIEW"


@pytest.mark.asyncio
async def test_job_taken_by_another_worker_does_not_finish(db: Connection, tmp_path: Path) -> None:
    """İş başka çalışana geçtiyse testler yayına girmez, kaynağın durumu yazılmaz."""
    source_id = await make_source(db)
    page = await seed_page(db, source_id)
    [exam_id, *_] = await seed_exam(db, source_id, page, "Test 1", ["PUBLISHED"])
    job = await make_job(db, source_id)
    await db.execute("UPDATE background_job SET attempts = attempts + 1 WHERE id = %s", (job.id,))

    async def step(source_id: int, context: IngestContext) -> None:
        """Hiçbir şey yapmayan adım."""

    await run_steps(job, make_context(db, tmp_path), {IngestStep.REGISTERED: step})

    assert await read_status(db, READ_SOURCE_STATUS, source_id) == "PROCESSING"
    assert await read_status(db, READ_EXAM_STATUS, exam_id) == "DRAFT"
