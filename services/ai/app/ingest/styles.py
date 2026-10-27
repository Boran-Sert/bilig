"""PDF sayfasını stilli satırlara çevirir (hazırlık hattı A4).

Her metin parçasının stili PyMuPDF'in verdiği font, yarım puana yuvarlanmış boyut, kalınlık,
italiklik ve yazı rengiyle parçanın ortasının düştüğü en küçük dolgulu kutudan oluşur. Kutu
sayılan çizim dikdörtgen, dörtgen ya da köşesi yuvarlak kutudur (eğri köşeler ve en az üç düz
kenar); daire, dilim ve üçgen kutu değildir. Görünmez dolgu (opaklık 0) ve sayfanın
PROFILE_BOX_MAX_PAGE_SHARE kadarını kaplayan zemin de kutu sayılmaz. Bazı PDF'ler basılmayan
(kırpılmış ya da üstü örtülmüş) dolgular taşır; bu yüzden sayfa düşük çözünürlükte basılır ve
kenar ortalarına yakın noktalarının çoğu kutunun renginde görünen çizim kutu sayılır; yarı
saydam dolgu karışık renkte basıldığı için kutu sayılmaz, iç kutu dış kutunun kenar ortalarını
örtüyorsa dış kutu düşer. Aynı alanlı kutulardan en son çizilen (üstte kalan) seçilir. PyMuPDF
birleşik harfin işaretini ayrı, çoğu zaman başka fontlu bir parça olarak verebilir (s ve
çengel); sadece birleşen işaretten oluşan parça önceki parçaya eklenir ve parça NFC'ye çevrilir.
Profil sayımı ve uygulaması (profile.py) bu satırları kullanır.
"""

import unicodedata
from collections.abc import Iterator
from typing import Any

import pymupdf

from app.constants import (
    PROFILE_BOX_CHECK_DPI,
    PROFILE_BOX_COLOR_TOLERANCE,
    PROFILE_BOX_MAX_PAGE_SHARE,
    PROFILE_BOX_MIN_MATCHING_POINTS,
    PROFILE_BOX_SAMPLE_INSET,
    PROFILE_SIZE_STEP,
)
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
    candidates = [
        (order, pymupdf.Rect(drawing["rect"]), drawing["fill"])
        for order, drawing in enumerate(page.get_drawings())
        if is_box(drawing)
        and pymupdf.Rect(drawing["rect"]).get_area() < PROFILE_BOX_MAX_PAGE_SHARE * page_area
    ]
    if not candidates:
        return []
    rendered = page.get_pixmap(dpi=PROFILE_BOX_CHECK_DPI)
    boxes = [
        (rect.get_area(), -order, rect, to_hex(fill))
        for order, rect, fill in candidates
        if shows_color(rendered, page, rect, fill)
    ]
    return [(rect, color) for _, _, rect, color in sorted(boxes, key=lambda box: box[:2])]


def shows_color(
    rendered: pymupdf.Pixmap, page: pymupdf.Page, rect: pymupdf.Rect, fill: tuple[float, ...]
) -> bool:
    """Kutunun kenar ortalarına yakın noktalarının çoğu basılı sayfada kutu rengindeyse doğru."""
    inset_x, inset_y = rect.width * PROFILE_BOX_SAMPLE_INSET, rect.height * PROFILE_BOX_SAMPLE_INSET
    middle_x, middle_y = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
    points = [
        (middle_x, rect.y0 + inset_y),
        (middle_x, rect.y1 - inset_y),
        (rect.x0 + inset_x, middle_y),
        (rect.x1 - inset_x, middle_y),
    ]
    expected = [round(channel * 255) for channel in fill[:3]]
    matching = sum(
        all(
            abs(actual - wanted) <= PROFILE_BOX_COLOR_TOLERANCE
            for actual, wanted in zip(pixel_at(rendered, page, x, y), expected, strict=True)
        )
        for x, y in points
    )
    return matching >= PROFILE_BOX_MIN_MATCHING_POINTS


def pixel_at(rendered: pymupdf.Pixmap, page: pymupdf.Page, x: float, y: float) -> list[int]:
    """Çizim koordinatındaki noktanın basılı görüntüdeki rengini verir; sayfa dönüşünü uygular."""
    point = pymupdf.Point(x, y) * page.rotation_matrix
    column = int(point.x / page.rect.width * rendered.width)
    row = int(point.y / page.rect.height * rendered.height)
    pixel = rendered.pixel(
        min(rendered.width - 1, max(0, column)), min(rendered.height - 1, max(0, row))
    )
    return list(pixel[:3])


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
