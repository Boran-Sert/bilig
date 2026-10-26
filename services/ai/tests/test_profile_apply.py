"""Profili sayfaya uygulamayı ve satırın markdown'ını test eder (hazırlık hattı A4)."""

import pymupdf

from app.ingest.profile import apply_profile, dominant_span_index, line_markdown
from app.schemas.profile import StyledLine, StyledSpan, StyleMatch, TextStyle
from tests.profile_pdf import INFO_BOX, build_document, charis, sample_profile

BODY = charis()
ITALIC = BODY.model_copy(update={"italic": True})
BOLD = BODY.model_copy(update={"bold": True})
BOLD_ITALIC = BODY.model_copy(update={"bold": True, "italic": True})


def build_line(*spans: tuple[str, TextStyle]) -> StyledLine:
    """Verilen parçalardan satır kurar."""
    parts = [StyledSpan(text=text, style=style, box_bbox=None) for text, style in spans]
    return StyledLine(spans=parts, page_no=1, bbox=(0, 0, 1, 1))


def test_apply_profile_turns_styles_into_block_types() -> None:
    """Başlık BASLIK, kutudaki metin BILGI, gövde METIN olur, italik korunur, numara atılır."""
    lines = apply_profile(build_document()[0], sample_profile())

    assert [(line.block_type, line.markdown) for line in lines] == [
        ("BASLIK", "Roman Türleri"),
        ("BILGI", "Tarihî roman konusunu tarihten alır."),
        ("METIN", "Yakup Kadri *Kiralık Konak* romanını 1922'de yazdı."),
    ]
    assert [line.page_no for line in lines] == [1, 1, 1]
    assert [line.style for line in lines] == [
        charis("-Bold", size=14),
        charis(box="#d9ebff"),
        BODY,
    ]
    assert lines[1].box_bbox == (INFO_BOX.x0, INFO_BOX.y0, INFO_BOX.x1, INFO_BOX.y1)
    assert lines[0].box_bbox is None and lines[2].box_bbox is None
    assert INFO_BOX.y0 < lines[1].bbox[1] < lines[1].bbox[3] < INFO_BOX.y1


def test_apply_profile_gives_unmatched_lines_body_type() -> None:
    """Hiçbir kurala uymayan satır METIN olur, atılmaz; boş satır hiç satır sayılmaz."""
    profile = sample_profile(rules=[{"match": {"size": 30}, "block_type": "BASLIK"}])

    lines = apply_profile(build_document()[0], profile)

    assert [line.block_type for line in lines] == ["METIN"] * 4
    assert lines[0].markdown == "**Roman Türleri**"
    assert lines[-1].markdown == "174"


def test_italic_is_kept_even_when_it_fills_most_of_the_line() -> None:
    """Satırın çoğunu tutan italik eser adı da işaretlenir."""
    page = pymupdf.open().new_page()
    html = '<p style="font-size:10px"><i>Kiralık Konak</i> romanı</p>'
    page.insert_htmlbox(pymupdf.Rect(50, 50, 500, 150), html)

    lines = apply_profile(page, sample_profile())

    assert [line.markdown for line in lines] == ["*Kiralık Konak* romanı"]


def test_line_markdown_marks_bold_and_italic_runs() -> None:
    """Kalın ve italik parçalar işaretlenir, boşluklar işaretin dışında kalır."""
    line = build_line(
        ("Bu ", BODY),
        ("Sefiller", ITALIC),
        (", ", BODY),
        ("önemli ", BOLD),
        ("Eser", BOLD_ITALIC),
        ("  dir.", BODY),
    )

    assert line_markdown(line, StyleMatch(size=10)) == "Bu *Sefiller*, **önemli** ***Eser*** dir."


def test_line_markdown_keeps_spaces_outside_marks() -> None:
    """Parçanın başındaki ve sonundaki boşluk işaretin dışına konur."""
    line = build_line(("Bu", BODY), (" Eser ", ITALIC), ("güzel.", BODY))

    assert line_markdown(line, None) == "Bu *Eser* güzel."


def test_line_style_is_the_dominant_span_style() -> None:
    """Satırın stili ilk parçanın değil, en çok harf tutan parçanın stilidir."""
    page = pymupdf.open().new_page()
    html = '<p style="font-size:10px"><b>1.</b> Halk edebiyatımız zengindir.</p>'
    page.insert_htmlbox(pymupdf.Rect(50, 50, 500, 150), html)

    lines = apply_profile(page, sample_profile())

    assert [(line.markdown, line.style) for line in lines] == [
        ("**1.** Halk edebiyatımız zengindir.", BODY)
    ]


def test_line_markdown_merges_neighbour_spans_with_same_marks() -> None:
    """Boyutu farklı olsa da aynı işaretli komşu parçalar tek işaret çifti alır."""
    larger = ITALIC.model_copy(update={"size": 10.5})
    line = build_line(("Kiralık", ITALIC), (" ", BODY), ("Konak", larger), (" romanı", BODY))

    assert line_markdown(line, None) == "*Kiralık Konak* romanı"


def test_line_markdown_skips_marks_the_rule_asks_for() -> None:
    """Kural kalını istiyorsa kalın işareti, italiği istiyorsa italik işareti konmaz."""
    heading = build_line(("Tarihî Roman: ", BOLD), ("Ateşten Gömlek", BOLD_ITALIC))
    quote = build_line(("Ey ", ITALIC), ("Türk", BOLD_ITALIC), (" gençliği!", ITALIC))

    assert line_markdown(heading, StyleMatch(bold=True)) == "Tarihî Roman: *Ateşten Gömlek*"
    assert line_markdown(quote, StyleMatch(italic=True)) == "Ey **Türk** gençliği!"


def test_line_markdown_escapes_literal_asterisks() -> None:
    """Metindeki yıldız, alt çizgi ve ters bölü işaretle karışmasın diye kaçışlanır."""
    line = build_line(("Not* ve a\\b ____ ", BODY), ("Eser", ITALIC))

    assert line_markdown(line, None) == "Not\\* ve a\\\\b \\_\\_\\_\\_ *Eser*"


def test_dominant_span_ignores_whitespace_and_prefers_first_on_tie() -> None:
    """Baskın stil boşluk sayılmadan bulunur; eşit harfte önce gelen kazanır."""
    tie = build_line(("abcd", BODY), ("efgh", BOLD))
    spaces = build_line(("ab", BODY), ("          ", BOLD), ("c", BOLD))

    assert dominant_span_index(tie) == 0
    assert dominant_span_index(spaces) == 0
    assert dominant_span_index(build_line(("a", BODY), ("bcd", BOLD))) == 1
