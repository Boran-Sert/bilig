"""Kitap okuyucu: ders kitabı ve konu anlatımı PDF'lerinden başlık yollu bloklar (tek dosya).

Yayınevine özel profil yoktur; kurallar her belgeden yeniden çıkarılır. Dosya iki bölümdür.

ORTAK bölüm test okuyucuyla birebir aynıdır (PDF okuma, görünürlük, bozuk font onarımı, OCR,
üst/alt bilgi, XY-cut okuma sırası, satır birleştirme); açıklaması test_reader.py'dedir.

KİTAP bölümü:
1. Başlık: bölgedeki satırlar aynı stil, aynı hizalama ve belgeden öğrenilen paragraf adımından
   sıkı aralıkla öbeklenir. Öbek gövdeden belirgin büyük ya da kalın/renkli/büyük harfliyse, en
   çok üç satırsa, cümle gibi bitmiyorsa (iki noktayla bitip ardından madde gelen hariç), küçük
   harfle ya da açık tırnakla başlamıyorsa, sağa yaslı imza ya da çizgili tablo hücresi değilse
   ve ardından cümle sürmüyorsa başlıktır. Numaralı başlık büyük harfli ya da büyük olmalıdır.
   Düzey boyut, kalınlık ve ortalanmışlığa göredir (büyük, kalın, ortalı önce).
2. Başlık yolu: üstteki daha büyük başlıklar. Kutudaki ilk başlık kutunun adıdır; kutudan
   çıkınca kutu içinde açılan başlıklar yoldan düşer.
3. İçindekiler: satırlarının çoğu noktalı sayfa yönlendirmesi ya da sayı olan parça tek blok
   olur; başlığı ("İçindekiler") sonraki içeriğin yoluna girmez.
4. Metin: başlıklar arasındaki satırlar ortak satır birleştirmeyle paragraflara ayrılır; sütun
   ve sayfa geçişinde yarım kalan paragraf sürer. "1.", "a)", "•" ile başlayan satırlar madde,
   ardışık maddeler tek listedir. Kalın ve iki noktayla biten kısa etiket ("**Modernizm:**")
   sonraki paragrafın başına bağlanır.
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
from functools import cache
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image

# ================================================================== ORTAK BAŞLANGIÇ

TEXT_LAYER_MIN_CHARS = 20
LAYOUT_ENABLED = os.environ.get("LAYOUT", "0") == "1"
LAYOUT_MODEL = os.environ.get("LAYOUT_MODEL", "")
LAYOUT_CACHE_DIR = os.environ.get("LAYOUT_CACHE_DIR")
LAYOUT_DPI = 150
LAYOUT_MIN_SCORE = 0.3
LAYOUT_DUPLICATE_IOU = 0.7
LAYOUT_WORD_TOLERANCE = 0.25
LAYOUT_CONTAIN_SHARE = 0.8
FURNITURE_LABELS = frozenset({"header", "footer", "number", "seal", "header_image", "footer_image"})
GAP_BREAK_MIN_JUMP = 1.25
GAP_MIN_STEP = 1.08
GAP_NOISE_FACTOR = 2.0
SAME_ROW_PITCH = 0.3
VERSE_FIT_SHARE = 0.5
VERSE_UPPER_SHARE = 0.6
VERSE_FIT_ONLY_SHARE = 0.75
VERSE_OPEN_UPPER_SHARE = 0.8
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
BOLD_NAME = re.compile(r"bold|black|heavy|demi", re.IGNORECASE)
BOLD_WEIGHTS = range(600, 901)
ITALIC_NAME = re.compile(r"italic|oblique", re.IGNORECASE)
SOFT_HYPHEN = "\u00ad"
TRUETYPE_SPACE_GLYPH = 3
OCR_VOTE_MIN_PUNCT_CONFIDENCE = 20.0
UNKNOWN_GLYPH = "\ufffd"
BULLET = "•"
TURKISH_EXTENDED = frozenset("ĞğİıŞş")
PRIVATE_USE = range(0xE000, 0xF900)
LATIN_EXTENDED_A = range(0x100, 0x180)
OCR_VOTES_ENOUGH = 5
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
BRAND_MAX_WORDS = 3
BOLD_SEAM = re.compile(r"\*\*(\s+)\*\*")
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
    weight: int = 0
    suspect: bool = False


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
    layout: list[LayoutBox] = field(default_factory=list)


@dataclass
class LayoutBox:
    """Düzen modelinin bölgesi: etiket, güven, okuma sırası ve kutu (punto, üst-sol orijin)."""

    label: str
    score: float
    order: int
    x0: float
    y0: float
    x1: float
    y1: float


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
    layout: list[LayoutBox] = field(default_factory=list)


def read_document(path: str) -> list[PageIR]:
    """PDF'i sayfa ara temsiline çevirir; bozuk fontları belge düzeyinde çözer."""
    document = pdfium.PdfDocument(path)
    votes: Counter[tuple[str, int, str]] = Counter()
    raws = []
    try:
        for index in range(len(document)):
            raws.append(read_raw_page(document, index, settled_codes(votes)))
            votes.update(raws[-1].votes)
    finally:
        document.close()
    resolve_weights([char for raw in raws for char in raw.chars])
    decoder = GlyphDecoder(votes)
    pages = [finish_page(raw, decoder) for raw in raws]
    for page in pages:
        page.document = path
    return pages


def font_family(font: str) -> str:
    """Fontun ailesi: alt küme öneki, stil eki ve MT/PS ekleri atılmış ad."""
    base = re.split(r"[,-]", font.split("+", 1)[-1])[0]
    return re.sub(r"(?:PS)?(?:MT)?$", "", base)


def resolve_weights(chars: list[Char]) -> None:
    """Adında kalın üyesi olan ailede kalınlığı ad, öbürlerinde geçerli ağırlık belirler."""
    named = {font_family(c.font) for c in chars if BOLD_NAME.search(c.font)}
    for char in chars:
        if not char.bold and font_family(char.font) not in named:
            char.bold = char.weight in BOLD_WEIGHTS


def read_raw_page(
    document: pdfium.PdfDocument, index: int, settled: set[tuple[str, int]]
) -> RawPage:
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
        elif any((c.broken or c.suspect) and c.ink for c in chars):
            votes = vote_broken_glyphs(page, chars, settled)
        layout = detect_layout(page)
        return RawPage(
            index + 1, page.get_width(), page.get_height(), chars, shapes, ocr_words, votes, layout
        )
    finally:
        textpage.close()
        page.close()


@cache
def layout_model() -> tuple[Any, Any] | None:
    """Düzen modelini (PP-DocLayoutV3) bir kez yükler; kütüphane kurulu değilse kural yolu kalır."""
    if not LAYOUT_ENABLED:
        return None
    if not LAYOUT_MODEL:
        raise RuntimeError("LAYOUT=1 requires LAYOUT_MODEL")
    try:
        from transformers import AutoImageProcessor, AutoModelForObjectDetection
    except ImportError:
        return None
    processor = AutoImageProcessor.from_pretrained(LAYOUT_MODEL)
    model = AutoModelForObjectDetection.from_pretrained(LAYOUT_MODEL).eval()
    return processor, model


def detect_layout(page: pdfium.PdfPage) -> list[LayoutBox]:
    """Sayfa görüntüsünde düzen bölgelerini ve okuma sırasını bulur (model yoksa boş liste)."""
    if not LAYOUT_ENABLED:
        return []
    scale = LAYOUT_DPI / 72
    image = page.render(scale=scale).to_pil().convert("RGB")
    cached = None
    if LAYOUT_CACHE_DIR:
        folder = Path(LAYOUT_CACHE_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        cached = folder / f"{hashlib.sha1(image.tobytes()).hexdigest()}.json"
        if cached.exists():
            return [LayoutBox(**row) for row in json.loads(cached.read_text(encoding="utf-8"))]
    loaded = layout_model()
    if loaded is None:
        return []
    boxes = run_layout(loaded, image, scale)
    if cached:
        cached.write_text(json.dumps([box.__dict__ for box in boxes]), encoding="utf-8")
    return boxes


def run_layout(loaded: tuple[Any, Any], image: Image.Image, scale: float) -> list[LayoutBox]:
    """Modeli görüntüde çalıştırır; kutuları puntoya çevirir, örtüşen kopyaları atar."""
    import torch

    processor, model = loaded
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    result = processor.post_process_object_detection(
        outputs, threshold=LAYOUT_MIN_SCORE, target_sizes=[image.size[::-1]]
    )[0]
    boxes = []
    found = zip(result["scores"], result["labels"], result["boxes"], strict=True)
    for order, (score, label, box) in enumerate(found):
        x0, y0, x1, y1 = (float(v) / scale for v in box.tolist())
        name = model.config.id2label[int(label)]
        boxes.append(LayoutBox(name, round(float(score), 3), order, x0, y0, x1, y1))
    kept: list[LayoutBox] = []
    for box in sorted(boxes, key=lambda b: -b.score):
        if all(overlap_ratio(box, other) < LAYOUT_DUPLICATE_IOU for other in kept):
            kept.append(box)
    return sorted(kept, key=lambda b: b.order)


def overlap_ratio(a: LayoutBox, b: LayoutBox) -> float:
    """İki kutunun kesişiminin birleşimine oranı (IoU)."""
    width = min(a.x1, b.x1) - max(a.x0, b.x0)
    height = min(a.y1, b.y1) - max(a.y0, b.y0)
    if width <= 0 or height <= 0:
        return 0.0
    inter = width * height
    area_a = (a.x1 - a.x0) * (a.y1 - a.y0)
    area_b = (b.x1 - b.x0) * (b.y1 - b.y0)
    return inter / (area_a + area_b - inter)


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
        text = BULLET if code in PRIVATE_USE else chr(code) if code else ""
        if pdfium_c.FPDFText_IsHyphen(textpage, index) == 1 or code == 2:
            text = SOFT_HYPHEN
        left, bottom, right, top = textpage.get_charbox(index, loose=True)
        tight = textpage.get_charbox(index)
        font, flags = font_info(textpage, index)
        weight = pdfium_c.FPDFText_GetFontWeight(textpage, index)
        chars.append(
            Char(
                text=text,
                x0=left,
                y0=height - top,
                x1=right,
                y1=height - bottom,
                size=round(pdfium_c.FPDFText_GetFontSize(textpage, index) * scale, 1),
                font=font,
                bold=bool(flags & FORCE_BOLD_FLAG) or bool(BOLD_NAME.search(font)),
                italic=bool(flags & ITALIC_FLAG) or bool(ITALIC_NAME.search(font)),
                color=fill_color(textpage, index),
                code=code,
                broken=pdfium_c.FPDFText_HasUnicodeMapError(textpage, index) == 1,
                ink=has_ink(ink, tight[0], height - tight[3], tight[2], height - tight[1], 1)
                and not hidden_char(
                    textpage, index, layers, (left, height - top, right, height - bottom)
                ),
                weight=weight,
                suspect=code in LATIN_EXTENDED_A and text not in TURKISH_EXTENDED,
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


def vote_broken_glyphs(
    page: pdfium.PdfPage, chars: list[Char], settled: set[tuple[str, int]]
) -> Counter[tuple[str, int, str]]:
    """Bozuk ya da şüpheli fontlu metni tek başına çizip OCR'la okur; (font, kod, harf) oyları."""
    doubtful = [c for c in chars if (c.broken or c.suspect) and c.ink]
    if all((c.font, c.code) in settled for c in doubtful):
        return Counter()
    fonts = {c.font for c in doubtful}
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
            if char.broken or char.suspect:
                votes[(char.font, char.code, letter)] += 1
    return votes


def settled_codes(votes: Counter[tuple[str, int, str]]) -> set[tuple[str, int]]:
    """Yeterince ve açık farkla oylanmış (font, kod) çiftleri."""
    tallies: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    for (font, code, letter), count in votes.items():
        tallies[(font, code)][letter] += count
    settled = set()
    for key, tally in tallies.items():
        ranked = tally.most_common(2)
        lead = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0)
        if lead >= OCR_VOTES_ENOUGH:
            settled.add(key)
    return settled


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
            elif char.suspect and (char.font, char.code) in decoder.table:
                char = replace(char, text=decoder.table[(char.font, char.code)], broken=True)
            chars.append(char)
        if any(c.text == UNKNOWN_GLYPH for c in chars):
            notes.append("UNDECODED_GLYPHS")
        if any(c.broken for c in chars):
            notes.append("REPAIRED_GLYPHS")
        words, source = build_words(chars), "TEXT"
    lines = build_lines(words, raw.page_no)
    source = source if lines else "EMPTY"
    return PageIR(
        raw.page_no, raw.width, raw.height, lines, raw.shapes, source, notes, layout=raw.layout
    )


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
    label: str | None = None


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
    break_ratio: float = float("inf")
    pitch_of: dict[int, float] = field(default_factory=dict)


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
    """Üst/alt bilgi: kenarda aynen tekrarlayan, gövdede olmayan stilde koşu başlığı ya da sayı."""
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
    inner = {
        line_style(text_line)
        for page in pages
        for text_line in page.lines
        if band(text_line, page) is None
    }
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
                and style not in inner
                and alone_in_row(line, page)
            )
            lone_number = (
                outer(line, page)
                and not DIGITS.sub("", line.text).strip(" -–/.|")
                and alone_in_row(line, page, float("inf"))
            )
            tiny = outer(line, page) and line.size < TINY_PRINT_RATIO * body_style[1]
            if repeated or running or lone_number or tiny:
                furniture.add(id(line))
        furniture |= brand_lines(page, furniture, body_style[1])
    return furniture


def brand_lines(page: PageIR, furniture: set[int], body_size: float) -> set[int]:
    """Kenardaki küçük yazıya (logo alt yazısı) üst üste bitişen kısa satırlar."""
    marked = {
        id(line)
        for line in page.lines
        if id(line) in furniture and line.size < TINY_PRINT_RATIO * body_size
    }
    grew = True
    while grew:
        grew = False
        anchors = [line for line in page.lines if id(line) in marked]
        for line in page.lines:
            if id(line) in marked or not outer(line, page) or len(line.words) > BRAND_MAX_WORDS:
                continue
            if any(stacked(line, anchor) for anchor in anchors):
                marked.add(id(line))
                grew = True
    return marked


def stacked(a: Line, b: Line) -> bool:
    """İki satır yatayda örtüşüp dikeyde bitişik mi (aynı öbek)."""
    gap = max(a.y0 - b.y1, b.y0 - a.y1)
    return a.x0 < b.x1 and b.x0 < a.x1 and gap < min(a.size, b.size)


def alone_in_row(line: Line, page: PageIR, reach: float = ROW_MERGE_GAP_EM) -> bool:
    """Satırın aynı sırada, verilen uzaklıktan (em) yakın komşusu yok mu."""
    middle = (line.y0 + line.y1) / 2
    for other in page.lines:
        if other is line or abs((other.y0 + other.y1) / 2 - middle) >= ROW_TOLERANCE_EM * line.size:
            continue
        gap = max(other.x0 - line.x1, line.x0 - other.x1)
        if gap <= reach * line.size:
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
        if page.layout:
            blocks, dropped = layout_blocks(page, lines, body_size, len(pages))
            furniture.extend(dropped)
            for index, (label, block_lines, box) in enumerate(blocks):
                left = min(text_line.x0 for text_line in block_lines)
                right = max(text_line.x1 for text_line in block_lines)
                regions.append(Region((page.page_no, index), left, right, block_lines, box, label))
            continue
        for index, (group, box) in enumerate(page_regions(lines, page, body_size)):
            regions.append(Region((page.page_no, index), 0.0, 0.0, merge_segments(group), box))
    rule_regions = [region for region in regions if region.label is None]
    set_edges(rule_regions, body_size)
    box_edges(rule_regions)
    ordered = [line for region in regions for line in region.lines]
    region_of = {id(line): region for region in regions for line in region.lines}
    shapes = {page.page_no: page.shapes for page in pages}
    by_number = {page.page_no: page for page in pages}
    body = Body(ordered, furniture, region_of, shapes, body_size, regions, by_number)
    body.pitch_of = line_pitches(regions)
    body.break_ratio = paragraph_break_ratio(regions, body.pitch_of)
    return body


def line_pitches(regions: list[Region]) -> dict[int, float]:
    """Her satırın, bölgesinde bir üst sıradaki en yakın satıra göre adımı (araya giren dahil)."""
    pitches: dict[int, float] = {}
    for region in regions:
        ordered = sorted(region.lines, key=lambda text_line: text_line.y1)
        for index, line in enumerate(ordered):
            for upper in reversed(ordered[:index]):
                pitch = line_pitch(upper, line)
                if pitch > SAME_ROW_PITCH:
                    pitches[id(line)] = pitch
                    break
    return pitches


def paragraph_break_ratio(regions: list[Region], pitch_of: dict[int, float]) -> float:
    """Paragraf arası eşiği: cümlesi süren satırların adımının üstündeki doğal kırılma."""
    values, continuing = [], []
    for region in regions:
        ordered = sorted(region.lines, key=lambda text_line: text_line.y1)
        for upper, lower in zip(ordered, ordered[1:], strict=False):
            if line_pitch(upper, lower) <= SAME_ROW_PITCH:
                continue
            values.append(pitch_of[id(lower)])
            if lower.words[0].text[:1].islower():
                continuing.append(pitch_of[id(lower)])
    if not values:
        return float("inf")
    return natural_break(values, median(continuing or values))


def line_pitch(upper: Line, lower: Line) -> float:
    """İki satırın alt kenarları arası, büyük olanın boyutuna oranla."""
    return (lower.y1 - upper.y1) / max(upper.size, lower.size, 1.0)


def natural_break(values: list[float], usual: float) -> float:
    """Olağan değerin üstündeki en alçak ayrık küme sınırı (log ölçekte yinelenen Otsu)."""
    logs = np.log(sorted(value for value in values if value > 0))
    if len(logs) < 4 or usual <= 0:
        return float("inf")
    low, high, best = 0, len(logs), float("inf")
    while high - low >= 2:
        split = otsu_split(logs[low:high])
        if split is None:
            break
        lower, upper = logs[low : low + split], logs[low + split : high]
        boundary = (lower[-1] + upper[0]) / 2
        if boundary <= np.log(usual):
            low += split
            continue
        if distinct(lower, upper):
            best = float(np.exp(boundary))
        high = low + split
    return best


def distinct(lower: np.ndarray, upper: np.ndarray) -> bool:
    """Kümeler ayrık mı: ortalamalar uzak ya da aradaki boşluk alt kümenin yayılımını aşıyor."""
    if upper.mean() - lower.mean() >= np.log(GAP_BREAK_MIN_JUMP):
        return True
    gap = upper[0] - lower[-1]
    spread = np.percentile(lower, 75) - np.percentile(lower, 25)
    return bool(gap >= np.log(GAP_MIN_STEP) and gap >= GAP_NOISE_FACTOR * spread)


def otsu_split(values: np.ndarray) -> int | None:
    """Sıralı değerleri, sınıflar arası farkı en büyük iki kümeye bölen sıra; bölünemezse None."""
    count = len(values)
    prefix = np.cumsum(values)
    sizes = np.arange(1, count)
    lower_mean = prefix[:-1] / sizes
    upper_mean = (prefix[-1] - prefix[:-1]) / (count - sizes)
    score = sizes * (count - sizes) * (upper_mean - lower_mean) ** 2
    score[values[1:] == values[:-1]] = -1.0
    if score.max() <= 0:
        return None
    return int(score.argmax()) + 1


def layout_blocks(
    page: PageIR, lines: list[Line], size: float, page_count: int
) -> tuple[list[tuple[str, list[Line], Shape | None]], list[Line]]:
    """Kelimeleri düzen bölgelerine, kutusuzları kural bloklarına dağıtıp okuma sırasına koyar."""
    holders: dict[int, list[Word]] = defaultdict(list)
    orphans: list[Word] = []
    boxes = outermost(page.layout)
    for text_line in lines:
        for word in text_line.words:
            box = holding_box(word, boxes)
            if box is None:
                orphans.append(word)
            else:
                holders[box.order].append(word)
    blocks: list[tuple[float, str, list[Line]]] = []
    dropped: list[Line] = []
    by_order = {box.order: box for box in page.layout}
    for order, words in holders.items():
        box = by_order[order]
        block_lines = ordered_lines(words, page.page_no, size)
        if box.label in FURNITURE_LABELS and (box.label != "header" or page_count == 1):
            dropped.extend(block_lines)
            continue
        label = "doc_title" if box.label == "header" else box.label
        blocks.append((float(order), label, block_lines))
    blocks.extend(orphan_blocks(orphans, page, blocks, size))
    blocks.sort(key=lambda block: block[0])
    shaped = [
        (label, block_lines, enclosing_box(block_lines, page))
        for _, label, block_lines in order_blocks(blocks, size)
    ]
    return shaped, dropped


def order_blocks(
    blocks: list[tuple[float, str, list[Line]]], size: float
) -> list[tuple[float, str, list[Line]]]:
    """Blokları bölünmez öğe olarak XY-cut'la sıralar; model sırası yalnız eşit konumda kalır."""
    items = []
    for _, _, block_lines in blocks:
        x0, y0, x1, y1 = bounds(block_lines)
        items.append(Item(x0, y0, x1, y1, sum(len(text_line.text) for text_line in block_lines)))
    index_of = {id(item): k for k, item in enumerate(items)}
    return [blocks[index_of[id(item)]] for group in xy_cut(items, size) for item in group]


def outermost(boxes: list[LayoutBox]) -> list[LayoutBox]:
    """Daha büyük bir kutunun içinde kalmayan düzen kutuları (iç içe kutular tek blok olur)."""
    return [
        box for box in boxes if not any(other is not box and within(box, other) for other in boxes)
    ]


def within(inner: LayoutBox, outer_box: LayoutBox) -> bool:
    """Kutunun alanının çoğu daha büyük kutunun içinde mi."""
    width = min(inner.x1, outer_box.x1) - max(inner.x0, outer_box.x0)
    height = min(inner.y1, outer_box.y1) - max(inner.y0, outer_box.y0)
    area = (inner.x1 - inner.x0) * (inner.y1 - inner.y0)
    larger = (outer_box.x1 - outer_box.x0) * (outer_box.y1 - outer_box.y0) > area
    return larger and width > 0 and height > 0 and width * height >= LAYOUT_CONTAIN_SHARE * area


def holding_box(word: Word, boxes: list[LayoutBox]) -> LayoutBox | None:
    """Kelimenin ortasını içeren en küçük düzen kutusu (biraz payla)."""
    pad = LAYOUT_WORD_TOLERANCE * (word.y1 - word.y0)
    cx, cy = (word.x0 + word.x1) / 2, (word.y0 + word.y1) / 2
    inside = [
        box
        for box in boxes
        if box.x0 - pad <= cx <= box.x1 + pad and box.y0 - pad <= cy <= box.y1 + pad
    ]
    return min(inside, key=lambda b: ((b.x1 - b.x0) * (b.y1 - b.y0), -b.score), default=None)


def ordered_lines(words: list[Word], page_no: int, size: float) -> list[Line]:
    """Bloğun kelimelerinden satırları kurar; blok içinde sütun varsa sütun sırasıyla dizer."""
    lines = build_lines(words, page_no)
    groups = flatten(xy_cut(make_items(lines, []), size), size)
    return [text_line for group, _ in groups for text_line in merge_segments(group)]


def orphan_blocks(
    words: list[Word], page: PageIR, blocks: list[tuple[float, str, list[Line]]], size: float
) -> list[tuple[float, str, list[Line]]]:
    """Kutusuz kelimeleri bloklar; her parçayı sütunundaki üst bloğun arkasına yerleştirir."""
    if not words:
        return []
    spans = [(order, bounds(block_lines)) for order, _, block_lines in blocks]
    pieces: list[list[Line]] = []
    for group, _ in page_regions(build_lines(words, page.page_no), page, size):
        current: list[Line] = []
        for text_line in merge_segments(group):
            if current and any(
                overlaps_x(span, text_line)
                and current[-1].y1 <= span[1]
                and span[3] <= text_line.y0
                for _, span in spans
            ):
                pieces.append(current)
                current = []
            current.append(text_line)
        if current:
            pieces.append(current)
    placed = []
    for piece in pieces:
        x0, y0, x1, y1 = bounds(piece)
        column = [(order, span) for order, span in spans if span[0] < x1 and x0 < span[2]]
        above = [(order, span) for order, span in column if span[3] <= y0 + 1]
        below = [(order, span) for order, span in column if span[1] >= y0]
        if above:
            position = max(above, key=lambda item: item[1][3])[0] + 0.5
        elif below:
            position = min(below, key=lambda item: item[1][1])[0] - 0.5
        else:
            position = max((order for order, _ in spans), default=0.0) + 0.5
        placed.append((position + y0 / 1e6, "text", piece))
    return placed


def bounds(lines: list[Line]) -> tuple[float, float, float, float]:
    """Satırların ortak kutusu."""
    return (
        min(text_line.x0 for text_line in lines),
        min(text_line.y0 for text_line in lines),
        max(text_line.x1 for text_line in lines),
        max(text_line.y1 for text_line in lines),
    )


def overlaps_x(span: tuple[float, float, float, float], line: Line) -> bool:
    """Kutu ile satır yatayda örtüşüyor mu."""
    return span[0] < line.x1 and line.x0 < span[2]


def enclosing_box(lines: list[Line], page: PageIR) -> Shape | None:
    """Bloğu içine alan en küçük kutu ya da çerçeve (sayfanın tamamı değil)."""
    x0, y0, x1, y1 = bounds(lines)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    holders = [
        shape
        for shape in page.shapes
        if shape.kind in ("BOX", "FRAME")
        and shape.x0 <= cx <= shape.x1
        and shape.y0 <= cy <= shape.y1
        and (shape.x1 - shape.x0) * (shape.y1 - shape.y0)
        < BOX_MAX_PAGE_SHARE * page.width * page.height
    ]
    return min(holders, key=lambda s: (s.x1 - s.x0) * (s.y1 - s.y0), default=None)


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
    starts = indent_starts(rows, body)
    paragraphs: list[list[Row]] = []
    for k, row in enumerate(rows):
        if k == 0 or k in starts or paragraph_break(rows[k - 1], row, body):
            paragraphs.append([])
        paragraphs[-1].append(row)
    result = []
    for paragraph in paragraphs:
        plain = not keep_bold and mostly_bold([w for row in paragraph for w in row.words])
        verse = verse_like(paragraph, body, right)
        text = words_md(paragraph[0].words, row_hlines(paragraph[0], body), notes, plain)
        for previous, row in zip(paragraph, paragraph[1:], strict=False):
            joint = line_join(previous, row, body, right, verse)
            text += joint + words_md(row.words, row_hlines(row, body), notes, plain)
        text = BOLD_SEAM.sub(r"\1", text)
        if text.strip():
            result.append((text, paragraph))
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


def paragraph_break(previous: Row, current: Row, body: Body) -> bool:
    """İki satır arasında paragraf biter mi: kalınlık, satır adımı, blok değişimi, kısa satır."""
    run_in = not previous.words[-1].bold and not mostly_bold(current.words)
    if mostly_bold(previous.words) != mostly_bold(current.words) and not run_in:
        return True
    if previous.joined:
        return False
    if current.words[0].text[:1].islower() and not CLOSED.search(previous.words[-1].text):
        return False
    region = body.region_of[id(previous.line)]
    following = body.region_of[id(current.first_line)]
    if region is following:
        pitch = body.pitch_of.get(id(current.first_line))
        if pitch is None:
            pitch = line_pitch(previous.line, current.first_line)
        return pitch > body.break_ratio
    if region.label is not None or following.label is not None:
        return True
    return previous.end_x < region.right - 1.5 * previous.words[-1].size


def line_join(previous: Row, current: Row, body: Body, right: float | None, verse: bool) -> str:
    """Aynı paragrafta satır birleşimi: dize ya da kasıtlı kırılmada satır sonu, değilse boşluk."""
    if previous.joined:
        return " "
    if body.region_of[id(previous.line)] is not body.region_of[id(current.first_line)]:
        return " "
    fits = next_word_fits(previous, current, body, right)
    if HARD_START.match(current.words[0].text):
        return "\n"
    if verse:
        return " " if current.words[0].text[:1].islower() and not fits else "\n"
    return "\n" if fits else " "


def next_word_fits(previous: Row, current: Row, body: Body, right: float | None) -> bool:
    """Sonraki satırın ilk kelimesi bu satırın sonuna sığar mıydı (sığarsa kırılma kasıtlıdır)."""
    size = previous.words[-1].size
    edge = right if right is not None else body.region_of[id(previous.line)].right
    first = current.words[0]
    margin = OCR_FIT_MARGIN_EM * size if first.ocr else 0.0
    return previous.end_x + 0.3 * size + (first.x1 - first.x0) <= edge + 1 - margin


def verse_like(rows: list[Row], body: Body, right: float | None) -> bool:
    """Paragraf dize mi: satırlar erken bitiyor ya da cümle bitmeden büyük harfle sürüyor."""
    pairs = [
        (a, b)
        for a, b in zip(rows, rows[1:], strict=False)
        if not a.joined and body.region_of[id(a.line)] is body.region_of[id(b.first_line)]
    ]
    if len(pairs) < 2:
        return False
    fits = sum(next_word_fits(a, b, body, right) for a, b in pairs) / len(pairs)
    upper = sum(b.words[0].text[:1].isupper() for _, b in pairs) / len(pairs)
    if (fits >= VERSE_FIT_SHARE and upper >= VERSE_UPPER_SHARE) or fits >= VERSE_FIT_ONLY_SHARE:
        return True
    open_pairs = [(a, b) for a, b in pairs if not CLOSED.search(a.words[-1].text)]
    if len(open_pairs) < 2:
        return False
    capital = sum(b.words[0].text[:1].isupper() for _, b in open_pairs) / len(open_pairs)
    return capital >= VERSE_OPEN_UPPER_SHARE


# ================================================================== ORTAK SONU

# ================================================================== KİTAP

HEADING_SIZE_RATIO = 1.15
HEADING_MAX_WIDTH_SHARE = 0.75
HEADING_MAX_CHARS = 90
HEADING_MAX_LINES = 3
CENTER_TOLERANCE_EM = 2.0
TABLE_CELL_MAX_LINES = 3
TOC_MIN_SHARE = 0.5
RUN_IN_MAX_CHARS = 60
ITEM_MARK = re.compile(r"^(?:\*\*)?(\d{1,2}[.)]|[a-zçğıöşü]\)|[•▪●■])(?:\*\*)?\s+")
ITEM_START = re.compile(r"^(?:\d{1,2}[.)]|[a-zçğıöşü]\)|[•▪●■])$")
HEADING_END = re.compile(r"[.!?…;:,\"”’]$")
WORDLIKE = re.compile(r"[^\W\d_]{2}")
TOC_LEADER = re.compile(r"(?:\.{4,}|…{2,})\s*\d{0,3}\s*$")
ANSWER_LINE = re.compile(r"^(?:Doğru\s+)?(?:Cevap|Yanıt)\s*:", re.IGNORECASE)


@dataclass
class Block:
    """Kitap bloğu: tür, başlık düzeyi, markdown, başlık yolu, sayfalar ve içinde olduğu kutu."""

    kind: str
    md: str
    level: int | None
    title_path: list[str]
    pages: list[int]
    box: str | None = None


@dataclass
class Segment:
    """Okuma sırasındaki ardışık satırlar: başlık ya da metin; hangi kutuda olduğu."""

    kind: str
    lines: list[Line]
    box: Shape | None


def read_book(pages: list[PageIR]) -> list[Block]:
    """Sayfalardan başlık yolu, paragraf ve madde bloklarını okuma sırasıyla çıkarır."""
    body = reading_order(pages)
    headings = heading_lines(body)
    levels = heading_levels([line for line in body.lines if id(line) in headings], body)
    blocks: list[Block] = []
    path: list[tuple[int, str, int | None]] = []
    titles: dict[int, str] = {}
    current_box: int | None = None
    contexts = box_contexts(segments_list := segments(body, headings))
    for segment in segments_list:
        box_id = contexts[id(segment)]
        if box_id != current_box:
            path = [entry for entry in path if entry[2] is None or entry[2] == box_id]
            current_box = box_id
        if segment.kind == "HEADING":
            text = heading_text(segment.lines, body)
            level = levels[heading_key(segment.lines[0], body)]
            path = [entry for entry in path if entry[0] < level]
            if box_id is not None:
                titles.setdefault(box_id, text)
            blocks.append(
                Block(
                    "HEADING",
                    text,
                    level,
                    [t for _, t, _ in path],
                    pages_of(segment.lines),
                    titles.get(box_id) if box_id is not None else None,
                )
            )
            path.append((level, text, box_id))
            continue
        trail = [t for _, t, _ in path]
        box = titles.get(box_id) if box_id is not None else None
        if is_contents(segment):
            if blocks and blocks[-1].kind == "HEADING" and path:
                path.pop()
            text = "\n".join(line.text for line in segment.lines)
            blocks.append(Block("CONTENTS", text, None, trail[:-1], pages_of(segment.lines)))
            continue
        blocks.extend(text_blocks(segment, body, trail, box))
    return blocks


def is_contents(segment: Segment) -> bool:
    """Metin parçası içindekiler mi: satırlarının çoğu noktalı sayfa yönlendirmesi ya da sayı."""
    lines = segment.lines
    guides = sum(1 for line in lines if TOC_LEADER.search(line.text) or line.text.isdigit())
    return len(lines) >= 3 and guides >= TOC_MIN_SHARE * len(lines)


def box_contexts(parts: list[Segment]) -> dict[int, int | None]:
    """Her parçanın kutu bağlamı; sonraki sayfada aynı yerde süren kutu aynı bağlamdır."""
    contexts: dict[int, int | None] = {}
    last_box: Shape | None = None
    last_context: int | None = None
    last_page = 0
    for part in parts:
        box = part.box
        page = part.lines[0].page_no
        if box is None:
            contexts[id(part)] = None
        elif last_box is not None and (
            box is last_box or same_place(box, last_box) and page == last_page + 1
        ):
            contexts[id(part)] = last_context
        else:
            last_context = id(box)
            contexts[id(part)] = last_context
        if box is not None:
            last_box, last_page = box, part.lines[-1].page_no
        elif part.kind == "HEADING":
            last_box = None
    return contexts


def same_place(a: Shape, b: Shape) -> bool:
    """İki kutu sayfada aynı yatay yerde ve aynı türde mi."""
    return a.kind == b.kind and abs(a.x0 - b.x0) < 3 and abs(a.x1 - b.x1) < 3


def heading_lines(body: Body) -> dict[int, int]:
    """Başlık satırlarının öbeği: belirgin büyük ya da vurgulu, cümle gibi bitmeyen ayrık öbek."""
    styles: Counter[tuple[str, float, bool, str]] = Counter()
    for line in body.lines:
        styles[line_style(line)] += len(line.text)
    body_style = styles.most_common(1)[0][0] if styles else ("", 0.0, False, "")
    result: dict[int, int] = {}
    for region in body.regions:
        lines = [line for line in region.lines if not ANSWER_LINE.match(line.text)]
        groups: list[list[Line]] = []
        for line in lines:
            if groups and not apart(groups[-1][-1], line, body):
                groups[-1].append(line)
            else:
                groups.append([line])
        for index, group in enumerate(groups):
            following = groups[index + 1][0] if index + 1 < len(groups) else None
            if is_heading(group, following, region, body, body_style):
                result.update({id(line): id(group[0]) for line in group})
    return result


def is_heading(
    group: list[Line],
    following: Line | None,
    region: Region,
    body: Body,
    body_style: tuple[str, float, bool, str],
) -> bool:
    """Öbek başlık mı (bkz. heading_lines); numaralıysa büyük ya da büyük harfli olmalı."""
    first = group[0]
    text = " ".join(line.text for line in group)
    style = line_style(first)
    big = style[1] >= body.body_size * HEADING_SIZE_RATIO
    numbered = ITEM_START.match(first.words[0].text) is not None
    words = [w for line in group for w in line.words][1 if numbered else 0 :]
    letters = [c for w in words for c in w.text if c.isalpha()]
    caps = len(letters) >= 3 and all(c.isupper() for c in letters)
    if len(group) > HEADING_MAX_LINES or len(text) > HEADING_MAX_CHARS:
        return False
    if not WORDLIKE.search(text) or TOC_LEADER.search(text):
        return False
    if HEADING_END.search(text) and not introduces_list(text, following):
        return False
    if not words or (numbered and not (big or caps)) or fragment(words):
        return False
    if any(right_aligned(line, region) for line in group) or in_table(first, body):
        return False
    strong = mostly_bold(words) or caps or style[3] != body_style[3]
    return (big or strong) and (following is None or not continues_sentence(following))


def apart(upper: Line, lower: Line, body: Body) -> bool:
    """İki satır ayrık mı: stil, belgeden öğrenilen paragraf adımı ya da hizalama farkı."""
    if line_style(upper) != line_style(lower):
        return True
    if body.pitch_of.get(id(lower), 0.0) > body.break_ratio:
        return True
    return not same_alignment(upper, lower)


def same_alignment(a: Line, b: Line) -> bool:
    """İki satır aynı hizada mı: ortaları ya da sol kenarları yakın."""
    tolerance = CENTER_TOLERANCE_EM * max(a.size, b.size)
    middles = abs((a.x0 + a.x1) / 2 - (b.x0 + b.x1) / 2) < tolerance
    return middles or abs(a.x0 - b.x0) < tolerance


def fragment(words: list[Word]) -> bool:
    """Kelimeler cümle parçası mı: küçük harfle başlıyor ya da tırnağı açık kalıyor."""
    text = " ".join(w.text for w in words)
    unbalanced = text.count("“") != text.count("”") or text.count('"') % 2 == 1
    return text[:1].islower() or unbalanced


def centered(line: Line, region: Region) -> bool:
    """Satır bölgede ortalanmış mı: soldan içeride başlıyor, ortası bölgenin ortasında."""
    tolerance = CENTER_TOLERANCE_EM * line.size
    middle = (region.left + region.right) / 2
    return line.x0 > region.left + tolerance and abs((line.x0 + line.x1) / 2 - middle) < tolerance


def right_aligned(line: Line, region: Region) -> bool:
    """Satır sağ yarıda başlayıp sağ kenarda bitiyor mu (imza, kaynak adı)."""
    middle = (region.left + region.right) / 2
    return line.x0 > middle and region.right - line.x1 < CENTER_TOLERANCE_EM * line.size


def continues_sentence(line: Line) -> bool:
    """Satır küçük harfle sürüyor mu (madde işareti değil)."""
    first = line.words[0].text
    return first[:1].islower() and not ITEM_START.match(first)


def introduces_list(text: str, following: Line | None) -> bool:
    """İki noktayla biten satırın ardından madde mi geliyor (liste başlığı)."""
    return (
        text.endswith(":")
        and following is not None
        and bool(ITEM_START.match(following.words[0].text))
    )


def in_table(line: Line, body: Body) -> bool:
    """Satır çizgili tablo hücresinde mi: dört yanı çizgili, az satırlı, üst/alt çizgisi taşan."""
    shapes = body.shapes[line.page_no]
    cx, cy = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
    walls = [s for s in shapes if s.kind == "VLINE" and s.y0 <= cy <= s.y1]
    every = [s for s in shapes if s.kind == "HLINE"]
    rules = [s for s in every if s.x0 <= cx <= s.x1]
    lefts = [s.x1 for s in walls if s.x1 <= line.x0 + 1]
    rights = [s.x0 for s in walls if s.x0 >= line.x1 - 1]
    tops = [s for s in rules if s.y1 <= line.y0 + 1]
    bottoms = [s for s in rules if s.y0 >= line.y1 - 1]
    if not (lefts and rights and tops and bottoms):
        return False
    left, right = max(lefts), min(rights)
    top, bottom = max(tops, key=lambda s: s.y1), min(bottoms, key=lambda s: s.y0)
    inside = sum(
        1
        for other in body.pages[line.page_no].lines
        if left <= other.x0 and other.x1 <= right and top.y1 <= other.y0 and other.y1 <= bottom.y0
    )
    spill = any(
        min(r.x0 for r in level) < left - line.size or max(r.x1 for r in level) > right + line.size
        for level in ([r for r in every if abs(r.y0 - s.y0) < 1.5] for s in (top, bottom))
    )
    return inside <= TABLE_CELL_MAX_LINES and spill


def heading_key(line: Line, body: Body) -> tuple[float, bool, bool]:
    """Başlık düzeyini belirleyen stil: yuvarlanmış boyut, kalınlık ve ortalanmışlık."""
    style = line_style(line)
    return round(style[1]), style[2], centered(line, body.region_of[id(line)])


def heading_levels(lines: list[Line], body: Body) -> dict[tuple[float, bool, bool], int]:
    """Başlık stillerini düzeylere çevirir: büyük, kalın ve ortalı önce (en üst 1)."""
    keys = sorted(
        {heading_key(line, body) for line in lines}, key=lambda k: (-k[0], not k[1], not k[2])
    )
    return {key: level for level, key in enumerate(keys, start=1)}


def segments(body: Body, headings: dict[int, int]) -> list[Segment]:
    """Okuma sırasındaki satırları başlık ve metin parçalarına böler (kutu değişince de)."""
    result: list[Segment] = []
    for line in body.lines:
        region = body.region_of[id(line)]
        kind = "HEADING" if id(line) in headings else "TEXT"
        last = result[-1] if result else None
        same = (
            last is not None
            and last.kind == kind
            and last.box is region.box
            and (kind == "TEXT" or headings[id(last.lines[-1])] == headings[id(line)])
        )
        if same and last is not None:
            last.lines.append(line)
        else:
            result.append(Segment(kind, [line], region.box))
    return result


def heading_text(lines: list[Line], body: Body) -> str:
    """Başlığın düz metni (markdown işaretsiz, tek satır)."""
    paragraphs = compose([(line.words, line) for line in lines], body)
    return " ".join(" ".join(paragraphs).replace("*", "").split())


def pages_of(lines: list[Line]) -> list[int]:
    """Satırların sayfaları."""
    return sorted({line.page_no for line in lines})


def text_blocks(segment: Segment, body: Body, trail: list[str], box: str | None) -> list[Block]:
    """Metin parçasını paragraf ve madde bloklarına çevirir; öndeki kalın etiketi bağlar."""
    pieces = [(line.words, line) for line in segment.lines]
    paragraphs = compose_paragraphs(pieces, body, keep_bold=True)
    blocks: list[Block] = []
    pending = ""
    for text, rows in paragraphs:
        pages = sorted({r.first_line.page_no for r in rows} | {r.line.page_no for r in rows})
        text = pending + text
        pending = ""
        if run_in_label(text):
            pending = text + " "
            continue
        items = split_items(text)
        if len(items) > 1 or ITEM_MARK.match(text):
            blocks.append(Block("LIST", "\n".join(items), None, trail, pages, box))
        else:
            blocks.append(Block("PARAGRAPH", text, None, trail, pages, box))
    if pending:
        blocks.append(
            Block("PARAGRAPH", pending.strip(), None, trail, pages_of(segment.lines), box)
        )
    return merge_lists(blocks)


def run_in_label(text: str) -> bool:
    """Paragraf yalnızca kalın, kısa ve iki noktayla biten bir etiket mi ("**Modernizm:**")."""
    plain = text.replace("*", "").strip()
    return (
        text.startswith("**")
        and text.rstrip().endswith("**")
        and plain.endswith(":")
        and len(plain) <= RUN_IN_MAX_CHARS
    )


def split_items(text: str) -> list[str]:
    """Paragraf içindeki madde başlarından ("1.", "a)", "•") maddeleri ayırır."""
    items: list[str] = []
    for part in text.split("\n"):
        match = ITEM_MARK.match(part)
        if match or not items:
            marker = match[1] if match else ""
            rest = part[match.end() :] if match else part
            if match and part.startswith("**") and not match[0].rstrip().endswith("**"):
                rest = "**" + rest
            items.append(f"{marker} {rest}".strip())
        else:
            items[-1] += " " + part
    return items


def merge_lists(blocks: list[Block]) -> list[Block]:
    """Ardışık madde bloklarını tek liste bloğunda birleştirir."""
    merged: list[Block] = []
    for block in blocks:
        previous = merged[-1] if merged else None
        if (
            previous is not None
            and previous.kind == block.kind == "LIST"
            and previous.box == block.box
        ):
            previous.md += "\n" + block.md
            previous.pages = sorted(set(previous.pages) | set(block.pages))
        else:
            merged.append(block)
    return merged


def main(arguments: list[str]) -> None:
    """Komut satırı: PDF'leri okuyup blokları yazar (--json ile JSON)."""
    as_json = "--json" in arguments
    for path in [a for a in arguments if not a.startswith("--")]:
        pages = read_document(path)
        blocks = read_book(pages)
        if as_json:
            print(json.dumps([b.__dict__ for b in blocks], ensure_ascii=False))
            continue
        print(f"\n######## {Path(path).name}  sayfalar: {[(p.source, p.notes) for p in pages]}")
        for block in blocks:
            where = " › ".join(block.title_path)
            box = f" [kutu: {block.box}]" if block.box else ""
            if block.kind == "HEADING":
                print(
                    f"\n{'#' * (block.level or 1)} {block.md}  (s.{block.pages}){box} yol: {where}"
                )
            else:
                text = block.md.replace("\n", " ⏎ ")
                print(f"  [{block.kind} s.{block.pages}{box}] {text}")


if __name__ == "__main__":
    main(sys.argv[1:])
