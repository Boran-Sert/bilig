"""PDF sayfasını stilli satırlara çevirmeyi test eder (hazırlık hattı A4).

Sayfalar testte üretilir: kutular draw_rect ile, metin insert_text (Helvetica) ve insert_htmlbox
(Türkçe harfli CharisSIL) ile yazılır.
"""

from collections.abc import Callable

import pymupdf
import pytest

from app.ingest.styles import filled_boxes, styled_lines
from app.schemas.profile import TextStyle

BLUE = (0.85, 0.92, 1.0)


def new_page() -> pymupdf.Page:
    """Boş A4 sayfası açar."""
    return pymupdf.open().new_page()


def only_style(page: pymupdf.Page) -> TextStyle:
    """Sayfadaki tek satırın ilk parçasının stilini döner."""
    lines = list(styled_lines(page))
    assert len(lines) == 1
    return lines[0].spans[0].style


@pytest.mark.parametrize(
    ("size", "expected"), [(10.0, 10.0), (10.2, 10.0), (10.3, 10.5), (9.8, 10.0), (11.6, 11.5)]
)
def test_size_is_rounded_to_half_points(size: float, expected: float) -> None:
    """Boyut yarım puana yuvarlanır."""
    page = new_page()
    page.insert_text((50, 100), "Roman", fontsize=size)

    assert only_style(page).size == expected


@pytest.mark.parametrize(
    ("fontname", "bold", "italic"),
    [("helv", False, False), ("hebo", True, False), ("heit", False, True), ("hebi", True, True)],
)
def test_bold_and_italic_come_from_font_flags(fontname: str, bold: bool, italic: bool) -> None:
    """Kalınlık ve italiklik PyMuPDF'in font bayraklarından okunur."""
    page = new_page()
    page.insert_text((50, 100), "Roman", fontname=fontname, fontsize=10)

    style = only_style(page)

    assert (style.bold, style.italic) == (bold, italic)


@pytest.mark.parametrize(
    ("color", "expected"), [((0, 0, 0), "#000000"), ((0, 0, 1), "#0000ff"), ((1, 0, 0), "#ff0000")]
)
def test_color_is_lowercase_six_digit_hex(color: tuple[float, ...], expected: str) -> None:
    """Yazı rengi baştaki sıfırları korunmuş küçük harfli #rrggbb olur."""
    page = new_page()
    page.insert_text((50, 100), "Roman", fontsize=10, color=color)

    assert only_style(page).color == expected


def test_text_in_nested_boxes_takes_the_smallest_box() -> None:
    """İç içe kutularda metin en küçük kutunun rengini ve sınırlarını alır."""
    page = new_page()
    page.draw_rect(pymupdf.Rect(40, 60, 400, 200), color=None, fill=(0.9, 0.9, 0.9))
    page.draw_rect(pymupdf.Rect(45, 80, 300, 120), color=None, fill=BLUE)
    page.insert_text((50, 100), "Bilgi", fontsize=10)

    span = next(styled_lines(page)).spans[0]

    assert span.style.box == "#d9ebff"
    assert span.box_bbox == (45, 80, 300, 120)


def test_rounded_box_is_a_box() -> None:
    """Köşesi yuvarlatılmış bilgi kutusu da kutu sayılır."""
    page = new_page()
    page.draw_rect(pymupdf.Rect(40, 60, 300, 200), color=None, fill=BLUE, radius=0.2)
    page.insert_text((50, 100), "Bilgi", fontsize=10)

    assert only_style(page).box == "#d9ebff"


def test_box_is_chosen_by_span_center() -> None:
    """Kutunun kenarına taşan metin, ortası kutudaysa kutulu, değilse kutusuz sayılır."""
    inside, outside = new_page(), new_page()
    for page in (inside, outside):
        page.draw_rect(pymupdf.Rect(0, 0, 70, 200), color=None, fill=BLUE)
    inside.insert_text((20, 100), "Uzun bir", fontsize=10)
    outside.insert_text((60, 100), "Uzun bir", fontsize=10)

    assert only_style(inside).box == "#d9ebff"
    assert only_style(outside).box is None


@pytest.mark.parametrize(
    "draw",
    [
        lambda page: page.draw_rect(page.rect, color=None, fill=(1, 1, 1)),
        lambda page: page.draw_rect(
            pymupdf.Rect(40, 60, 300, 200), color=None, fill=BLUE, fill_opacity=0
        ),
        lambda page: page.draw_circle((100, 100), 80, color=None, fill=BLUE),
        lambda page: page.draw_sector((150, 150), (250, 150), 90, color=None, fill=BLUE),
        lambda page: page.draw_polyline(
            [(20, 20), (300, 20), (150, 300), (20, 20)], color=None, fill=BLUE
        ),
        lambda page: page.draw_rect(pymupdf.Rect(40, 60, 300, 200), color=(0, 0, 0)),
    ],
    ids=[
        "page-background",
        "invisible-fill",
        "circle",
        "sector",
        "triangle",
        "frame-without-fill",
    ],
)
def test_backgrounds_invisible_fills_and_other_shapes_are_not_boxes(
    draw: Callable[[pymupdf.Page], object],
) -> None:
    """Zemin, görünmez dolgu, daire, dilim, üçgen ve dolgusuz çerçeve kutu sayılmaz."""
    page = new_page()
    draw(page)
    page.insert_text((50, 100), "Metin", fontsize=10)

    assert only_style(page).box is None
    assert filled_boxes(page) == []


def test_equal_boxes_take_the_one_drawn_last() -> None:
    """Aynı yerdeki iki kutudan en son çizilen, yani üstte kalan seçilir."""
    page = new_page()
    rect = pymupdf.Rect(40, 60, 300, 200)
    page.draw_rect(rect, color=None, fill=(0.9, 0.9, 0.9))
    page.draw_rect(rect, color=None, fill=BLUE)
    page.insert_text((50, 100), "Bilgi", fontsize=10)

    assert only_style(page).box == "#d9ebff"


def test_combining_mark_span_joins_previous_span() -> None:
    """Ayrı parça gelen birleşen işaret önceki parçaya eklenir ve harf NFC'de birleşir."""
    page = new_page()
    html = '<p style="font-size:10px">Ders s\N{COMBINING CEDILLA}iiri okur.</p>'
    page.insert_htmlbox(pymupdf.Rect(50, 50, 500, 150), html)

    line = next(styled_lines(page))

    assert "".join(span.text for span in line.spans) == "Ders şiiri okur."
    assert {span.style.font for span in line.spans} == {"CharisSIL"}


def test_blank_lines_are_skipped_and_page_no_starts_at_one() -> None:
    """Sadece boşluktan oluşan satır verilmez; sayfa sırası 1'den başlar."""
    document = pymupdf.open()
    document.new_page()
    page = document.new_page()
    page.insert_text((50, 100), "   ", fontsize=10)
    page.insert_text((50, 130), "Metin", fontsize=10)

    lines = list(styled_lines(page))

    assert [(line.page_no, line.spans[0].text) for line in lines] == [(2, "Metin")]


def test_fill_hidden_under_another_fill_is_not_a_box() -> None:
    """Üstü başka bir dolguyla örtülüp basılmayan koyu dolgu kutu sayılmaz."""
    page = new_page()
    page.draw_rect(pymupdf.Rect(40, 60, 300, 200), color=None, fill=(0.14, 0.12, 0.13))
    page.draw_rect(pymupdf.Rect(30, 50, 310, 210), color=None, fill=(1, 1, 1))
    page.insert_text((50, 100), "Metin", fontsize=10)

    assert only_style(page).box == "#ffffff"


BOX = pymupdf.Rect(40, 60, 300, 200)
EDGE_MIDDLES = {
    "top": (170, 65.6),
    "bottom": (170, 194.4),
    "left": (50.4, 130),
    "right": (289.6, 130),
}


@pytest.mark.parametrize(
    ("covered", "kept"),
    [(["top", "bottom"], True), (["top", "bottom", "left"], False)],
    ids=["two-visible", "one-visible"],
)
def test_box_needs_two_visible_edge_middles(covered: list[str], kept: bool) -> None:
    """Kenar ortalarından en az ikisi kutunun renginde görünen kutu sayılır."""
    page = new_page()
    page.draw_rect(BOX, color=None, fill=BLUE)
    for side in covered:
        x, y = EDGE_MIDDLES[side]
        page.draw_rect(pymupdf.Rect(x - 4, y - 4, x + 4, y + 4), color=None, fill=(1, 1, 1))

    assert ("#d9ebff" in [color for _, color in filled_boxes(page)]) is kept


@pytest.mark.parametrize(("difference", "kept"), [(20, True), (40, False)])
def test_box_color_must_match_within_tolerance(difference: int, kept: bool) -> None:
    """Basılı renk kutunun renginden tolerans kadar farklıysa kutu sayılır, fazlasıysa sayılmaz."""
    page = new_page()
    hidden = (0.5, 0.5, 0.5)
    shown = tuple((127.5 + difference) / 255 for _ in range(3))
    page.draw_rect(BOX, color=None, fill=hidden)
    page.draw_rect(BOX, color=None, fill=shown)

    colors = [color for _, color in filled_boxes(page)]

    assert ("#808080" in colors) is kept


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_boxes_are_found_on_rotated_pages(rotation: int) -> None:
    """Dönük sayfada da kutu basılı görüntüde doğru yerden denetlenir."""
    page = new_page()
    page.set_rotation(rotation)
    page.draw_rect(BOX, color=None, fill=BLUE)
    page.insert_text((50, 100), "Bilgi", fontsize=10)

    assert only_style(page).box == "#d9ebff"


def test_boxes_are_found_on_cropped_pages() -> None:
    """Kırpılmış sayfada da kutu basılı görüntüde doğru yerden denetlenir."""
    page = new_page()
    page.draw_rect(BOX, color=None, fill=BLUE)
    page.draw_rect(pymupdf.Rect(300, 60, 560, 200), color=None, fill=(1, 0.8, 0.8))
    page.set_cropbox(pymupdf.Rect(30, 40, 580, 800))

    assert sorted(color for _, color in filled_boxes(page)) == ["#d9ebff", "#ffcccc"]


def test_page_without_box_candidates_is_not_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kutu adayı olmayan sayfa basılmaz."""
    page = new_page()
    page.insert_text((50, 100), "Metin", fontsize=10)

    def fail_render(*arguments: object, **keywords: object) -> None:
        """Basma çağrılırsa testi düşürür."""
        raise AssertionError("page must not be rendered")

    monkeypatch.setattr(pymupdf.Page, "get_pixmap", fail_render)

    assert filled_boxes(page) == []
