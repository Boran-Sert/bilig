"""Görüntü yolu (A5, #142): metni düzelmeyen kitap sayfasını görüntüsünden Claude'la okuma.

Metin katmanı sağlam olmayan sayfa (PageReport'ta LOW_TEXT_LAYER) PNG olarak Haiku'ya verilir
(PAGE_EXTRACT); model emin değilse ya da hiç metin dönmezse aynı sayfa Sonnet'e
(PAGE_EXTRACT_FALLBACK) verilir. Metin katmanıyla karşılaştırma yapılmaz: bu sayfalarda katman
zaten bozuktur. Okuma geçerse sayfanın motor blokları görüntüden okunanlarla değiştirilir; ikisi
de geçemezse motorun okuması kalır ve sayfa incelemeye düşer (readers/textbook.py). Görüntüde
başlık düzeyi bilinmediği için başlık yolu sayfadan önceki bloğun yolundan sürer, sayfadaki
başlık onun altına eklenir. Sayfa görüntüsü REGISTERED adımında depolamaya yazılmıştır, burada
yeniden çizilmez.
"""

import asyncio
from collections.abc import Sequence

from pydantic import BaseModel

from app.constants import SEARCH_PATH_SEPARATOR
from app.llm.runner import run_task
from app.llm.tasks import LlmTask
from app.schemas.page_extract import ExtractedBlock, PageExtraction
from app.schemas.pdf import PageReport
from app.schemas.textbook import TextbookBlock
from app.storage import FileStorage, page_image_key

LOW_TEXT_LAYER_NOTE = "LOW_TEXT_LAYER"
IMAGE_TASKS = (LlmTask.PAGE_EXTRACT, LlmTask.PAGE_EXTRACT_FALLBACK)


class PageImageResult(BaseModel):
    """Görüntü yolunun sonucu: bloklar, okuyan görev ve kontrolü geçip geçmediği."""

    page_no: int
    blocks: list[ExtractedBlock]
    task: LlmTask
    passed: bool


def needs_image_path(report: PageReport) -> bool:
    """Metin katmanı zayıf kalan sayfa görüntü yolundan okunur."""
    return LOW_TEXT_LAYER_NOTE in report.notes


def passes_checks(extraction: PageExtraction) -> bool:
    """Model okuduğundan emin ve bloklarda metin varsa doğru döner."""
    text = "\n".join(block.markdown for block in extraction.blocks).strip()
    return not extraction.unreadable and bool(text)


async def extract_page_image(
    storage: FileStorage, source_id: int, page_no: int, source_title: str
) -> PageImageResult:
    """Sayfa görüntüsünü Haiku'ya verir; kontrol geçmezse Sonnet'e verir."""
    image = await asyncio.to_thread(storage.read, page_image_key(source_id, page_no))
    variables = {"source_title": source_title, "page_no": page_no}
    result = PageImageResult(page_no=page_no, blocks=[], task=IMAGE_TASKS[0], passed=False)
    for task in IMAGE_TASKS:
        extraction = await run_task(task, variables, output_model=PageExtraction, images=[image])
        result = PageImageResult(
            page_no=page_no, blocks=extraction.blocks, task=task, passed=passes_checks(extraction)
        )
        if result.passed:
            break
    return result


def replace_page_blocks(
    blocks: Sequence[TextbookBlock], result: PageImageResult, source_title: str
) -> list[TextbookBlock]:
    """Sayfanın motor bloklarını görüntüden okunanlarla değiştirir; başlık yolu önceden sürer."""
    before = [block for block in blocks if block.page_no < result.page_no]
    after = [block for block in blocks if block.page_no > result.page_no]
    path = before[-1].title_path if before else source_title
    replaced = []
    for position, block in enumerate(result.blocks):
        if block.block_type == "BASLIK":
            path = SEARCH_PATH_SEPARATOR.join([path, block.markdown])
        replaced.append(
            TextbookBlock(
                block_type=block.block_type,
                markdown=block.markdown,
                title_path=path,
                page_no=result.page_no,
                position=position,
                pages=[result.page_no],
            )
        )
    return [*before, *replaced, *after]


async def read_weak_pages(
    storage: FileStorage,
    source_id: int,
    source_title: str,
    blocks: Sequence[TextbookBlock],
    pages: Sequence[PageReport],
) -> tuple[list[TextbookBlock], set[int]]:
    """Zayıf sayfaları görüntüden okur; geçenlerin bloklarını değiştirir ve sayfalarını döner."""
    result_blocks = list(blocks)
    fixed: set[int] = set()
    for report in pages:
        if not needs_image_path(report):
            continue
        result = await extract_page_image(storage, source_id, report.page_no, source_title)
        if result.passed:
            result_blocks = replace_page_blocks(result_blocks, result, source_title)
            fixed.add(report.page_no)
    return result_blocks, fixed
