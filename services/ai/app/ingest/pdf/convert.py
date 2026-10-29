"""Motor çıktılarını ortak formata çevirir (plan 13.6): sorular, kitap blokları, düz satırlar.

Soru: kök, şık ve ortak parça paragrafları paragraph bloğu olur; art arda "I.", "II." ile başlayan
satırlar numbered_items bloğudur. Markdown (italik, kalın, <u>altı çizili</u>) motordan olduğu
gibi gelir. Numara bir öncekinden küçük ya da ona eşitse yeni test başlar; numarasız soru
bulunduğu testte kalır. Kitap: başlık BASLIK, kutudaki metin BILGI, öbür paragraf ve liste
METIN olur; içindekiler blok olarak dönmez. Başlık yolu kaynak adı ve üstteki başlıklardır,
başlığın kendi yolu kendisiyle biter. Düz satırlar okuma sırasındaki görünen satırlardır;
paragraf arasına boş satır konur (sütun ya da sayfa geçişinde küçük harfle süren cümle kırılmaz),
satır sonu tiresi "-" olarak kalır.
"""

import re
from collections import Counter
from collections.abc import Sequence
from itertools import groupby
from typing import cast

from app.constants import SEARCH_PATH_SEPARATOR
from app.ingest.pdf import book_reader, question_reader
from app.schemas.pdf import PageReport, PageSource
from app.schemas.question import (
    OPTION_LABELS,
    Block,
    ParsedQuestion,
    QuestionContent,
    QuestionOption,
)
from app.schemas.textbook import BlockType, TextbookBlock

_NUMBERED_ITEM = re.compile(r"^(?:I{1,3}|IV|VI{0,3})\.\s")
_SOFT_HYPHEN = "­"


def to_tests(questions: Sequence[question_reader.Question]) -> list[list[ParsedQuestion]]:
    """Soruları ortak biçime çevirir; numara başa dönünce yeni test başlatır."""
    tests: list[list[ParsedQuestion]] = []
    previous: int | None = None
    for question in questions:
        number = question.number
        if not tests or (number is not None and previous is not None and number <= previous):
            tests.append([])
        tests[-1].append(to_question(question))
        previous = number if number is not None else previous
    return tests


def to_question(question: question_reader.Question) -> ParsedQuestion:
    """Motorun sorusunu kök, şık ve ortak parça bloklarıyla ParsedQuestion'a çevirir."""
    options = [
        QuestionOption(label=label, blocks=to_blocks(question.options[label]))
        for label in OPTION_LABELS
        if label in question.options
    ]
    content = QuestionContent(
        passage=to_blocks(question.passage) if question.passage else None,
        stem=to_blocks(question.stem),
        options=options,
    )
    answer = question.answer if question.answer in OPTION_LABELS else None
    return ParsedQuestion(
        number=question.number,
        page_no=question.page_no,
        content=content,
        correct_option=answer,
    )


def to_blocks(paragraphs: Sequence[str]) -> list[Block]:
    """Paragrafları paragraph, art arda Roma rakamlı maddeleri numbered_items bloğu yapar."""
    blocks = []
    for paragraph in paragraphs:
        lines = paragraph.split("\n")
        for is_item, group in groupby(lines, key=lambda line: bool(_NUMBERED_ITEM.match(line))):
            block_type = "numbered_items" if is_item else "paragraph"
            blocks.append(Block(type=block_type, md="\n".join(group)))
    return blocks


def to_textbook(blocks: Sequence[book_reader.Block], source_title: str) -> list[TextbookBlock]:
    """Kitap motorunun bloklarını tür, başlık yolu ve sayfa sırasıyla TextbookBlock'a çevirir."""
    positions: Counter[int] = Counter()
    result = []
    for block in blocks:
        if block.kind == "CONTENTS":
            continue
        heading = block.kind == "HEADING"
        block_type: BlockType = "BASLIK" if heading else "BILGI" if block.boxed else "METIN"
        path = [source_title, *block.title_path, *([block.md] if heading else [])]
        page_no = block.pages[0]
        result.append(
            TextbookBlock(
                block_type=block_type,
                markdown=block.md,
                title_path=SEARCH_PATH_SEPARATOR.join(path),
                page_no=page_no,
                position=positions[page_no],
                pages=block.pages,
            )
        )
        positions[page_no] += 1
    return result


def to_lines(body: book_reader.Body) -> list[str]:
    """Gövde satırlarını düz metin olarak verir; paragraf arasına boş satır koyar."""
    lines: list[str] = []
    for index, line in enumerate(body.lines):
        if index and paragraph_ends(body.lines[index - 1], line, body):
            lines.append("")
        text = line.text
        lines.append(text[:-1] + "-" if text.endswith(_SOFT_HYPHEN) else text)
    return lines


def paragraph_ends(
    previous: book_reader.Line, line: book_reader.Line, body: book_reader.Body
) -> bool:
    """Bölge değişiyorsa ya da satır adımı paragraf eşiğini aşıyorsa doğru; süren cümle kırılmaz."""
    if line.text[:1].islower() and not book_reader.CLOSED.search(previous.text):
        return False
    if body.region_of[id(previous)] is not body.region_of[id(line)]:
        return True
    return body.pitch_of.get(id(line), 0.0) > body.break_ratio


def to_page_reports(
    pages: Sequence[question_reader.PageIR] | Sequence[book_reader.PageIR],
) -> list[PageReport]:
    """Sayfaların kaynağını, okuma notlarını ve Türkçe kelime oranını rapora çevirir."""
    return [
        PageReport(
            page_no=page.page_no,
            source=cast(PageSource, page.source),
            notes=list(page.notes),
            text_ratio=page.text_ratio,
        )
        for page in pages
    ]
