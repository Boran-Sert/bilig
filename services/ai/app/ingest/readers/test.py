"""Test okuyucusu: profil uygulanmış sayfa satırlarından sorular (hazırlık hattı A5).

Bir dosya bir testtir: ilk soru 1'dir, her soru bir öncekinin bir fazlasıdır; böylece kökteki
"12. yüzyıl" gibi satırlar soru sanılmaz. Satırlar ingest/layout.py'nin okuma sırasıyla gelir. Soru
sütunun solunda "1." ile başlar; "A)"-"E)" ile başlayan parçalar şıktır, aynı satırda birden çok
şık olabilir. "4-5.", "3. ve 4." ya da "3, 4 ve 5. soruları ... cevaplayınız." başlığından sonraki
metin, sıradaki soru başlayana kadar o soruların ortak parçasıdır; noktalama ile bitmeyen başlığın
en fazla TEST_HEADING_MAX_CONTINUATION satırı başlığa sayılır. Soru başıyla başlayan satır ancak
başlık satırın başındaysa ("3. ve 4. soruları ...") başlık sayılır. Kendi satırındaki "Cevap: A"
içeriğe girmez, sorunun cevabı olur. "I."-"VI." maddeleri numbered_items bloğu olur. Kaçırılan
soru başı, sonraki soruyu öncekinin şıklarına katar; kontroller (A6) bunu şık sayısından yakalar.
Altı çizili söz, kelime altındaki numaralar ve tablolar metin katmanında görünmez; bu sorular
görüntü yolundan (#142) geçer.
"""

import re
from collections.abc import Sequence
from itertools import groupby

from pydantic import BaseModel

from app.constants import TEST_HEADING_MAX_CONTINUATION, TEST_QUESTION_MAX_INDENT
from app.ingest.layout import ITEM_PATTERN, TextPiece, column_pieces, join_pieces
from app.ingest.readers.answer_key import find_inline_answer
from app.schemas.profile import ProfiledLine
from app.schemas.question import (
    OPTION_LABELS,
    Block,
    OptionLabel,
    ParsedQuestion,
    QuestionContent,
    QuestionOption,
)

_QUESTION_START = re.compile(r"^(\*\*)?(\d{1,2})\.(\*\*)?(?=\s|$)\s*")
_SHARED_PASSAGE = re.compile(r"(\d{1,2})\.?((?:\s*(?:[-–]|,|ve)\s*\d{1,2}\.?)+)\s*soruları")
_OPTION_START = re.compile(r"^(\*\*)?([A-E])\)(\*\*)?\s*")
_OPTION_SPLIT = re.compile(r"(?<!\S)(?=(?:\*\*)?[A-E]\)(?:\*\*)?\s)")
_NUMBERED_ITEM = re.compile("^" + ITEM_PATTERN)
_SENTENCE_END = re.compile(r"[.:!?]$")


class QuestionDraft(BaseModel):
    """Okunmakta olan soru: numara, sayfa, ortak parça, kök, şıklar ve satırındaki cevap."""

    number: int
    page_no: int
    passage: list[TextPiece] | None = None
    stem: list[TextPiece] = []
    options: list[tuple[OptionLabel, list[TextPiece]]] = []
    answer: OptionLabel | None = None


class ReaderState(BaseModel):
    """Okuma sırasında biriken sorular ve toplanmakta olan ortak parça."""

    drafts: list[QuestionDraft] = []
    passage: list[TextPiece] | None = None
    passage_numbers: set[int] = set()
    heading_lines_left: int = 0
    collecting_passage: bool = False


def read_questions(lines: Sequence[ProfiledLine], page_width: float) -> list[ParsedQuestion]:
    """Profil uygulanmış satırlardan soruları okur; cevap sadece sorunun altındaysa dolar."""
    state = ReaderState()
    for piece in column_pieces(lines, page_width):
        number = question_number(piece, state.drafts) if piece.row_start else None
        if state.heading_lines_left and number is None:
            ended = _SENTENCE_END.search(piece.text.rstrip("*")) is not None
            state.heading_lines_left = 0 if ended else state.heading_lines_left - 1
            continue
        state.heading_lines_left = 0
        heading_first = number is None or _SHARED_PASSAGE.match(piece.text.lstrip("*"))
        if piece.row_start and heading_first and start_passage(state, piece.text):
            continue
        if number is not None:
            start_question(state, number, piece.page_no)
            piece = piece.model_copy(update={"text": strip_prefix(_QUESTION_START, piece.text)})
        add_piece(state, piece)
    return [to_question(draft) for draft in state.drafts]


def start_passage(state: ReaderState, text: str) -> bool:
    """Metin ortak parça başlığıysa parçayı açar ve doğru döner."""
    match = _SHARED_PASSAGE.search(text)
    if not match:
        return False
    numbers = [int(number) for number in re.findall(r"\d{1,2}", match[0])]
    is_range = bool(re.search(r"[-–]", match[2]))
    state.passage_numbers = set(range(min(numbers), max(numbers) + 1)) if is_range else set(numbers)
    state.passage = []
    state.collecting_passage = True
    ended = _SENTENCE_END.search(text.rstrip("*")) is not None
    state.heading_lines_left = 0 if ended else TEST_HEADING_MAX_CONTINUATION
    return True


def question_number(piece: TextPiece, drafts: list[QuestionDraft]) -> int | None:
    """Parça sütunun solunda sıradaki soru numarasıyla başlıyorsa numarayı döner."""
    match = _QUESTION_START.match(piece.text)
    indent = piece.left - piece.column_left
    if not match or indent > TEST_QUESTION_MAX_INDENT * piece.size:
        return None
    number = int(match[2])
    expected = drafts[-1].number + 1 if drafts else 1
    return number if number == expected else None


def strip_prefix(prefix: re.Pattern[str], text: str) -> str:
    """Soru ya da şık önekini atar; önekin açtığı kalın işaret kapanmadıysa metne geri koyar."""
    match = prefix.match(text)
    if not match:
        return text
    rest = text[match.end() :]
    return "**" + rest if match[1] and not match[3] else rest


def start_question(state: ReaderState, number: int, page_no: int) -> None:
    """Yeni soruyu başlatır; numarası ortak parçanın kapsamındaysa parçayı ona bağlar."""
    state.collecting_passage = False
    passage = state.passage if number in state.passage_numbers else None
    state.drafts.append(QuestionDraft(number=number, page_no=page_no, passage=passage))


def add_piece(state: ReaderState, piece: TextPiece) -> None:
    """Parçayı ortak parçaya, cevaba ya da şıklara bölüp son sorunun köküne veya şıkkına ekler."""
    if state.collecting_passage and state.passage is not None:
        state.passage.append(piece)
        return
    if not state.drafts:
        return
    draft = state.drafts[-1]
    answer = find_inline_answer(piece.text.replace("*", "")) if piece.row_start else None
    if answer is not None:
        draft.answer = answer
        return
    for part in _OPTION_SPLIT.split(piece.text):
        text = part.strip()
        if not text:
            continue
        option = _OPTION_START.match(text)
        if option:
            label = OPTION_LABELS[OPTION_LABELS.index(option[2])]
            rest = piece.model_copy(update={"text": strip_prefix(_OPTION_START, text)})
            draft.options.append((label, [rest]))
        elif draft.options:
            draft.options[-1][1].append(piece.model_copy(update={"text": text}))
        else:
            draft.stem.append(piece.model_copy(update={"text": text}))


def to_question(draft: QuestionDraft) -> ParsedQuestion:
    """Taslak soruyu ortak içerik formatına çevirir."""
    options = [
        QuestionOption(label=label, blocks=[Block(type="paragraph", md=join_pieces(pieces))])
        for label, pieces in draft.options
    ]
    content = QuestionContent(
        passage=to_blocks(draft.passage) if draft.passage else None,
        stem=to_blocks(draft.stem),
        options=options,
    )
    return ParsedQuestion(
        number=draft.number, page_no=draft.page_no, content=content, correct_option=draft.answer
    )


def to_blocks(pieces: Sequence[TextPiece]) -> list[Block]:
    """Birleştirilmiş satırları paragraf ve madde bloklarına ayırır."""
    blocks = []
    lines = join_pieces(pieces).split("\n")
    for is_item, group in groupby(lines, key=lambda line: bool(_NUMBERED_ITEM.match(line))):
        block_type = "numbered_items" if is_item else "paragraph"
        blocks.append(Block(type=block_type, md="\n".join(group)))
    return blocks
