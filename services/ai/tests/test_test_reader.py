"""Test okuyucusunun kontrol katmanını (#130) elle kurulan sorularla ve gerçek Postgres'le sınar.

Sorun bulma ve özet saf işlevlerdir; inceleme kaydı testi kendi kaynak satırını yazar ve test
bitince geri alınır.
"""

import psycopg
import pytest
from psycopg.rows import TupleRow

from app.db.queries.question import content_hash
from app.ingest.readers.test import (
    answer_problems,
    failed_problems,
    find_problems,
    report_problems,
)
from app.ingest.validators import ValidationProblem
from app.schemas.pdf import QuestionReading
from tests.test_pipeline import make_source
from tests.test_validators import build_question

Connection = psycopg.AsyncConnection[TupleRow]

COUNT_REVIEWS = """
SELECT count(*) FROM review_item
WHERE source_document_id = %s AND reason = %s AND status = 'OPEN'
"""
READ_STATUS = "SELECT status FROM source_document WHERE id = %s"


def test_clean_reading_has_no_problems() -> None:
    """Cevabı bulunan ve kontrolleri geçen sorularda sorun yoktur."""
    problems = find_problems([[build_question(1), build_question(2)]])

    assert problems.is_clean


def test_question_without_answer_is_reported_as_missing() -> None:
    """Cevabı bulunamayan soru, testi ve numarasıyla NO_ANSWER_KEY adayıdır."""
    problems = find_problems(
        [[build_question(1)], [build_question(1), build_question(2, correct_option=None)]]
    )

    assert [(m.test_index, m.number) for m in problems.missing_answers] == [(1, 2)]
    assert problems.failed == []


def test_question_failing_checks_is_reported_with_its_problems() -> None:
    """A6 kontrolünden geçemeyen soru VALIDATION_FAILED adayıdır; eksik cevap sayılmaz."""
    broken = build_question(2, labels=["A", "B", "C", "D"])

    problems = find_problems([[build_question(1), broken]])

    [failed] = problems.failed
    assert (failed.test_index, failed.check.number) == (0, 2)
    assert failed.check.problems == [ValidationProblem.OPTION_COUNT]
    assert problems.missing_answers == []


def test_same_question_gets_same_hash_and_other_question_differs() -> None:
    """Aynı içerik aynı özeti verir; biçim ve büyük-küçük harf farkı özeti değiştirmez."""
    first = build_question(1, stem="Aşağıdakilerden hangisi doğrudur?")
    again = build_question(7, stem="aşağıdakilerden  *hangisi* doğrudur?")
    other = build_question(1, stem="Aşağıdakilerden hangisi yanlıştır?")

    assert content_hash(first.content) == content_hash(again.content)
    assert content_hash(first.content) != content_hash(other.content)
    assert len(content_hash(first.content)) == 64


@pytest.mark.asyncio
async def test_problems_open_one_review_per_reason_and_mark_source_review(db: Connection) -> None:
    """Cevapsız ve kontrolü geçemeyen soru ayrı neden açar; tekrar çalışınca kopya olmaz."""
    source_id = await make_source(db)
    tests = [[build_question(1, correct_option=None), build_question(2, labels=["A", "B"])]]
    problems = find_problems(tests)
    reading = QuestionReading(tests=tests, pages=[])
    failed = failed_problems(reading, problems)

    await report_problems(db, source_id, answer_problems(problems), failed)
    await report_problems(db, source_id, answer_problems(problems), failed)

    for reason in ("NO_ANSWER_KEY", "VALIDATION_FAILED"):
        row = await (await db.execute(COUNT_REVIEWS, (source_id, reason))).fetchone()
        assert row == (1,)
    assert await (await db.execute(READ_STATUS, (source_id,))).fetchone() == ("REVIEW",)


@pytest.mark.asyncio
async def test_clean_reading_opens_no_review(db: Connection) -> None:
    """Sorun yoksa kayıt açılmaz ve kaynak durumu değişmez."""
    source_id = await make_source(db)

    await report_problems(db, source_id, [], [])

    row = await (await db.execute(COUNT_REVIEWS, (source_id, "NO_ANSWER_KEY"))).fetchone()
    assert row == (0,)
    assert await (await db.execute(READ_STATUS, (source_id,))).fetchone() == ("UPLOADED",)
