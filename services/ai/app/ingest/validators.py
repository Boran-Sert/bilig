"""Ayrıştırılan içeriğin kontrolleri (hazırlık hattı A6).

Sorularda beş şık (A-E sırasıyla, hiçbiri boş değil), dolu kök, şıklardan biri olan cevap ve
1'den başlayıp birer artan numara aranır; numara kontrolü bir testin bütün soruları için çağrılır,
numarasız soru bu sıraya girmez.
Cevap anahtarı hiç bulunamayan soru burada değil, okuyucuda NO_ANSWER_KEY olarak incelemeye düşer
(#130); bu yüzden boş cevap sorun sayılmaz. Görüntüden üretilen metin, sayfanın metin katmanı
varsa ona en az TEXT_SIMILARITY_MIN_RATIO oranında benzemelidir. Benzerlik markdown işaretleri,
tablo ayırıcı satırları, liste imleri, satır sonu tireleri, yumuşak tireler, boşluk ve büyük-küçük
harf farkları atılarak rapidfuzz ile ölçülür; okuma sırası farklıysa benzerlik düşer. Kontroller
sadece sorunları döner; geçemeyen içeriği inceleme listesine (VALIDATION_FAILED) sonraki hazırlık
adımı yazar. Okuma raporunda metin katmanı bozuk kalan (LOW_TEXT_LAYER) ya da harfi çözülemeyen
(UNDECODED_GLYPHS) sayfa da sorundur.
"""

import re
from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel
from rapidfuzz import fuzz

from app.constants import TEXT_SIMILARITY_MIN_RATIO
from app.schemas.pdf import PageReport
from app.schemas.question import OPTION_LABELS, Block, ParsedQuestion
from app.schemas.review import ProblemCode, SourceProblem
from app.text.turkish import normalize_nfc, tr_lower

_TABLE_SEPARATOR = re.compile(
    r"^[ \t]*\|?(?:[ \t]*:?-+:?[ \t]*\|)+[ \t]*(?::?-+:?[ \t]*)?$", re.MULTILINE
)
_LIST_MARKER = re.compile(r"^[ \t]*[-+•][ \t]+", re.MULTILINE)
_MARKDOWN_MARK = re.compile(r"\*\*|\*|</?u>|\|")
_HYPHEN_BREAK = re.compile(r"(\w)-[ \t]*\n\s*(\w)")
_SOFT_HYPHEN = re.compile(r"\N{SOFT HYPHEN}\s*")
_WHITESPACE = re.compile(r"\s+")
_HORIZONTAL_SPACE = re.compile(r"[ \t]+")
_PAGE_NOTE_PROBLEMS: dict[str, ProblemCode] = {
    "LOW_TEXT_LAYER": "LOW_TEXT_LAYER",
    "UNDECODED_GLYPHS": "UNDECODED_GLYPHS",
}


class ValidationProblem(StrEnum):
    """Bir sorunun geçemediği kontrol."""

    OPTION_COUNT = "OPTION_COUNT"
    OPTION_LABELS = "OPTION_LABELS"
    EMPTY_OPTION = "EMPTY_OPTION"
    EMPTY_STEM = "EMPTY_STEM"
    ANSWER_NOT_OPTION = "ANSWER_NOT_OPTION"
    NUMBER_SEQUENCE = "NUMBER_SEQUENCE"


class QuestionCheck(BaseModel):
    """Kontrolden geçemeyen sorunun listedeki yeri, numarası ve sorunları."""

    index: int
    number: int | None
    problems: list[ValidationProblem]


def validate_questions(questions: Sequence[ParsedQuestion]) -> list[QuestionCheck]:
    """Bir testin sorularını tek tek ve numara sırasıyla kontrol eder; sorunlu olanları döner."""
    numbered = [(index, q.number) for index, q in enumerate(questions) if q.number is not None]
    positions = positions_out_of_sequence([number for _, number in numbered])
    out_of_sequence = {numbered[position][0] for position in positions}
    checks = []
    for index, question in enumerate(questions):
        problems = check_question(question)
        if index in out_of_sequence:
            problems.append(ValidationProblem.NUMBER_SEQUENCE)
        if problems:
            checks.append(QuestionCheck(index=index, number=question.number, problems=problems))
    return checks


def check_question(question: ParsedQuestion) -> list[ValidationProblem]:
    """Tek sorunun şıklarını, kökünü ve cevabını kontrol eder."""
    options = question.content.options
    labels = tuple(option.label for option in options)
    problems = []
    if len(options) != len(OPTION_LABELS):
        problems.append(ValidationProblem.OPTION_COUNT)
    if labels != OPTION_LABELS[: len(labels)]:
        problems.append(ValidationProblem.OPTION_LABELS)
    if any(is_empty(option.blocks) for option in options):
        problems.append(ValidationProblem.EMPTY_OPTION)
    if is_empty(question.content.stem):
        problems.append(ValidationProblem.EMPTY_STEM)
    if question.correct_option is not None and question.correct_option not in labels:
        problems.append(ValidationProblem.ANSWER_NOT_OPTION)
    return problems


def positions_out_of_sequence(numbers: Sequence[int]) -> list[int]:
    """1'den başlayıp birer artmayan soru numaralarının listedeki yerlerini döner."""
    positions = []
    expected = 1
    for position, number in enumerate(numbers):
        if number != expected:
            positions.append(position)
        expected = number + 1
    return positions


def is_empty(blocks: Sequence[Block]) -> bool:
    """Bloklarda markdown işaretleri dışında hiç metin yoksa doğru döner."""
    return not any(normalize_for_comparison(block.md) for block in blocks)


def text_similarity(extracted: str, text_layer: str) -> float:
    """Üretilen metnin metin katmanına benzerliğini 0 ile 1 arasında verir."""
    return (
        fuzz.ratio(normalize_for_comparison(extracted), normalize_for_comparison(text_layer)) / 100
    )


def matches_text_layer(extracted: str, text_layer: str) -> bool:
    """Üretilen metin katmana yeterince benziyorsa doğru döner; katmansız sayfada çağrılmaz."""
    return text_similarity(extracted, text_layer) >= TEXT_SIMILARITY_MIN_RATIO


def normalize_for_comparison(text: str) -> str:
    """Markdown işaretlerini, satır sonu tirelerini ve boşluk farklarını atıp küçültür."""
    spaced = _HORIZONTAL_SPACE.sub(" ", _SOFT_HYPHEN.sub("", normalize_nfc(text)))
    joined = _HYPHEN_BREAK.sub(r"\1\2", spaced)
    plain = _MARKDOWN_MARK.sub(" ", _LIST_MARKER.sub("", _TABLE_SEPARATOR.sub(" ", joined)))
    return tr_lower(_WHITESPACE.sub(" ", plain).strip())


def page_problems(pages: Sequence[PageReport]) -> list[SourceProblem]:
    """Metin katmanı bozuk kalan ya da harfi çözülemeyen sayfaları sorun olarak döner."""
    return [
        SourceProblem(code=_PAGE_NOTE_PROBLEMS[note], page_no=page.page_no)
        for page in pages
        for note in page.notes
        if note in _PAGE_NOTE_PROBLEMS
    ]
