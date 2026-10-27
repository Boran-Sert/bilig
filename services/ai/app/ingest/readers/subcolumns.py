"""Kitap sayfasında yan yana duran iki alt sütun (iki sütunlu şiir) (hazırlık hattı A5).

layout.py satırları soldan sağa okur; sayfanın içinde iki sütun hâlinde basılmış bir şiirde bu, iki
kıtanın dizelerini birbirine karıştırır. Bir satırda parçalar arasında yazı boyutunun
TEXTBOOK_SUBCOLUMN_GAP katından geniş boşluk varsa orada iki alt sütun olabilir. Bölge, sağ sütunun
hizasında başlayan önceki satırlara ve boşluğun üstünden geçmeyen sonraki satırlara uzar; sonundaki,
sağ sütunda parçası olmayan satırlar bölgeden çıkar. Tablo da yan yana hücrelerden oluşur ama
hücreyi satırından koparmak eşleşmeyi bozar; bu yüzden bölge sadece en az
TEXTBOOK_SUBCOLUMN_MIN_ROWS satırında iki yanda da metin olan ve sol yanındaki metinler ortalama
TEXTBOOK_SUBCOLUMN_MIN_CHARS harften uzun (dize) olan yerde alt sütun sayılır; o zaman önce sol,
sonra sağ alt sütun okunur.
"""

from itertools import groupby
from statistics import median

from app.constants import (
    LAYOUT_ROW_TOLERANCE,
    TEXTBOOK_SUBCOLUMN_GAP,
    TEXTBOOK_SUBCOLUMN_MIN_CHARS,
    TEXTBOOK_SUBCOLUMN_MIN_ROWS,
)
from app.ingest.layout import TextPiece

Row = list[TextPiece]


def split_subcolumns(pieces: list[TextPiece]) -> list[TextPiece]:
    """Alt sütunlu bölgeleri önce sol, sonra sağ sütun sırasıyla; kalanı olduğu gibi verir."""
    rows = rows_of(pieces)
    gutters: list[float | None] = [None] * len(rows)
    checked: set[int] = set()
    for index, row in enumerate(rows):
        gutter = gutter_of(row)
        if gutter is None or index in checked:
            continue
        start, end = region_bounds(rows, index, gutter)
        checked.update(range(start, end + 1))
        if is_verse_region(rows[start : end + 1], gutter):
            gutters[start : end + 1] = [gutter] * (end + 1 - start)
    ordered: list[TextPiece] = []
    for gutter, group in groupby(zip(gutters, rows, strict=True), key=lambda item: item[0]):
        region = [row for _, row in group]
        if gutter is None:
            ordered.extend(piece for row in region for piece in row)
        else:
            ordered.extend(read_region(region, gutter))
    return ordered


def region_bounds(rows: list[Row], index: int, gutter: float) -> tuple[int, int]:
    """Bölgeyi hizalı önceki ve boşluğu kesmeyen sonraki satırlara uzatıp sınırlarını döner."""
    anchor = rows[index]
    start = index
    while start > 0 and aligned(rows[start - 1], anchor, gutter):
        start -= 1
    end = index
    while end + 1 < len(rows) and belongs(rows[end + 1], anchor, gutter):
        end += 1
    while end > index and not any(piece.left >= gutter for piece in rows[end]):
        end -= 1
    return start, end


def is_verse_region(region: list[Row], gutter: float) -> bool:
    """Bölgede yeterince iki yanlı satır varsa ve sol yanı dize uzunluğundaysa doğru döner."""
    both = [row for row in region if has_side(row, gutter, False) and has_side(row, gutter, True)]
    lefts = [piece.text for row in region for piece in row if piece.left < gutter]
    long_lines = bool(lefts) and median(len(text) for text in lefts) >= TEXTBOOK_SUBCOLUMN_MIN_CHARS
    return len(both) >= TEXTBOOK_SUBCOLUMN_MIN_ROWS and long_lines


def has_side(row: Row, gutter: float, right_side: bool) -> bool:
    """Satırın istenen alt sütunda parçası varsa doğru döner."""
    return any((piece.left >= gutter) is right_side for piece in row)


def belongs(row: Row, anchor: Row, gutter: float) -> bool:
    """Satır aynı sayfa sütununda ve hiçbir parçası alt sütun boşluğunu kesmiyorsa doğru döner."""
    first = anchor[0]
    same_column = (row[0].page_no, row[0].column_left) == (first.page_no, first.column_left)
    return same_column and not any(piece.left < gutter < piece.right for piece in row)


def aligned(row: Row, anchor: Row, gutter: float) -> bool:
    """Satır bölgeye uyuyor ve bir parçası sağ alt sütunun hizasında başlıyorsa doğru döner."""
    tolerance = LAYOUT_ROW_TOLERANCE * anchor[0].size
    starts_at_gutter = any(abs(piece.left - gutter) <= tolerance for piece in row)
    return belongs(row, anchor, gutter) and starts_at_gutter


def rows_of(pieces: list[TextPiece]) -> list[Row]:
    """Parçaları satırlara böler."""
    rows: list[Row] = []
    for piece in pieces:
        if piece.row_start or not rows:
            rows.append([piece])
        else:
            rows[-1].append(piece)
    return rows


def gutter_of(row: Row) -> float | None:
    """Satırdaki parçalar arasında alt sütun boşluğu varsa sağ alt sütunun sol kenarını döner."""
    for left, right in zip(row, row[1:], strict=False):
        if right.left - left.right > TEXTBOOK_SUBCOLUMN_GAP * left.size:
            return right.left
    return None


def read_region(region: list[Row], gutter: float) -> list[TextPiece]:
    """Alt sütunlu bölgenin parçalarını önce sol sütun, sonra sağ sütun sırasıyla verir."""
    ordered = []
    for right_side in (False, True):
        side_rows = [
            [piece for piece in row if (piece.left >= gutter) is right_side] for row in region
        ]
        side = [piece for row in side_rows for piece in row]
        if not side:
            continue
        edges = {
            "column_left": min(piece.left for piece in side),
            "column_right": max(piece.right for piece in side),
        }
        for row in side_rows:
            for index, piece in enumerate(row):
                ordered.append(piece.model_copy(update={"row_start": index == 0, **edges}))
    return ordered
