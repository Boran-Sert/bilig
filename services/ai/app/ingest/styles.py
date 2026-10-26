"""PDF sayfasını stilli satırlara çevirir (hazırlık hattı A4).

Her metin parçasının stili PyMuPDF'in verdiği font, yarım puana yuvarlanmış boyut, kalınlık,
italiklik ve yazı rengiyle parçanın ortasının düştüğü en küçük dolgulu kutudan oluşur. Kutu
sayılan çizim dikdörtgen, dörtgen ya da köşesi yuvarlak kutudur (eğri köşeler ve en az üç düz
kenar); daire, dilim ve üçgen kutu değildir. Görünmez dolgu (opaklık 0) ve sayfanın
PROFILE_BOX_MAX_PAGE_SHARE kadarını kaplayan zemin de kutu sayılmaz. Aynı alanlı kutulardan en son
çizilen (üstte kalan) seçilir. PyMuPDF birleşik harfin işaretini ayrı, çoğu zaman başka fontlu
bir parça olarak verebilir (s ve çengel); sadece birleşen işaretten oluşan parça önceki parçaya
eklenir ve parça NFC'ye çevrilir. Profil sayımı ve uygulaması (profile.py) bu satırları kullanır.
"""

import unicodedata
from collections.abc import Iterator
from typing import Any

import pymupdf

from app.constants import PROFILE_BOX_MAX_PAGE_SHARE, PROFILE_SIZE_STEP
from app.schemas.profile import BoundingBox, StyledLine, StyledSpan, TextStyle
from app.text.turkish import normalize_nfc

_BOX_ITEMS = frozenset({"re", "qu"})
_ROUNDED_ITEMS = frozenset({"l", "c"})
_ROUNDED_MIN_LINES = 3
_ZERO_WIDTH = frozenset(
    "\N{ZERO WIDTH SPACE}\N{ZERO WIDTH NON-JOINER}"
    "\N{ZERO WIDTH JOINER}\N{ZERO WIDTH NO-BREAK SPACE}"
)

Box = tuple[pymupdf.Rect, str]


def styled_lines(page: pymupdf.Page) -> Iterator[StyledLine]:
    """Sayfanın metin taşıyan satırlarını stilli parçalarıyla, akış sırasıyla verir."""
    boxes = filled_boxes(page)
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = merge_marks([to_span(span, boxes) for span in line["spans"] if span["text"]])
            if any(span.text.strip() for span in spans):
                yield StyledLine(spans=spans, page_no=page.number + 1, bbox=tuple(line["bbox"]))


def merge_marks(spans: list[StyledSpan]) -> list[StyledSpan]:
    """Sadece birleşen işaretten oluşan parçaları önceki parçaya ekleyip NFC'ye çevirir."""
    merged: list[StyledSpan] = []
    for span in spans:
        if merged and is_mark_only(span.text):
            previous = merged[-1]
            merged[-1] = previous.model_copy(update={"text": previous.text + span.text})
        else:
            merged.append(span)
    return [span.model_copy(update={"text": normalize_nfc(span.text)}) for span in merged]


def is_mark_only(text: str) -> bool:
    """Metin sadece birleşen işaret ve sıfır genişlikli karakterden oluşuyorsa doğru döner."""
    return all(unicodedata.combining(char) or char in _ZERO_WIDTH for char in text)


def to_span(span: dict[str, Any], boxes: list[Box]) -> StyledSpan:
    """PyMuPDF metin parçasını stili ve kutusuyla birlikte modele çevirir."""
    flags = int(span["flags"])
    x0, y0, x1, y1 = span["bbox"]
    center = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
    box = next(((rect, color) for rect, color in boxes if center in rect), None)
    style = TextStyle(
        font=span["font"],
        size=round(float(span["size"]) / PROFILE_SIZE_STEP) * PROFILE_SIZE_STEP,
        bold=bool(flags & pymupdf.TEXT_FONT_BOLD),
        italic=bool(flags & pymupdf.TEXT_FONT_ITALIC),
        color=f"#{int(span['color']):06x}",
        box=box[1] if box else None,
    )
    box_bbox: BoundingBox | None = (box[0].x0, box[0].y0, box[0].x1, box[0].y1) if box else None
    return StyledSpan(text=span["text"], style=style, box_bbox=box_bbox)


def filled_boxes(page: pymupdf.Page) -> list[Box]:
    """Sayfadaki görünür dolgulu kutuları alanı küçükten büyüğe, eşitse üstteki önce döner."""
    page_area = page.rect.get_area()
    boxes = []
    for order, drawing in enumerate(page.get_drawings()):
        if not is_box(drawing):
            continue
        rect = pymupdf.Rect(drawing["rect"])
        if rect.get_area() < PROFILE_BOX_MAX_PAGE_SHARE * page_area:
            boxes.append((rect.get_area(), -order, rect, to_hex(drawing["fill"])))
    return [(rect, color) for _, _, rect, color in sorted(boxes, key=lambda box: box[:2])]


def is_box(drawing: dict[str, Any]) -> bool:
    """Çizim görünür dolgulu dikdörtgen, dörtgen ya da köşesi yuvarlak kutuysa doğru döner."""
    opacity = drawing.get("fill_opacity")
    visible = opacity is None or opacity > 0
    kinds = [item[0] for item in drawing["items"]]
    rectangle = bool(kinds) and set(kinds) <= _BOX_ITEMS
    rounded = set(kinds) == _ROUNDED_ITEMS and kinds.count("l") >= _ROUNDED_MIN_LINES
    return drawing.get("fill") is not None and visible and (rectangle or rounded)


def to_hex(color: tuple[float, ...]) -> str:
    """0-1 arası RGB rengini küçük harfli #rrggbb biçimine çevirir."""
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in color[:3])
