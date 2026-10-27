"""Sayfa düzeni: okuma sırası ve satır birleştirme (hazırlık hattı A5).

Profil uygulanmış satırlar sayfa sayfa, sütun sütun (sol kenarın sayfa ortasına göre yeri),
yukarıdan aşağı ve satır içinde soldan sağa okunur; birkaç puan farklı yükseklikteki parçalar aynı
satır sayılır. Sütun, iki sütunlu test sayfasının sütunu ya da iki sayfalık kitap açılımının bir
sayfasıdır. Sütun kenarları bütün belgedeki o taraftaki satırlardan bulunur; sol kenar alt, sağ
kenar üst yüzdelikten alınır, tek tük taşkın satır (geniş kutu, tablo) kenarı kaydırmaz. Sağ
yarısında en az LAYOUT_TWO_COLUMN_MIN_LINES satır başlayan sayfa iki sütunludur; orada ortadan geçen
satır (test adı) atılır. Sütunun sağ kenarına kadar dolu satır sonrakiyle birleşir; istenirse
(kitap) noktalamayla bitip büyük harfle süren dolu satır da dize sayılıp ayrı kalır; satır sonu
tiresiyle bölünen kelime tiresiz, büyük harfle süren birleşik kelime ("Türk-İslam") tireli birleşir;
kısa biten satır (dize, diyalog) ve madde imi, çizgi ya da "I."-"VI." ile başlayan satır ayrı
satırda kalır. Eşikler yazı boyutunun katıdır. Test (readers/test.py) ve kitap okuyucuları bu
parçaları kullanır.
"""

import math
import re
from collections.abc import Iterator, Sequence
from itertools import groupby

from pydantic import BaseModel

from app.constants import (
    LAYOUT_EDGE_PERCENTILE,
    LAYOUT_FULL_LINE_SLACK,
    LAYOUT_ROW_TOLERANCE,
    LAYOUT_SOFT_WRAP_SLACK,
    LAYOUT_TWO_COLUMN_MIN_LINES,
)
from app.schemas.profile import ProfiledLine

ITEM_PATTERN = r"(?:I{1,3}|IV|VI?)\.\s"
_HARD_START = re.compile(r"^(?:" + ITEM_PATTERN + r"|•|–|-\s)")
_LINE_END_HYPHEN = re.compile(r"\w-(\**)$")
_CLAUSE_END = re.compile(r"[.,;:!?…]\**$")
_COMPOUND_START = re.compile(r"^[A-ZÇĞİÖŞÜ][a-zçğıöşüâîû]")


class TextPiece(BaseModel):
    """Sütundaki metin parçası, kaynak satırı, kenarları ve satırın ilk parçası olup olmadığı."""

    line: ProfiledLine
    text: str
    size: float
    left: float
    right: float
    column_left: float
    column_right: float
    page_no: int
    row_start: bool


def column_pieces(lines: Sequence[ProfiledLine], page_width: float) -> Iterator[TextPiece]:
    """Satırları sayfa, sütun ve satır sırasıyla, sütun kenarlarıyla birlikte parça olarak verir."""
    middle = page_width / 2
    by_page = sorted(lines, key=lambda line: line.page_no)
    pages = [
        (page_no, drop_page_wide_lines(list(page_lines), middle))
        for page_no, page_lines in groupby(by_page, key=lambda line: line.page_no)
    ]
    kept = [line for _, page_lines in pages for line in page_lines]
    edges = {
        side: column_edges(side_lines)
        for side in (False, True)
        if (side_lines := [line for line in kept if (line.bbox[0] >= middle) is side])
    }
    for page_no, page_lines in pages:
        for side in (False, True):
            column = [line for line in page_lines if (line.bbox[0] >= middle) is side]
            if column:
                yield from row_pieces(column, page_no, edges[side])


def column_edges(lines: list[ProfiledLine]) -> tuple[float, float]:
    """Sütunun kenarlarını satırların alt ve üst yüzdeliğinden bulur; taşkın satır kaydırmaz."""
    lefts = sorted(line.bbox[0] for line in lines)
    rights = sorted(line.bbox[2] for line in lines)
    last = len(lines) - 1
    left = lefts[int(LAYOUT_EDGE_PERCENTILE * last)]
    right = rights[math.ceil((1 - LAYOUT_EDGE_PERCENTILE) * last)]
    return left, right


def drop_page_wide_lines(page_lines: list[ProfiledLine], middle: float) -> list[ProfiledLine]:
    """İki sütunlu sayfada ortadan geçen satırları (test adı, başlık) atar."""
    right_column = sum(line.bbox[0] >= middle for line in page_lines)
    if right_column < LAYOUT_TWO_COLUMN_MIN_LINES:
        return page_lines
    return [line for line in page_lines if not line.bbox[0] < middle < line.bbox[2]]


def row_pieces(
    column: list[ProfiledLine], page_no: int, edges: tuple[float, float]
) -> Iterator[TextPiece]:
    """Sütunun satırlarını hizalarına göre kümeleyip yukarıdan aşağı, soldan sağa verir."""
    rows: list[list[ProfiledLine]] = []
    for line in sorted(column, key=lambda line: line.bbox[1]):
        tolerance = LAYOUT_ROW_TOLERANCE * line.style.size
        if rows and line.bbox[1] - rows[-1][0].bbox[1] < tolerance:
            rows[-1].append(line)
        else:
            rows.append([line])
    for row in rows:
        for index, line in enumerate(sorted(row, key=lambda line: line.bbox[0])):
            yield TextPiece(
                line=line,
                text=line.markdown,
                size=line.style.size,
                left=line.bbox[0],
                right=line.bbox[2],
                column_left=edges[0],
                column_right=edges[1],
                page_no=page_no,
                row_start=index == 0,
            )


def join_pieces(pieces: Sequence[TextPiece], verse_breaks: bool = False) -> str:
    """Parçaları satır sonu kurallarıyla tek metne birleştirir; istenirse dize sonlarını korur."""
    text = ""
    previous: TextPiece | None = None
    for piece in pieces:
        current = " ".join(piece.text.split())
        if not current:
            continue
        if previous is None:
            text = current
        elif mark := wrapped_word_mark(text, previous, piece, current):
            text = text[: -len(mark)] + current[len(mark) - 1 :]
        else:
            text += line_separator(text, previous, piece, current, verse_breaks) + current
        previous = piece
    return text


def wrapped_word_mark(text: str, previous: TextPiece, piece: TextPiece, current: str) -> str:
    """Dolu satır tireyle bitip bu satır küçük harfle sürüyorsa silinecek "-" ve işareti döner."""
    hyphen = _LINE_END_HYPHEN.search(text)
    if not hyphen or not piece.row_start:
        return ""
    mark = hyphen[1]
    full = previous.column_right - previous.right <= LAYOUT_SOFT_WRAP_SLACK * previous.size
    continues = current.startswith(mark) and current[len(mark) : len(mark) + 1].islower()
    return "-" + mark if continues and full else ""


def line_separator(
    text: str, previous: TextPiece, piece: TextPiece, current: str, verse_breaks: bool
) -> str:
    """İki parça arasına boşluk, satır sonu ya da (tireli birleşik kelimede) hiçbir şey koyar."""
    if not piece.row_start:
        return " "
    if _HARD_START.match(current):
        return "\n"
    gap = previous.column_right - previous.right
    if gap <= LAYOUT_FULL_LINE_SLACK * previous.size:
        if _LINE_END_HYPHEN.search(text) and _COMPOUND_START.match(current):
            return ""
        verse = verse_breaks and _CLAUSE_END.search(text) and current[:1].isupper()
        return "\n" if verse else " "
    if current[:1].islower() and gap <= LAYOUT_SOFT_WRAP_SLACK * previous.size:
        return " "
    return "\n"
