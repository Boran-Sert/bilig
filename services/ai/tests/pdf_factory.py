"""Testler için küçük PDF'ler üretir (pypdfium2'nin yazma API'siyle, PyMuPDF'siz).

Metin parçası sayfanın üstünden ölçülen taban çizgisine yazılır; "**kalın**" ve "*italik*"
işaretli bölümler Liberation Sans'ın kalın ve italik fontlarıyla ayrı metin nesnesi olur. Çizgi
(altı çizili söz, tablo kenarı), dolgulu kutu ve metin katmanı olmayan yazılı resim (OCR testi) de
çizilebilir; kutular metni örtmesin diye önce çizilir. Fontlar tests/fixtures/fonts
altındadır (SIL OFL 1.1). Üretilen PDF bayt olarak döner; okuyuculara olduğu gibi verilir.
"""

import ctypes
import io
import re
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "fixtures" / "fonts"
FONT_FILES = {
    "regular": "LiberationSans-Regular.ttf",
    "bold": "LiberationSans-Bold.ttf",
    "italic": "LiberationSans-Italic.ttf",
}
PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARKUP = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")
PICTURE_DPI = 300


@dataclass
class Text:
    """Sol kenarı x, taban çizgisi sayfanın üstünden y olan metin; ** ve * stil işaretidir.

    standard ise metin Türkçe harfleri kodlayamayan gömülmemiş Helvetica ile yazılır.
    """

    text: str
    x: float
    y: float
    size: float = 10.0
    standard: bool = False


@dataclass
class Rule:
    """Sayfanın üstünden y yüksekliğinde x0'dan x1'e yatay çizgi."""

    x0: float
    x1: float
    y: float
    width: float = 0.6


@dataclass
class Box:
    """Üst-sol köşesi (x0, y0), alt-sağ köşesi (x1, y1) olan dolgulu kutu."""

    x0: float
    y0: float
    x1: float
    y1: float
    gray: int = 220


@dataclass
class Picture:
    """Sol üst köşesi (x, y) olan, satırları siyahla yazılmış beyaz resim (metin katmanı yok)."""

    lines: list[str]
    x: float
    y: float
    size: float = 14.0


Item = Text | Rule | Box | Picture


def make_pdf(pages: list[list[Item]]) -> bytes:
    """Her sayfanın öğelerini A4 sayfaya çizip PDF'in baytlarını döner."""
    document = pdfium.PdfDocument.new()
    fonts = {style: load_font(document, name) for style, name in FONT_FILES.items()}
    fonts["standard"] = pdfium_c.FPDFText_LoadStandardFont(document.raw, b"Helvetica")
    for items in pages:
        page = document.new_page(PAGE_WIDTH, PAGE_HEIGHT)
        for item in sorted(items, key=lambda item: not isinstance(item, Box)):
            if isinstance(item, Text):
                draw_text(document, page, fonts, item)
            elif isinstance(item, Picture):
                draw_picture(document, page, item)
            else:
                draw_shape(page, item)
        pdfium_c.FPDFPage_GenerateContent(page.raw)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def lines_pdf(pages: list[list[str]], size: float = 10.0, leading: float = 1.5) -> bytes:
    """Her sayfaya satırları alt alta yazar; boş satır paragraf arası boşluk bırakır."""
    left, top = 56.0, 72.0
    return make_pdf(
        [
            [
                Text(line, left, top + index * size * leading, size)
                for index, line in enumerate(lines)
                if line
            ]
            for lines in pages
        ]
    )


def load_font(document: pdfium.PdfDocument, name: str) -> ctypes.c_void_p:
    """TrueType fontu belgeye gömer (CID, Türkçe harfler için)."""
    data = (FONT_DIR / name).read_bytes()
    buffer = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    font: ctypes.c_void_p = pdfium_c.FPDFText_LoadFont(
        document.raw, buffer, len(data), pdfium_c.FPDF_FONT_TRUETYPE, True
    )
    return font


def draw_text(
    document: pdfium.PdfDocument,
    page: pdfium.PdfPage,
    fonts: dict[str, ctypes.c_void_p],
    item: Text,
) -> None:
    """Metni stil işaretlerine göre parçalara bölüp art arda yazar."""
    if item.standard:
        write_run(document, page, fonts["standard"], item.text, item.x, item)
        return
    x = item.x
    for part in MARKUP.split(item.text):
        if not part:
            continue
        style, content = "regular", part
        if part.startswith("**"):
            style, content = "bold", part[2:-2]
        elif part.startswith("*"):
            style, content = "italic", part[1:-1]
        x = write_run(document, page, fonts[style], content, x, item)


def write_run(
    document: pdfium.PdfDocument,
    page: pdfium.PdfPage,
    font: ctypes.c_void_p,
    content: str,
    x: float,
    item: Text,
) -> float:
    """Tek stilli metni yazar; sonraki parçanın başlayacağı x'i döner."""
    obj = pdfium_c.FPDFPageObj_CreateTextObj(document.raw, font, item.size)
    encoded = ctypes.create_string_buffer((content + "\x00").encode("utf-16-le"))
    pdfium_c.FPDFText_SetText(obj, ctypes.cast(encoded, pdfium_c.FPDF_WIDESTRING))
    pdfium_c.FPDFPageObj_Transform(obj, 1, 0, 0, 1, x, PAGE_HEIGHT - item.y)
    pdfium_c.FPDFPage_InsertObject(page.raw, obj)
    right = ctypes.c_float()
    left, bottom, top = ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
    pdfium_c.FPDFPageObj_GetBounds(obj, left, bottom, right, top)
    trailing = len(content) - len(content.rstrip(" "))
    return right.value + trailing * item.size * 0.28


def draw_shape(page: pdfium.PdfPage, item: Rule | Box) -> None:
    """Çizgiyi ya da dolgulu kutuyu çizer."""
    if isinstance(item, Rule):
        path = pdfium_c.FPDFPageObj_CreateNewPath(item.x0, PAGE_HEIGHT - item.y)
        pdfium_c.FPDFPath_LineTo(path, item.x1, PAGE_HEIGHT - item.y)
        pdfium_c.FPDFPageObj_SetStrokeColor(path, 0, 0, 0, 255)
        pdfium_c.FPDFPageObj_SetStrokeWidth(path, item.width)
        pdfium_c.FPDFPath_SetDrawMode(path, pdfium_c.FPDF_FILLMODE_NONE, True)
    else:
        path = pdfium_c.FPDFPageObj_CreateNewRect(
            item.x0, PAGE_HEIGHT - item.y1, item.x1 - item.x0, item.y1 - item.y0
        )
        pdfium_c.FPDFPageObj_SetFillColor(path, item.gray, item.gray, item.gray, 255)
        pdfium_c.FPDFPath_SetDrawMode(path, pdfium_c.FPDF_FILLMODE_WINDING, False)
    pdfium_c.FPDFPage_InsertObject(page.raw, path)


def draw_picture(document: pdfium.PdfDocument, page: pdfium.PdfPage, item: Picture) -> None:
    """Satırları resme yazıp sayfaya resim nesnesi olarak koyar."""
    scale = PICTURE_DPI / 72
    font = ImageFont.truetype(str(FONT_DIR / FONT_FILES["regular"]), round(item.size * scale))
    leading = item.size * 1.5
    width = max(font.getlength(line) for line in item.lines) / scale + item.size
    height = leading * len(item.lines) + item.size
    image = Image.new("L", (round(width * scale), round(height * scale)), 255)
    pen = ImageDraw.Draw(image)
    for index, line in enumerate(item.lines):
        pen.text((item.size * scale / 2, (item.size / 2 + index * leading) * scale), line, 0, font)
    picture = pdfium.PdfImage.new(document)
    picture.set_bitmap(pdfium.PdfBitmap.from_pil(image))
    picture.set_matrix(
        pdfium.PdfMatrix().scale(width, height).translate(item.x, PAGE_HEIGHT - item.y - height)
    )
    page.insert_obj(picture)


def raw_page_text(data: bytes) -> str:
    """PDF'in ilk sayfasının ham metin katmanı (onarım ve düzeltme yapılmadan)."""
    document = pdfium.PdfDocument(data)
    try:
        page = document[0]
        textpage = page.get_textpage()
        text: str = textpage.get_text_range()
        textpage.close()
        page.close()
    finally:
        document.close()
    return text
