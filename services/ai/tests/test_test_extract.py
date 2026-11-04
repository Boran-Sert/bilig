"""Test PDF'inin soru yazma adımını (#130) sahte PDF okuması ve gerçek Postgres'le sınar.

PDF okuması sahte: hazır ParsedQuestion testleri döner; böylece sınanan şey kontrol, ünite
bulma ve yazmadır. Müfredat, ünite, kaynak ve sayfa kaydı testin kendi transaction'ında yazılır.
"""

from pathlib import Path

import psycopg
import pytest
from psycopg.rows import TupleRow

from app.ingest import pdf
from app.ingest.pipeline import IngestContext
from app.ingest.readers.test import extract_tests
from app.schemas.pdf import PageReport, QuestionReading
from app.schemas.question import ParsedQuestion
from app.storage import source_key
from tests.test_pipeline import make_context
from tests.test_validators import build_question

Connection = psycopg.AsyncConnection[TupleRow]

SEED = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('TESTYAZ', 'Test Yazma') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Test Yazma Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), unit_row AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT id, 12, 1, 'Şiir' FROM curriculum_row
), user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Test Yazma' FROM tenant
    RETURNING id
), document_row AS (
    INSERT INTO source_document (curriculum_id, title, sha256, file_path, uploaded_by)
    SELECT curriculum_row.id, %(title)s, repeat('f', 64), 'sources/0.pdf', user_row.id
    FROM curriculum_row, user_row
    RETURNING id
), page_row AS (
    INSERT INTO source_page (source_document_id, page_no)
    SELECT id, 1 FROM document_row
)
SELECT id FROM document_row
"""
COUNT_QUESTIONS = """
SELECT count(*) FROM question
JOIN source_page ON source_page.id = question.source_page_id
WHERE source_page.source_document_id = %s
"""
READ_LINKS = """
SELECT exam.title, exam_question.position, question.correct_option, question.status
FROM exam
JOIN exam_question ON exam_question.exam_id = exam.id
JOIN question ON question.id = exam_question.question_id
WHERE exam.source_document_id = %s
ORDER BY exam.title, exam_question.position
"""
COUNT_REVIEWS = """
SELECT reason FROM review_item WHERE source_document_id = %s AND status = 'OPEN' ORDER BY reason
"""
READ_REVIEW_DETAILS = """
SELECT reason, detail FROM review_item
WHERE source_document_id = %s AND status = 'OPEN'
ORDER BY reason
"""
READ_PAGE_ID = "SELECT id FROM source_page WHERE source_document_id = %s AND page_no = 1"


def make_test(*stems: str) -> list[ParsedQuestion]:
    """Numaraları 1'den giden, her biri başka metinli soruları kurar."""
    return [build_question(number, stem=stem) for number, stem in enumerate(stems, start=1)]


async def prepare(
    db: Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tests: list[list[ParsedQuestion]],
    title: str = "ÖDSGM 12 Şiir Kazanım Testi 1",
) -> tuple[int, IngestContext]:
    """Kaynağı ve sahte PDF okumasını kurar; kaynak numarasını ve bağlamı döner."""
    row = await (await db.execute(SEED, {"title": title})).fetchone()
    assert row is not None
    source_id = int(row[0])
    context = make_context(db, tmp_path)
    context.storage.write(source_key(source_id), b"%PDF")
    reading = QuestionReading(tests=tests, pages=[])
    monkeypatch.setattr(pdf, "read_questions", lambda _content: reading)
    return source_id, context


async def review_details(db: Connection, source_id: int) -> dict[str, list[dict[str, object]]]:
    """Kaynağın açık kayıtlarının sorunlarını nedenine göre döner."""
    rows = await (await db.execute(READ_REVIEW_DETAILS, (source_id,))).fetchall()
    return {str(reason): detail["problems"] for reason, detail in rows}


async def first_page_id(db: Connection, source_id: int) -> int:
    """Kaynağın ilk sayfasının kaydını döner."""
    row = await (await db.execute(READ_PAGE_ID, (source_id,))).fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.asyncio
async def test_clean_questions_are_written_once_with_positions(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sorular testin sırasıyla yazılır, DRAFT olur; adım tekrar çalışınca kopya olmaz."""
    tests = [make_test("Birinci soru metni", "İkinci soru metni")]
    source_id, context = await prepare(db, tmp_path, monkeypatch, tests)

    for _ in range(2):
        await extract_tests(source_id, context)

    assert await (await db.execute(COUNT_QUESTIONS, (source_id,))).fetchone() == (2,)
    links = await (await db.execute(READ_LINKS, (source_id,))).fetchall()
    assert links == [
        ("ÖDSGM 12 Şiir Kazanım Testi 1 Test 1", 1, "C", "DRAFT"),
        ("ÖDSGM 12 Şiir Kazanım Testi 1 Test 1", 2, "C", "DRAFT"),
    ]
    assert await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall() == []


@pytest.mark.asyncio
async def test_unanswered_and_broken_questions_are_not_written(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cevapsız ve kontrolü geçemeyen soru yazılmaz; ikisi için de inceleme kaydı açılır."""
    test = [
        build_question(1, stem="Sağlam soru"),
        build_question(2, stem="Cevapsız soru", correct_option=None),
        build_question(3, stem="Şıkları eksik soru", labels=["A", "B"]),
    ]
    source_id, context = await prepare(db, tmp_path, monkeypatch, [test])

    await extract_tests(source_id, context)

    assert await (await db.execute(COUNT_QUESTIONS, (source_id,))).fetchone() == (1,)
    page_id = await first_page_id(db, source_id)
    assert await review_details(db, source_id) == {
        "NO_ANSWER_KEY": [
            {"code": "NO_ANSWER_KEY", "pageNo": 1, "pageId": page_id, "test": 1, "number": 2}
        ],
        "VALIDATION_FAILED": [
            {"code": "OPTION_COUNT", "pageNo": 1, "pageId": page_id, "test": 1, "number": 3},
            {"code": "ANSWER_NOT_OPTION", "pageNo": 1, "pageId": page_id, "test": 1, "number": 3},
        ],
    }


@pytest.mark.asyncio
async def test_unknown_unit_writes_nothing_and_opens_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test adından ünite bulunamazsa hiçbir soru yazılmaz, kaynak incelemeye düşer."""
    source_id, context = await prepare(
        db, tmp_path, monkeypatch, [make_test("Soru metni")], title="Bilinmeyen Yayınevi Denemesi"
    )

    await extract_tests(source_id, context)

    assert await (await db.execute(COUNT_QUESTIONS, (source_id,))).fetchone() == (0,)
    assert await review_details(db, source_id) == {
        "VALIDATION_FAILED": [{"code": "UNIT_NOT_FOUND"}]
    }


@pytest.mark.asyncio
async def test_source_without_questions_opens_one_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hiç soru çıkmayan kaynak incelemeye düşer; adım tekrar çalışınca kayıt çoğalmaz."""
    source_id, context = await prepare(db, tmp_path, monkeypatch, [])

    for _ in range(2):
        await extract_tests(source_id, context)

    reasons = [row[0] for row in await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall()]
    assert reasons == ["VALIDATION_FAILED"]
    assert await review_details(db, source_id) == {"VALIDATION_FAILED": [{"code": "NO_CONTENT"}]}


@pytest.mark.asyncio
async def test_weak_pages_and_dropped_option_sets_open_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Metin katmanı bozuk sayfa ve kökünde soru olmayan şık kümesi sayfasıyla incelemeye düşer."""
    source_id, context = await prepare(db, tmp_path, monkeypatch, [])
    page = PageReport(page_no=1, source="TEXT", notes=["LOW_TEXT_LAYER"], text_ratio=0.4)
    reading = QuestionReading(
        tests=[make_test("Soru metni")], pages=[page], not_multiple_choice_pages=[1]
    )
    monkeypatch.setattr(pdf, "read_questions", lambda _content: reading)

    await extract_tests(source_id, context)

    page_id = await first_page_id(db, source_id)
    assert await (await db.execute(COUNT_QUESTIONS, (source_id,))).fetchone() == (1,)
    assert await review_details(db, source_id) == {
        "VALIDATION_FAILED": [
            {"code": "LOW_TEXT_LAYER", "pageNo": 1, "pageId": page_id},
            {"code": "NOT_MULTIPLE_CHOICE", "pageNo": 1, "pageId": page_id},
        ]
    }
