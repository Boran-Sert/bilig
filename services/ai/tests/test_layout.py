"""Sayfa düzeninin okuma sırasını ve satır birleştirme kurallarını test eder (hazırlık hattı A5).

Satırlar elle kurulur (tests/profiled_lines.py); son satır sütunun sağ kenarını belirleyen dolu
satırdır.
"""

import pytest

from app.ingest.layout import column_pieces, join_pieces
from app.schemas.profile import ProfiledLine
from tests.profiled_lines import PAGE_WIDTH, line

FULL = "Sağ kenara kadar dolu satır."


def joined(lines: list[ProfiledLine], verse_breaks: bool = False) -> str:
    """Satırları okuma sırasıyla parçalara çevirip birleştirir."""
    return join_pieces(list(column_pieces(lines, PAGE_WIDTH)), verse_breaks)


def with_full_line(lines: list[ProfiledLine]) -> list[ProfiledLine]:
    """Sütunun sağ kenarını belirleyen dolu bir satırı en alta ekler."""
    return [*lines, line(FULL, 400)]


def test_full_line_joins_next_line_with_space() -> None:
    """Dolu satır, büyük harfle başlayan sonraki satırla boşlukla birleşir."""
    lines = [line("Tanzimat romanı", 100), line("Batı etkisiyle doğdu.", 114, right=150)]

    assert joined(lines) == "Tanzimat romanı Batı etkisiyle doğdu."


def test_short_line_ends_the_line() -> None:
    """Kısa biten satır (dize) büyük harfle süren satırdan satır sonuyla ayrılır."""
    lines = with_full_line(
        [line("Gül dalında", 100, right=120), line("Bülbül öter", 114, right=120)]
    )

    assert joined(lines) == f"Gül dalında\nBülbül öter\n{FULL}"


def test_nearly_full_line_joins_only_a_lowercase_continuation() -> None:
    """Kenara yakın biten satır küçük harfle sürerse birleşir, büyük harfle sürerse kesilir."""
    lower = [line("Roman türleri", 100, right=230), line("arasında tarihî roman", 114, right=200)]
    upper = [line("Roman türleri", 100, right=230), line("Tarihî roman", 114, right=200)]

    assert joined(with_full_line(lower)) == f"Roman türleri arasında tarihî roman\n{FULL}"
    assert joined(with_full_line(upper)) == f"Roman türleri\nTarihî roman\n{FULL}"


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("Halk edebiyatımız geti-", "ren şiirlerle doludur.", "Halk edebiyatımız getiren"),
        ("Yazarın *Araba Sevda-*", "*sı* romanıdır.", "Yazarın *Araba Sevdası* romanıdır."),
        ("Bu Türk-", "İslam edebiyatıdır.", "Bu Türk-İslam edebiyatıdır."),
        ("Yazarın - - - -", "adlı eseri hangisidir?", "Yazarın - - - - adlı eseri"),
    ],
    ids=["wrapped-word", "wrapped-italic-word", "compound", "dash-placeholders"],
)
def test_line_end_hyphens(first: str, second: str, expected: str) -> None:
    """Satır sonu tiresi kelimeyi birleştirir, birleşik kelimede kalır, çizgilere dokunmaz."""
    assert joined([line(first, 100), line(second, 114, right=150)]).startswith(expected)


def test_short_line_ending_with_hyphen_is_not_joined() -> None:
    """Kısa biten satırdaki tire kelime bölmesi sayılmaz."""
    lines = with_full_line([line("Kuzey-", 100, right=90), line("güney ekseni", 114, right=150)])

    assert joined(lines) == f"Kuzey-\ngüney ekseni\n{FULL}"


@pytest.mark.parametrize("marker", ["• ", "- ", "– ", "II. ", "V. "])
def test_bullets_dashes_and_items_start_a_new_line(marker: str) -> None:
    """Madde imi, çizgi ya da madde numarasıyla başlayan satır önceki dolu satırdan ayrılır."""
    lines = [line("Aşağıdakilerden hangisi doğrudur:", 100), line(f"{marker}x", 114, right=90)]

    assert joined(lines) == f"Aşağıdakilerden hangisi doğrudur:\n{marker}x"


def test_century_numeral_continues_the_line() -> None:
    """Yüzyıl numarasıyla ("XIX.") başlayan satır madde sayılmaz, satır sürer."""
    lines = [line("Bu akım ilk kez", 100), line("XIX. yüzyılda görülür.", 114, right=150)]

    assert joined(lines) == "Bu akım ilk kez XIX. yüzyılda görülür."


def test_pieces_on_the_same_row_join_with_space() -> None:
    """Aynı hizadaki iki parça, aradaki boşluk ne kadar olursa olsun boşlukla birleşir."""
    lines = with_full_line([line("Kısa", 100, right=80), line("ifade", 100, 200, 230)])

    assert joined(lines) == f"Kısa ifade\n{FULL}"


def test_row_order_survives_small_vertical_offsets() -> None:
    """Aynı satırın parçaları birkaç puan farklı yükseklikte olsa da soldan sağa okunur."""
    pieces = [line("1.", 101.5, right=50), line("Kısa", 98.8, 55, 80), line("ifade", 100, 200, 230)]

    rows = list(column_pieces(with_full_line(pieces), PAGE_WIDTH))

    assert [(piece.text, piece.row_start) for piece in rows] == [
        ("1.", True),
        ("Kısa", False),
        ("ifade", False),
        (FULL, True),
    ]


def test_columns_are_read_left_then_right_and_hyphen_joins_across() -> None:
    """Sol sütun bitince sağ sütun okunur; sütun sonunda bölünen kelime birleşir."""
    lines = [line("Aşağıdakilerden hangisi Tanzimat ro-", 700)]
    lines += [line("manının özelliğidir?", 60, 320, 470)]

    assert joined(lines) == "Aşağıdakilerden hangisi Tanzimat romanının özelliğidir?"


def test_page_wide_line_is_dropped_only_on_two_column_pages() -> None:
    """İki sütunlu sayfada ortadan geçen test adı atılır; tek sütunlu sayfada geniş satır kalır."""
    title = line("Roman - 1", 40, 250, 350)
    right = [line(f"Sağ {index}", 100 + 14 * index, 320, 560) for index in range(3)]
    two_columns = [title, line("Sol sütun", 100, right=280), *right]
    one_column = [line("Geniş tek sütunlu sayfadaki satır", 100, 40, 560)]

    assert joined(two_columns) == "Sol sütun Sağ 0 Sağ 1 Sağ 2"
    assert joined(one_column) == "Geniş tek sütunlu sayfadaki satır"


def test_single_right_aligned_line_does_not_make_two_columns() -> None:
    """Sağdaki tek sayfa numarası sayfayı iki sütunlu yapmaz; geniş satırlar atılmaz."""
    lines = [line("Geniş satır bir", 100, 40, 560), line("Geniş satır iki", 114, 40, 560)]
    lines.append(line("Sayfa 2", 800, 500, 540))

    assert joined(lines) == "Geniş satır bir Geniş satır iki Sayfa 2"


def test_stray_line_left_of_margin_does_not_move_the_edge() -> None:
    """Kenar boşluğunun solundaki tek taşkın satır sütunun sol kenarını kaydırmaz."""
    lines = [line("Kenar yazısı", 50, 10, 30)]
    lines += [line(f"Satır {index}", 100 + 14 * index, 40, 280) for index in range(12)]

    pieces = list(column_pieces(lines, PAGE_WIDTH))

    assert {piece.column_left for piece in pieces} == {40}


@pytest.mark.parametrize(("verse_breaks", "separator"), [(True, "\n"), (False, " ")])
def test_verse_breaks_are_kept_only_when_asked(verse_breaks: bool, separator: str) -> None:
    """Noktalamayla biten dolu satır ve büyük harfli devamı sadece istenirse (kitap) ayrı kalır."""
    lines = [line("Korkma, sönmez bu şafaklarda yüzen al sancak;", 100)]
    lines += [line("Sönmeden yurdumun üstünde tüten en son ocak.", 114)]

    assert joined(lines, verse_breaks) == (
        f"Korkma, sönmez bu şafaklarda yüzen al sancak;{separator}"
        "Sönmeden yurdumun üstünde tüten en son ocak."
    )


def test_right_edge_ignores_a_few_overhanging_lines() -> None:
    """Sağ kenar üst yüzdelikten alınır; tek bir taşkın satır dolu satırları kısa göstermez."""
    lines = [
        line(f"Satır {index} uzunca bir gövde satırı ve dev-", 100 + 14 * index)
        for index in range(11)
    ]
    lines.append(line("am eder.", 254, right=120))
    lines.append(line("Taşkın geniş tablo satırı", 300, right=400))

    assert "devam eder." in joined(lines)
