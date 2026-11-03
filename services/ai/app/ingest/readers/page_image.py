"""Görüntü yolu (A5, #142): metni düzelmeyen sayfa görüntüsünden Claude'la blok okuma.

Metin katmanı sağlam olmayan sayfa (PageReport'ta LOW_TEXT_LAYER) PNG olarak Haiku'ya verilir
(PAGE_EXTRACT); çıktı kontrolden geçmezse aynı sayfa Sonnet'e (PAGE_EXTRACT_FALLBACK) verilir.
Kontrol: model okuduğundan emin olmalı, en az bir dolu blok olmalı ve metin katmanı varsa ona
en az TEXT_SIMILARITY_MIN_RATIO benzemeli.
İkisi de geçemezse sonuç passed=False döner; sayfayı incelemeye düşürmek çağıranın işidir.
Sayfa görüntüsü REGISTERED adımında depolamaya yazılmıştır, burada yeniden çizilmez.
"""

from pydantic import BaseModel

from app.ingest.validators import matches_text_layer
from app.llm.runner import run_task
from app.llm.tasks import LlmTask
from app.schemas.page_extract import ExtractedBlock, PageExtraction
from app.schemas.pdf import PageReport
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


def passes_checks(extraction: PageExtraction, text_layer: str | None) -> bool:
    """Model emin mi, bloklarda metin var mı ve varsa metin katmanına yeterince benziyor mu."""
    text = "\n".join(block.markdown for block in extraction.blocks).strip()
    if extraction.unreadable or not text:
        return False
    return text_layer is None or matches_text_layer(text, text_layer)


async def extract_page_image(
    storage: FileStorage,
    source_id: int,
    page_no: int,
    source_title: str,
    text_layer: str | None = None,
) -> PageImageResult:
    """Sayfa görüntüsünü Haiku'ya verir; kontrol geçmezse Sonnet'e verir."""
    image = storage.read(page_image_key(source_id, page_no))
    variables = {"source_title": source_title, "page_no": page_no}
    result = PageImageResult(page_no=page_no, blocks=[], task=IMAGE_TASKS[0], passed=False)
    for task in IMAGE_TASKS:
        extraction = await run_task(task, variables, output_model=PageExtraction, images=[image])
        result = PageImageResult(
            page_no=page_no,
            blocks=extraction.blocks,
            task=task,
            passed=passes_checks(extraction, text_layer),
        )
        if result.passed:
            break
    return result
