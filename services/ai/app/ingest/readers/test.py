"""Test okuyucusunun kontrol katmanı (hazırlık hattı A5, #130).

PDF dış yüzünün (pdf.read_questions) testlere bölünmüş soruları burada incelenir: cevabı
bulunamayan soru NO_ANSWER_KEY, A6 kontrollerinden (validators.py) geçemeyen soru
VALIDATION_FAILED olur. Cevap doğru şıkkı question.correct_option'a gider, content'e girmez.
content_hash sorunun metninden çıkar; aynı soru ikinci kez eklenmesin diye question tablosunda
tektir. Sorunlu soru yazılmaz, kaynak için inceleme kaydı açılır (db/queries/review.py).
Soruları question tablosuna yazmak ünite kararı (question.curriculum_unit_id) beklediği için bu
dosyada yoktur.
"""

import hashlib
from collections.abc import Sequence

from psycopg import AsyncConnection
from pydantic import BaseModel

from app.db.queries.review import open_source_review
from app.ingest.validators import QuestionCheck, normalize_for_comparison, validate_questions
from app.schemas.question import ParsedQuestion, QuestionContent


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


def content_hash(content: QuestionContent) -> str:
    """Sorunun içeriğinden 64 karakterlik özet üretir; biçim farkları özeti değiştirmez."""
    text = normalize_for_comparison(content.to_text())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def report_problems(
    connection: AsyncConnection, source_id: int, problems: ReadingProblems
) -> None:
    """Sorun varsa nedenine göre kaynak için inceleme kaydı açar; yoksa dokunmaz."""
    if problems.missing_answers:
        await open_source_review(connection, source_id, "NO_ANSWER_KEY")
    if problems.failed:
        await open_source_review(connection, source_id, "VALIDATION_FAILED")
