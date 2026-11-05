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
from app.ingest.readers.answer_key import check_answer_key
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
READ_UNITS = """
SELECT exam_unit.title, question_unit.title
FROM exam
JOIN exam_question ON exam_question.exam_id = exam.id
JOIN question ON question.id = exam_question.question_id
LEFT JOIN curriculum_unit AS exam_unit ON exam_unit.id = exam.curriculum_unit_id
LEFT JOIN curriculum_unit AS question_unit ON question_unit.id = question.curriculum_unit_id
WHERE exam.source_document_id = %s
"""


def make_test(*stems: str) -> list[ParsedQuestion]:
    """Numaraları 1'den giden, her biri başka metinli soruları kurar."""
    return [build_question(number, stem=stem) for number, stem in enumerate(stems, start=1)]


async def prepare(
    db: Connection,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tests: list[list[ParsedQuestion]],
    title: str = "ÖDSGM 12 Şiir Kazanım Testi 1",
    page_text: str = "",
) -> tuple[int, IngestContext]:
    """Kaynağı, sahte PDF okumasını ve ilk sayfa metnini kurar; kaynağı ve bağlamı döner."""
    row = await (await db.execute(SEED, {"title": title})).fetchone()
    assert row is not None
    source_id = int(row[0])
    context = make_context(db, tmp_path)
    context.storage.write(source_key(source_id), b"%PDF")
    reading = QuestionReading(tests=tests, pages=[])
    monkeypatch.setattr(pdf, "read_questions", lambda _content: reading)
    monkeypatch.setattr(pdf, "read_first_page_text", lambda _content: page_text)
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
async def test_unit_is_found_from_page_heading(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adında ünite olmayan testin ünitesi ilk sayfadaki "Şiir - 4" başlığından bulunur."""
    page_text = "12. Sınıf\nTürk Dili ve\nEdebiyatı\n1. Soru metni\nŞiir - 4\r\n"
    source_id, context = await prepare(
        db, tmp_path, monkeypatch, [make_test("Soru metni")], title="14.pdf", page_text=page_text
    )

    await extract_tests(source_id, context)

    units = await (await db.execute(READ_UNITS, (source_id,))).fetchall()
    assert units == [("Şiir", "Şiir")]
    assert await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall() == []


@pytest.mark.asyncio
async def test_unknown_unit_still_writes_questions_without_unit(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ünite ne addan ne başlıktan bulunursa sorular ünitesiz yazılır, inceleme açılmaz."""
    source_id, context = await prepare(
        db, tmp_path, monkeypatch, [make_test("Soru metni")], title="Bilinmeyen Yayınevi Denemesi"
    )

    await extract_tests(source_id, context)

    assert await (await db.execute(READ_UNITS, (source_id,))).fetchall() == [(None, None)]
    assert await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall() == []


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


LINK_KEY_SOURCE = """
WITH key_row AS (
    INSERT INTO source_document (title, kind, sha256, file_path, uploaded_by)
    SELECT 'CEVAP_ANAHTARI.pdf', 'ANSWER_KEY', repeat('e', 64), 'sources/1.pdf', uploaded_by
    FROM source_document WHERE id = %(source_id)s
    RETURNING id
)
UPDATE source_document SET answer_key_source_id = key_row.id
FROM key_row
WHERE source_document.id = %(source_id)s
RETURNING key_row.id
"""
FOOTER = "E) Teşhis\r\nŞiir - 4\r\n14"


def unanswered_test() -> list[ParsedQuestion]:
    """Cevabı sayfada olmayan üç soruluk testi kurar."""
    stems = ["Birinci soru metni", "İkinci soru metni", "Üçüncü soru metni"]
    return [
        build_question(number, stem=stem, correct_option=None)
        for number, stem in enumerate(stems, start=1)
    ]


async def link_key(
    db: Connection,
    context: IngestContext,
    monkeypatch: pytest.MonkeyPatch,
    source_id: int,
    text: str,
) -> int:
    """Teste ayrı cevap anahtarı kaynağı bağlar ve anahtarın metnini verir."""
    row = await (await db.execute(LINK_KEY_SOURCE, {"source_id": source_id})).fetchone()
    assert row is not None
    context.storage.write(source_key(int(row[0])), b"%PDF")
    monkeypatch.setattr(pdf, "read_text", lambda _content: text)
    return int(row[0])


@pytest.mark.asyncio
async def test_linked_answer_key_fills_answers_and_closes_old_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sonradan bağlanan anahtarın testteki bölümü sorulara yazılır, eski NO_ANSWER_KEY kapanır."""
    tests = [unanswered_test()]
    source_id, context = await prepare(db, tmp_path, monkeypatch, tests, page_text=FOOTER)
    await extract_tests(source_id, context)
    assert await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall() == [("NO_ANSWER_KEY",)]

    key = "Test 13 1. \r\nB 2. \r\nD 3. \r\nC\r\nTest 14 1. \r\nE 2. A 3. \r\nB\r\n"
    await link_key(db, context, monkeypatch, source_id, key)
    await extract_tests(source_id, context)

    links = await (await db.execute(READ_LINKS, (source_id,))).fetchall()
    assert [(position, answer) for _, position, answer, _ in links] == [
        (1, "E"),
        (2, "A"),
        (3, "B"),
    ]
    assert await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall() == []


@pytest.mark.asyncio
async def test_answer_key_with_extra_numbers_is_not_applied(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anahtar bölümünde testte olmayan numara varsa anahtar uygulanmaz."""
    source_id, context = await prepare(
        db, tmp_path, monkeypatch, [unanswered_test()], page_text=FOOTER
    )
    await link_key(db, context, monkeypatch, source_id, "Test 14 1. E 2. A 3. B 4. C")

    await extract_tests(source_id, context)

    assert await (await db.execute(COUNT_QUESTIONS, (source_id,))).fetchone() == (0,)
    assert await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall() == [("NO_ANSWER_KEY",)]


@pytest.mark.asyncio
async def test_answer_key_source_without_answers_opens_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cevap çıkmayan anahtar dosyası incelemeye düşer; okunabilir hale gelince kayıt kapanır."""
    source_id, context = await prepare(db, tmp_path, monkeypatch, [])

    monkeypatch.setattr(pdf, "read_text", lambda _content: "CEVAP ANAHTARI\n12. Sınıf")
    await check_answer_key(source_id, context)
    assert await review_details(db, source_id) == {"VALIDATION_FAILED": [{"code": "NO_CONTENT"}]}

    monkeypatch.setattr(pdf, "read_text", lambda _content: "Test 1 1. C 2. D")
    await check_answer_key(source_id, context)
    assert await (await db.execute(COUNT_REVIEWS, (source_id,))).fetchall() == []
