"""Test okuyucu: çoktan seçmeli test PDF'lerinden soruları çıkarır (tek dosya, doğruluk sürümü).

Yayınevine özel profil yoktur; kurallar her belgeden yeniden çıkarılır. Dosya iki bölümdür.

ORTAK bölüm (kitap okuyucuda birebir aynısı vardır):
1. PDFium karakterleri font, gerçek boyut (metin matrisiyle), kalınlık, italik, renk ve konumla
   verir; döndürülmüş süs yazısı atılır, satır sonu tiresi yumuşak tire olur.
2. Görünürlük: sayfa bir kez tam, bir kez metin (ve bir kez çizim) nesneleri kapalı çizilir;
   mürekkebi görünmeyen karakter ve çizim (gizli katman, örtülmüş, kırpılmış, beyaz) atılır.
3. Bozuk font eşlemesi: bozuk metin nesneleri tek başına siyah çizilip Tesseract'la okunur; OCR
   kelimesi karakter kutularıyla eşlenir ve her (font, kod) için oy sayılır. Kod oy çokluğuyla,
   oyu yoksa fontun kod kaymasıyla çözülür; mürekkepsiz bozuk kod boşluktur.
4. Metin katmanı olmayan sayfa (harfleri çizim, tarama) Tesseract'la okunur; kalınlık harf
   çizgisinin kalınlığından tahmin edilir.
5. Düzen: kenar bandında tekrarlayan satır, aynı stilde koşu başlığı ve kenardaki yalnız sayı üst
   ya da alt bilgidir. Okuma sırası XY-cut ile bulunur: kutular bölünmez; dar satırlar arasında
   oluk varsa sütunlara, oluğu kesen satırların üstünden ve altından bantlara bölünür.
6. Satır birleştirme: tireyle bölünen kelime birleşir; sığacakken bitmiş satır (şiir, diyalog),
   kısa satırdan sonra büyük harf ve madde başı yeni satırdır; büyük boşluk, kalınlığın değişmesi
   ve girintili ilk satır yeni paragraftır. İtalik, kalın ve altı çizili markdown olarak korunur.

TEST bölümü:
7. Soru numarası: satır başındaki "12.", "12)", "Soru 12:", "12. Soru" adayları imzaya
   (etiket, noktalama, kalın, renk, şekil içinde mi, sütun soluna göre yer) göre gruplanır;
   ardışık zincir (testte yeniden başlayabilir) ve tam A-E şık takımıyla puanlanır.
8. Şıklar geometriyle bulunur; işaretsiz satır x'ine göre bir şıkkın devamıdır.
9. Ortak parça iki soru arasında kalan metindir ("3-4. soruları" ipucu); cevap "Cevap: C"
   satırından, "1-D 2-E" çiftlerinden ya da alt alta sayı/harf ızgarasından okunur.
10. OCR'la okunan sorularda Roma rakamları (I, II, III...) sıralarına göre düzeltilir.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from itertools import combinations
from pathlib import Path
from statistics import median

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image

# ================================================================== ORTAK BAŞLANGIÇ

TEXT_LAYER_MIN_CHARS = 20
VISIBILITY_SCALE = 2.0
VISIBILITY_TEXT_DIFF = 24
VISIBILITY_PATH_DIFF = 6
OCR_COMMAND = os.environ.get("TESSERACT_CMD", "tesseract")
OCR_LANGUAGE = "tur"
OCR_DPI = 300
OCR_PAGE_PSM = 3
OCR_SPARSE_PSM = 11
OCR_VOTE_MIN_CONFIDENCE = 60.0
OCR_CACHE_DIR = os.environ.get("OCR_CACHE_DIR")
OCR_BOLD_STROKE_RATIO = 1.3
OCR_HEIGHT_PER_SIZE = 0.93
OCR_FIT_MARGIN_EM = 1.0
ITALIC_FLAG = 1 << 6
FORCE_BOLD_FLAG = 1 << 18
SOFT_HYPHEN = "\u00ad"
TRUETYPE_SPACE_GLYPH = 3
OCR_VOTE_MIN_PUNCT_CONFIDENCE = 20.0
UNKNOWN_GLYPH = "\ufffd"
SPACES = frozenset(" \r\n\t\xa0   ")
WORD_GAP_EM = 0.25
ROW_TOLERANCE_EM = 0.45
SEGMENT_GAP_EM = 1.0
ROW_MERGE_GAP_EM = 1.8
BAND_SHARE = 0.15
OUTER_TOP_SHARE = 0.10
OUTER_BOTTOM_SHARE = 0.92
FURNITURE_PAGE_SHARE = 0.3
BOX_MAX_PAGE_SHARE = 0.9
GUTTER_SCAN = (0.15, 0.85)
GUTTER_MIN_SIDE_SHARE = 0.15
GUTTER_MAX_CROSSING_SHARE = 0.08
GUTTER_MIN_WIDTH_EM = 0.6
GUTTER_MAX_CROSSING_ITEMS = 2
HORIZONTAL_GAP_EM = 0.8
EDGE_GROUP_EM = 1.5
PARAGRAPH_INDENT_EM = 0.8
UNDERLINE_EXTRA_EM = 2.0
CLOSED = re.compile(r"[.!?:…\"”’)]\**$")
TINY_PRINT_RATIO = 0.7
BOLD_SEAM = re.compile(r"\*\*(\s+)\*\*")
PROSE_FULL_SHARE = 0.6
PROSE_LINE_SHARE = 0.8
STRIP_GAP_EM = 1.5
DIGITS = re.compile(r"\d+")
HARD_START = re.compile(r"^(?:[–—•▪●-]|(?:I{1,3}|IV|VI{0,3})\.)$")
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})


def tr_lower(text: str) -> str:
    """Türkçe kurallarla küçük harfe çevirir (I→ı, İ→i)."""
    return text.translate(_TR_LOWER).lower()


@dataclass
class Char:
    """Sayfadaki tek karakter: metin, kutu (üst-sol orijin), stil ve okuma bilgisi."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    font: str
    bold: bool
    italic: bool
    color: str
    code: int = 0
    broken: bool = False
    ink: bool = True


@dataclass
class Word:
    """Boşlukla ayrılmış kelime; stil ilk harften, kalın/italik çoğunluktan."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    font: str
    bold: bool
    italic: bool
    color: str
    chars: list[Char] = field(repr=False, default_factory=list)
    ocr: bool = False
    confidence: float = 100.0
    order: int = 0


@dataclass
class Line:
    """Aynı satırdaki kelimeler (bir sütun içinde)."""

    words: list[Word]
    page_no: int

    @property
    def x0(self) -> float:
        """Sol kenar."""
        return min(w.x0 for w in self.words)

    @property
    def x1(self) -> float:
        """Sağ kenar."""
        return max(w.x1 for w in self.words)

    @property
    def y0(self) -> float:
        """Üst kenar."""
        return min(w.y0 for w in self.words)

    @property
    def y1(self) -> float:
        """Alt kenar."""
        return max(w.y1 for w in self.words)

    @property
    def text(self) -> str:
        """Kelimelerin boşlukla birleşimi."""
        return " ".join(w.text for w in self.words)

    @property
    def size(self) -> float:
        """Kelime boyutlarının ortancası."""
        sizes = sorted(w.size for w in self.words)
        return sizes[len(sizes) // 2]


@dataclass
class Shape:
    """Görünen çizim: kutu, yatay/dikey çizgi, çerçeve ya da diğer şekil."""

    kind: str
    x0: float
    y0: float
    x1: float
    y1: float
    fill: str | None
    stroke: str | None


@dataclass
class PageIR:
    """Kütüphaneden bağımsız sayfa: satırlar, çizimler ve okuma notları."""

    page_no: int
    width: float
    height: float
    lines: list[Line]
    shapes: list[Shape]
    source: str = "TEXT"
    notes: list[str] = field(default_factory=list)
    document: str = ""


@dataclass
class OcrWord:
    """Tesseract kelimesi: metin, piksel kutusu, güven ve satır anahtarı."""

    text: str
    x0: int
    y0: int
    x1: int
    y1: int
    confidence: float
    line_key: tuple[int, int, int]
    order: int


@dataclass
class RawPage:
    """Okunmuş ama bozuk fontları henüz çözülmemiş sayfa."""

    page_no: int
    width: float
    height: float
    chars: list[Char]
    shapes: list[Shape]
    ocr_words: list[Word]
    votes: Counter[tuple[str, int, str]]


def read_document(path: str) -> list[PageIR]:
    """PDF'i sayfa ara temsiline çevirir; bozuk fontları belge düzeyinde çözer."""
    document = pdfium.PdfDocument(path)
    try:
        raws = [read_raw_page(document, index) for index in range(len(document))]
    finally:
        document.close()
    votes: Counter[tuple[str, int, str]] = Counter()
    for raw in raws:
        votes.update(raw.votes)
    decoder = GlyphDecoder(votes)
    pages = [finish_page(raw, decoder) for raw in raws]
    for page in pages:
        page.document = path
    return pages


def read_raw_page(document: pdfium.PdfDocument, index: int) -> RawPage:
    """Sayfanın görünen karakterlerini ve çizimlerini okur; gerekirse OCR'a başvurur."""
    page = document[index]
    textpage = page.get_textpage()
    try:
        text_ink, path_ink = ink_masks(page)
        chars = read_chars(page, textpage, text_ink)
        shapes = read_shapes(page, path_ink)
        ocr_words: list[Word] = []
        votes: Counter[tuple[str, int, str]] = Counter()
        visible = sum(1 for c in chars if c.ink and c.text not in SPACES)
        if visible < TEXT_LAYER_MIN_CHARS and path_ink.any():
            ocr_words = read_page_by_ocr(page)
            shapes = drop_glyph_shapes(shapes, ocr_words)
        elif any(c.broken and c.ink for c in chars):
            votes = vote_broken_glyphs(page, chars)
        return RawPage(
            index + 1, page.get_width(), page.get_height(), chars, shapes, ocr_words, votes
        )
    finally:
        textpage.close()
        page.close()


def render_gray(page: pdfium.PdfPage, scale: float) -> Image.Image:
    """Sayfayı gri tonlu çizer."""
    return page.render(scale=scale, grayscale=True).to_pil().convert("L")


@contextmanager
def deactivated(page: pdfium.PdfPage, hide: Callable[[pdfium.PdfObject], bool]) -> Iterator[None]:
    """Seçilen yaprak nesneleri çizimden geçici olarak çıkarır."""
    hidden = [
        obj for obj in page.get_objects() if obj.type != pdfium_c.FPDF_PAGEOBJ_FORM and hide(obj)
    ]
    for obj in hidden:
        pdfium_c.FPDFPageObj_SetIsActive(obj.raw, False)
    try:
        yield
    finally:
        for obj in hidden:
            pdfium_c.FPDFPageObj_SetIsActive(obj.raw, True)


def ink_masks(page: pdfium.PdfPage) -> tuple[np.ndarray, np.ndarray]:
    """Metin ve çizim nesnelerinin sayfaya bıraktığı görünür mürekkep maskeleri."""
    full = np.asarray(render_gray(page, VISIBILITY_SCALE), dtype=np.int16)
    masks = []
    for kind, threshold in (
        (pdfium_c.FPDF_PAGEOBJ_TEXT, VISIBILITY_TEXT_DIFF),
        (pdfium_c.FPDF_PAGEOBJ_PATH, VISIBILITY_PATH_DIFF),
    ):
        with deactivated(page, lambda obj, kind=kind: obj.type == kind):
            bare = np.asarray(render_gray(page, VISIBILITY_SCALE), dtype=np.int16)
        masks.append(np.abs(full - bare) > threshold)
    return masks[0], masks[1]


def has_ink(mask: np.ndarray, x0: float, y0: float, x1: float, y1: float, pad: int = 0) -> bool:
    """Kutunun içinde (ölçekli) görünür mürekkep var mı."""
    s = VISIBILITY_SCALE
    top, bottom = max(int(y0 * s) - pad, 0), min(int(y1 * s) + 1 + pad, mask.shape[0])
    left, right = max(int(x0 * s) - pad, 0), min(int(x1 * s) + 1 + pad, mask.shape[1])
    return bottom > top and right > left and bool(mask[top:bottom, left:right].any())


def font_info(textpage: pdfium.PdfTextPage, index: int) -> tuple[str, int]:
    """Karakterin font adı ve bayrakları."""
    flags = ctypes.c_int(0)
    size = pdfium_c.FPDFText_GetFontInfo(textpage, index, None, 0, ctypes.byref(flags))
    if size <= 0:
        return "", 0
    buffer = ctypes.create_string_buffer(size)
    pdfium_c.FPDFText_GetFontInfo(textpage, index, buffer, size, ctypes.byref(flags))
    return buffer.value.decode("utf-8", "replace"), flags.value


def fill_color(textpage: pdfium.PdfTextPage, index: int) -> str:
    """Karakterin dolgu rengi (#rrggbb)."""
    r, g, b, a = (ctypes.c_uint(0) for _ in range(4))
    ok = pdfium_c.FPDFText_GetFillColor(textpage, index, *(ctypes.byref(v) for v in (r, g, b, a)))
    return f"#{r.value:02x}{g.value:02x}{b.value:02x}" if ok else "#000000"


def text_matrix(textpage: pdfium.PdfTextPage, index: int) -> tuple[float, bool]:
    """Karakterin metin matrisi ölçeği (InDesign boyutu matriste tutar) ve döndürülmüşlüğü."""
    matrix = pdfium_c.FS_MATRIX()
    if not pdfium_c.FPDFText_GetMatrix(textpage, index, ctypes.byref(matrix)):
        return 1.0, False
    rotated = abs(matrix.b) > 1e-3 or abs(matrix.c) > 1e-3
    return abs(matrix.a * matrix.d - matrix.b * matrix.c) ** 0.5 or 1.0, rotated


@dataclass
class Stacking:
    """Çizim sırası: metin nesnelerinin sırası, kırpma kutuları ve üstlerini örten opak çizimler."""

    order: dict[int, int]
    clips: dict[int, tuple[float, float, float, float]]
    covers: list[tuple[int, float, float, float, float]]

    def hidden(self, obj_address: int, box: tuple[float, float, float, float]) -> bool:
        """Karakter kırpma alanının dışında ya da sonradan çizilen opak bir şeklin altında mı."""
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        clip = self.clips.get(obj_address)
        if clip and not (clip[0] <= cx <= clip[2] and clip[1] <= cy <= clip[3]):
            return True
        z = self.order.get(obj_address, -1)
        return any(
            cz > z and cx0 <= x0 + 0.5 and cy0 <= y0 + 0.5 and cx1 >= x1 - 0.5 and cy1 >= y1 - 0.5
            for cz, cx0, cy0, cx1, cy1 in self.covers
        )


def stacking(page: pdfium.PdfPage) -> Stacking:
    """Sayfa nesnelerinin çizim sırasını, metin kırpmalarını ve opak örtüleri toplar."""
    height = page.get_height()
    order, clips, covers = {}, {}, []
    for z, obj in enumerate(page.get_objects()):
        address = ctypes.addressof(obj.raw.contents)
        order[address] = z
        if obj.type == pdfium_c.FPDF_PAGEOBJ_TEXT:
            clip = clip_box(obj, height)
            if clip:
                clips[address] = clip
        elif obj.type in (pdfium_c.FPDF_PAGEOBJ_PATH, pdfium_c.FPDF_PAGEOBJ_IMAGE) and opaque(obj):
            left, bottom, right, top = obj.get_bounds()
            covers.append((z, left, height - top, right, height - bottom))
    return Stacking(order, clips, covers)


def opaque(obj: pdfium.PdfObject) -> bool:
    """Nesne arkasını tamamen örten opak bir dolgu ya da resim mi."""
    if pdfium_c.FPDFPageObj_HasTransparency(obj.raw):
        return False
    if obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
        return True
    fillmode, stroke = ctypes.c_int(0), ctypes.c_int(0)
    pdfium_c.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fillmode), ctypes.byref(stroke))
    r, g, b, a = (ctypes.c_uint(0) for _ in range(4))
    ok = fillmode.value and pdfium_c.FPDFPageObj_GetFillColor(
        obj.raw, *(ctypes.byref(v) for v in (r, g, b, a))
    )
    return bool(ok) and a.value == 255 and pdfium_c.FPDFPath_CountSegments(obj.raw) <= 6


def clip_box(obj: pdfium.PdfObject, height: float) -> tuple[float, float, float, float] | None:
    """Nesnenin kırpma yollarının kesişiminin kutusu (üst-sol orijin)."""
    clip = pdfium_c.FPDFPageObj_GetClipPath(obj.raw)
    if not clip:
        return None
    box = None
    for path in range(pdfium_c.FPDFClipPath_CountPaths(clip)):
        xs, ys = [], []
        for index in range(pdfium_c.FPDFClipPath_CountPathSegments(clip, path)):
            segment = pdfium_c.FPDFClipPath_GetPathSegment(clip, path, index)
            x, y = ctypes.c_float(), ctypes.c_float()
            pdfium_c.FPDFPathSegment_GetPoint(segment, ctypes.byref(x), ctypes.byref(y))
            xs.append(x.value)
            ys.append(height - y.value)
        if not xs:
            continue
        part = (min(xs), min(ys), max(xs), max(ys))
        box = (
            part
            if box is None
            else (
                max(box[0], part[0]),
                max(box[1], part[1]),
                min(box[2], part[2]),
                min(box[3], part[3]),
            )
        )
    return box


def read_chars(page: pdfium.PdfPage, textpage: pdfium.PdfTextPage, ink: np.ndarray) -> list[Char]:
    """Sayfanın döndürülmemiş karakterlerini stil ve görünürlükleriyle okur."""
    height = page.get_height()
    layers = stacking(page)
    chars = []
    for index in range(textpage.count_chars()):
        scale, rotated = text_matrix(textpage, index)
        if rotated:
            continue
        code = pdfium_c.FPDFText_GetUnicode(textpage, index)
        text = chr(code) if code else ""
        if pdfium_c.FPDFText_IsHyphen(textpage, index) == 1 or code == 2:
            text = SOFT_HYPHEN
        left, bottom, right, top = textpage.get_charbox(index, loose=True)
        tight = textpage.get_charbox(index)
        font, flags = font_info(textpage, index)
        weight = pdfium_c.FPDFText_GetFontWeight(textpage, index)
        name = font.lower()
        chars.append(
            Char(
                text=text,
                x0=left,
                y0=height - top,
                x1=right,
                y1=height - bottom,
                size=round(pdfium_c.FPDFText_GetFontSize(textpage, index) * scale, 1),
                font=font,
                bold=weight >= 600 or bool(flags & FORCE_BOLD_FLAG) or "bold" in name,
                italic=bool(flags & ITALIC_FLAG) or "italic" in name or "oblique" in name,
                color=fill_color(textpage, index),
                code=code,
                broken=pdfium_c.FPDFText_HasUnicodeMapError(textpage, index) == 1,
                ink=has_ink(ink, tight[0], height - tight[3], tight[2], height - tight[1], 1)
                and not hidden_char(
                    textpage, index, layers, (left, height - top, right, height - bottom)
                ),
            )
        )
    return chars


def hidden_char(
    textpage: pdfium.PdfTextPage,
    index: int,
    layers: Stacking,
    box: tuple[float, float, float, float],
) -> bool:
    """Karakterin metin nesnesi kırpılmış ya da üstü örtülmüş mü."""
    obj = pdfium_c.FPDFText_GetTextObject(textpage, index)
    return bool(obj) and layers.hidden(ctypes.addressof(obj.contents), box)


def object_font(obj: pdfium.PdfObject) -> str:
    """Metin nesnesinin font adı."""
    font = pdfium_c.FPDFTextObj_GetFont(obj.raw)
    size = pdfium_c.FPDFFont_GetBaseFontName(font, None, 0)
    buffer = ctypes.create_string_buffer(size)
    pdfium_c.FPDFFont_GetBaseFontName(font, buffer, size)
    return buffer.value.decode("utf-8", "replace")


@contextmanager
def blackened(objects: list[pdfium.PdfObject]) -> Iterator[None]:
    """Metin nesnelerini OCR için geçici olarak siyaha boyar."""
    saved = []
    for obj in objects:
        r, g, b, a = (ctypes.c_uint(0) for _ in range(4))
        pdfium_c.FPDFPageObj_GetFillColor(obj.raw, *(ctypes.byref(v) for v in (r, g, b, a)))
        saved.append((obj, r.value, g.value, b.value, a.value))
        pdfium_c.FPDFPageObj_SetFillColor(obj.raw, 0, 0, 0, 255)
    try:
        yield
    finally:
        for obj, r, g, b, a in saved:
            pdfium_c.FPDFPageObj_SetFillColor(obj.raw, r, g, b, a)


def vote_broken_glyphs(page: pdfium.PdfPage, chars: list[Char]) -> Counter[tuple[str, int, str]]:
    """Bozuk fontlu metni tek başına çizip OCR'la okur; (font, kod, harf) oylarını sayar."""
    fonts = {c.font for c in chars if c.broken and c.ink}
    texts = [
        obj
        for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_TEXT])
        if object_font(obj) in fonts
    ]
    keep = {ctypes.addressof(obj.raw.contents) for obj in texts}
    scale = OCR_DPI / 72
    with (
        deactivated(page, lambda obj: ctypes.addressof(obj.raw.contents) not in keep),
        blackened(texts),
    ):
        image = render_gray(page, scale)
    votes: Counter[tuple[str, int, str]] = Counter()
    candidates = [c for c in chars if c.ink and c.text not in SPACES]
    for word in run_ocr(image, OCR_SPARSE_PSM):
        punct = len(word.text) == 1 and not word.text.isalnum()
        minimum = OCR_VOTE_MIN_PUNCT_CONFIDENCE if punct else OCR_VOTE_MIN_CONFIDENCE
        if word.confidence < minimum:
            continue
        box = (word.x0 / scale, word.y0 / scale, word.x1 / scale, word.y1 / scale)
        inside = sorted((c for c in candidates if center_in(c, box)), key=lambda c: c.x0)
        if len(inside) != len(word.text):
            continue
        for char, letter in zip(inside, word.text, strict=True):
            if char.broken:
                votes[(char.font, char.code, letter)] += 1
    return votes


def center_in(char: Char, box: tuple[float, float, float, float]) -> bool:
    """Karakterin yatay ortası kutuda, dikey ortası kutu ortasına yakın mı (ince tire dahil)."""
    cx, cy = (char.x0 + char.x1) / 2, (char.y0 + char.y1) / 2
    near = abs(cy - (box[1] + box[3]) / 2) < 0.5 * (char.y1 - char.y0)
    return box[0] <= cx <= box[2] and near


class GlyphDecoder:
    """Bozuk eşlemeli fontların kodlarını OCR oylarıyla ve fontun kod kaymasıyla çözer."""

    def __init__(self, votes: Counter[tuple[str, int, str]]) -> None:
        """Oylardan kod tablosunu ve font başına kod kaymasını kurar."""
        tallies: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
        for (font, code, letter), count in votes.items():
            tallies[(font, code)][letter] += count
        self.table: dict[tuple[str, int], str] = {}
        for key, tally in tallies.items():
            ranked = tally.most_common(2)
            if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
                self.table[key] = ranked[0][0]
        shifts: dict[str, Counter[int]] = defaultdict(Counter)
        for (font, code), letter in self.table.items():
            if letter.isascii() and letter.isalnum():
                shifts[font][ord(letter) - code] += 1
        self.shift = {
            font: tally.most_common(1)[0][0]
            for font, tally in shifts.items()
            if tally.most_common(1)[0][1] >= 3
            and tally.most_common(1)[0][1] * 10 >= 6 * sum(tally.values())
        }

    def sibling_letter(self, char: Char) -> str | None:
        """Aynı kod kaymasına sahip (aynı glif sıralı) başka bozuk fonttaki oyu kullanır."""
        shift = self.shift.get(char.font)
        if shift is None:
            return None
        for font, other in self.shift.items():
            letter = self.table.get((font, char.code))
            if font != char.font and other == shift and letter:
                return letter
        return None

    def decode(self, char: Char) -> str:
        """Bozuk karakterin harfi; mürekkepsizse boşluk, çözülemezse yerine geçen işaret."""
        if not char.ink:
            return " "
        letter = self.table.get((char.font, char.code)) or self.sibling_letter(char)
        if letter:
            return letter
        shift = self.shift.get(char.font)
        if shift is not None and 0x20 <= char.code + shift <= 0x7E:
            return chr(char.code + shift)
        if char.code == TRUETYPE_SPACE_GLYPH:
            return " "
        return UNKNOWN_GLYPH


def run_ocr(image: Image.Image, psm: int) -> list[OcrWord]:
    """Görüntüyü Tesseract'la (Türkçe) okur; kelimeleri piksel kutularıyla verir."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "page.png"
        image.save(path)
        cached = ocr_cache_path(path.read_bytes(), psm)
        if cached and cached.exists():
            output = cached.read_text(encoding="utf-8")
        else:
            command = [OCR_COMMAND, str(path), "stdout", "-l", OCR_LANGUAGE, "--psm", str(psm)]
            output = subprocess.run(
                [*command, "tsv"], capture_output=True, text=True, check=True
            ).stdout
            if cached:
                cached.write_text(output, encoding="utf-8")
    words = []
    for row in output.splitlines()[1:]:
        parts = row.split("\t")
        if len(parts) < 12 or parts[0] != "5" or not parts[11].strip():
            continue
        left, top, width, height = (int(v) for v in parts[6:10])
        key = (int(parts[2]), int(parts[3]), int(parts[4]))
        text = unicodedata.normalize("NFC", parts[11].strip())
        box = (left, top, left + width, top + height)
        words.append(OcrWord(text, *box, float(parts[10]), key, len(words)))
    return words


def ocr_cache_path(image_bytes: bytes, psm: int) -> Path | None:
    """Geliştirme için OCR önbelleği (OCR_CACHE_DIR verilmişse)."""
    if not OCR_CACHE_DIR:
        return None
    folder = Path(OCR_CACHE_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{hashlib.sha1(image_bytes).hexdigest()}_{psm}.tsv"


def read_page_by_ocr(page: pdfium.PdfPage) -> list[Word]:
    """Metin katmanı olmayan sayfayı OCR'la kelimelere çevirir; kalınlığı tahmin eder."""
    scale = OCR_DPI / 72
    image = render_gray(page, scale)
    found = run_ocr(image, OCR_PAGE_PSM)
    gray = np.asarray(image)
    strokes = [stroke_width(gray, w) for w in found]
    typical = median([s for s in strokes if s > 0] or [1.0])
    heights: dict[tuple[int, int, int], float] = defaultdict(float)
    for word in found:
        heights[word.line_key] = max(heights[word.line_key], (word.y1 - word.y0) / scale)
    words = []
    for index, (word, stroke) in enumerate(zip(found, strokes, strict=True)):
        size = round(heights[word.line_key] / OCR_HEIGHT_PER_SIZE, 1)
        around = [
            strokes[k]
            for k in (index - 1, index, index + 1)
            if 0 <= k < len(found) and found[k].line_key == word.line_key and strokes[k] > 0
        ]
        bold = stroke > 0 and median(around) >= OCR_BOLD_STROKE_RATIO * typical
        words.append(ocr_word(word, scale, size, bold))
    return words


def ocr_word(found: OcrWord, scale: float, size: float, bold: bool) -> Word:
    """OCR kelimesini harflere eşit bölünmüş kutularla kelimeye çevirir."""
    x0, y0, x1, y1 = (v / scale for v in (found.x0, found.y0, found.x1, found.y1))
    step = (x1 - x0) / max(len(found.text), 1)
    chars = [
        Char(
            letter, x0 + i * step, y0, x0 + (i + 1) * step, y1, size, "OCR", bold, False, "#000000"
        )
        for i, letter in enumerate(found.text)
    ]
    return Word(
        found.text,
        x0,
        y0,
        x1,
        y1,
        size,
        "OCR",
        bold,
        False,
        "#000000",
        chars,
        True,
        found.confidence,
        found.order,
    )


def stroke_width(gray: np.ndarray, word: OcrWord) -> float:
    """Harf çizgisi kalınlığı: koyu yatay ve dikey koşuların ortalama uzunluğunun küçüğü."""
    dark = gray[word.y0 : word.y1, word.x0 : word.x1] < 128
    if not dark.size or not any(ch.isalnum() for ch in word.text):
        return 0.0
    runs = []
    for grid in (dark, dark.T):
        starts = int(grid[:, 0].sum()) + int((grid[:, 1:] & ~grid[:, :-1]).sum())
        runs.append(float(grid.sum()) / starts if starts else 0.0)
    return min(runs)


def render_crop(page: PageIR, box: tuple[float, float, float, float]) -> np.ndarray:
    """Sayfanın bir bölgesini OCR çözünürlüğünde gri tonlu çizer."""
    document = pdfium.PdfDocument(page.document)
    try:
        pdf_page = document[page.page_no - 1]
        x0, y0, x1, y1 = box
        crop = (x0, page.height - y1, page.width - x1, y0)
        image = pdf_page.render(scale=OCR_DPI / 72, grayscale=True, crop=crop).to_pil()
        pdf_page.close()
    finally:
        document.close()
    return np.asarray(image.convert("L"))


@dataclass
class Blob:
    """Koyu piksellerden bağlı bileşen: kutu ve piksel sayısı."""

    x0: int
    y0: int
    x1: int
    y1: int
    count: int
    mask: np.ndarray = field(repr=False, default_factory=lambda: np.zeros((0, 0), bool))

    @property
    def fill(self) -> float:
        """Kutunun ne kadarı dolu."""
        return self.count / max((self.x1 - self.x0) * (self.y1 - self.y0), 1)


def find_blobs(gray: np.ndarray) -> list[Blob]:
    """Görüntüdeki koyu bağlı bileşenleri (8 komşuluk) soldan sağa verir."""
    dark = gray < 128
    seen = np.zeros_like(dark)
    height, width = dark.shape
    blobs = []
    for y, x in zip(*np.nonzero(dark), strict=True):
        if seen[y, x]:
            continue
        seen[y, x] = True
        stack, ys, xs = [(y, x)], [], []
        while stack:
            cy, cx = stack.pop()
            ys.append(cy)
            xs.append(cx)
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < height and 0 <= nx < width and dark[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        x0, y0 = min(xs), min(ys)
        mask = np.zeros((max(ys) + 1 - y0, max(xs) + 1 - x0), bool)
        mask[np.array(ys) - y0, np.array(xs) - x0] = True
        blobs.append(Blob(x0, y0, max(xs) + 1, max(ys) + 1, len(xs), mask))
    return sorted(blobs, key=lambda b: b.x0)


def drop_glyph_shapes(shapes: list[Shape], words: list[Word]) -> list[Shape]:
    """OCR sayfasında harf çizimlerini atar; alt çizgileri ve büyük kutuları bırakır."""
    if not words:
        return shapes
    size = median(w.size for w in words)
    kept = []
    for shape in shapes:
        if shape.kind in ("HLINE", "VLINE"):
            if not any(within_glyphs(shape, w) for w in words):
                kept.append(shape)
        elif min(shape.x1 - shape.x0, shape.y1 - shape.y0) > 2 * size:
            kept.append(shape)
    return kept


def within_glyphs(shape: Shape, word: Word) -> bool:
    """Çizgi kelimenin harf alanında mı (alt kenara yapışık alt çizgi değil)."""
    height = word.y1 - word.y0
    horizontal = word.x0 - 1 <= shape.x0 and shape.x1 <= word.x1 + 1
    if not any(ch.isalnum() for ch in word.text):
        return horizontal and word.y0 - 1 <= shape.y0 and shape.y1 <= word.y1 + 1
    return horizontal and word.y0 - 1 <= shape.y0 and shape.y1 <= word.y1 - 0.2 * height


def read_shapes(page: pdfium.PdfPage, ink: np.ndarray) -> list[Shape]:
    """Sayfanın görünen yol nesnelerini kutu, çizgi, çerçeve ya da şekil olarak okur."""
    height, width = page.get_height(), page.get_width()
    shapes = []
    for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_PATH]):
        left, bottom, right, top = obj.get_bounds()
        x0, y0, x1, y1 = (
            max(left, 0),
            max(height - top, 0),
            min(right, width),
            min(height - bottom, height),
        )
        if x1 <= x0 and y1 <= y0 or not has_ink(ink, x0, y0, x1, y1, 1):
            continue
        fill, stroke = path_colors(obj)
        shapes.append(
            Shape(shape_kind(obj, x1 - x0, y1 - y0, fill, stroke), x0, y0, x1, y1, fill, stroke)
        )
    return shapes


def path_colors(obj: pdfium.PdfObject) -> tuple[str | None, str | None]:
    """Yolun görünen dolgu ve çizgi renkleri."""
    fillmode, stroke = ctypes.c_int(0), ctypes.c_int(0)
    pdfium_c.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fillmode), ctypes.byref(stroke))
    colors: list[str | None] = []
    for active, getter in (
        (fillmode.value, pdfium_c.FPDFPageObj_GetFillColor),
        (stroke.value, pdfium_c.FPDFPageObj_GetStrokeColor),
    ):
        r, g, b, a = (ctypes.c_uint(0) for _ in range(4))
        ok = active and getter(obj.raw, *(ctypes.byref(v) for v in (r, g, b, a)))
        colors.append(f"#{r.value:02x}{g.value:02x}{b.value:02x}" if ok and a.value else None)
    return colors[0], colors[1]


def shape_kind(
    obj: pdfium.PdfObject, width: float, height: float, fill: str | None, stroke: str | None
) -> str:
    """Yolun türü: yatay/dikey çizgi, dolgulu kutu, çerçeve ya da şekil."""
    if height <= 2.0 and width > 4:
        return "HLINE"
    if width <= 2.0 and height > 4:
        return "VLINE"
    if pdfium_c.FPDFPath_CountSegments(obj.raw) <= 6 and (fill or stroke):
        return "BOX" if fill else "FRAME"
    return "SHAPE"


def finish_page(raw: RawPage, decoder: GlyphDecoder) -> PageIR:
    """Bozuk karakterleri çözüp gizlileri atar; kelime ve satırları kurar."""
    notes: list[str] = []
    if raw.ocr_words:
        words, source = raw.ocr_words, "OCR"
    else:
        chars = []
        for char in raw.chars:
            if char.broken:
                char = replace(char, text=decoder.decode(char))
            elif not char.ink and char.text not in SPACES:
                continue
            chars.append(char)
        if any(c.text == UNKNOWN_GLYPH for c in chars):
            notes.append("UNDECODED_GLYPHS")
        if any(c.broken for c in chars):
            notes.append("REPAIRED_GLYPHS")
        words, source = build_words(chars), "TEXT"
    lines = build_lines(words, raw.page_no)
    source = source if lines else "EMPTY"
    return PageIR(raw.page_no, raw.width, raw.height, lines, raw.shapes, source, notes)


def build_words(chars: list[Char]) -> list[Word]:
    """Boşlukta, satır değişiminde ve büyük aralıkta kelimeyi böler."""
    words: list[Word] = []
    current: list[Char] = []

    def flush() -> None:
        if current:
            words.append(make_word(current))
            current.clear()

    for char in chars:
        if not char.text or char.text in SPACES:
            flush()
            continue
        if current:
            previous = current[-1]
            size = max(char.size, 1)
            same_line = abs((previous.y0 + previous.y1) - (char.y0 + char.y1)) / 2 < 0.5 * size
            gap = char.x0 - previous.x1
            if not same_line or gap > WORD_GAP_EM * size or gap < -2 * size:
                flush()
        current.append(char)
    flush()
    return words


def make_word(chars: list[Char]) -> Word:
    """Karakterlerden kelime kurar (NFC)."""
    first = chars[0]
    return Word(
        text=unicodedata.normalize("NFC", "".join(c.text for c in chars)),
        x0=min(c.x0 for c in chars),
        y0=min(c.y0 for c in chars),
        x1=max(c.x1 for c in chars),
        y1=max(c.y1 for c in chars),
        size=first.size,
        font=first.font,
        bold=sum(c.bold for c in chars) * 2 > len(chars),
        italic=sum(c.italic for c in chars) * 2 > len(chars),
        color=first.color,
        chars=list(chars),
    )


def build_lines(words: list[Word], page_no: int) -> list[Line]:
    """Kelimeleri dikey ortasına göre satırlara toplar; sütun aralığı kadar boşlukta böler."""
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda w: ((w.y0 + w.y1) / 2, w.x0)):
        middle = (word.y0 + word.y1) / 2
        if rows:
            last = rows[-1]
            last_middle = sum((w.y0 + w.y1) / 2 for w in last) / len(last)
            if abs(middle - last_middle) < ROW_TOLERANCE_EM * word.size:
                last.append(word)
                continue
        rows.append([word])
    lines = []
    for row in rows:
        row.sort(key=lambda w: (w.order, w.x0) if w.ocr else (0, w.x0))
        segment = [row[0]]
        for word in row[1:]:
            if word.x0 - segment[-1].x1 > SEGMENT_GAP_EM * max(word.size, segment[-1].size):
                lines.append(Line(segment, page_no))
                segment = [word]
            else:
                segment.append(word)
        lines.append(Line(segment, page_no))
    return lines


# ---------------------------------------------------------------- düzen


@dataclass
class Region:
    """Okuma bölgesi (sütun): anahtarı ve belge düzeyindeki sol/sağ kenarı."""

    key: tuple[int, int]
    left: float
    right: float
    lines: list[Line] = field(default_factory=list, repr=False)
    box: Shape | None = None


@dataclass
class Body:
    """Okuma sırasındaki gövde satırları, bölgeleri ve çizimler."""

    lines: list[Line]
    furniture: list[Line]
    region_of: dict[int, Region]
    shapes: dict[int, list[Shape]]
    body_size: float
    regions: list[Region] = field(default_factory=list)
    pages: dict[int, PageIR] = field(default_factory=dict)


@dataclass
class Item:
    """XY-cut öğesi: satır ya da içindekilerle birlikte bölünmez kutu."""

    x0: float
    y0: float
    x1: float
    y1: float
    chars: int
    line: Line | None = None
    box: Shape | None = None
    inner: list[Item] = field(default_factory=list)


def band(line: Line, page: PageIR) -> str | None:
    """Satır sayfanın üst ya da alt kenar bandında mı."""
    if line.y1 < BAND_SHARE * page.height:
        return "TOP"
    if line.y0 > (1 - BAND_SHARE) * page.height:
        return "BOTTOM"
    return None


def outer(line: Line, page: PageIR) -> bool:
    """Satır sayfanın en dış kenarında mı (koşu başlığı, sayfa numarası yeri)."""
    return line.y1 < OUTER_TOP_SHARE * page.height or line.y0 > OUTER_BOTTOM_SHARE * page.height


def line_style(line: Line) -> tuple[str, float, bool, str]:
    """Satırın baskın stili: font ailesi, boyut, kalınlık, renk."""
    counts: Counter[tuple[str, float, bool, str]] = Counter()
    for word in line.words:
        family = word.font.split("+", 1)[-1]
        counts[(family, round(word.size * 2) / 2, word.bold, word.color)] += len(word.text)
    return counts.most_common(1)[0][0]


def find_furniture(pages: list[PageIR], body_style: tuple[str, float, bool, str]) -> set[int]:
    """Üst/alt bilgi: kenarda aynen tekrarlayan, aynı stilde koşu başlığı ya da yalnız sayı."""
    texts: Counter[tuple[str | None, str]] = Counter()
    styles: Counter[tuple[str | None, tuple[str, float, bool, str]]] = Counter()
    for page in pages:
        texts.update(
            {
                (band(text_line, page), text_line.text)
                for text_line in page.lines
                if band(text_line, page)
            }
        )
        styles.update(
            {
                (band(text_line, page), line_style(text_line))
                for text_line in page.lines
                if outer(text_line, page)
            }
        )
    furniture = set()
    for page in pages:
        for line in page.lines:
            zone = band(line, page)
            if zone is None:
                continue
            count = texts[(zone, line.text)]
            repeated = count >= 2 and (
                outer(line, page) or count >= FURNITURE_PAGE_SHARE * len(pages)
            )
            style = line_style(line)
            running = (
                outer(line, page)
                and style[0] != "OCR"
                and style != body_style
                and styles[(zone, style)] >= 2
                and alone_in_row(line, page)
            )
            lone_number = (
                outer(line, page)
                and not DIGITS.sub("", line.text).strip(" -–/.|")
                and alone_in_row(line, page)
            )
            tiny = outer(line, page) and line.size < TINY_PRINT_RATIO * body_style[1]
            if repeated or running or lone_number or tiny:
                furniture.add(id(line))
    return furniture


def alone_in_row(line: Line, page: PageIR) -> bool:
    """Satırın aynı sırada, birleşecek kadar yakın komşusu yok mu (sayfa numarası gibi)."""
    middle = (line.y0 + line.y1) / 2
    for other in page.lines:
        if other is line or abs((other.y0 + other.y1) / 2 - middle) >= ROW_TOLERANCE_EM * line.size:
            continue
        gap = max(other.x0 - line.x1, line.x0 - other.x1)
        if gap <= ROW_MERGE_GAP_EM * line.size:
            return False
    return True


def reading_order(pages: list[PageIR]) -> Body:
    """Üst/alt bilgiyi ayırır; satırları XY-cut bölgelerine ve okuma sırasına koyar."""
    sizes = [
        w.size for p in pages for text_line in p.lines for w in text_line.words for _ in w.text
    ]
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 10.0
    styles: Counter[tuple[str, float, bool, str]] = Counter()
    for page in pages:
        for line in page.lines:
            styles[line_style(line)] += len(line.text)
    body_style = styles.most_common(1)[0][0] if styles else ("", 0.0, False, "")
    furniture_ids = find_furniture(pages, body_style)
    furniture, regions = [], []
    for page in pages:
        lines = [text_line for text_line in page.lines if id(text_line) not in furniture_ids]
        furniture.extend(text_line for text_line in page.lines if id(text_line) in furniture_ids)
        for index, (group, box) in enumerate(page_regions(lines, page, body_size)):
            regions.append(Region((page.page_no, index), 0.0, 0.0, merge_segments(group), box))
    set_edges(regions, body_size)
    box_edges(regions)
    ordered = [line for region in regions for line in region.lines]
    region_of = {id(line): region for region in regions for line in region.lines}
    shapes = {page.page_no: page.shapes for page in pages}
    by_number = {page.page_no: page for page in pages}
    return Body(ordered, furniture, region_of, shapes, body_size, regions, by_number)


def page_regions(
    lines: list[Line], page: PageIR, size: float
) -> list[tuple[list[Line], Shape | None]]:
    """Sayfanın satırlarını kutular bölünmeden XY-cut ile okuma bölgelerine ayırır."""
    boxes = [
        s
        for s in page.shapes
        if s.kind in ("BOX", "FRAME")
        and (s.x1 - s.x0) * (s.y1 - s.y0) < BOX_MAX_PAGE_SHARE * page.width * page.height
    ]
    return flatten(xy_cut(make_items(lines, boxes), size), size)


def make_items(lines: list[Line], boxes: list[Shape]) -> list[Item]:
    """Satırları, en az iki satır içeren en dış kutulara toplar; kalanlar tek tek öğedir."""
    holders = [b for b in boxes if sum(1 for text_line in lines if inside(text_line, b)) >= 2]
    outermost = [b for b in holders if not any(o is not b and contains(o, b) for o in holders)]
    items, used = [], set()
    for box in outermost:
        members = [
            text_line for text_line in lines if inside(text_line, box) and id(text_line) not in used
        ]
        if not members:
            continue
        used.update(id(text_line) for text_line in members)
        inner_boxes = [b for b in holders if b is not box and contains(box, b)]
        inner = make_items(members, inner_boxes)
        chars = sum(i.chars for i in inner)
        items.append(Item(box.x0, box.y0, box.x1, box.y1, chars, None, box, inner))
    for line in lines:
        if id(line) not in used:
            items.append(Item(line.x0, line.y0, line.x1, line.y1, len(line.text), line))
    return items


def inside(line: Line, box: Shape) -> bool:
    """Satırın ortası kutunun içinde mi."""
    cx, cy = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
    return box.x0 <= cx <= box.x1 and box.y0 <= cy <= box.y1


def contains(outer_box: Shape, inner_box: Shape) -> bool:
    """Bir kutu ötekini içeriyor mu."""
    return (
        outer_box.x0 <= inner_box.x0 + 1
        and outer_box.y0 <= inner_box.y0 + 1
        and outer_box.x1 >= inner_box.x1 - 1
        and outer_box.y1 >= inner_box.y1 - 1
        and (outer_box.x1 - outer_box.x0) * (outer_box.y1 - outer_box.y0)
        > (inner_box.x1 - inner_box.x0) * (inner_box.y1 - inner_box.y0)
    )


def xy_cut(items: list[Item], size: float, depth: int = 0) -> list[list[Item]]:
    """Öğeleri sütunlara ve bantlara böler; her grup yukarıdan aşağı okunur."""
    if len(items) < 4 or depth > 24:
        return [sorted(items, key=lambda i: (i.y0, i.x0))]
    strip = edge_strip(items, size)
    if strip is not None:
        above = [i for i in items if i.y1 <= strip]
        below = [i for i in items if i.y1 > strip]
        return xy_cut(above, size, depth + 1) + xy_cut(below, size, depth + 1)
    gutter = find_gutter(items, size)
    crossing = [i for i in items if gutter is not None and i.x0 < gutter < i.x1]
    if gutter is None or len(crossing) > GUTTER_MAX_CROSSING_ITEMS:
        cut = horizontal_cut(items, size)
        if cut is None:
            return [sorted(items, key=lambda i: (i.y0, i.x0))]
        above = [i for i in items if (i.y0 + i.y1) / 2 < cut]
        below = [i for i in items if (i.y0 + i.y1) / 2 >= cut]
        upper, lower = xy_cut(above, size, depth + 1), xy_cut(below, size, depth + 1)
        if len(upper) == 1 and len(lower) == 1:
            return [upper[0] + lower[0]]
        return upper + lower
    if not crossing:
        left = [i for i in items if (i.x0 + i.x1) / 2 < gutter]
        right = [i for i in items if (i.x0 + i.x1) / 2 >= gutter]
        return xy_cut(left, size, depth + 1) + xy_cut(right, size, depth + 1)
    groups: list[list[Item]] = []
    for band_items in bands_around(items, crossing):
        groups.extend(xy_cut(band_items, size, depth + 1))
    return groups


def horizontal_cut(items: list[Item], size: float) -> float | None:
    """Öğeleri ayıran en geniş yatay boşluğun ortası (sütun bulunamayınca)."""
    spans = sorted((i.y0, i.y1) for i in items)
    best, cut = HORIZONTAL_GAP_EM * size, None
    reach = spans[0][1]
    for y0, y1 in spans[1:]:
        if y0 - reach > best:
            best, cut = y0 - reach, (reach + y0) / 2
        reach = max(reach, y1)
    return cut


def edge_strip(items: list[Item], size: float) -> float | None:
    """Üstte ya da altta, en çok iki sıralık, en az üç parçalı ve büyük boşlukla ayrılan şerit."""
    ordered = sorted(items, key=lambda i: (i.y0 + i.y1) / 2)
    rows: list[list[Item]] = []
    for item in ordered:
        if rows and same_row(item, rows[-1][-1], size):
            rows[-1].append(item)
        else:
            rows.append([item])
    for count in (1, 2):
        for top, strip_rows in ((True, rows[:count]), (False, rows[-count:])):
            strip = [i for row in strip_rows for i in row]
            rest = [i for i in items if all(i is not t for t in strip)]
            if len(strip) < 3 or len(rest) < 2:
                continue
            if top:
                gap = min(r.y0 for r in rest) - max(t.y1 for t in strip)
                cut = max(t.y1 for t in strip)
            else:
                gap = min(t.y0 for t in strip) - max(r.y1 for r in rest)
                cut = max(r.y1 for r in rest)
            if gap >= STRIP_GAP_EM * size:
                return cut
    return None


def same_row(a: Item, b: Item, size: float) -> bool:
    """İki öğe aynı sırada mı."""
    return abs((a.y0 + a.y1) / 2 - (b.y0 + b.y1) / 2) < ROW_TOLERANCE_EM * size


def row_count(items: list[Item]) -> int:
    """Öğelerin kaç ayrı sıraya yayıldığı."""
    middles = sorted((i.y0 + i.y1) / 2 for i in items)
    return sum(1 for a, b in zip([None, *middles], middles, strict=True) if a is None or b - a > 3)


def bands_around(items: list[Item], crossing: list[Item]) -> list[list[Item]]:
    """Oluğu kesen öğelerin üstündeki, kendisi ve altındaki öğeleri ayrı bantlara koyar."""
    crossing = sorted(crossing, key=lambda i: i.y0)
    cross_ids = {id(i) for i in crossing}
    bands: list[list[Item]] = [[] for _ in range(2 * len(crossing) + 1)]
    for item in items:
        if id(item) in cross_ids:
            bands[2 * crossing.index(item) + 1].append(item)
            continue
        middle = (item.y0 + item.y1) / 2
        bands[2 * sum(1 for c in crossing if (c.y0 + c.y1) / 2 < middle)].append(item)
    return [b for b in bands if b]


def find_gutter(items: list[Item], size: float) -> float | None:
    """İki yanında yeterli metin olan ve neredeyse hiç kesilmeyen en geniş dikey boşluk."""
    left_edge, right_edge = min(i.x0 for i in items), max(i.x1 for i in items)
    width = int(right_edge - left_edge) + 2
    total = sum(i.chars for i in items) or 1
    crossing, lefts, rights = (np.zeros(width + 2) for _ in range(3))
    left_count, right_count = np.zeros(width + 2), np.zeros(width + 2)
    for item in items:
        start, end = int(item.x0 - left_edge) + 1, int(np.ceil(item.x1 - left_edge)) - 1
        if end >= start:
            crossing[start] += item.chars
            crossing[end + 1] -= item.chars
        after = int(np.ceil(item.x1 - left_edge))
        lefts[min(after, width + 1)] += item.chars
        left_count[min(after, width + 1)] += 1
        before = int(item.x0 - left_edge)
        rights[max(before, 0)] += item.chars
        right_count[max(before, 0)] += 1
    crossing = np.cumsum(crossing)
    lefts, left_count = np.cumsum(lefts), np.cumsum(left_count)
    rights, right_count = np.cumsum(rights[::-1])[::-1], np.cumsum(right_count[::-1])[::-1]
    lo, hi = int(GUTTER_SCAN[0] * width), int(GUTTER_SCAN[1] * width)
    valid = [
        x
        for x in range(lo, hi + 1)
        if crossing[x] <= GUTTER_MAX_CROSSING_SHARE * total
        and min(lefts[x], rights[x]) >= GUTTER_MIN_SIDE_SHARE * total
        and left_count[x] >= 2
        and right_count[x] >= 2
    ]
    return widest_run(valid, crossing, size, left_edge)


def widest_run(valid: list[int], crossing: np.ndarray, size: float, offset: float) -> float | None:
    """En az kesilen konumların en geniş ardışık aralığının ortası."""
    if not valid:
        return None
    least = min(crossing[x] for x in valid)
    xs = [x for x in valid if crossing[x] == least]
    runs, run = [], [xs[0]]
    for x in xs[1:]:
        if x == run[-1] + 1:
            run.append(x)
        else:
            runs.append(run)
            run = [x]
    runs.append(run)
    best = max(runs, key=len)
    if least == 0 and len(best) < GUTTER_MIN_WIDTH_EM * size:
        return None
    return offset + (best[0] + best[-1]) / 2


def flatten(groups: list[list[Item]], size: float) -> list[tuple[list[Line], Shape | None]]:
    """XY-cut gruplarını bölgelere açar: ardışık satırlar bir bölge, kutu kendi bölgeleri."""
    regions: list[tuple[list[Line], Shape | None]] = []
    for group in groups:
        lines: list[Line] = []
        for item in group:
            if item.line is not None:
                lines.append(item.line)
                continue
            if lines:
                regions.append((lines, None))
                lines = []
            for inner_lines, inner_box in flatten(xy_cut(item.inner, size), size):
                regions.append((inner_lines, inner_box or item.box))
        if lines:
            regions.append((lines, None))
    return regions


def merge_segments(lines: list[Line]) -> list[Line]:
    """Bölgedeki satır parçalarını sıraya koyar; aynı sırada yakın parçaları birleştirir."""
    rows: list[list[Line]] = []
    for line in sorted(lines, key=lambda text_line: (text_line.y0 + text_line.y1) / 2):
        middle = (line.y0 + line.y1) / 2
        if rows:
            last = rows[-1]
            last_middle = sum((text_line.y0 + text_line.y1) / 2 for text_line in last) / len(last)
            if abs(middle - last_middle) < ROW_TOLERANCE_EM * line.size:
                last.append(line)
                continue
        rows.append([line])
    merged = []
    for row in rows:
        row.sort(key=lambda text_line: text_line.x0)
        current = row[0]
        for line in row[1:]:
            if line.x0 - current.x1 <= ROW_MERGE_GAP_EM * line.size:
                current = Line(current.words + line.words, current.page_no)
            else:
                merged.append(current)
                current = line
        merged.append(current)
    return merged


def box_edges(regions: list[Region]) -> None:
    """Tek sütunlu kutunun sağ kenarı, metnin kutuya soldan girintisi kadar içeridedir."""
    per_box = Counter(id(r.box) for r in regions if r.box is not None)
    for region in regions:
        box = region.box
        if box is not None and per_box[id(box)] == 1:
            inset = max(region.left - box.x0, 0.0)
            region.right = max(region.right, box.x1 - inset)


def set_edges(regions: list[Region], size: float) -> None:
    """Bölge kenarlarını belge düzeyinde, benzer genişlikteki bölgelerin satırlarıyla bulur."""
    groups: list[list[Region]] = []
    spans = {}
    for region in regions:
        if not region.lines:
            continue
        lefts = sorted(text_line.x0 for text_line in region.lines)
        rights = sorted(text_line.x1 for text_line in region.lines)
        spans[id(region)] = (lefts[len(lefts) // 20], rights[int(0.95 * (len(rights) - 1))])
        left, right = spans[id(region)]
        for group in groups:
            g_left, g_right = spans[id(group[0])]
            if (
                abs(left - g_left) < EDGE_GROUP_EM * size
                and abs(right - g_right) < EDGE_GROUP_EM * size
            ):
                group.append(region)
                break
        else:
            groups.append([region])
    for group in groups:
        lines = [text_line for r in group for text_line in r.lines]
        lefts, rights = (
            sorted(text_line.x0 for text_line in lines),
            sorted(text_line.x1 for text_line in lines),
        )
        left, right = lefts[len(lefts) // 20], rights[int(0.95 * (len(rights) - 1))]
        for region in group:
            region.left, region.right = left, right


# ---------------------------------------------------------------- markdown ve satır birleştirme


def underlined(char: Char, hlines: list[Shape]) -> bool:
    """Karakterin altında yatay çizgi var mı."""
    cx = (char.x0 + char.x1) / 2
    return any(h.x0 <= cx <= h.x1 and -1 <= h.y0 - char.y1 + 3 <= 5 for h in hlines)


def words_md(
    words: list[Word],
    hlines: list[Shape],
    notes: dict[int, str] | None = None,
    plain_bold: bool = False,
) -> str:
    """Kelimeleri karakter düzeyinde italik/kalın/altı çizili işaretleriyle markdown'a çevirir."""
    if not words:
        return ""
    notes = notes or {}
    out, state = [], (False, False, False)

    def close(s: tuple[bool, bool, bool]) -> str:
        return ("</u>" if s[2] else "") + ("*" if s[1] else "") + ("**" if s[0] else "")

    def open_(s: tuple[bool, bool, bool]) -> str:
        return ("**" if s[0] else "") + ("*" if s[1] else "") + ("<u>" if s[2] else "")

    for k, word in enumerate(words):
        space = " " if k else ""
        marks = [underlined(c, hlines) for c in word.chars]
        if word.ocr:
            marks = [sum(marks) * 2 >= len(marks)] * len(marks)
        note_at = max((i for i, m in enumerate(marks) if m), default=len(marks) - 1)
        for i, char in enumerate(word.chars):
            if char.text == SOFT_HYPHEN:
                continue
            new = (char.bold and not plain_bold, char.italic, marks[i] and bool(char.text.strip()))
            if new != state:
                out.append(close(state) + space + open_(new))
                state = new
            elif space:
                out.append(space)
            space = ""
            out.append(char.text)
            if i == note_at and id(word) in notes:
                out.append(close(state) + notes[id(word)])
                state = (False, False, False)
    out.append(close(state))
    return unicodedata.normalize("NFC", "".join(out).replace("<u></u>", ""))


def mostly_bold(words: list[Word]) -> bool:
    """Harflerin en az %60'ı kalınsa doğru."""
    letters = [c for w in words for c in w.chars if c.text.strip()]
    return bool(letters) and sum(c.bold for c in letters) >= 0.6 * len(letters)


@dataclass
class Row:
    """Birleştirilecek satır: kelimeleri ve boşluk/sığma ölçümü için geometrisi."""

    words: list[Word]
    line: Line
    bottom: float
    end_x: float
    top: float
    first_line: Line
    joined: bool = False


def hyphen_joins(last: Word, first: Word) -> bool:
    """Satır sonu tiresi kelimeyi bölüyor mu (PDFium işareti ya da OCR'da küçük harfle süren)."""
    if last.text.endswith(SOFT_HYPHEN):
        return True
    return (
        (last.ocr or last.chars[-1].broken)
        and len(last.text) > 2
        and last.text.endswith("-")
        and last.text[-2].isalpha()
        and first.text[:1].islower()
    )


def join_rows(pieces: list[tuple[list[Word], Line]], bottoms: dict[int, float]) -> list[Row]:
    """Satır parçalarını, tireyle bölünen kelimeyi birleştirerek sıralara çevirir."""
    rows: list[Row] = []
    for words, line in pieces:
        bottom = max(line.y1, bottoms.get(id(line), line.y1))
        if rows and hyphen_joins(rows[-1].words[-1], words[0]):
            last, first = rows[-1].words[-1], words[0]
            kept = [c for c in last.chars if c.text != SOFT_HYPHEN]
            if last.text.endswith("-"):
                kept = kept[:-1]
            text = "".join(c.text for c in kept) + first.text
            rows[-1].words[-1] = replace(last, text=text, chars=kept + first.chars)
            rows[-1].joined = True
            words = words[1:]
            if not words:
                rows[-1].line, rows[-1].bottom, rows[-1].end_x = line, bottom, line.x1
                rows[-1].joined = False
                continue
        rows.append(Row(words, line, bottom, words[-1].x1, line.y0, line))
    return rows


def compose(
    pieces: list[tuple[list[Word], Line]],
    body: Body,
    notes: dict[int, str] | None = None,
    right: float | None = None,
    bottoms: dict[int, float] | None = None,
    keep_bold: bool = False,
) -> list[str]:
    """Satır parçalarını paragraflara birleştirir; paragraflar markdown metinleridir."""
    return [text for text, _ in compose_paragraphs(pieces, body, notes, right, bottoms, keep_bold)]


def compose_paragraphs(
    pieces: list[tuple[list[Word], Line]],
    body: Body,
    notes: dict[int, str] | None = None,
    right: float | None = None,
    bottoms: dict[int, float] | None = None,
    keep_bold: bool = False,
) -> list[tuple[str, list[Row]]]:
    """Satır parçalarını paragraflara birleştirir; her paragraf markdown metni ve satırlarıdır."""
    rows = join_rows([(list(w), text_line) for w, text_line in pieces if w], bottoms or {})
    if not rows:
        return []
    usual_gap = usual_row_gap(rows, body)
    starts = indent_starts(rows, body)
    prose = full_share(rows, body, right) >= PROSE_FULL_SHARE
    paragraphs: list[list[tuple[str, Row]]] = []
    for k, row in enumerate(rows):
        sep = (
            "\n\n"
            if k == 0 or k in starts
            else separator(rows[k - 1], row, body, right, usual_gap, prose)
        )
        if sep == "\n\n":
            paragraphs.append([])
        paragraphs[-1].append((sep, row))
    result = []
    for paragraph in paragraphs:
        plain = not keep_bold and mostly_bold([w for _, row in paragraph for w in row.words])
        text = ""
        for k, (sep, row) in enumerate(paragraph):
            text += (sep if k else "") + words_md(row.words, row_hlines(row, body), notes, plain)
        text = BOLD_SEAM.sub(r"\1", text)
        if text.strip():
            result.append((text, [row for _, row in paragraph]))
    return result


def row_hlines(row: Row, body: Body) -> list[Shape]:
    """Satırın alt çizgi adayları: satırdan çok daha geniş olmayan yatay çizgiler (ayraç değil)."""
    width = row.end_x - row.words[0].x0
    size = row.words[0].size
    return [
        s
        for s in body.shapes[row.line.page_no]
        if s.kind == "HLINE" and s.x1 - s.x0 <= width + UNDERLINE_EXTRA_EM * size
    ]


def usual_row_gap(rows: list[Row], body: Body) -> float:
    """Aynı bölgedeki ardışık satırlar arasındaki olağan boşluk."""
    gaps = sorted(
        b.top - a.bottom
        for a, b in zip(rows, rows[1:], strict=False)
        if body.region_of[id(a.line)] is body.region_of[id(b.first_line)]
    )
    return max(gaps[len(gaps) // 2], 0.0) if gaps else 0.0


def indent_starts(rows: list[Row], body: Body) -> set[int]:
    """Girintili ilk satırla başlayan paragrafların sıra numaraları."""

    def indent(row: Row) -> float:
        region = body.region_of[id(row.first_line)]
        return (row.words[0].x0 - region.left) / max(row.words[0].size, 1)

    starts = set()
    for k in range(1, len(rows)):
        same = body.region_of[id(rows[k - 1].line)] is body.region_of[id(rows[k].first_line)]
        following = rows[k + 1] if k + 1 < len(rows) else None
        hanging = following is not None and indent(following) >= PARAGRAPH_INDENT_EM / 2
        previous_flat = indent(rows[k - 1]) < 0.5 or not same
        if (
            not rows[k - 1].joined
            and indent(rows[k]) >= PARAGRAPH_INDENT_EM
            and previous_flat
            and not hanging
        ):
            starts.add(k)
    return starts


def full_share(rows: list[Row], body: Body, right: float | None) -> float:
    """Son satır dışındaki satırların ne kadarı sağ kenara kadar dolu (düz yazı ölçüsü)."""
    measured = rows[:-1]
    if len(measured) < 2:
        return 0.0
    full = 0
    for row in measured:
        region = body.region_of[id(row.line)]
        edge = right if right is not None else region.right
        full += row.end_x >= region.left + PROSE_LINE_SHARE * (edge - region.left)
    return full / len(measured)


def separator(
    previous: Row,
    current: Row,
    body: Body,
    right: float | None,
    usual_gap: float,
    prose: bool = False,
) -> str:
    """İki satır arasına boşluk, satır sonu ya da paragraf sonu koyar."""
    size = previous.words[-1].size
    run_in = not previous.words[-1].bold and not mostly_bold(current.words)
    if mostly_bold(previous.words) != mostly_bold(current.words) and not run_in:
        return "\n\n"
    region = body.region_of[id(previous.line)]
    same_region = region is body.region_of[id(current.first_line)]
    if same_region and current.top - previous.bottom > usual_gap + 0.5 * size:
        return "\n\n"
    if previous.joined:
        return " "
    if (
        not same_region
        and current.words[0].text[:1].islower()
        and not CLOSED.search(previous.words[-1].text)
    ):
        return " "
    if not same_region and previous.end_x < region.right - 1.5 * size:
        return "\n\n"
    first = current.words[0]
    if HARD_START.match(first.text):
        return "\n"
    edge = right if right is not None else region.right
    if not prose and first.text[:1].isupper() and previous.end_x < edge - 1.5 * size:
        return "\n"
    margin = OCR_FIT_MARGIN_EM * size if first.ocr else 0.0
    fits = previous.end_x + 0.3 * size + (first.x1 - first.x0) <= edge + 1 - margin
    return "\n" if fits else " "


# ================================================================== ORTAK SONU

# ================================================================== TEST

NUMBER = re.compile(r"^(\d{1,3})([.)\-–:]?)$")
GLUED_MARKER = re.compile(r"^(\d{1,3})([.)])(soru)([.:)]?)$")
LABEL = re.compile(r"^(soru|sual)([.:]?)$")
OPTION = re.compile(r"^\(?([A-E])([).\-:])\)?$")
INLINE_ANSWER = re.compile(r"^(?:Doğru\s+)?(?:Cevap|Yanıt)\s*:?\s*([A-E])\.?$", re.IGNORECASE)
KEY_PAIR = re.compile(r"(?<![\w.])(\d{1,3})\s*[.)\-–:]\s*([A-E])(?!\w)")
KEY_HEADING = re.compile(r"^(cevap anahtarı|cevaplar|yanıt anahtarı):?$")
PASSAGE_CUE = re.compile(r"(\d{1,3})\.?((?:\s*(?:[-–]|,|ve)\s*\d{1,3}\.?)+)\s*soru", re.IGNORECASE)
ROMAN = re.compile(r"^(?:I{1,3}|IV|VI{0,3}|IX|X)$")
ROMAN_LIKE = re.compile(r"^(\(?)([IVXl1|ıiMWN]{1,4})(\)?)([.,;:]?)$")
ROMANS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
OCR_GLUED_OPTION = re.compile(r"^([A-EGÇ€©])\)(.*)$")
OCR_OPTION_ALIASES = {"G": "C", "Ç": "C", "€": "C", "©": "C"}
EMBEDDED_ROMAN = re.compile(r"\(([IVXl1|ıiMWN!]{1,4})\)")
ITEM_ROMAN = re.compile(r"^([IVXl1|ıiMWN!]{1,4})\.")
ROMANISH = re.compile(r"^[IVXl1|ıiMWN!ve,.\sYalnız]+$")
ROMAN_TOKEN_GAP = 0.35
ROMAN_CAP_SHARE = 0.85
CHAIN_START_PENALTY = 1.5
MARK_GAP_EM = 0.8
OPTION_LABELS = list("ABCDE")


@dataclass
class Question:
    """Ayrıştırılmış soru: numara, sayfa, kök, şıklar, ortak parça, cevap ve sorunlar."""

    number: int
    page_no: int
    stem: list[str] = field(default_factory=list)
    options: dict[str, list[str]] = field(default_factory=dict)
    passage: list[str] | None = None
    answer: str | None = None
    answer_source: str | None = None
    problems: list[str] = field(default_factory=list)
    tail: list[Line] = field(default_factory=list, repr=False)


@dataclass
class Candidate:
    """Soru numarası adayı: satır sırası, numara, imza ve numaradan sonraki ilk kelime."""

    position: int
    number: int
    signature: tuple
    line: Line
    skip: int


@dataclass
class Mark:
    """Şık işareti: satır ve kelime sırası, harf ve konum."""

    line_index: int
    word_index: int
    label: str
    x: float
    y: float


def marker_of(line: Line) -> tuple[int, str, str, int] | None:
    """Satır başındaki soru numarası: (numara, etiket, noktalama, atlanacak kelime sayısı)."""
    words = [tr_lower(w.text) for w in line.words[:3]]
    glued = GLUED_MARKER.match(words[0])
    if glued:
        return int(glued[1]), glued[3], glued[2] + glued[4], 1
    label = LABEL.match(words[0])
    if label and len(words) > 1 and NUMBER.match(words[1]):
        number = NUMBER.match(words[1])
        assert number
        return int(number[1]), label[1], number[2], 2
    number = NUMBER.match(words[0])
    if not number:
        return None
    if len(words) > 1 and LABEL.match(words[1]):
        return int(number[1]), "soru", number[2], 2
    return (int(number[1]), "", number[2], 1) if len(line.words) >= 2 else None


def in_shape(word: Word, shapes: list[Shape]) -> str | None:
    """Kelime küçük dolgulu bir şeklin içindeyse şeklin rengi."""
    cx, cy = (word.x0 + word.x1) / 2, (word.y0 + word.y1) / 2
    for shape in shapes:
        small = (shape.x1 - shape.x0) < 6 * word.size
        if shape.fill and small and shape.x0 <= cx <= shape.x1 and shape.y0 <= cy <= shape.y1:
            return shape.fill
    return None


def position_class(word: Word, left: float) -> str:
    """Numaranın sütun soluna göre kaba yeri: dışarıda, hizada ya da içeride."""
    offset = (word.x0 - left) / word.size
    if offset < -1.0:
        return "OUT"
    return "FLUSH" if offset <= 1.5 else "IN"


def number_candidates(body: Body, excluded: set[int]) -> list[Candidate]:
    """Satır başındaki numara adaylarını imzalarıyla toplar."""
    candidates = []
    for position, line in enumerate(body.lines):
        if id(line) in excluded:
            continue
        found = marker_of(line)
        if not found:
            continue
        number, label, punct, skip = found
        first = line.words[0]
        region = body.region_of[id(line)]
        shape = in_shape(first, body.shapes[line.page_no])
        signature = (
            label,
            punct,
            None if first.ocr else first.bold,
            first.color,
            shape,
            position_class(first, region.left),
        )
        candidates.append(Candidate(position, number, signature, line, skip))
    return candidates


def best_chains(numbers: list[int]) -> tuple[float, list[int]]:
    """Ardışık artan zincirlerden (yeniden başlayabilir) en yüksek puanlı alt diziyi seçer."""
    n = len(numbers)
    if n == 0:
        return 0.0, []
    best = [0.0] * n
    previous = [-1] * n
    for i in range(n):
        base = max(range(i), key=lambda j: best[j], default=-1)
        carried = best[base] if base >= 0 and best[base] > 0 else 0.0
        best[i] = carried + 1 - CHAIN_START_PENALTY
        previous[i] = base if carried > 0 else -1
        for j in range(i):
            if numbers[i] == numbers[j] + 1 and best[j] + 1 > best[i]:
                best[i], previous[i] = best[j] + 1, j
    end = max(range(n), key=lambda i: best[i])
    chosen, i = [], end
    while i >= 0:
        chosen.append(i)
        i = previous[i]
    return best[end], sorted(chosen)


def find_marks(span: list[Line], first_word: int) -> list[Mark]:
    """A..E'yi en çok tamamlayan imzadaki şık işaretleri, harf sırasıyla."""
    by_signature: dict[tuple, list[Mark]] = defaultdict(list)
    for li, line in enumerate(span):
        start = first_word if li == 0 else 0
        for wi in range(start, len(line.words)):
            word = line.words[wi]
            match = OPTION.match(word.text)
            gap_ok = wi == start or word.x0 - line.words[wi - 1].x1 > MARK_GAP_EM * word.size
            if match and gap_ok:
                bold = None if word.ocr else word.bold
                by_signature[(match[2], bold)].append(Mark(li, wi, match[1], word.x0, word.y0))
    best: list[Mark] = []
    for marks in by_signature.values():
        picked: dict[str, Mark] = {}
        for mark in marks:
            picked.setdefault(mark.label, mark)
        labels = sorted(picked)
        if len(labels) > len(best):
            best = [picked[label] for label in labels]
    return best


def key_regions(body: Body) -> tuple[set[int], dict[int, str]]:
    """Cevap anahtarı satırlarını bulur: "1-B 2-E" çiftleri ya da alt alta sayı/harf ızgarası."""
    excluded, key = set(), {}
    for row in page_rows(body.lines):
        pairs = KEY_PAIR.findall(" ".join(line.text for line in row))
        if len(pairs) >= 3:
            excluded.update(id(line) for line in row)
            key.update({int(n): letter for n, letter in pairs})
    for line in body.lines:
        if KEY_HEADING.match(tr_lower(line.text).strip()):
            excluded.add(id(line))
    numbers = [
        text_line
        for text_line in body.lines
        if len(text_line.words) == 1 and text_line.words[0].text.isdigit()
    ]
    letters = [
        text_line
        for text_line in body.lines
        if len(text_line.words) == 1 and text_line.words[0].text in OPTION_LABELS
    ]
    grid: list[tuple[Line, Line]] = []
    for number in numbers:
        cx = (number.x0 + number.x1) / 2
        below = [
            letter
            for letter in letters
            if letter.page_no == number.page_no
            and abs((letter.x0 + letter.x1) / 2 - cx) < 6
            and 0 < letter.y0 - number.y1 < 2 * number.size
        ]
        if below:
            grid.append((number, below[0]))
    if len(grid) >= 3:
        for number, letter in grid:
            excluded.update({id(number), id(letter)})
            key[int(number.words[0].text)] = letter.words[0].text
    return excluded, key


def page_rows(lines: list[Line]) -> list[list[Line]]:
    """Aynı sayfada aynı yükseklikteki satırları (sütunlardan bağımsız) soldan sağa toplar."""
    rows: list[list[Line]] = []
    for line in sorted(
        lines, key=lambda text_line: (text_line.page_no, (text_line.y0 + text_line.y1) / 2)
    ):
        middle = (line.y0 + line.y1) / 2
        last = rows[-1] if rows else None
        if (
            last
            and last[0].page_no == line.page_no
            and abs(middle - (last[0].y0 + last[0].y1) / 2) < ROW_TOLERANCE_EM * line.size
        ):
            last.append(line)
        else:
            rows.append([line])
    return [sorted(row, key=lambda text_line: text_line.x0) for row in rows]


def attach_numerals(
    span: list[Line], body: Body
) -> tuple[list[Line], dict[int, str], dict[int, float]]:
    """Altı çizili kelimelerin altındaki I-IV numaralarını o kelimelere not olarak bağlar."""
    notes: dict[int, str] = {}
    bottoms: dict[int, float] = {}
    kept: list[Line] = []
    for line in span:
        if kept and all(ROMAN.match(w.text) for w in line.words):
            above = kept[-1]
            gap = line.y0 - above.y1
            if -0.5 * line.size <= gap < 1.5 * line.size and annotate(line, above, body, notes):
                bottoms[id(above)] = max(bottoms.get(id(above), above.y1), line.y1)
                continue
        kept.append(line)
    return kept, notes, bottoms


def annotate(numerals: Line, above: Line, body: Body, notes: dict[int, str]) -> bool:
    """Her numarayı üstteki satırda x'i en yakın altı çizili kelime dizisinin sonuna bağlar."""
    hlines = [s for s in body.shapes[above.page_no] if s.kind == "HLINE"]
    lined = [any(underlined(c, hlines) for c in w.chars) for w in above.words]
    if not any(lined):
        return False
    for numeral in numerals.words:
        cx = (numeral.x0 + numeral.x1) / 2
        index = min(
            (i for i, flag in enumerate(lined) if flag),
            key=lambda i: abs((above.words[i].x0 + above.words[i].x1) / 2 - cx),
        )
        while index + 1 < len(above.words) and lined[index + 1]:
            index += 1
        notes[id(above.words[index])] = f" ({numeral.text})"
    return True


def fix_ocr_romans(span: list[Line], body: Body) -> None:
    """OCR'ın bozduğu Roma rakamlarını harf bileşenlerini sayarak düzeltir: "(11)" → "(II)"."""
    words = [(w, line) for line in span for w in line.words if w.ocr]
    if not words:
        return
    numbered = [(w, text_line) for w, text_line in words if EMBEDDED_ROMAN.search(w.text)]
    starts = [
        (line.words[k], line)
        for line in span
        for k in (0, 1)
        if len(line.words) > k
        and (k == 0 or OPTION.match(line.words[0].text))
        and ITEM_ROMAN.match(line.words[k].text)
    ]
    for group in (numbered, starts):
        decoded = [decode_roman_word(w, body.pages[text_line.page_no]) for w, text_line in group]
        for (word, _), roman in zip(group, decoded, strict=True):
            if roman:
                pattern = EMBEDDED_ROMAN if group is numbered else ITEM_ROMAN
                set_word_text(word, replace_roman(word.text, roman, pattern))


def replace_roman(text: str, roman: str, pattern: re.Pattern[str]) -> str:
    """Kelimedeki ilk Roma rakamı benzeri parçayı verilen rakamla değiştirir."""
    match = pattern.search(text)
    assert match
    return text[: match.start(1)] + roman + text[match.end(1) :]


def decode_roman_word(word: Word, page: PageIR) -> str | None:
    """Kelime görüntüsündeki Roma rakamını bileşenlerden okur (I ince dolu çubuk, V üstte geniş)."""
    pad = 0.15 * word.size
    gray = render_crop(page, (word.x0 - pad, word.y0 - pad, word.x1 + pad, word.y1 + pad))
    blobs = line_blobs(gray, pad * OCR_DPI / 72)
    if not blobs:
        return None
    cap = cap_height(blobs)
    letters = []
    for blob in blobs:
        kind = roman_kind(blob, gray, cap)
        if kind in ("I", "V", "X"):
            letters.append(kind)
        elif kind == "OTHER" and letters:
            break
    roman = "".join(letters)
    return roman if ROMAN.match(roman) else None


def cap_height(blobs: list[Blob]) -> int:
    """Büyük harf yüksekliği: ayraç gibi ince ve kavisli bileşenler dışındaki en yüksek."""
    solid = [
        b.y1 - b.y0 for b in blobs if not (b.x1 - b.x0 <= 0.45 * (b.y1 - b.y0) and b.fill < 0.6)
    ]
    return max(solid or [b.y1 - b.y0 for b in blobs])


def roman_kind(blob: Blob, gray: np.ndarray, cap: int) -> str:
    """Bileşenin türü: I, V, X, PAREN (ayraç), SMALL (küçük harf, nokta) ya da OTHER."""
    height, width = blob.y1 - blob.y0, blob.x1 - blob.x0
    if height < ROMAN_CAP_SHARE * cap:
        return "SMALL"
    if width <= 0.3 * height:
        return "I" if blob.fill >= 0.7 else "PAREN"
    dark = blob.mask
    band = max(height // 6, 1)
    middle = height // 2 - band // 2
    top, bottom = extent(dark[:band]), extent(dark[-band:])
    center = extent(dark[middle : middle + band])
    if top >= 0.7 * width and bottom <= 0.45 * width:
        return "V"
    if top >= 0.7 * width and bottom >= 0.7 * width and center <= 0.5 * width:
        return "X"
    return "OTHER"


def extent(rows: np.ndarray) -> int:
    """Satırlardaki koyu piksellerin yatay yayılımı."""
    columns = np.nonzero(rows.any(axis=0))[0]
    return int(columns[-1] - columns[0] + 1) if columns.size else 0


def line_blobs(gray: np.ndarray, pad_px: float) -> list[Blob]:
    """Kırpıntıda yalnızca kelime bandına (üst/alt pay dışı) ortası düşen bileşenler."""
    top, bottom = pad_px, gray.shape[0] - pad_px
    return [
        b for b in find_blobs(gray) if b.count > 3 and top - 2 <= (b.y0 + b.y1) / 2 <= bottom + 2
    ]


def decode_roman_phrase(words: list[Word], page: PageIR) -> str | None:
    """Şık metnini bileşenlerden Roma rakamı öbeğine çevirir ("I ve II", "Yalnız III")."""
    if not words:
        return None
    pad = 0.15 * words[0].size
    box = (
        min(w.x0 for w in words) - pad,
        min(w.y0 for w in words) - pad,
        max(w.x1 for w in words) + pad,
        max(w.y1 for w in words) + pad,
    )
    gray = render_crop(page, box)
    blobs = line_blobs(gray, pad * OCR_DPI / 72)
    cap = cap_height(blobs) if blobs else 0
    while blobs and roman_kind(blobs[0], gray, cap) == "PAREN":
        blobs = blobs[1:]
    if not blobs:
        return None
    tokens: list[list[Blob]] = []
    for blob in blobs:
        if tokens and blob.x0 - max(b.x1 for b in tokens[-1]) <= ROMAN_TOKEN_GAP * cap:
            tokens[-1].append(blob)
        else:
            tokens.append([blob])
    parts = [roman_token(token, gray, cap) for token in tokens]
    if any(part is None for part in parts):
        return None
    phrase = " ".join(p for p in parts if p).replace(" ,", ",")
    return phrase if phrase in ROMAN_PHRASE_SET else None


def roman_token(token: list[Blob], gray: np.ndarray, cap: int) -> str | None:
    """Bileşen grubunu Roma rakamına, "ve"ye ya da "Yalnız"a çevirir."""
    kinds = [roman_kind(b, gray, cap) for b in token]
    small = [b for b, k in zip(token, kinds, strict=True) if k == "SMALL"]
    if kinds[:1] == ["V"] and len(small) >= 3:
        return "Yalnız"
    if len(small) == 2 and len(token) == 2:
        return "ve"
    count = 0
    while count < len(kinds) and kinds[count] in ("I", "V", "X"):
        count += 1
    letters, rest = "".join(kinds[:count]), token[count:]
    low = all(
        k == "SMALL" and b.y0 - min(t.y0 for t in token) > 0.6 * cap
        for b, k in zip(rest, kinds[count:], strict=True)
    )
    if letters and ROMAN.match(letters) and len(rest) <= 1 and low:
        return letters + ("," if rest else "")
    return None


def snap_roman_options(
    question: Question, pieces: dict[str, list[tuple[list[Word], Line]]], body: Body
) -> None:
    """OCR'la okunan Roma rakamlı şıkları bileşen sayımıyla geçerli öbeklere oturtur."""
    romanish = {
        label: [w for words, _ in parts for w in words]
        for label, parts in pieces.items()
        if parts and ROMANISH.match(" ".join(w.text for words, _ in parts for w in words))
    }
    if len(romanish) < 3:
        return
    for label, words in romanish.items():
        line = pieces[label][0][1]
        phrase = decode_roman_phrase(words, body.pages[line.page_no])
        if phrase:
            question.options[label] = [phrase]


def fix_sequence(words: list[Word]) -> None:
    """Sırayla I, II, III... olması gereken kelimeleri, sıra tutarlıysa düzeltir."""
    if len(words) < 2 or len(words) > len(ROMANS):
        return
    inner = [ROMAN_LIKE.match(w.text) for w in words]
    valid = [(k, m[2]) for k, m in enumerate(inner) if m and ROMAN.match(m[2])]
    if any(roman != ROMANS[k] for k, roman in valid) or len(valid) * 2 < len(words) - 1:
        return
    for k, (word, match) in enumerate(zip(words, inner, strict=True)):
        if match and match[2] != ROMANS[k]:
            set_word_text(word, match[1] + ROMANS[k] + match[3] + match[4])


def set_word_text(word: Word, text: str) -> None:
    """OCR kelimesinin metnini ve eşit bölünmüş harflerini yeniler."""
    template = word.chars[0]
    step = (word.x1 - word.x0) / max(len(text), 1)
    word.text = text
    word.chars = [
        replace(template, text=letter, x0=word.x0 + i * step, x1=word.x0 + (i + 1) * step)
        for i, letter in enumerate(text)
    ]


def normalize_ocr_marks(lines: list[Line]) -> None:
    """OCR'ın şık işaretlerini düzeltir: yapışık "C)I" ayrılır, C'ye benzeyen "G)" C olur."""
    for line in lines:
        words: list[Word] = []
        for word in line.words:
            match = OCR_GLUED_OPTION.match(word.text) if word.ocr else None
            if not match:
                words.append(word)
                continue
            label = OCR_OPTION_ALIASES.get(match[1], match[1]) + ")"
            if not match[2]:
                set_word_text(word, label)
                words.append(word)
                continue
            cut = word.chars[2].x0 if len(word.chars) > 2 else word.x1
            head = replace(word, text="", x1=cut, chars=word.chars[:1])
            tail = replace(word, text="", x0=cut, chars=word.chars[:1])
            set_word_text(head, label)
            set_word_text(tail, match[2])
            words.extend([head, tail])
        line.words = words


def roman_phrases() -> list[str]:
    """Şıklardaki Roma rakamı öbekleri: "Yalnız I", "I ve II", "I, II ve III"..."""
    phrases = []
    for count in range(1, 6):
        for combo in combinations(ROMANS[:5], count):
            if count == 1:
                phrases.extend([combo[0], f"Yalnız {combo[0]}"])
            else:
                phrases.append(", ".join(combo[:-1]) + " ve " + combo[-1])
    return phrases


def parse(pages: list[PageIR]) -> tuple[list[Question], dict]:
    """Sayfalardan soruları, öğrenilen biçim profiliyle birlikte çıkarır."""
    body = reading_order(pages)
    normalize_ocr_marks(body.lines)
    excluded, key = key_regions(body)
    groups: dict[tuple, list[Candidate]] = defaultdict(list)
    for candidate in number_candidates(body, excluded):
        groups[candidate.signature].append(candidate)
    scored = []
    for signature, group in groups.items():
        score, chosen = best_chains([c.number for c in group])
        markers = [group[i] for i in chosen]
        complete = sum(
            len(find_marks(question_span(body, markers, k, excluded), markers[k].skip)) == 5
            for k in range(len(markers))
        )
        scored.append((score + complete, signature, markers))
    scored.sort(key=lambda item: -item[0])
    if not scored or scored[0][0] <= 0:
        return [], {"reason": "no question markers", "pages": [p.source for p in pages]}
    total, signature, markers = scored[0]
    questions = [build_question(body, markers, k, key, excluded) for k in range(len(markers))]
    attach_passages(body, questions)
    names = ["label", "punct", "bold", "color", "in_shape", "position"]
    profile = {
        "question_marker": dict(zip(names, signature, strict=True)),
        "marker_score": round(total, 1),
        "runner_up": [(round(s, 1), sig) for s, sig, _ in scored[1:3]],
        "regions": len(body.regions),
        "body_size": body.body_size,
        "furniture": sorted({text_line.text for text_line in body.furniture})[:8],
        "answer_key_entries": len(key),
        "pages": [(p.source, p.notes) for p in pages],
    }
    return questions, profile


def question_span(body: Body, markers: list[Candidate], k: int, excluded: set[int]) -> list[Line]:
    """Sorunun numarasından sonraki sorunun numarasına kadar olan satırlar."""
    end = markers[k + 1].position if k + 1 < len(markers) else len(body.lines)
    return [
        text_line
        for text_line in body.lines[markers[k].position : end]
        if id(text_line) not in excluded
    ]


def build_question(
    body: Body, markers: list[Candidate], k: int, key: dict[int, str], excluded: set[int]
) -> Question:
    """Sorunun kökünü, şıklarını ve cevabını çıkarır."""
    marker = markers[k]
    span = question_span(body, markers, k, excluded)
    fix_ocr_romans(span, body)
    span, notes, bottoms = attach_numerals(span, body)
    question = Question(number=marker.number, page_no=marker.line.page_no)
    marks = find_marks(span, marker.skip)
    first_mark_line = marks[0].line_index if marks else len(span)
    stem_pieces = [
        (span[li].words[marker.skip :] if li == 0 else span[li].words, span[li])
        for li in range(first_mark_line)
    ]
    option_pieces = collect_options(span, marks, marker.skip, question, stem_pieces, body)
    question.stem = compose(stem_pieces, body, notes, bottoms=bottoms)
    rights = option_rights(marks, span, body)
    for label in sorted(option_pieces):
        question.options[label] = compose(option_pieces[label], body, notes, rights[label])
    if question.answer is None and marker.number in key:
        question.answer, question.answer_source = key[marker.number], "KEY"
    if list(question.options) != OPTION_LABELS:
        question.problems.append("OPTION_COUNT")
    if not question.stem:
        question.problems.append("EMPTY_STEM")
    if question.answer is None:
        question.problems.append("NO_ANSWER_KEY")
    if any(w.ocr for line in span for w in line.words):
        snap_roman_options(question, option_pieces, body)
        question.problems.append("OCR_TEXT")
    return question


def collect_options(
    span: list[Line],
    marks: list[Mark],
    skip: int,
    question: Question,
    stem_pieces: list[tuple[list[Word], Line]],
    body: Body,
) -> dict[str, list[tuple[list[Word], Line]]]:
    """Şık işaretlerinden sonraki satırları şıklara dağıtır; şık alanı bitince kalanı ayırır."""
    option_pieces: dict[str, list[tuple[list[Word], Line]]] = {m.label: [] for m in marks}
    first_mark_line = marks[0].line_index if marks else len(span)
    last_line = None
    for li in range(first_mark_line, len(span)):
        line = span[li]
        inline = INLINE_ANSWER.match(line.text)
        if inline:
            question.answer, question.answer_source = inline[1].upper(), "INLINE"
            continue
        row_marks = sorted((m for m in marks if m.line_index == li), key=lambda m: m.x)
        if row_marks:
            head = line.words[(skip if li == 0 else 0) : row_marks[0].word_index]
            if head and li == first_mark_line:
                stem_pieces.append((head, line))
            elif head:
                option_pieces[owner(marks, line.x0, li)].append((head, line))
            for a, b in zip(row_marks, [*row_marks[1:], None], strict=True):
                end = b.word_index if b else len(line.words)
                option_pieces[a.label].append((line.words[a.word_index + 1 : end], line))
            last_line = line
            continue
        if last_line is not None and not continues(last_line, line, body):
            question.tail = span[li:]
            break
        option_pieces[owner(marks, line.x0, li)].append((line.words, line))
        last_line = line
    return option_pieces


def option_rights(marks: list[Mark], span: list[Line], body: Body) -> dict[str, float]:
    """Her şıkkın sağ kenarı: aynı sıradaki sağdaki şıkkın başı, yoksa bölgenin sağ kenarı."""
    rights = {}
    for mark in marks:
        line = span[mark.line_index]
        size = line.size
        same_row = [m.x for m in marks if m.x > mark.x and abs(m.y - mark.y) < 0.5 * size]
        rights[mark.label] = (
            min(same_row) - 0.5 * size if same_row else body.region_of[id(line)].right
        )
    return rights


def owner(marks: list[Mark], x: float, line_index: int) -> str:
    """İşaretsiz satırın ait olduğu şık: önceki satırlardaki, x'i soldan en yakın işaret."""
    before = [m for m in marks if m.line_index < line_index and m.x <= x + 2]
    return max(before, key=lambda m: (m.line_index, m.x)).label if before else marks[-1].label


def continues(previous: Line, line: Line, body: Body) -> bool:
    """Satır şık alanının devamı mı: aynı bölge ve normal satır aralığı."""
    same_region = body.region_of[id(previous)] is body.region_of[id(line)]
    gap = line.y0 - previous.y1
    return same_region and -0.5 * line.size <= gap < 0.8 * line.size


def attach_passages(body: Body, questions: list[Question]) -> None:
    """Şık alanından sonra kalan metni sonraki soru(lar)ın ortak parçası yapar."""
    for k, question in enumerate(questions):
        tail = question.tail
        if not tail:
            continue
        cue_line = next(
            (i for i, text_line in enumerate(tail[:2]) if PASSAGE_CUE.search(text_line.text)), None
        )
        numbers = {questions[k + 1].number} if k + 1 < len(questions) else set()
        start = 0
        if cue_line is not None:
            cue = PASSAGE_CUE.search(tail[cue_line].text)
            assert cue
            found = [int(n) for n in re.findall(r"\d{1,3}", cue[0])]
            ranged = bool(re.search(r"[-–]", cue[2]))
            numbers = set(range(min(found), max(found) + 1)) if ranged else set(found)
            start = cue_line + 1
        passage = compose([(text_line.words, text_line) for text_line in tail[start:]], body)
        for later in questions[k + 1 : k + 7]:
            if later.number in numbers:
                later.passage = passage
                if cue_line is None:
                    later.problems.append("PASSAGE_WITHOUT_CUE")


ROMAN_PHRASES = roman_phrases()
ROMAN_PHRASE_SET = frozenset(ROMAN_PHRASES)


def show(paragraphs: list[str]) -> str:
    """Paragrafları ¶, paragraf içi satır sonlarını ⏎ ile tek satırda gösterir."""
    return " ¶ ".join(p.replace("\n", " ⏎ ") for p in paragraphs)


def main(arguments: list[str]) -> None:
    """Komut satırı: PDF'leri okuyup soruları yazar (--json ile JSON)."""
    as_json = "--json" in arguments
    for path in [a for a in arguments if not a.startswith("--")]:
        questions, profile = parse(read_document(path))
        if as_json:
            print(json.dumps([q.__dict__ | {"tail": None} for q in questions], ensure_ascii=False))
            continue
        print(f"\n######## {Path(path).name}")
        print("profil:", json.dumps(profile, ensure_ascii=False, default=str))
        for q in questions:
            print(
                f"--- Soru {q.number} (s.{q.page_no}) cevap={q.answer} ({q.answer_source}) "
                f"sorun={q.problems}"
            )
            if q.passage:
                print("  ORTAK PARÇA:", show(q.passage))
            print("  KÖK:", show(q.stem))
            for label, text in q.options.items():
                print(f"  {label}) {show(text)}")


if __name__ == "__main__":
    main(sys.argv[1:])
