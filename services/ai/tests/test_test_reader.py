"""Test okuyucusunu kendi ürettiğimiz iki sütunlu test PDF'iyle test eder (hazırlık hattı A5).

PDF ÖDSGM testlerinin düzenini taklit eder: ortadan geçen test adı, sol ve sağ sütunda kalın
numaralı sorular, satır sonunda tireyle bölünen kelimeler, aynı satırda iki şık, I-II-III
maddeleri, iki soruya ortak parça ve ikinci sayfaya geçen sorular.
"""

import pymupdf
import pytest

from app.ingest.profile import apply_profile
from app.ingest.readers.test import read_questions
from app.schemas.profile import SourceProfile
from app.schemas.question import ParsedQuestion

LEFT = (40.0, 280.0)
RIGHT = (320.0, 560.0)
PROFILE = SourceProfile(name="test_ornek", description="Testte üretilen PDF.", rules=[])


def place(page: pymupdf.Page, column: tuple[float, float], top: float, html: str) -> None:
    """Verilen sütuna, verilen yükseklikten başlayarak 10 puanlık HTML yazar."""
    rect = pymupdf.Rect(column[0], top, column[1], top + 200)
    page.insert_htmlbox(rect, f'<div style="font-size:10px;line-height:1.3">{html}</div>')


def build_test_pdf() -> pymupdf.Document:
    """İki sayfalık, beş soruluk test PDF'i üretir."""
    document = pymupdf.open()
    first = document.new_page()
    first.insert_htmlbox(
        pymupdf.Rect(250, 30, 350, 60), '<p style="font-size:10px"><b>Roman - 1</b></p>'
    )
    place(
        first,
        LEFT,
        80,
        "<b>1.</b> Aşağıdakilerden hangisi Tanzimat ro-<br>"
        "manının özelliği değildir?<br>A) Olay örgüsü zayıftır.<br>B) Yazar araya girer.<br>"
        "C) Karakterler tek yönlüdür.<br>D) İç monolog yaygındır.<br>E) Konular toplumsaldır.",
    )
    place(
        first,
        LEFT,
        260,
        "<b>2.</b> I. <i>Araba Sevdası</i><br>II. <i>Eylül</i><br>III. <i>Mai ve Siyah</i><br>"
        "Hangileri realist romandır?<br>"
        "A) Yalnız I&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;B) Yalnız II<br>C) I ve II&nbsp;&nbsp;&nbsp;"
        "&nbsp;&nbsp;D) II ve III<br>E) I, II ve III",
    )
    place(
        first,
        RIGHT,
        80,
        "<b>3-4. soruları aşağıdaki parçaya göre cevaplayınız.</b><br>"
        "Bir zamanlar bu kasabada<br>herkes birbirini tanırdı.",
    )
    place(
        first,
        RIGHT,
        180,
        "<b>3.</b> Parçanın türü hangisidir?<br>A) Roman<br>B) Hikâye<br>C) Deneme<br>"
        "D) Makale<br>E) Söyleşi",
    )
    second = document.new_page()
    place(
        second,
        LEFT,
        80,
        "<b>4.</b> Parçada hangi anlatıcı vardır?<br>A) Kahraman<br>B) Gözlemci<br>"
        "C) İlahi<br>D) Yazar<br>E) Hiçbiri",
    )
    place(
        second,
        RIGHT,
        80,
        "<b>5.</b> Türk romanı<br>12. yüzyılda değil, 19. yüzyılda doğmuştur. Bu bilgiye göre "
        "hangisi doğrudur?<br>A) a<br>B) b<br>C) c<br>D) d<br>E) e",
    )
    return document


def read_pdf(document: pymupdf.Document) -> list[ParsedQuestion]:
    """PDF'in bütün sayfalarına profili uygulayıp soruları okur."""
    lines = [line for page in document.pages() for line in apply_profile(page, PROFILE)]
    return read_questions(lines, document[0].rect.width)


@pytest.fixture(scope="module")
def questions() -> list[ParsedQuestion]:
    """Test PDF'inden okunan sorular."""
    return read_pdf(build_test_pdf())


def stem_text(question: ParsedQuestion) -> list[tuple[str, str]]:
    """Kök bloklarını tür ve metin olarak döner."""
    return [(block.type, block.md) for block in question.content.stem]


def option_texts(question: ParsedQuestion) -> list[tuple[str, str]]:
    """Şıkları harf ve metin olarak döner."""
    return [
        (option.label, "\n".join(block.md for block in option.blocks))
        for option in question.content.options
    ]


def test_questions_are_read_in_column_and_page_order(questions: list[ParsedQuestion]) -> None:
    """Sorular sol sütun, sağ sütun, sonraki sayfa sırasıyla okunur; test adı soruya girmez."""
    assert [(question.number, question.page_no) for question in questions] == [
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 2),
        (5, 2),
    ]
    assert all(question.correct_option is None for question in questions)


def test_stem_joins_hyphenated_word_and_options_split(questions: list[ParsedQuestion]) -> None:
    """Satır sonunda bölünen kelime birleşir, her şık kendi satırından okunur."""
    first = questions[0]

    assert stem_text(first) == [
        (
            "paragraph",
            "Aşağıdakilerden hangisi Tanzimat romanının özelliği değildir?",
        )
    ]
    assert option_texts(first) == [
        ("A", "Olay örgüsü zayıftır."),
        ("B", "Yazar araya girer."),
        ("C", "Karakterler tek yönlüdür."),
        ("D", "İç monolog yaygındır."),
        ("E", "Konular toplumsaldır."),
    ]


def test_numbered_items_and_two_options_on_a_row(questions: list[ParsedQuestion]) -> None:
    """I-II-III maddeleri ayrı blok olur, italik korunur, aynı satırdaki iki şık ayrılır."""
    second = questions[1]

    assert stem_text(second) == [
        ("numbered_items", "I. *Araba Sevdası*\nII. *Eylül*\nIII. *Mai ve Siyah*"),
        ("paragraph", "Hangileri realist romandır?"),
    ]
    assert option_texts(second) == [
        ("A", "Yalnız I"),
        ("B", "Yalnız II"),
        ("C", "I ve II"),
        ("D", "II ve III"),
        ("E", "I, II ve III"),
    ]


def test_shared_passage_belongs_to_its_questions(questions: list[ParsedQuestion]) -> None:
    """Ortak parça aralıktaki iki soruya bağlanır, dizeleri ayrı kalır, başkasına bağlanmaz."""
    passages = [question.content.passage for question in questions]

    assert passages[2] == passages[3]
    assert passages[2] is not None
    assert [block.md for block in passages[2]] == [
        "Bir zamanlar bu kasabada\nherkes birbirini tanırdı."
    ]
    assert passages[0] is None and passages[1] is None and passages[4] is None
    assert stem_text(questions[2]) == [("paragraph", "Parçanın türü hangisidir?")]


def test_number_inside_stem_is_not_a_new_question(questions: list[ParsedQuestion]) -> None:
    """Kökte satır başına gelen "12. yüzyılda" sıradaki numara olmadığı için soru sayılmaz."""
    assert len(questions) == 5
    assert stem_text(questions[4])[0][1].startswith("Türk romanı\n12. yüzyılda değil")


def test_reading_is_independent_of_line_order() -> None:
    """Satırlar karışık sırayla verilse de aynı sorular okunur."""
    document = build_test_pdf()
    lines = [line for page in document.pages() for line in apply_profile(page, PROFILE)]

    assert read_questions(list(reversed(lines)), document[0].rect.width) == read_pdf(document)


def test_no_question_without_numbered_start() -> None:
    """Numaralı soru başı olmayan sayfadan soru çıkmaz."""
    document = pymupdf.open()
    place(document.new_page(), LEFT, 80, "Açıklama metni.<br>A) Şık gibi görünen satır")

    assert read_pdf(document) == []
