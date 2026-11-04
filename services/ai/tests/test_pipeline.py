"""Hazırlık hattının iş akışını gerçek Postgres'te test eder (#120).

Adımlar sahte işlevlerle denenir; REGISTERED adımı kendi ürettiğimiz küçük PDF ve geçici bir
klasörle çalışır. İşler ve kaynaklar db fixture'ının geri alınan transaction'ında yaşar.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from app.constants import JOB_MAX_ATTEMPTS
from app.ingest import pipeline
from app.ingest.pipeline import STEPS, IngestContext, StepFunction, register_source, run_steps
from app.ingest.steps import IngestStep
from app.jobs.queue import Job
from app.storage import LocalFileStorage, page_image_key, source_key
from tests.pdf_factory import lines_pdf
from tests.test_job_step import read_step
from tests.test_postgres_queue import PAST, STALE_AGE, Connection, add_job, make_queue

INSERT_SOURCE = """
WITH user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Hat Testi' FROM tenant
    RETURNING id
)
INSERT INTO source_document (title, sha256, file_path, uploaded_by)
SELECT 'Test Kaynağı', repeat('b', 64), 'sources/0.pdf', id FROM user_row
RETURNING id
"""

READ_SOURCE_STATUS = "SELECT status FROM source_document WHERE id = %s"
READ_PAGES = "SELECT page_no, image_path FROM source_page WHERE source_document_id = %s ORDER BY 2"


class RecordingSteps:
    """Çalışan adımları sayar; belirtilen adım belirtilen kadar hata verir."""

    def __init__(self, fail_step: IngestStep | None = None, failures: int = 0) -> None:
        """Hata verecek adımı ve kaç kez hata vereceğini saklar."""
        self.calls: list[IngestStep] = []
        self.fail_step = fail_step
        self.failures = failures

    def step(self, step: IngestStep) -> StepFunction:
        """Verilen adım için sahte işlev döner."""

        async def run(source_id: int, context: IngestContext) -> None:
            """Çağrıyı kaydeder; sırası gelmişse hata verir."""
            self.calls.append(step)
            if step == self.fail_step and self.failures > 0:
                self.failures -= 1
                raise ValueError("broken page")

        return run


async def make_source(db: Connection) -> int:
    """Test kaynağını ekler ve numarasını döner."""
    cursor = await db.execute(INSERT_SOURCE)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def make_job(db: Connection, source_id: int, attempts: int = 1) -> Job:
    """Kaynağa ait INGEST_SOURCE işini ekleyip alır."""
    queue = make_queue(db)
    job_id = await add_job(db)
    await db.execute(
        "UPDATE background_job SET payload = jsonb_build_object('sourceId', %s::bigint),"
        " attempts = %s - 1 WHERE id = %s",
        (source_id, attempts, job_id),
    )
    [job] = await queue.claim(1)
    return job


def make_context(db: Connection, tmp_path: Path) -> IngestContext:
    """Aynı bağlantıyı ve geçici klasörü kullanan bağlamı kurar."""

    @asynccontextmanager
    async def connect() -> AsyncIterator[Connection]:
        """Verilen bağlantıyı döner."""
        yield db

    return IngestContext(connect=connect, queue=make_queue(db), storage=LocalFileStorage(tmp_path))


@pytest.mark.asyncio
async def test_each_step_is_recorded_and_unregistered_steps_are_skipped(
    db: Connection, tmp_path: Path
) -> None:
    """Her adımdan sonra last_completed_step ilerler; kayıtlı olmayan adım yazılmaz."""
    source_id = await make_source(db)
    job = await make_job(db, source_id)
    recorder = RecordingSteps()
    steps = {step: recorder.step(step) for step in (IngestStep.REGISTERED, IngestStep.EXTRACT)}

    await run_steps(job, make_context(db, tmp_path), steps)

    assert recorder.calls == [IngestStep.REGISTERED, IngestStep.EXTRACT]
    assert await read_step(db, job.id) == ("EXTRACT", "RUNNING")
    cursor = await db.execute(READ_SOURCE_STATUS, (source_id,))
    assert await cursor.fetchone() == ("PROCESSING",)


@pytest.mark.asyncio
async def test_failed_step_resumes_from_same_step_on_retry(db: Connection, tmp_path: Path) -> None:
    """Hata veren adım tekrar alınan işte baştan, önceki adımlar yeniden çalışmadan başlar."""
    source_id = await make_source(db)
    job = await make_job(db, source_id)
    recorder = RecordingSteps(fail_step=IngestStep.EXTRACT, failures=1)
    steps = {step: recorder.step(step) for step in (IngestStep.REGISTERED, IngestStep.EXTRACT)}
    context = make_context(db, tmp_path)

    with pytest.raises(ValueError, match="broken page"):
        await run_steps(job, context, steps)
    await context.queue.fail(job, "ValueError: broken page")
    await db.execute("UPDATE background_job SET run_after = %s WHERE id = %s", (PAST, job.id))
    [retried] = await context.queue.claim(1)
    await run_steps(retried, context, steps)

    assert retried.last_completed_step == IngestStep.REGISTERED
    assert recorder.calls == [IngestStep.REGISTERED, IngestStep.EXTRACT, IngestStep.EXTRACT]
    assert await read_step(db, job.id) == ("EXTRACT", "RUNNING")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("attempts", "expected"), [(1, "PROCESSING"), (JOB_MAX_ATTEMPTS, "FAILED")]
)
async def test_source_is_failed_only_on_last_attempt(
    db: Connection, tmp_path: Path, attempts: int, expected: str
) -> None:
    """Kaynak sadece son denemede FAILED olur; hata her durumda fırlatılır."""
    source_id = await make_source(db)
    job = await make_job(db, source_id, attempts=attempts)
    recorder = RecordingSteps(fail_step=IngestStep.REGISTERED, failures=1)

    with pytest.raises(ValueError, match="broken page"):
        await run_steps(
            job,
            make_context(db, tmp_path),
            {IngestStep.REGISTERED: recorder.step(IngestStep.REGISTERED)},
        )

    cursor = await db.execute(READ_SOURCE_STATUS, (source_id,))
    assert await cursor.fetchone() == (expected,)


@pytest.mark.asyncio
async def test_register_source_writes_page_images_and_rows(db: Connection, tmp_path: Path) -> None:
    """Sayfa görüntüleri pages/{id}/{sayfa:04d}.png yoluna yazılır ve satırlar kaydedilir."""
    source_id = await make_source(db)
    context = make_context(db, tmp_path)
    context.storage.write(source_key(source_id), lines_pdf([["Bir"], ["İki"]]))

    await register_source(source_id, context)
    await register_source(source_id, context)

    keys = [page_image_key(source_id, 1), page_image_key(source_id, 2)]
    assert all(context.storage.read(key).startswith(b"\x89PNG") for key in keys)
    cursor = await db.execute(READ_PAGES, (source_id,))
    assert await cursor.fetchall() == [(1, keys[0]), (2, keys[1])]


@pytest.mark.asyncio
async def test_source_is_failed_when_last_attempt_is_abandoned(db: Connection) -> None:
    """Son denemesinde çalışanı ölen işin kaynağı da FAILED olur."""
    source_id = await make_source(db)
    job_id = await add_job(db, status="RUNNING", attempts=JOB_MAX_ATTEMPTS, age=STALE_AGE)
    await db.execute(
        "UPDATE background_job SET payload = jsonb_build_object('sourceId', %s::bigint)"
        " WHERE id = %s",
        (source_id, job_id),
    )
    await db.execute("UPDATE source_document SET status = 'PROCESSING' WHERE id = %s", (source_id,))

    await make_queue(db).claim(1)

    cursor = await db.execute(READ_SOURCE_STATUS, (source_id,))
    assert await cursor.fetchone() == ("FAILED",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "expected"),
    [("TEXTBOOK", "textbook"), ("TEST", "tests"), ("QUESTION_BANK", "tests"), ("PROGRAM", None)],
)
async def test_extract_reads_source_with_reader_of_its_kind(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, expected: str | None
) -> None:
    """EXTRACT kaynağı türünün okuyucusuyla okur; program ve cevap anahtarı burada okunmaz."""
    source_id = await make_source(db)
    await db.execute("UPDATE source_document SET kind = %s WHERE id = %s", (kind, source_id))
    calls: list[str] = []

    async def record(name: str) -> None:
        """Çağrılan okuyucunun adını kaydeder."""
        calls.append(name)

    monkeypatch.setattr(pipeline, "extract_textbook", lambda *_: record("textbook"))
    monkeypatch.setattr(pipeline, "extract_tests", lambda *_: record("tests"))

    await pipeline.extract_source(source_id, make_context(db, tmp_path))

    assert calls == ([expected] if expected else [])


@pytest.mark.asyncio
async def test_extract_rejects_source_of_unknown_kind(db: Connection, tmp_path: Path) -> None:
    """Türü belirlenmemiş kaynak tahminle okunmaz, hata verir."""
    source_id = await make_source(db)

    with pytest.raises(ValueError, match="UNKNOWN"):
        await pipeline.extract_source(source_id, make_context(db, tmp_path))


def test_registered_and_extract_steps_are_registered() -> None:
    """Bu aşamada sadece REGISTERED ve EXTRACT kayıtlıdır; diğer adımlar atlanır."""
    assert set(STEPS) == {IngestStep.REGISTERED, IngestStep.EXTRACT}
