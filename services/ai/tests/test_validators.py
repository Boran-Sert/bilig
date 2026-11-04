"""Ayrıştırılan içeriğin kontrollerini test eder (hazırlık hattı A6).

Kurallar elle kurulan sorularla ölçülür; kontrol setindeki (data/kontrol_seti) 100 gerçek ÖDSGM
sorusu da hiçbir kontrole takılmamalıdır.
"""

import json
import time
from pathlib import Path

import pytest

from app.ingest.validators import (
    QuestionCheck,
    ValidationProblem,
    check_question,
    matches_text_layer,
    normalize_for_comparison,
    page_problems,
    positions_out_of_sequence,
    text_similarity,
    validate_questions,
)
from app.schemas.pdf import PageReport
from app.schemas.question import (
    Block,
    OptionLabel,
    ParsedQuestion,
    QuestionContent,
    QuestionOption,
)
from app.schemas.review import SourceProblem

LABELS: list[OptionLabel] = ["A", "B", "C", "D", "E"]
CONTROL_SET = Path(__file__).resolve().parents[3] / "data" / "kontrol_seti" / "sorular.jsonl"


def paragraph(md: str) -> Block:
    """Tek paragraflık blok kurar."""
    return Block(type="paragraph", md=md)


def build_question(
    number: int = 1,
    labels: list[OptionLabel] | None = None,
    stem: str = "Aşağıdakilerden hangisi *Kiralık Konak* romanının yazarıdır?",
    empty_label: str | None = None,
    correct_option: OptionLabel | None = "C",
) -> ParsedQuestion:
    """Varsayılanı geçerli olan bir soru kurar; tek alan bozularak kontroller denenir."""
    options = [
        QuestionOption(label=label, blocks=[paragraph("" if label == empty_label else label * 3)])
        for label in (LABELS if labels is None else labels)
    ]
    content = QuestionContent(stem=[paragraph(stem)], options=options)
    return ParsedQuestion(number=number, page_no=1, content=content, correct_option=correct_option)


@pytest.mark.parametrize(
    ("question", "problems"),
    [
        (build_question(), []),
        (build_question(correct_option=None), []),
        (build_question(labels=["A", "B", "C", "D"]), [ValidationProblem.OPTION_COUNT]),
        (
            build_question(labels=["A", "B", "C", "D", "E", "E"]),
            [ValidationProblem.OPTION_COUNT, ValidationProblem.OPTION_LABELS],
        ),
        (build_question(labels=["A", "B", "D", "C", "E"]), [ValidationProblem.OPTION_LABELS]),
        (build_question(labels=["A", "A", "B", "C", "D"]), [ValidationProblem.OPTION_LABELS]),
        (build_question(empty_label="D"), [ValidationProblem.EMPTY_OPTION]),
        (build_question(stem="  \n"), [ValidationProblem.EMPTY_STEM]),
        (build_question(stem="** **"), [ValidationProblem.EMPTY_STEM]),
        (build_question(stem="<u></u>"), [ValidationProblem.EMPTY_STEM]),
        (
            build_question(labels=["A", "B", "C", "D"], correct_option="E"),
            [ValidationProblem.OPTION_COUNT, ValidationProblem.ANSWER_NOT_OPTION],
        ),
    ],
    ids=[
        "valid",
        "no-answer-key-is-not-a-problem",
        "four-options",
        "six-options",
        "wrong-order",
        "repeated-label",
        "empty-option",
        "blank-stem",
        "markup-only-stem",
        "underline-only-stem",
        "answer-missing-from-options",
    ],
)
def test_broken_question_reports_its_problems(
    question: ParsedQuestion, problems: list[ValidationProblem]
) -> None:
    """Her bozukluk kendi koduyla raporlanır; geçerli ve cevap anahtarı bulunmayan soru geçer."""
    assert check_question(question) == problems


def test_question_without_stem_blocks_is_empty() -> None:
    """Hiç bloğu olmayan kök boş sayılır."""
    question = build_question()
    question.content.stem = []

    assert check_question(question) == [ValidationProblem.EMPTY_STEM]


@pytest.mark.parametrize(
    ("numbers", "expected"),
    [
        ([1, 2, 3, 4], []),
        ([2, 3, 4], [0]),
        ([1, 2, 4, 5], [2]),
        ([1, 2, 2, 3], [2]),
        ([1, 3, 2], [1, 2]),
        ([], []),
    ],
    ids=["sequential", "starts-at-two", "gap", "repeat", "swap", "empty"],
)
def test_positions_out_of_sequence(numbers: list[int], expected: list[int]) -> None:
    """1'den başlayıp birer artmayan numaraların yeri, bozulmanın olduğu yerden işaretlenir."""
    assert positions_out_of_sequence(numbers) == expected


def test_validate_questions_returns_only_failing_questions() -> None:
    """Sadece sorunlu sorular döner; numara sırası ve soru kontrolleri birlikte raporlanır."""
    questions = [
        build_question(number=1),
        build_question(number=2, empty_label="B"),
        build_question(number=4),
        build_question(number=5),
    ]

    assert validate_questions(questions) == [
        QuestionCheck(index=1, number=2, problems=[ValidationProblem.EMPTY_OPTION]),
        QuestionCheck(index=2, number=4, problems=[ValidationProblem.NUMBER_SEQUENCE]),
    ]


def test_validate_questions_flags_only_the_repeated_question() -> None:
    """Numarası tekrar eden sorulardan sadece ikincisi işaretlenir; yerinden ayırt edilir."""
    questions = [build_question(number=number) for number in (1, 2, 2, 3)]

    assert validate_questions(questions) == [
        QuestionCheck(index=2, number=2, problems=[ValidationProblem.NUMBER_SEQUENCE])
    ]


def test_unnumbered_question_stays_out_of_number_sequence() -> None:
    """Numarasız örnek soru sıra kontrolüne girmez; çevresindeki numaralar yine denetlenir."""
    questions = [build_question(1), build_question(1), build_question(2), build_question(4)]
    questions[1] = questions[1].model_copy(update={"number": None})
    assert validate_questions(questions) == [
        QuestionCheck(index=3, number=4, problems=[ValidationProblem.NUMBER_SEQUENCE])
    ]


def test_normalize_drops_markup_and_case() -> None:
    """İşaretler, tablo çizgisi ve büyük harf karşılaştırmaya girmez."""
    markdown = "**İSTANBUL** ve *Kiralık Konak*\n\n| Eser | Yazar |\n|---|---|\n| <u>Ka</u> | O |"
    text_layer = "İstanbul ve Kiralık\nKonak Eser Yazar Ka O"

    assert normalize_for_comparison(markdown) == "istanbul ve kiralık konak eser yazar ka o"
    assert normalize_for_comparison(text_layer) == normalize_for_comparison(markdown)


@pytest.mark.parametrize(
    "separator",
    ["|---|---|", "|:--:|---:|", "---|---", "|---|---", "| - | - |", "|:-:|:-:|"],
)
def test_normalize_drops_every_table_separator_form(separator: str) -> None:
    """GFM tablo ayırıcı satırının bütün yazımları atılır."""
    assert normalize_for_comparison(f"| a | b |\n{separator}\n| c | d |") == "a b c d"


def test_normalize_keeps_prose_dashes() -> None:
    """Düz metindeki tire ve uzun çizgi ayırıcı sayılmaz."""
    assert normalize_for_comparison("Tanzimat - Servetifünun\n---") == "tanzimat - servetifünun ---"
    assert normalize_for_comparison("1923-1940 arası") == "1923-1940 arası"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("edebi-\nyat", "edebiyat"),
        ("edebi- \n  yat", "edebiyat"),
        ("dö\N{SOFT HYPHEN}\nnemi", "dönemi"),
        ("ör\N{SOFT HYPHEN}nek", "örnek"),
    ],
    ids=["hyphen", "hyphen-spaces", "soft-hyphen-break", "soft-hyphen-inline"],
)
def test_normalize_joins_words_broken_at_line_end(text: str, expected: str) -> None:
    """Satır sonunda tireyle ya da yumuşak tireyle bölünen kelime birleşir."""
    assert normalize_for_comparison(text) == expected


def test_normalize_unifies_decomposed_letters_and_list_markers() -> None:
    """Ayrık yazılmış Türkçe harfler birleşir; markdown ve PDF liste imleri atılır."""
    decomposed = "I\N{COMBINING DOT ABOVE}lk s\N{COMBINING CEDILLA}iir"

    assert normalize_for_comparison(decomposed) == normalize_for_comparison("İlk şiir")
    assert normalize_for_comparison("- birinci\n+ ikinci") == normalize_for_comparison(
        "• birinci\nikinci"
    )


def test_normalize_handles_long_blank_runs_quickly() -> None:
    """Binlerce boş satır ya da boşluk içeren metin hızla işlenir."""
    started = time.perf_counter()

    assert normalize_for_comparison("\n" * 20000 + "x") == "x"
    assert normalize_for_comparison(" " * 20000 + "x") == "x"
    assert normalize_for_comparison("\t" * 20000 + "|||x") == "x"
    assert time.perf_counter() - started < 1.0


def test_text_matching_threshold() -> None:
    """Metin katmanına yüzde 90 ve üstü benzeyen çıktı geçer, altı geçmez."""
    text_layer = "a" * 100
    close = "a" * 90 + "b" * 10
    far = "a" * 89 + "b" * 11

    assert text_similarity(close, text_layer) == pytest.approx(0.90)
    assert matches_text_layer(close, text_layer)
    assert not matches_text_layer(far, text_layer)
    assert text_similarity("*Çalıkuşu* romanı", "ÇALIKUŞU romanı") == 1.0


def test_real_control_set_questions_pass() -> None:
    """Kontrol setindeki gerçek ÖDSGM soruları hiçbir soru kontrolüne takılmaz."""
    lines = CONTROL_SET.read_text(encoding="utf-8").splitlines()
    questions = []
    for line in lines:
        record = json.loads(line)
        options = [
            QuestionOption(label=label, blocks=[paragraph(text)])
            for label, text in record["options"].items()
        ]
        content = QuestionContent(stem=[paragraph(record["stem"])], options=options)
        questions.append(
            ParsedQuestion(number=1, page_no=1, content=content, correct_option=record["correct"])
        )

    assert len(questions) == 100
    assert [check_question(question) for question in questions] == [[]] * 100


def test_weak_pages_become_problems() -> None:
    """Metin katmanı bozuk kalan ve harfi çözülemeyen sayfa soruna döner; öbür notlar dönmez."""
    pages = [
        PageReport(page_no=1, source="TEXT", notes=["REPAIRED_GLYPHS"], text_ratio=0.95),
        PageReport(page_no=2, source="TEXT", notes=["LOW_TEXT_LAYER"], text_ratio=0.4),
        PageReport(page_no=3, source="OCR", notes=["UNDECODED_GLYPHS"], text_ratio=None),
    ]

    assert page_problems(pages) == [
        SourceProblem(code="LOW_TEXT_LAYER", page_no=2),
        SourceProblem(code="UNDECODED_GLYPHS", page_no=3),
    ]
