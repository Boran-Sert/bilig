"""Kontrol setinin (data/kontrol_seti/sorular.jsonl) sözleşmeye uyduğunu test eder."""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

CONTROL_SET = Path(__file__).resolve().parents[3] / "data" / "kontrol_seti" / "sorular.jsonl"
QUESTION_COUNT = 100
FIELDS = {"id", "source", "unit", "stem", "options", "correct", "outcomes"}
OPTION_KEYS = ["A", "B", "C", "D", "E"]
UNITS = {"Giriş", "Hikâye", "Şiir", "Roman", "Tiyatro", "Deneme - Söylev (Nutuk)"}
SOURCE_PATTERN = re.compile(r"^ÖDSGM 12 (?P<unit>.+) Kazanım Testi \d{1,2}, Soru \d{1,2}$")
OUTCOME_CODE_PATTERN = re.compile(r"^(A\.[1-4]\.\d{1,2}|B\.\d{1,2}|C\.[12]\.\d{1,2})$")


def read_lines() -> list[str]:
    """Dosyanın satırlarını satır sonu ayırmadan döndürür."""
    return CONTROL_SET.read_text(encoding="utf-8").splitlines()


@pytest.fixture(scope="module")
def questions() -> list[dict[str, Any]]:
    """Her satırı JSON olarak okur."""
    return [json.loads(line) for line in read_lines()]


def test_every_line_is_a_json_object() -> None:
    """Dosya geçerli JSONL'dir: boş satır yoktur, her satır bir JSON nesnesidir."""
    lines = read_lines()

    assert lines
    for number, line in enumerate(lines, start=1):
        assert line.strip(), f"satır {number} boş"
        assert isinstance(json.loads(line), dict), f"satır {number} nesne değil"


def test_has_exactly_hundred_questions(questions: list[dict[str, Any]]) -> None:
    """Sette tam 100 soru vardır."""
    assert len(questions) == QUESTION_COUNT


def test_ids_are_sequential(questions: list[dict[str, Any]]) -> None:
    """Kimlikler ks-001'den ks-100'e sırayla gider."""
    expected = [f"ks-{number:03d}" for number in range(1, QUESTION_COUNT + 1)]

    assert [question["id"] for question in questions] == expected


def test_fields_match_contract(questions: list[dict[str, Any]]) -> None:
    """Her soruda sözleşmedeki alanlar vardır, fazlası yoktur."""
    for question in questions:
        assert set(question) == FIELDS, question["id"]


def test_question_text_is_not_empty(questions: list[dict[str, Any]]) -> None:
    """Soru kökü ve beş şıkkın her biri dolu metindir."""
    for question in questions:
        assert isinstance(question["stem"], str) and question["stem"].strip(), question["id"]
        assert list(question["options"]) == OPTION_KEYS, question["id"]
        for text in question["options"].values():
            assert isinstance(text, str) and text.strip(), question["id"]


def test_text_is_clean_unicode() -> None:
    """Dosya NFC'dir; satır başı (CR) ve yumuşak tire (U+00AD) içermez."""
    content = CONTROL_SET.read_bytes().decode("utf-8")

    assert unicodedata.is_normalized("NFC", content)
    assert "\r" not in content
    assert "­" not in content


def test_correct_answer_is_an_option(questions: list[dict[str, Any]]) -> None:
    """Doğru cevap A-E harflerinden biridir."""
    for question in questions:
        assert question["correct"] in OPTION_KEYS, question["id"]


def test_outcomes_is_a_list_of_codes(questions: list[dict[str, Any]]) -> None:
    """Her soruda en az bir kazanım vardır; kodlar tekrarsızdır ve programın biçimindedir."""
    for question in questions:
        outcomes = question["outcomes"]
        assert isinstance(outcomes, list) and outcomes, question["id"]
        assert all(OUTCOME_CODE_PATTERN.match(code) for code in outcomes), question["id"]
        assert len(outcomes) == len(set(outcomes)), question["id"]


def test_every_unit_is_represented(questions: list[dict[str, Any]]) -> None:
    """12. sınıfın her ünitesinden soru vardır, liste dışı ünite yoktur."""
    counts = Counter(question["unit"] for question in questions)

    assert set(counts) == UNITS


def test_source_names_unit_and_question(questions: list[dict[str, Any]]) -> None:
    """Kaynak testi ve soru numarasını verir, ünitesi soruyla aynıdır, tekrar etmez."""
    sources = [question["source"] for question in questions]

    assert len(sources) == len(set(sources))
    for question in questions:
        match = SOURCE_PATTERN.match(question["source"])
        assert match, question["id"]
        assert match.group("unit") == question["unit"], question["id"]
