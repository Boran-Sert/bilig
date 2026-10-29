"""İş kuyruğu çalışanı (plan 13.12).

python -m app.worker ile ayrı süreç olarak başlar. JOB_POLL_INTERVAL_SECONDS'ta bir boş yer kadar
iş alır ve en fazla WORKER_CONCURRENCY işi aynı anda yürütür. Her iş, türünün HANDLERS'taki
fonksiyonuyla çalışır; iş sürerken JOB_HEARTBEAT_INTERVAL_SECONDS'ta bir heartbeat atılır, iş başka
çalışana geçtiyse iptal edilir. SIGTERM ya da Ctrl+C gelince yeni iş almaz, çalışan işleri bitirip
kapanır. Zorla kapatılırsa heartbeat kesilir; iş başka çalışana geçer ve kaldığı adımdan devam eder.
psycopg Windows'ta varsayılan döngüde bağlanamadığı için selector döngüsüyle başlar.
"""

import asyncio
import contextlib
import signal
from collections.abc import Mapping

import structlog

from app.config import load_settings, load_worker_settings
from app.constants import JOB_HEARTBEAT_INTERVAL_SECONDS, JOB_POLL_INTERVAL_SECONDS
from app.db.pool import close_pool, open_pool
from app.jobs.handlers import HANDLERS, JobHandler
from app.jobs.postgres_queue import PostgresJobQueue
from app.jobs.queue import Job, JobQueue, JobType
from app.log import configure_logging


async def run() -> None:
    """Ayarları okur, havuzu açar ve durdurulana kadar işleri çalıştırır."""
    settings = load_settings()
    concurrency = load_worker_settings().worker_concurrency
    configure_logging(settings.log)
    pool = await open_pool(settings.database)
    stop = asyncio.Event()
    _stop_on_signals(stop)
    try:
        await work(PostgresJobQueue(pool.connection), HANDLERS, concurrency, stop)
    finally:
        await close_pool()


async def work(
    queue: JobQueue,
    handlers: Mapping[JobType, JobHandler],
    concurrency: int,
    stop: asyncio.Event,
) -> None:
    """Durdurulana kadar boş yer kadar iş alır; durunca çalışan işlerin bitmesini bekler."""
    running: set[asyncio.Task[None]] = set()
    while not stop.is_set():
        free = concurrency - len(running)
        if free > 0:
            for job in await _claim(queue, free):
                task = asyncio.create_task(execute(queue, handlers, job))
                running.add(task)
                task.add_done_callback(running.discard)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), JOB_POLL_INTERVAL_SECONDS)
    if running:
        await asyncio.wait(running)


async def execute(queue: JobQueue, handlers: Mapping[JobType, JobHandler], job: Job) -> None:
    """İşi türünün fonksiyonuyla çalıştırır ve sonucunu kuyruğa yazar."""
    structlog.contextvars.bind_contextvars(jobId=job.id, jobType=job.job_type.value)
    log = structlog.get_logger()
    handler = handlers.get(job.job_type)
    try:
        if handler is None:
            raise LookupError(f"No handler for job type {job.job_type}")
        owned = await _run_with_heartbeat(queue, job, handler)
        if owned:
            owned = await queue.complete(job)
    except Exception as error:
        log.exception("job failed")
        owned = await queue.fail(job, f"{type(error).__name__}: {error}")
    if not owned:
        log.warning("job taken by another worker")


async def _run_with_heartbeat(queue: JobQueue, job: Job, handler: JobHandler) -> bool:
    """İşi çalıştırırken heartbeat atar; iş başkasına geçerse işi iptal eder ve False döner."""
    task = asyncio.create_task(handler(job))
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=JOB_HEARTBEAT_INTERVAL_SECONDS)
            if done:
                task.result()
                return True
            if not await queue.heartbeat(job):
                return False
    finally:
        task.cancel()
        await asyncio.wait({task})


async def _claim(queue: JobQueue, limit: int) -> list[Job]:
    """Sıradaki işleri alır; hata olursa log'a yazar ve boş liste döner."""
    try:
        return await queue.claim(limit)
    except Exception:
        structlog.get_logger().exception("job claim failed")
        return []


def _stop_on_signals(stop: asyncio.Event) -> None:
    """SIGTERM ya da Ctrl+C gelince stop'u kurar."""
    loop = asyncio.get_running_loop()
    for signal_number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signal_number, lambda *_: loop.call_soon_threadsafe(stop.set))


if __name__ == "__main__":
    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)
