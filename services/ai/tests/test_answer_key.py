"""Cevap anahtarı okuyucusunu test eder (hazırlık hattı A5).

Anahtar metinleri gerçek biçimlerin elle yazılmış örnekleridir: tek satırlık "1-B 2-E", alt alta
"1. C" ve ÖDSGM'nin birden çok testi "Test N" başlıklarıyla tek sayfada veren anahtarı.
"""

import pytest

from app.ingest.readers.answer_key import (
    AttachedAnswers,
    attach_answers,
    find_inline_answer,
    is_answer_key,
    parse_answer_key,
    split_by_test,
)
from app.schemas.question import Block, OptionLabel, ParsedQuestion, QuestionContent

MULTI_TEST_KEY = """CEVAP ANAHTARI
12. Sınıf
Türk Dili ve
Edebiyatı
Test 1
1. C
2. C
3. D
Test 2
1. B
2. E
TEST 10
1. A
"""


def build_question(number: int, correct_option: OptionLabel | None = None) -> ParsedQuestion:
    """Sadece numarası ve cevabı önemli olan soru kurar."""
    content = QuestionContent(stem=[Block(type="paragraph", md="Kök")], options=[])
    return ParsedQuestion(number=number, page_no=1, content=content, correct_option=correct_option)


@pytest.mark.parametrize(
    "text",
    [
        "1-B 2-E 3-A",
        "1. B\n2. E\n3. A",
        "1) B   2) E   3) A",
        "1.B 2:E 3 – A",
        "Cevaplar: 1-B, 2-E, 3-A.",
    ],
    ids=["dash", "lines", "parenthesis", "mixed", "sentence"],
)
def test_parse_answer_key_reads_common_formats(text: str) -> None:
    """Yaygın anahtar yazımları numara → şık olarak okunur."""
    assert parse_answer_key(text) == {1: "B", 2: "E", 3: "A"}


@pytest.mark.parametrize(
    "text",
    ["12. Sınıf", "1. Ahmet Haşim", "1.5-E", "2018-A", "10. Fen", "1. b", "Ünite 2 A grubu"],
    ids=["grade", "word", "decimal", "year", "word-after-letter", "lowercase", "no-separator"],
)
def test_parse_answer_key_ignores_text_that_only_looks_like_an_answer(text: str) -> None:
    """Başlık, sayı ve kelime parçaları cevap sanılmaz."""
    assert parse_answer_key(text) == {}


def test_parse_answer_key_accepts_repeated_same_answer() -> None:
    """Aynı cevabın iki kez yazılması sorun değildir."""
    assert parse_answer_key("1-A 2-B 1-A") == {1: "A", 2: "B"}


def test_parse_answer_key_rejects_conflicting_answers() -> None:
    """Aynı soruya iki farklı cevap yazılmışsa okuma hatayla durur."""
    with pytest.raises(ValueError, match="two answers for question 1"):
        parse_answer_key("1-A 2-B 1-C")


def test_split_by_test_reads_each_section_of_multi_test_key() -> None:
    """Çok testli anahtar başlıklarına bölünür, her bölüm kendi testinin anahtarıdır."""
    sections = split_by_test(MULTI_TEST_KEY)

    assert {number: parse_answer_key(text) for number, text in sections.items()} == {
        1: {1: "C", 2: "C", 3: "D"},
        2: {1: "B", 2: "E"},
        10: {1: "A"},
    }


def test_whole_multi_test_key_is_not_one_key() -> None:
    """Çok testli anahtar bölünmeden okunursa çakışan cevaplar hatayla yakalanır."""
    with pytest.raises(ValueError, match="two answers"):
        parse_answer_key(MULTI_TEST_KEY)


def test_split_by_test_rejects_repeated_test_heading() -> None:
    """Aynı test başlığı iki kez geçerse bölme hatayla durur."""
    with pytest.raises(ValueError, match="two sections for test 1"):
        split_by_test("Test 1\n1. A\nTest 1\n1. B")


def test_split_by_test_ignores_heading_inside_sentence() -> None:
    """Satırın tamamı olmayan "Test 3" başlık sayılmaz; başlıksız metin bölüm vermez."""
    assert split_by_test("Bu Test 3 için cevaplar: 1-A") == {}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hangisidir?\nA) x\nB) y\nCevap: D", "D"),
        ("CEVAP : B", "B"),
        ("Yanıt: E", "E"),
        ("YANIT: C.", "C"),
        ("Doğru cevap: A", "A"),
        ("cevap: B", "B"),
        ("Hangisi cevap değildir?", None),
        ("Cevap: Doğru", None),
        ("Cevap: a", None),
        ("Bu soruda Cevap: D olmalı", None),
    ],
    ids=[
        "below-question",
        "upper-spaced",
        "yanit",
        "upper-yanit-period",
        "dogru-cevap",
        "lowercase-word",
        "no-answer",
        "word",
        "lowercase-letter",
        "inside-sentence",
    ],
)
def test_find_inline_answer(text: str, expected: OptionLabel | None) -> None:
    """Kendi satırındaki "Cevap: A" okunur; cümle içindeki ve benzeyen yazımlar cevap sayılmaz."""
    assert find_inline_answer(text) == expected


def test_attach_answers_writes_key_and_reports_missing_and_unused() -> None:
    """Anahtardaki cevap yazılır; cevapsız soru ve hiçbir soruya denk gelmeyen anahtar ayrılır."""
    questions = [build_question(1), build_question(2, correct_option="E"), build_question(3)]

    result = attach_answers(questions, {1: "C", 2: "E", 7: "A"})

    assert [question.correct_option for question in result.questions] == ["C", "E", None]
    assert (result.missing, result.conflicting, result.unused) == ([3], [], [7])
    assert [question.correct_option for question in questions] == [None, "E", None]


def test_attach_answers_reports_key_and_inline_conflict() -> None:
    """Anahtar sorunun altındaki cevapla çelişirse anahtar yazılır, numara çelişen olarak döner."""
    result = attach_answers([build_question(1, correct_option="B")], {1: "D"})

    assert result == AttachedAnswers(
        questions=[build_question(1, correct_option="D")], missing=[], conflicting=[1], unused=[]
    )


def test_attach_answers_keeps_inline_answer_when_key_has_none() -> None:
    """Anahtarda olmayan ama sorunun altında cevabı bulunan soru eksik sayılmaz."""
    result = attach_answers([build_question(1, correct_option="B")], {})

    assert result.questions[0].correct_option == "B"
    assert result.missing == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (MULTI_TEST_KEY, True),
        ("1-A 2-B 3-C 4-D 5-E", True),
        ("Cevap Anahtarı\n1. A", True),
        ("1-A 2-B 3-C 4-D", False),
        ("2-A 3-B 4-C 5-D 6-E", False),
        ("1. Aşağıdakilerden hangisi doğrudur?\nA) x\nB) y", False),
    ],
    ids=["heading", "five-entries", "heading-few", "four-entries", "not-from-one", "question"],
)
def test_is_answer_key(text: str, expected: bool) -> None:
    """Anahtar başlığı ya da 1'den başlayan en az beş cevap taşıyan metin anahtar sayılır."""
    assert is_answer_key(text) is expected


def test_answer_split_across_lines_is_read() -> None:
    """Tablo düzeninde numara ve şık ayrı satıra düşse de okunur."""
    assert parse_answer_key("1.\nB\n2.\nE") == {1: "B", 2: "E"}


def test_split_by_test_accepts_heading_with_colon() -> None:
    """İki noktalı "TEST 3:" başlığı da bölüm açar."""
    assert split_by_test("TEST 3:\n1. A") == {3: "\n1. A"}
