"""PDF dış yüzünü (app.ingest.pdf) kendi ürettiğimiz küçük PDF'lerle test eder.

Senaryolar Fatih'in okuyucu testlerinden (#192, #195) ve metin katmanı kontrolünden (A3) alındı:
kalın numaralı sorular, I-II-III maddeleri, anahtar, numarası başa dönen ikinci test, kutulu bilgi
metni, sabit kod kaymalı font ve metin katmanı olmayan yazılı resim.
"""

import pytest

from app.ingest import pdf
from app.ingest.validators import validate_questions
from app.schemas.question import Block
from tests.pdf_factory import Box, Picture, Text, lines_pdf, make_pdf
from tests.word_list import KNOWN_WORDS

OPTIONS = pdf.ReaderOptions(KNOWN_WORDS)
FIRST_TEST = [
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
SECOND_TEST = [
    "**1.** Aşağıdaki eserlerden hangisi bir tiyatro eseridir?",
    "A) *Şair Evlenmesi*",
    "B) *Eylül*",
    "C) *Huzur*",
    "D) *Sinekli Bakkal*",
    "E) *Çalıkuşu*",
    "",
    "",
    "**CEVAP ANAHTARI**",
    "1-A 2-D 3-E",
]
WORDS = [
    "masal halk arasinda anlatilan bir yazar metin",
    "roman tiyatro kitap zaman mekan olay kahraman",
    "sanat dil edebiyat anlam hikaye deneme makale",
    "tema konu karakter yer kalem yaprak bahar gece",
    "sabah aksam deniz dag orman nehir bulut yagmur",
]


def test_read_questions_gives_common_format() -> None:
    """Sorular kök, şık ve madde bloklarıyla, anahtardaki cevapla ve kontrolden geçerek döner."""
    reading = pdf.read_questions(lines_pdf([FIRST_TEST]), OPTIONS)
    [test] = reading.tests
    assert [(q.number, q.page_no, q.correct_option) for q in test] == [
        (1, 1, "B"),
        (2, 1, "C"),
        (3, 1, "B"),
    ]
    assert test[1].content.stem == [
        Block(
            type="paragraph",
            md="Aşağıdakilerden hangisi divan şiirinde bir nazım biçimi *değildir*?",
        )
    ]
    assert test[2].content.stem == [
        Block(type="numbered_items", md="I. *Araba Sevdası*\nII. *Eylül*\nIII. *Mai ve Siyah*"),
        Block(type="paragraph", md="Yukarıdakilerden hangileri realist romandır?"),
    ]
    assert [option.label for option in test[0].content.options] == ["A", "B", "C", "D", "E"]
    assert validate_questions(test) == []
    assert [(page.source, page.notes) for page in reading.pages] == [("TEXT", [])]


def test_read_questions_starts_new_test_when_numbers_restart() -> None:
    """Numara 1'e dönünce sorular ikinci teste ayrılır; her test kendi anahtarından cevap alır."""
    reading = pdf.read_questions(lines_pdf([FIRST_TEST, SECOND_TEST]), OPTIONS)
    assert [[q.number for q in test] for test in reading.tests] == [[1, 2, 3], [1]]
    assert [q.correct_option for q in reading.tests[0]] == ["B", "C", "B"]
    assert reading.tests[1][0].correct_option == "A"
    assert reading.tests[1][0].content.options[0].blocks[0].md == "*Şair Evlenmesi*"


def test_read_textbook_gives_types_paths_and_positions() -> None:
    """Başlık BASLIK, kutudaki metin BILGI, gerisi METIN; yol kaynak adıyla başlar."""
    source = make_pdf(
        [
            [
                Text("**ROMAN**", 56, 80, 18),
                Text("Roman, yaşanmış ya da yaşanabilecek olayları anlatan uzun", 56, 120),
                Text("bir anlatı türüdür. Türk edebiyatında ilk romanlar Tanzimat", 56, 135),
                Text("döneminde yazılmıştır.", 56, 150),
                Box(50, 175, 348, 212),
                Text("Konusunu tarihten alan romanlara tarihî roman denir. *Devlet Ana*", 56, 190),
                Text("bu türün bilinen örneklerindendir.", 56, 205),
            ]
        ]
    )
    reading = pdf.read_textbook(source, "TDE 12 Ders Kitabı", OPTIONS)
    blocks = [(b.block_type, b.title_path, b.page_no, b.position) for b in reading.blocks]
    assert blocks == [
        ("BASLIK", "TDE 12 Ders Kitabı › ROMAN", 1, 0),
        ("METIN", "TDE 12 Ders Kitabı › ROMAN", 1, 1),
        ("BILGI", "TDE 12 Ders Kitabı › ROMAN", 1, 2),
    ]
    assert reading.blocks[2].markdown == (
        "Konusunu tarihten alan romanlara tarihî roman denir. *Devlet Ana* bu türün bilinen "
        "örneklerindendir."
    )
    assert reading.blocks[1].search_text.startswith("TDE 12 Ders Kitabı › ROMAN\nRoman,")


def test_code_shifted_font_is_fixed_by_text_layer_check() -> None:
    """Harfleri 29 kod kaymış metin katmanı Fatih'in font düzeltmesiyle geri çevrilir."""
    shifted = ["".join(c if c == " " else chr(ord(c) - 29) for c in line) for line in WORDS]
    reading = pdf.read_textbook(lines_pdf([shifted]), "Deneme", OPTIONS)
    assert reading.pages[0].notes == ["FONT_FIX_CODE_SHIFT_29"]
    assert reading.pages[0].text_ratio == 1.0
    assert pdf.read_lines(lines_pdf([shifted]), OPTIONS) == WORDS


def test_text_in_picture_is_read_by_ocr() -> None:
    """Metin katmanı olmayan yazılı resim Tesseract'la okunur ve satırlara girer."""
    source = make_pdf(
        [
            [
                Text("**Masal**", 56, 80, 14),
                Picture(
                    ["Masal, olağanüstü olayların anlatıldığı", "kısa bir halk anlatısıdır."],
                    56,
                    110,
                ),
            ]
        ]
    )
    assert pdf.read_lines(source, OPTIONS) == [
        "Masal",
        "Masal, olağanüstü olayların anlatıldığı",
        "kısa bir halk anlatısıdır.",
    ]
    assert pdf.read_textbook(source, "Deneme", OPTIONS).pages[0].notes == ["IMAGE_OCR"]


def test_read_lines_keeps_paragraph_breaks() -> None:
    """Satırlar okuma sırasıyla gelir; geniş satır aralığı boş satırla ayrılır."""
    lines = [
        "A.2. 5. Metnin olay örgüsünü belirler.",
        "a) Olay örgüsünü oluşturan olaylar sıralanır.",
        "b) Olaylar arasındaki neden sonuç ilişkisi üzerinde durulur.",
        "",
        "A.2. 6. Metindeki şahıs kadrosunun özelliklerini belirler.",
        "a) Şahısların fiziksel ve ruhsal özellikleri üzerinde durulur.",
        "",
        "A.2. 7. Metindeki zaman ve mekânın özelliklerini belirler.",
    ]
    assert pdf.read_lines(lines_pdf([lines]), OPTIONS) == lines


def test_render_page_draws_png_at_requested_resolution() -> None:
    """Sayfa 150 dpi'da A4 boyutunda PNG olarak çizilir."""
    image = pdf.render_page(lines_pdf([["Sayfa"]]), page_no=1)
    assert image.startswith(b"\x89PNG")
    assert int.from_bytes(image[16:20], "big") == round(595 * 150 / 72)


def test_unreadable_pdf_raises_pdf_read_error() -> None:
    """PDF olmayan baytlar PdfReadError verir."""
    with pytest.raises(pdf.PdfReadError):
        pdf.read_questions(b"not a pdf", OPTIONS)


def test_missing_tesseract_raises_ocr_error() -> None:
    """Tesseract komutu bulunamazsa OCR gereken okuma OcrError verir."""
    lines = ["Masal, olağanüstü olayların anlatıldığı", "kısa bir halk anlatısıdır."]
    source = make_pdf([[Picture(lines, 56, 110)]])
    options = pdf.ReaderOptions(KNOWN_WORDS, tesseract_cmd="tesseract-yok")
    with pytest.raises(pdf.OcrError):
        pdf.read_lines(source, options)
