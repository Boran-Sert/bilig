"""Test okuyucusu (hazırlık hattı A5, EXTRACT adımının test dalı, #130, #269, #274, #275).

PDF dış yüzünün (pdf.read_questions) testlere bölünmüş soruları incelenir: cevabı bulunamayan
soru NO_ANSWER_KEY, A6 kontrollerinden (validators.py) geçemeyen soru VALIDATION_FAILED olur ve
yazılmaz. Kaynaktan hiç soru çıkmaması, metin katmanı bozuk kalan ya da harfi çözülemeyen sayfa ve
kökünde soru olmadığı için atılan şık kümesi de VALIDATION_FAILED'a girer. Her neden için kaynakta
bir inceleme kaydı açılır; ayrıntısında her sorun testi, soru numarası ve sayfasıyla durur
(db/queries/review.py). Kalan sorular testin sırasıyla question, exam ve exam_question tablolarına
yazılır. Ünite ipucu kaynak adından, o da yoksa ilk sayfanın "Şiir - 4" biçimli başlığından
bulunur (data/unit_map.txt); bulunamazsa sorular ünitesiz yazılır ve ünite kazanım eşleştirmesinde
bağlanan kazanımlardan çıkarılır. Doğru şık question.correct_option'a gider, content'e girmez.
Teste ayrı bir cevap anahtarı dosyası bağlıysa (source_document.answer_key_source_id) anahtarın
bu testin numarasındaki bölümü sorulara yazılır; anahtar soru numaralarına uymazsa (fazla numara,
çelişen cevap) hiç uygulanmaz ve sorular NO_ANSWER_KEY'e düşer. Yeniden okumada bir nedenden sorun
kalmadıysa o nedenin eski açık kaydı kapanır.
"""

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING

import structlog
from psycopg import AsyncConnection
from pydantic import BaseModel

from app.config import load_ingest_settings
from app.db.queries.question import save_exam
from app.db.queries.review import SourceReviewReason, close_source_review, open_source_review
from app.db.queries.source import fetch_answer_key_source_id, fetch_source_title
from app.db.queries.unit import fetch_unit_id
from app.ingest import pdf
from app.ingest.readers.answer_key import attach_answers, find_test_number, key_for_test
from app.ingest.unit_map import find_unit_heading, find_unit_title, load_unit_map
from app.ingest.validators import QuestionCheck, page_problems, validate_questions
from app.schemas.pdf import QuestionReading
from app.schemas.question import ParsedQuestion
from app.schemas.review import SourceProblem
from app.storage import source_key

if TYPE_CHECKING:
    from app.ingest.pipeline import IngestContext


class MissingAnswer(BaseModel):
    """Cevabı bulunamayan sorunun testi, numarası (numarasız soruda boş) ve sayfası."""

    test_index: int
    number: int | None
    page_no: int


class FailedQuestion(BaseModel):
    """Kontrolden geçemeyen sorunun testi ve kontrol sonucu."""

    test_index: int
    check: QuestionCheck


class ReadingProblems(BaseModel):
    """Okumanın incelemeye düşecek soruları."""

    missing_answers: list[MissingAnswer]
    failed: list[FailedQuestion]

    @property
    def is_clean(self) -> bool:
        """Cevapsız ya da kontrolden geçemeyen soru yoksa doğru döner."""
        return not self.missing_answers and not self.failed


def find_problems(tests: Sequence[Sequence[ParsedQuestion]]) -> ReadingProblems:
    """Her testin sorularını cevap ve A6 kontrolleri açısından inceler."""
    missing = [
        MissingAnswer(test_index=index, number=question.number, page_no=question.page_no)
        for index, test in enumerate(tests)
        for question in test
        if question.correct_option is None
    ]
    failed = [
        FailedQuestion(test_index=index, check=check)
        for index, test in enumerate(tests)
        for check in validate_questions(test)
    ]
    return ReadingProblems(missing_answers=missing, failed=failed)


def answer_problems(problems: ReadingProblems) -> list[SourceProblem]:
    """Cevabı bulunamayan soruları inceleme ayrıntısına çevirir."""
    return [
        SourceProblem(
            code="NO_ANSWER_KEY", test=item.test_index + 1, number=item.number, page_no=item.page_no
        )
        for item in problems.missing_answers
    ]


def failed_problems(reading: QuestionReading, problems: ReadingProblems) -> list[SourceProblem]:
    """Okumanın VALIDATION_FAILED'a düşecek bütün sorunlarını ayrıntısıyla toplar."""
    found = [
        SourceProblem(
            code=problem.value,
            test=item.test_index + 1,
            number=item.check.number,
            page_no=reading.tests[item.test_index][item.check.index].page_no,
        )
        for item in problems.failed
        for problem in item.check.problems
    ]
    found += page_problems(reading.pages)
    found += [
        SourceProblem(code="NOT_MULTIPLE_CHOICE", page_no=page_no)
        for page_no in reading.not_multiple_choice_pages
    ]
    if not any(reading.tests):
        found.append(SourceProblem(code="NO_CONTENT"))
    return found


async def report_problems(
    connection: AsyncConnection,
    source_id: int,
    missing: list[SourceProblem],
    failed: list[SourceProblem],
) -> None:
    """Her neden için sorun varsa ayrıntılı kayıt açar, yoksa o nedenin açık kaydını kapatır."""
    reviews: list[tuple[SourceReviewReason, list[SourceProblem]]] = [
        ("NO_ANSWER_KEY", missing),
        ("VALIDATION_FAILED", failed),
    ]
    for reason, problems in reviews:
        if problems:
            await open_source_review(connection, source_id, reason, problems)
        else:
            await close_source_review(connection, source_id, reason)


def writable_questions(
    tests: Sequence[Sequence[ParsedQuestion]], problems: ReadingProblems
) -> list[list[ParsedQuestion]]:
    """Cevabı bulunan ve kontrolü geçen soruları testlerine göre ayırır."""
    failed = {(item.test_index, item.check.index) for item in problems.failed}
    return [
        [
            question
            for index, question in enumerate(test)
            if question.correct_option is not None and (test_index, index) not in failed
        ]
        for test_index, test in enumerate(tests)
    ]


def answer_from_key(
    tests: list[list[ParsedQuestion]], key_text: str, page_text: str
) -> list[list[ParsedQuestion]]:
    """Bağlı anahtarın bu testteki cevaplarını tek testli kaynağa yazar; uymazsa dokunmaz."""
    test_number = find_test_number(page_text)
    try:
        key = key_for_test(key_text, test_number) if len(tests) == 1 else {}
    except ValueError:
        key = {}
    attached = attach_answers(tests[0], key) if key else None
    if attached is None or attached.conflicting or attached.unused:
        structlog.get_logger().warning(
            "answer key not applied",
            test_number=test_number,
            tests=len(tests),
            conflicting=attached.conflicting if attached else [],
            unused=attached.unused if attached else [],
        )
        return tests
    return [attached.questions]


async def read_linked_key(
    connection: AsyncConnection, context: "IngestContext", source_id: int
) -> str | None:
    """Teste bağlı cevap anahtarı dosyasının metnini okur; bağlı anahtar yoksa boş döner."""
    key_source_id = await fetch_answer_key_source_id(connection, source_id)
    if key_source_id is None:
        return None
    content = await asyncio.to_thread(context.storage.read, source_key(key_source_id))
    return await asyncio.to_thread(pdf.read_text, content)


async def extract_tests(source_id: int, context: "IngestContext") -> None:
    """Test PDF'inin sorularını okur, sorunları incelemeye ayırır, kalanını yazar."""
    content = await asyncio.to_thread(context.storage.read, source_key(source_id))
    reading = await asyncio.to_thread(pdf.read_questions, content)
    page_text = await asyncio.to_thread(pdf.read_first_page_text, content)
    rules = load_unit_map(load_ingest_settings().unit_map_path)
    async with context.connect() as connection:
        key_text = await read_linked_key(connection, context, source_id)
        if key_text is not None:
            tests = answer_from_key(reading.tests, key_text, page_text)
            reading = reading.model_copy(update={"tests": tests})
        problems = find_problems(reading.tests)
        title = await fetch_source_title(connection, source_id)
        unit_title = find_unit_title(title, rules) or find_unit_heading(page_text, rules)
        unit_id = await fetch_unit_id(connection, source_id, unit_title) if unit_title else None
        failed = failed_problems(reading, problems)
        await report_problems(connection, source_id, answer_problems(problems), failed)
        if unit_id is None:
            structlog.get_logger().info("unit hint not found", source_id=source_id, title=title)
        for number, questions in enumerate(writable_questions(reading.tests, problems), start=1):
            await save_exam(connection, source_id, unit_id, f"{title} Test {number}", questions)
