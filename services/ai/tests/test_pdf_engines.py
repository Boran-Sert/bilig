"""PDF motorlarını kendi ürettiğimiz küçük PDF'lerle ve ortak bölümün eşitliğiyle test eder."""

from app.ingest.pdf import book_reader, question_reader
from scripts.sync_pdf_shared import FOLDER, book_shared, shared
from tests.pdf_factory import Text, lines_pdf, make_pdf

QUESTIONS = [
    "**1.** Aşağıdakilerden hangisi bir roman türüdür?",
    "A) Gazel",
    "B) Tarihî roman",
    "C) Kaside",
    "D) Mesnevi",
    "E) Rubai",
    "",
    "**2.** Aşağıdakilerden hangisi divan şiirinde bir nazım biçimi *değildir*?",
    "A) Gazel",
    "B) Kaside",
    "C) Koşma",
    "D) Rubai",
    "E) Mesnevi",
    "",
    "**3.** I. *Araba Sevdası*",
    "II. *Eylül*",
    "III. *Mai ve Siyah*",
    "Yukarıdakilerden hangileri realist romandır?",
    "A) Yalnız I",
    "B) Yalnız II",
    "C) I ve II",
    "D) II ve III",
    "E) I, II ve III",
    "",
    "",
    "**CEVAP ANAHTARI**",
    "1-B 2-C 3-B",
]


def test_shared_section_is_identical() -> None:
    """Kitap motorundaki içe aktarmalar ve ortak bölüm test motorundakiyle birebir aynıdır."""
    test = (FOLDER / "question_reader.py").read_text(encoding="utf-8")
    book = (FOLDER / "book_reader.py").read_text(encoding="utf-8")
    assert shared(book) == book_shared(test)


def test_question_reader_finds_questions_options_and_answers() -> None:
    """Test motoru soruları numarası, kökü, beş şıkkı ve anahtardaki cevabıyla okur."""
    pages = question_reader.read_document(lines_pdf([QUESTIONS]), question_reader.OcrSettings())
    questions, _ = question_reader.parse(pages)
    assert [(q.number, q.answer, q.answer_source) for q in questions] == [
        (1, "B", "KEY"),
        (2, "C", "KEY"),
        (3, "B", "KEY"),
    ]
    assert questions[1].stem == [
        "Aşağıdakilerden hangisi divan şiirinde bir nazım biçimi *değildir*?"
    ]
    assert questions[0].options["B"] == ["Tarihî roman"]
    assert questions[2].stem[0].split("\n")[:3] == [
        "I. *Araba Sevdası*",
        "II. *Eylül*",
        "III. *Mai ve Siyah*",
    ]
    assert all(page.source == "TEXT" for page in pages)


def test_book_reader_builds_heading_path() -> None:
    """Kitap motoru başlıkları düzeyiyle, paragrafları başlık yoluyla ve italikle okur."""
    pdf = make_pdf(
        [
            [
                Text("**ROMAN**", 56, 80, 18),
                Text("Roman, yaşanmış ya da yaşanabilecek olayları anlatan uzun", 56, 120),
                Text("bir anlatı türüdür. Türk edebiyatında ilk romanlar Tanzimat", 56, 135),
                Text("döneminde yazılmıştır.", 56, 150),
                Text("**Tarihî Roman**", 56, 190, 13),
                Text("Konusunu tarihten alan romanlardır. *Devlet Ana* bu türün", 56, 215),
                Text("bilinen örneklerindendir.", 56, 230),
            ]
        ]
    )
    pages = book_reader.read_document(pdf, book_reader.OcrSettings())
    blocks = [(b.kind, b.level, b.title_path, b.md) for b in book_reader.read_book(pages)]
    assert blocks == [
        ("HEADING", 1, [], "ROMAN"),
        (
            "PARAGRAPH",
            None,
            ["ROMAN"],
            "Roman, yaşanmış ya da yaşanabilecek olayları anlatan uzun bir anlatı türüdür. "
            "Türk edebiyatında ilk romanlar Tanzimat döneminde yazılmıştır.",
        ),
        ("HEADING", 2, ["ROMAN"], "Tarihî Roman"),
        (
            "PARAGRAPH",
            None,
            ["ROMAN", "Tarihî Roman"],
            "Konusunu tarihten alan romanlardır. *Devlet Ana* bu türün bilinen örneklerindendir.",
        ),
    ]
