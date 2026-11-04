"""Hazırlık hattını çalıştıran iş fonksiyonu (plan Bölüm 6, 13.12).

run_ingest, INGEST_SOURCE işini last_completed_step'ten sonraki adımdan başlatıp adımları sırayla
çalıştırır; her adımın çıktısı yazıldıktan sonra adım işe kaydedilir, böylece hata alan iş
kaldığı adımdan devam eder. Adım listesi bir sözlüktür (STEPS): yeni adım bir satırla eklenir,
sözlükte olmayan adım atlanır ve kaydedilmez. EXTRACT kaynağı türünün okuyucusuyla okur (kitap ya
da test); program ve cevap anahtarı komutla yüklendiği için atlanır, türü bilinmeyen kaynak hata
verir. OUTCOMES içeriği kazanımlara bağlar (outcomes.py), INDEX vektörleri yazar (index.py);
VALIDATE ve ENTITIES henüz yoktur. Kaynak başlarken PROCESSING olur; FAILED yalnızca
son denemede yazılır, tekrar denenecek iş listede hatalı görünmez. PUBLISHED burada yazılmaz:
yayın içerik bazındadır. Hata her zaman yeniden fırlatılır, hata metnini çalışan kaydeder.
"""

import asyncio
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.config import load_storage_settings
from app.constants import JOB_MAX_ATTEMPTS, TEST_SOURCE_KINDS
from app.db.pool import get_pool
from app.db.queries.source import (
    fetch_source_kind,
    mark_failed,
    mark_processing,
    save_source_pages,
)
from app.ingest import pdf
from app.ingest.index import index_source
from app.ingest.outcomes import match_source_outcomes
from app.ingest.readers.test import extract_tests
from app.ingest.readers.textbook import extract_textbook
from app.ingest.steps import IngestStep, remaining_steps
from app.jobs.postgres_queue import ConnectionFactory, PostgresJobQueue
from app.jobs.queue import Job, JobQueue
from app.storage import FileStorage, LocalFileStorage, page_image_key, source_key


class IngestSourcePayload(BaseModel):
    """INGEST_SOURCE işinin yükü; Java'daki gibi camelCase yazılır."""

    model_config = ConfigDict(populate_by_name=True)

    source_id: int = Field(alias="sourceId")


@dataclass(frozen=True)
class IngestContext:
    """Adımların ihtiyaç duyduğu veritabanı bağlantısı, iş kuyruğu ve dosya saklama."""

    connect: ConnectionFactory
    queue: JobQueue
    storage: FileStorage


StepFunction = Callable[[int, IngestContext], Coroutine[Any, Any, None]]


async def register_source(source_id: int, context: IngestContext) -> None:
    """Kaynağın her sayfasını 150 dpi görüntü olarak yazar ve source_page satırını kaydeder."""
    content = await asyncio.to_thread(context.storage.read, source_key(source_id))

    def save(page_no: int, image: bytes) -> None:
        """Sayfa görüntüsünü saklamaya yazar."""
        context.storage.write(page_image_key(source_id, page_no), image)

    page_total = await asyncio.to_thread(pdf.render_pages, content, save)
    keys = [page_image_key(source_id, page_no) for page_no in range(1, page_total + 1)]
    async with context.connect() as connection:
        await save_source_pages(connection, source_id, keys)


async def extract_source(source_id: int, context: IngestContext) -> None:
    """Kaynağı türünün okuyucusuyla bloklara ya da sorulara çevirir."""
    async with context.connect() as connection:
        kind = await fetch_source_kind(connection, source_id)
    if kind == "TEXTBOOK":
        await extract_textbook(source_id, context)
    elif kind in TEST_SOURCE_KINDS:
        await extract_tests(source_id, context)
    elif kind == "UNKNOWN":
        raise ValueError(f"Source {source_id} kind is UNKNOWN; set its kind before EXTRACT")


async def match_source(source_id: int, context: IngestContext) -> None:
    """Kaynağın sorularını ve paragraflarını ölçtükleri kazanımlara bağlar."""
    async with context.connect() as connection:
        await match_source_outcomes(connection, source_id)


STEPS: dict[IngestStep, StepFunction] = {
    IngestStep.REGISTERED: register_source,
    IngestStep.EXTRACT: extract_source,
    IngestStep.OUTCOMES: match_source,
    IngestStep.INDEX: index_source,
}


async def run_ingest(job: Job) -> None:
    """INGEST_SOURCE işini havuz, ayarlar ve STEPS ile çalıştırır."""
    pool = get_pool()
    context = IngestContext(
        connect=pool.connection,
        queue=PostgresJobQueue(pool.connection),
        storage=LocalFileStorage(load_storage_settings().storage_dir),
    )
    await run_steps(job, context, STEPS)


async def run_steps(
    job: Job, context: IngestContext, steps: Mapping[IngestStep, StepFunction]
) -> None:
    """Kalan adımları sırayla çalıştırır; hata olursa son denemede kaynağı FAILED yapıp fırlatır."""
    source_id = IngestSourcePayload.model_validate(job.payload).source_id
    async with context.connect() as connection:
        await mark_processing(connection, source_id)
    try:
        for step in remaining_steps(job.last_completed_step):
            function = steps.get(step)
            if function is None:
                continue
            await function(source_id, context)
            if not await context.queue.record_step(job, step):
                structlog.get_logger().warning("job taken by another worker", step=step.value)
                return
    except Exception:
        if job.attempts >= JOB_MAX_ATTEMPTS:
            async with context.connect() as connection:
                await mark_failed(connection, source_id)
        raise
