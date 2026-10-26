"""Test okuyucusunun soru başı, ortak parça, cevap satırı, şık ve işaret kurallarını test eder.

Satırlar elle kurulur (tests/profiled_lines.py); sütun 40-280 arası, yazı boyutu 10.
"""

import pytest

from app.ingest.readers.test import read_questions
from app.schemas.profile import ProfiledLine
from app.schemas.question import ParsedQuestion
from tests.profiled_lines import PAGE_WIDTH, line, options


def stem_of(questions: list[ParsedQuestion], index: int = 0) -> str:
    """Sorunun kök bloklarını satır sonlarıyla birleştirir."""
    return "\n".join(block.md for block in questions[index].content.stem)


def question_lines(number: int, top: float, stem: str = "Soru kökü?") -> list[ProfiledLine]:
    """Sütunun solunda başlayan kısa köklü bir soru ve beş şıkkını kurar."""
    return [line(f"{number}. {stem}", top, right=150), *options(top + 16)]


def read(lines: list[ProfiledLine]) -> list[ParsedQuestion]:
    """Satırlardan soruları okur."""
    return read_questions(lines, PAGE_WIDTH)


@pytest.mark.parametrize(
    "heading",
    [
        "2-3. soruları aşağıdaki parçaya göre cevaplayınız.",
        "2 - 3. soruları aşağıdaki parçaya göre cevaplayınız.",
        "2–3. soruları aşağıdaki parçaya göre cevaplayınız.",
        "2. ve 3. soruları aşağıdaki parçaya göre cevaplayınız.",
        "Aşağıdaki parçaya göre 2, 3. soruları cevaplayınız.",
    ],
    ids=["dash", "spaced-dash", "en-dash", "ve", "comma-inside-sentence"],
)
def test_shared_passage_heading_forms(heading: str) -> None:
    """Ortak parça başlığının bütün yazımları parçayı aralıktaki sorulara bağlar."""
    lines = question_lines(1, 100) + [line(heading, 200), line("Parça metni.", 214, right=150)]
    lines += question_lines(2, 240) + question_lines(3, 340) + question_lines(4, 440)

    questions = read(lines)

    passages = [question.content.passage for question in questions]
    assert [question.number for question in questions] == [1, 2, 3, 4]
    assert passages[1] is not None and [block.md for block in passages[1]] == ["Parça metni."]
    assert passages[2] == passages[1]
    assert passages[0] is None and passages[3] is None
    assert [len(question.content.options) for question in questions] == [5, 5, 5, 5]


def test_listed_numbers_do_not_cover_the_gap() -> None:
    """Numaraları sayılan başlık ("2, 4 ve 5.") sadece sayılan sorulara bağlanır."""
    lines = question_lines(1, 100)
    lines += [line("2, 4 ve 5. soruları aşağıdaki parçaya göre cevaplayınız.", 200)]
    lines += [line("Parça.", 214, right=150)]
    lines += question_lines(2, 240) + question_lines(3, 340) + question_lines(4, 440)

    passages = [question.content.passage is not None for question in read(lines)]

    assert passages == [False, True, False, True]


def test_wrapped_heading_does_not_enter_the_passage() -> None:
    """İki satıra taşan başlığın ikinci satırı ortak parçaya girmez."""
    lines = [line("1-2. soruları aşağıdaki parçaya göre", 100)]
    lines += [line("cevaplayınız.", 114, right=120), line("Parça metni.", 128, right=150)]
    lines += question_lines(1, 150) + question_lines(2, 250)

    passage = read(lines)[0].content.passage

    assert passage is not None and [block.md for block in passage] == ["Parça metni."]


def test_heading_wrapped_over_three_lines_is_skipped() -> None:
    """Üç satıra taşan başlığın hiçbir parçası ortak parçaya girmez."""
    lines = [line("1-2. soruları", 100, right=150), line("aşağıdaki parçaya göre", 114, right=150)]
    lines += [line("cevaplayınız.", 128, right=120), line("Parça metni.", 142, right=150)]
    lines += question_lines(1, 170) + question_lines(2, 270)

    passage = read(lines)[0].content.passage

    assert passage is not None and [block.md for block in passage] == ["Parça metni."]


def test_inline_answer_line_becomes_the_answer() -> None:
    """Son şıktan sonraki "Cevap: C" satırı şıkka girmez, sorunun cevabı olur."""
    lines = question_lines(1, 100) + [line("Cevap: C", 200, right=100)]

    question = read(lines)[0]

    assert question.correct_option == "C"
    assert question.content.options[-1].blocks[0].md == "E"


def test_first_question_must_be_number_one() -> None:
    """Sütun solundaki "12. Sınıf" başlığı soru 12 sayılmaz; ilk soru 1'dir."""
    lines = [line("12. Sınıf Türk Dili ve Edebiyatı", 80, right=200)] + question_lines(1, 100)

    assert [question.number for question in read(lines)] == [1]


@pytest.mark.parametrize("text", ["2.5 puanlık soru", "12.yüzyılda yazıldı"])
def test_numbers_without_space_after_dot_are_not_questions(text: str) -> None:
    """Noktadan sonra boşluk olmayan sayı soru başı sayılmaz."""
    lines = question_lines(1, 100) + [line(text, 200, right=150)] + question_lines(2, 220)

    questions = read(lines)

    assert [question.number for question in questions] == [1, 2]
    assert stem_of(questions, 1) == "Soru kökü?"


def test_century_numeral_is_not_a_numbered_item() -> None:
    """Yüzyıl numarasıyla ("XX. yy.") başlayan kök madde bloğu olmaz."""
    lines = [line("1. XX. yy. yazarlarındandır.", 100, right=200), *options(116)]

    assert [block.type for block in read(lines)[0].content.stem] == ["paragraph"]


def test_whole_bold_line_keeps_its_marks() -> None:
    """Tamamı kalın soru ve şık satırında numara atılınca kalın işareti eşli kalır."""
    lines = [line("**1. Bütün satır kalın**", 100, right=200), line("**A) Kalın şık**", 116, 52)]
    lines += [line(f"{label}) {label}", 130 + 14 * i, 52, 90) for i, label in enumerate("BCDE")]

    question = read(lines)[0]

    assert stem_of([question]) == "**Bütün satır kalın**"
    assert question.content.options[0].blocks[0].md == "**Kalın şık**"


def test_bold_option_labels_on_one_row_are_split() -> None:
    """Aynı satırdaki kalın harfli şıklar ayrılır; köke gömülü "(B)" şık sayılmaz."""
    lines = [line("1. Hangisi (B) cümlesidir?", 100, right=200)]
    lines += [line("**A)** Bir   **B)** İki   **C)** Üç", 116, 52, 280)]
    lines += [line("D) Dört", 130, 52, 100), line("E) Beş", 144, 52, 100)]

    question = read(lines)[0]

    assert stem_of([question]) == "Hangisi (B) cümlesidir?"
    assert [option.blocks[0].md for option in question.content.options] == [
        "Bir",
        "İki",
        "Üç",
        "Dört",
        "Beş",
    ]


def test_wrapped_option_continues_the_option() -> None:
    """Şıkkın ikinci satırı köke değil şıkka eklenir."""
    lines = [line("1. Hangisi?", 100, right=120), line("A) Uzun bir şık metni ki", 114, 52)]
    lines += [line("sürüp gider", 128, 64, 130)]
    lines += [
        line(f"{label}) {label}", 142 + 14 * index, 52, 90) for index, label in enumerate("BCDE")
    ]

    question = read_questions(lines, PAGE_WIDTH)[0]

    assert stem_of([question]) == "Hangisi?"
    assert question.content.options[0].blocks[0].md == "Uzun bir şık metni ki sürüp gider"


def test_indented_number_is_not_a_question_start() -> None:
    """Sütunun solundan içeride başlayan "2." sıradaki numara olsa da soru başı sayılmaz."""
    lines = [line("1. Şunlar verilmiştir:", 100, right=150), line("2. madde", 114, 70, 120)]
    lines += options(130) + [line("2. İkinci soru?", 210, right=150)] + options(226)

    questions = read_questions(lines, PAGE_WIDTH)

    assert [question.number for question in questions] == [1, 2]
    assert stem_of(questions) == "Şunlar verilmiştir:\n2. madde"


def test_question_start_mentioning_other_questions_is_a_question() -> None:
    """Soru başı satırı içinde "1 ve 2. soruları" geçse de soru başlar, başlık sayılmaz."""
    lines = [line("1. Yukarıdaki 1 ve 2. soruları dikkate alınız", 100), *options(116)]

    questions = read(lines)

    assert [question.number for question in questions] == [1]
    assert questions[0].content.passage is None


def test_unterminated_heading_takes_at_most_two_more_lines() -> None:
    """Noktasız biten başlık en fazla iki satır daha alır; sonrası ortak parçadır."""
    lines = [line("1-2. soruları aşağıdaki parçaya göre cevaplayınız", 100)]
    lines += [line("Birinci satır", 114, right=150), line("İkinci satır", 128, right=150)]
    lines += [line("Parça metni.", 142, right=150)]
    lines += question_lines(1, 170) + question_lines(2, 270)

    passage = read(lines)[0].content.passage

    assert passage is not None and [block.md for block in passage] == ["Parça metni."]


def test_heading_continuation_never_swallows_a_question_start() -> None:
    """Noktasız başlıktan hemen sonra gelen soru başı başlığa sayılmaz."""
    lines = [line("1-2. soruları aşağıdaki parçaya göre cevaplayınız", 100)]
    lines += question_lines(1, 120) + question_lines(2, 220)

    assert [question.number for question in read(lines)] == [1, 2]


def test_heading_ending_with_colon_is_complete() -> None:
    """İki noktayla biten başlık tamamdır; sonraki satır ortak parçaya girer."""
    lines = [line("1-2. soruları aşağıdaki parçaya göre cevaplayınız:", 100)]
    lines += (
        [line("Parça metni.", 114, right=150)] + question_lines(1, 140) + question_lines(2, 240)
    )

    passage = read(lines)[0].content.passage

    assert passage is not None and [block.md for block in passage] == ["Parça metni."]
