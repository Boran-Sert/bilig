"""Test okuyucusu (hazırlık hattı A5, EXTRACT adımının test dalı, #130).

PDF dış yüzünün (pdf.read_questions) testlere bölünmüş soruları incelenir: cevabı bulunamayan
soru NO_ANSWER_KEY, A6 kontrollerinden (validators.py) geçemeyen soru VALIDATION_FAILED olur.
Sorunlu soru yazılmaz, kaynak için inceleme kaydı açılır (db/queries/review.py). Kalan sorular
kaynak adından bulunan ünite (data/unit_map.txt) ve testin sırasıyla question, exam ve
exam_question tablolarına yazılır. Ünite bulunamazsa hiçbir soru yazılmaz ve kaynak
VALIDATION_FAILED ile incelemeye düşer. Doğru şık question.correct_option'a gider, content'e girmez.
"""

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING

import structlog
from psycopg import AsyncConnection
from pydantic import BaseModel

from app.config import load_ingest_settings
from app.db.queries.question import save_exam
from app.db.queries.review import open_source_review
from app.db.queries.source import fetch_source_title
from app.db.queries.unit import fetch_unit_id
from app.ingest import pdf
from app.ingest.unit_map import find_unit_title, load_unit_map
from app.ingest.validators import QuestionCheck, validate_questions
from app.schemas.question import ParsedQuestion
from app.storage import source_key

if TYPE_CHECKING:
    from app.ingest.pipeline import IngestContext


class MissingAnswer(BaseModel):
    """Cevabı bulunamayan sorunun testi ve numarası (numarasız soruda boş)."""

    test_index: int
    number: int | None


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
        MissingAnswer(test_index=index, number=question.number)
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


async def report_problems(
    connection: AsyncConnection, source_id: int, problems: ReadingProblems
) -> None:
    """Sorun varsa nedenine göre kaynak için inceleme kaydı açar; yoksa dokunmaz."""
    if problems.missing_answers:
        await open_source_review(connection, source_id, "NO_ANSWER_KEY")
    if problems.failed:
        await open_source_review(connection, source_id, "VALIDATION_FAILED")


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


async def extract_tests(source_id: int, context: "IngestContext") -> None:
    """Test PDF'inin sorularını okur, sorunluları incelemeye ayırır, kalanını yazar."""
    content = await asyncio.to_thread(context.storage.read, source_key(source_id))
    reading = await asyncio.to_thread(pdf.read_questions, content)
    problems = find_problems(reading.tests)
    async with context.connect() as connection:
        title = await fetch_source_title(connection, source_id)
        unit_title = find_unit_title(title, load_unit_map(load_ingest_settings().unit_map_path))
        unit_id = await fetch_unit_id(connection, source_id, unit_title) if unit_title else None
        await report_problems(connection, source_id, problems)
        if unit_id is None:
            structlog.get_logger().warning("unit not found", source_id=source_id, title=title)
            await open_source_review(connection, source_id, "VALIDATION_FAILED")
            return
        for number, questions in enumerate(writable_questions(reading.tests, problems), start=1):
            await save_exam(connection, source_id, unit_id, f"{title} Test {number}", questions)
