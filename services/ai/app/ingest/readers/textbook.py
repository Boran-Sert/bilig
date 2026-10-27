"""Ders kitabı okuyucusu: profil uygulanmış satırlardan bloklar (hazırlık hattı A5).

Satırlar ingest/layout.py'nin okuma sırasıyla gelir; iki sayfalık açılımın her sayfası bir sütundur,
sayfa içindeki iki sütunlu şiir sonraki adımda (#129, 2/2) sıraya konur. Gölge için iki kez basılmış
aynı satır bir kez okunur. Blok, aynı türde ve aynı kutudaki ardışık satırlardır; tür, kutu ya da
başlık boyutu değişince, satırlar arasında boşluk büyüyünce ya da önceki satır bitmişken madde
("1.", "•") başlayınca yeni blok başlar. Blok içindeki satırlar layout.py'nin kurallarıyla birleşir;
satırın dolu olup olmadığı bloğun kendi sağ kenarına göre ölçülür (resim yanında daralan paragraf,
kutu), noktalamayla bitip büyük harfle süren satır (dize) ayrı kalır, italik *...* korunur. Sayfa
sütununun sonunda noktalama olmadan kalan blok, aynı ya da sonraki sayfadaki bir sonraki sütunun
başında küçük harfle süren aynı türden blokla birleşir (sayfa sonunda bölünen paragraf); blok ilk
sayfasına yazılır. Başlıklar boyutuna göre düzey alır; başlık yolu kaynak adı ve üstteki daha büyük
başlıklardır ("TDE 12 Ders Kitabı › ŞİİR › Cumhuriyet Dönemi Halk Şiiri"). Arama metni başlık yolu
ve markdown'dır; position, bloğun ilk sayfasındaki sırasıdır. Alıntının altındaki kaynak satırını
alıntıya bağlama henüz yapılmadı (#129 izleme işi).
"""

import re
from collections import Counter
from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from app.constants import (
    LAYOUT_FULL_LINE_SLACK,
    PROFILE_SIZE_STEP,
    SEARCH_PATH_SEPARATOR,
    TEXTBOOK_BLOCK_GAP,
)
from app.ingest.layout import TextPiece, column_pieces, join_pieces
from app.schemas.profile import BlockType, BoundingBox, ProfiledLine

_LIST_START = re.compile(r"^(?:\*\*)?(?:\d{1,2}[.)]|•|-)\s")
_MARK = re.compile(r"\*+")
_SENTENCE_END = re.compile(r"[.!?:…\"”’)]\**$")


class TextbookBlock(BaseModel):
    """Kitaptan okunan blok: tür, markdown, başlık yolu, ilk sayfası, sırası ve sayfaları."""

    block_type: BlockType
    markdown: str
    title_path: str
    page_no: int
    position: int
    pages: list[int]

    @property
    def search_text(self) -> str:
        """Arama metni: başlık yolu ve markdown."""
        return f"{self.title_path}\n{self.markdown}"


class _Draft(BaseModel):
    """Okunmakta olan blok ve parçaları."""

    block_type: BlockType
    box: BoundingBox | None
    pieces: list[TextPiece]


def read_textbook(
    lines: Sequence[ProfiledLine], page_width: float, source_title: str
) -> list[TextbookBlock]:
    """Profil uygulanmış satırlardan kitabın bloklarını başlık yollarıyla okur."""
    pieces = column_pieces(_unique_lines(lines), page_width)
    drafts = _merge_across_columns(_group_blocks(pieces), page_width / 2)
    levels = _heading_levels(drafts)
    headings: list[tuple[int, str]] = []
    positions: Counter[int] = Counter()
    blocks = []
    for draft in drafts:
        markdown = join_pieces(_fit_to_block(draft.pieces), verse_breaks=True)
        if draft.block_type == "BASLIK":
            level = levels[draft.pieces[0].size]
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, _plain_title(markdown)))
        pages = sorted({piece.page_no for piece in draft.pieces})
        blocks.append(
            TextbookBlock(
                block_type=draft.block_type,
                markdown=markdown,
                title_path=SEARCH_PATH_SEPARATOR.join(
                    [source_title, *(title for _, title in headings)]
                ),
                page_no=pages[0],
                position=positions[pages[0]],
                pages=pages,
            )
        )
        positions[pages[0]] += 1
    return blocks


def _unique_lines(lines: Sequence[ProfiledLine]) -> list[ProfiledLine]:
    """Gölge için aynı yere iki kez basılmış satırları bir kez bırakır."""
    seen: set[tuple[int, str, tuple[int, ...]]] = set()
    unique = []
    for line in lines:
        key = (line.page_no, line.markdown, tuple(round(value) for value in line.bbox))
        if key not in seen:
            seen.add(key)
            unique.append(line)
    return unique


def _group_blocks(pieces: Iterable[TextPiece]) -> list[_Draft]:
    """Parçaları tür, kutu, boşluk, başlık ve madde başına göre bloklara ayırır."""
    drafts: list[_Draft] = []
    for piece in pieces:
        current = drafts[-1] if drafts else None
        if current is None or (piece.row_start and _starts_block(current, piece)):
            drafts.append(
                _Draft(block_type=piece.line.block_type, box=piece.line.box_bbox, pieces=[piece])
            )
        else:
            current.pieces.append(piece)
    return drafts


def _starts_block(current: _Draft, piece: TextPiece) -> bool:
    """Satır yeni bir blok başlatıyorsa doğru döner."""
    previous = current.pieces[-1]
    if piece.page_no != previous.page_no or piece.column_left != previous.column_left:
        return True
    if piece.line.block_type != current.block_type or piece.line.box_bbox != current.box:
        return True
    if piece.line.bbox[1] - previous.line.bbox[3] > TEXTBOOK_BLOCK_GAP * piece.size:
        return True
    if current.block_type == "BASLIK":
        return abs(piece.size - previous.size) >= PROFILE_SIZE_STEP
    return bool(_LIST_START.match(piece.text)) and _line_finished(previous)


def _line_finished(piece: TextPiece) -> bool:
    """Satır noktalamayla bitiyorsa ya da sütunun sağ kenarına varmıyorsa doğru döner."""
    short = piece.column_right - piece.right > LAYOUT_FULL_LINE_SLACK * piece.size
    return short or bool(_SENTENCE_END.search(piece.text))


def _merge_across_columns(drafts: list[_Draft], middle: float) -> list[_Draft]:
    """Sütun sonunda yarım kalan bloğu sonraki sütunun başındaki aynı türden blokla birleştirir."""
    merged: list[_Draft] = []
    for draft in drafts:
        previous = merged[-1] if merged else None
        if previous is not None and _continues(previous, draft, middle):
            previous.pieces.extend(draft.pieces)
        else:
            merged.append(draft)
    return merged


def _continues(previous: _Draft, draft: _Draft, middle: float) -> bool:
    """Blok, aynı ya da önceki sayfadaki bir önceki sayfa sütununun son bloğunun devamıysa doğru."""
    last, first = previous.pieces[-1], draft.pieces[0]
    last_column = (last.page_no, last.line.bbox[0] >= middle)
    first_column = (first.page_no, first.line.bbox[0] >= middle)
    next_column = first_column != last_column and 0 <= first.page_no - last.page_no <= 1
    unfinished = not _SENTENCE_END.search(join_pieces(_fit_to_block(previous.pieces)))
    same_kind = previous.block_type == draft.block_type and draft.block_type != "BASLIK"
    same_box = (previous.box is None) == (draft.box is None)
    starts_lower = first.text.lstrip("*")[:1].islower()
    return next_column and unfinished and same_kind and same_box and starts_lower


def _heading_levels(drafts: list[_Draft]) -> dict[float, int]:
    """Başlık boyutlarını büyükten küçüğe düzeylere çevirir (en büyük 0)."""
    sizes = sorted({draft.pieces[0].size for draft in drafts if draft.block_type == "BASLIK"})
    return {size: level for level, size in enumerate(reversed(sizes))}


def _plain_title(markdown: str) -> str:
    """Başlığın markdown işaretlerini ve satır sonlarını atar."""
    return " ".join(_MARK.sub("", markdown).split())


def _fit_to_block(pieces: list[TextPiece]) -> list[TextPiece]:
    """Satırın dolu olup olmadığını bloğun kendi sağ kenarına göre ölçmek için kenarı daraltır."""
    right = max(piece.right for piece in pieces)
    return [piece.model_copy(update={"column_right": right}) for piece in pieces]
