"""İş kuyruğu çalışanını sahte kuyrukla test eder (#114).

Veritabanı kullanılmaz; FakeQueue kuyruğa yapılan çağrıları kaydeder. Çalışanın bekleme ve
heartbeat süreleri testte kısaltılır.
"""

import asyncio

import pytest
from pydantic import BaseModel

from app import worker
from app.jobs.handlers import JobHandler
from app.jobs.queue import Job, JobType

SHORT_WAIT_SECONDS = 0.01
TEST_TIMEOUT_SECONDS = 1


class FakeQueue:
    """Çağrıları kaydeden sahte iş kuyruğu."""

    def __init__(self, jobs: list[Job], *, owned: bool = True) -> None:
        """Verilecek işleri ve işin bu çalışanda kalıp kalmadığını saklar."""
        self.pending = list(jobs)
        self.owned = owned
        self.claim_error: Exception | None = None
        self.heartbeats = 0
        self.completed: list[int] = []
        self.failed: list[tuple[int, str]] = []

    async def enqueue(self, job_type: JobType, payload: BaseModel) -> int:
        """Çalışan kuyruğa iş koymaz."""
        raise NotImplementedError

    async def claim(self, limit: int) -> list[Job]:
        """Varsa bekleyen hatayı bir kez verir, yoksa sıradaki işleri sınır kadar verir."""
        if self.claim_error is not None:
            error, self.claim_error = self.claim_error, None
            raise error
        taken, self.pending = self.pending[:limit], self.pending[limit:]
        return taken

    async def heartbeat(self, job: Job) -> bool:
        """Heartbeat'i sayar."""
        self.heartbeats += 1
        return self.owned

    async def record_step(self, job: Job, step: str) -> bool:
        """Worker adım yazmaz; sadece sözleşmeyi sağlar."""
        raise NotImplementedError

    async def complete(self, job: Job) -> bool:
        """Biten işi kaydeder."""
        self.completed.append(job.id)
        return self.owned

    async def fail(self, job: Job, error: str) -> bool:
        """Hatalı işi ve hatasını kaydeder."""
        self.failed.append((job.id, error))
        return self.owned


def make_job(job_id: int) -> Job:
    """Hazırlık türünde bir iş kurar."""
    return Job(
        id=job_id,
        job_type=JobType.INGEST_SOURCE,
        payload={},
        last_completed_step=None,
        attempts=1,
    )


def handlers_of(handler: JobHandler) -> dict[JobType, JobHandler]:
    """Hazırlık türünü verilen fonksiyona bağlayan sözlük kurar."""
    return {JobType.INGEST_SOURCE: handler}


@pytest.fixture(autouse=True)
def short_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Çalışanın bekleme ve heartbeat sürelerini kısaltır."""
    monkeypatch.setattr(worker, "JOB_POLL_INTERVAL_SECONDS", SHORT_WAIT_SECONDS)
    monkeypatch.setattr(worker, "JOB_HEARTBEAT_INTERVAL_SECONDS", SHORT_WAIT_SECONDS)


@pytest.mark.asyncio
async def test_unknown_job_type_fails_job() -> None:
    """Sözlükte fonksiyonu olmayan iş türü hatayla kuyruğa bildirilir."""
    queue = FakeQueue([])

    await worker.execute(queue, {}, make_job(1))

    assert queue.failed == [(1, "LookupError: No handler for job type INGEST_SOURCE")]
    assert queue.completed == []


@pytest.mark.asyncio
async def test_successful_handler_completes_job() -> None:
    """Fonksiyonu hatasız biten iş tamamlandı olarak bildirilir."""
    queue = FakeQueue([])
    seen: list[int] = []

    async def handle(job: Job) -> None:
        """İşi kaydeder."""
        seen.append(job.id)

    await worker.execute(queue, handlers_of(handle), make_job(1))

    assert seen == [1]
    assert queue.completed == [1]
    assert queue.failed == []


@pytest.mark.asyncio
async def test_failing_handler_fails_job_with_error() -> None:
    """Fonksiyonu hata veren iş, hata türü ve mesajıyla bildirilir."""
    queue = FakeQueue([])

    async def handle(job: Job) -> None:
        """Hata verir."""
        raise ValueError("bad page")

    await worker.execute(queue, handlers_of(handle), make_job(1))

    assert queue.failed == [(1, "ValueError: bad page")]
    assert queue.completed == []


@pytest.mark.asyncio
async def test_long_job_sends_heartbeats() -> None:
    """Uzun süren iş boyunca heartbeat atılır."""
    queue = FakeQueue([])

    async def handle(job: Job) -> None:
        """Birkaç heartbeat süresi bekler."""
        await asyncio.sleep(SHORT_WAIT_SECONDS * 5)

    await worker.execute(queue, handlers_of(handle), make_job(1))

    assert queue.heartbeats >= 2
    assert queue.completed == [1]


@pytest.mark.asyncio
async def test_lost_job_is_cancelled_and_not_reported() -> None:
    """Başka çalışana geçen iş iptal edilir, sonucu kuyruğa yazılmaz."""
    queue = FakeQueue([], owned=False)
    cancelled = asyncio.Event()

    async def handle(job: Job) -> None:
        """İptal edilene kadar bekler."""
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    await asyncio.wait_for(
        worker.execute(queue, handlers_of(handle), make_job(1)), TEST_TIMEOUT_SECONDS
    )

    assert cancelled.is_set()
    assert queue.completed == []
    assert queue.failed == []


@pytest.mark.asyncio
async def test_work_runs_at_most_concurrency_jobs_at_once() -> None:
    """Aynı anda en fazla concurrency kadar iş çalışır, yer açılınca sıradaki alınır."""
    queue = FakeQueue([make_job(1), make_job(2), make_job(3)])
    release = asyncio.Event()
    started: list[int] = []
    stop = asyncio.Event()

    async def handle(job: Job) -> None:
        """Başladığını kaydeder ve izin bekler."""
        started.append(job.id)
        await release.wait()

    task = asyncio.create_task(worker.work(queue, handlers_of(handle), 2, stop))
    await asyncio.sleep(SHORT_WAIT_SECONDS * 5)
    assert started == [1, 2]

    release.set()
    await asyncio.sleep(SHORT_WAIT_SECONDS * 5)
    stop.set()
    await asyncio.wait_for(task, TEST_TIMEOUT_SECONDS)

    assert started == [1, 2, 3]
    assert sorted(queue.completed) == [1, 2, 3]


@pytest.mark.asyncio
async def test_stop_waits_for_running_job_and_takes_no_new_job() -> None:
    """Durdurulan çalışan elindeki işi bitirir, yeni iş almaz."""
    queue = FakeQueue([make_job(1), make_job(2)])
    started = asyncio.Event()
    release = asyncio.Event()
    stop = asyncio.Event()

    async def handle(job: Job) -> None:
        """Başladığını bildirir ve izin bekler."""
        started.set()
        await release.wait()

    task = asyncio.create_task(worker.work(queue, handlers_of(handle), 1, stop))
    await asyncio.wait_for(started.wait(), TEST_TIMEOUT_SECONDS)
    stop.set()
    await asyncio.sleep(SHORT_WAIT_SECONDS * 5)
    assert not task.done()

    release.set()
    await asyncio.wait_for(task, TEST_TIMEOUT_SECONDS)

    assert queue.completed == [1]
    assert [job.id for job in queue.pending] == [2]


@pytest.mark.asyncio
async def test_claim_error_does_not_stop_worker() -> None:
    """İş alırken çıkan hata çalışanı durdurmaz, sonraki turda iş alınır."""
    queue = FakeQueue([make_job(1)])
    queue.claim_error = ConnectionError("database is down")
    done = asyncio.Event()
    stop = asyncio.Event()

    async def handle(job: Job) -> None:
        """Çalıştığını bildirir."""
        done.set()

    task = asyncio.create_task(worker.work(queue, handlers_of(handle), 1, stop))
    await asyncio.wait_for(done.wait(), TEST_TIMEOUT_SECONDS)
    stop.set()
    await asyncio.wait_for(task, TEST_TIMEOUT_SECONDS)

    assert queue.completed == [1]
