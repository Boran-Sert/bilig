"""background_job tablosu üzerinde iş kuyruğu (plan 13.12).

claim, sırası gelmiş QUEUED işleri ve JOB_STALE_AFTER_SECONDS boyunca heartbeat atmamış RUNNING
işleri FOR UPDATE SKIP LOCKED ile seçer: başka çalışanın kilitlediği satır beklenmeden atlanır.
Seçim MATERIALIZED CTE'dedir, böylece kilitleme tek kez çalışır. Son denemesinde takılan iş tekrar
alınmaz, FAILED olur. fail, hakkı olan işi QUEUED'a döndürür ve run_after'ı deneme sayısıyla
orantılı ileri atar. Bağlantı verilen connect fonksiyonundan alınır (üretimde havuzun connection
metodu); her çağrı tek transaction'dır. Tablo core'un Flyway migration'larıyla kurulur.
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, LiteralString

from psycopg import AsyncConnection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from app.constants import JOB_MAX_ATTEMPTS, JOB_RETRY_DELAY_SECONDS, JOB_STALE_AFTER_SECONDS
from app.jobs.queue import Job, JobType

ABANDONED_JOB_ERROR = "Worker stopped during the last attempt"

INSERT_JOB = """
INSERT INTO background_job (job_type, payload)
VALUES (%(job_type)s, %(payload)s)
RETURNING id
"""

FAIL_ABANDONED_JOBS = """
UPDATE background_job
SET status = 'FAILED', last_error = %(error)s, updated_at = now()
WHERE status = 'RUNNING'
    AND updated_at < now() - make_interval(secs => %(stale_after)s)
    AND attempts >= %(max_attempts)s
"""

CLAIM_JOBS = """
WITH next_job AS MATERIALIZED (
    SELECT id
    FROM background_job
    WHERE (status = 'QUEUED' AND run_after <= now())
        OR (status = 'RUNNING' AND updated_at < now() - make_interval(secs => %(stale_after)s))
    ORDER BY run_after, id
    LIMIT %(limit)s
    FOR UPDATE SKIP LOCKED
)
UPDATE background_job
SET status = 'RUNNING', attempts = background_job.attempts + 1, updated_at = now()
FROM next_job
WHERE background_job.id = next_job.id
RETURNING background_job.id, background_job.job_type, background_job.payload,
    background_job.last_completed_step, background_job.attempts
"""

TOUCH_JOB = """
UPDATE background_job
SET updated_at = now()
WHERE id = %(id)s AND status = 'RUNNING' AND attempts = %(attempts)s
"""

RECORD_STEP = """
UPDATE background_job
SET last_completed_step = %(step)s, updated_at = now()
WHERE id = %(id)s AND status = 'RUNNING' AND attempts = %(attempts)s
"""

COMPLETE_JOB = """
UPDATE background_job
SET status = 'DONE', updated_at = now()
WHERE id = %(id)s AND status = 'RUNNING' AND attempts = %(attempts)s
"""

FAIL_JOB = """
UPDATE background_job
SET status = CASE WHEN attempts >= %(max_attempts)s THEN 'FAILED' ELSE 'QUEUED' END,
    last_error = %(error)s,
    run_after = now() + make_interval(secs => attempts * %(retry_delay)s),
    updated_at = now()
WHERE id = %(id)s AND status = 'RUNNING' AND attempts = %(attempts)s
"""

ConnectionFactory = Callable[[], AbstractAsyncContextManager[AsyncConnection[Any]]]


class PostgresJobQueue:
    """İşleri background_job tablosunda tutan kuyruk."""

    def __init__(self, connect: ConnectionFactory) -> None:
        """Bağlantı veren fonksiyonu saklar."""
        self._connect = connect

    async def enqueue(self, job_type: JobType, payload: BaseModel) -> int:
        """İşi QUEUED olarak kaydeder; payload Java'daki gibi camelCase yazılır."""
        values = {
            "job_type": job_type,
            "payload": Jsonb(payload.model_dump(mode="json", by_alias=True)),
        }
        async with self._connect() as connection:
            cursor = await connection.execute(INSERT_JOB, values)
            row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("Insert returned no id")
        return int(row[0])

    async def claim(self, limit: int) -> list[Job]:
        """Sırası gelmiş ve sahipsiz kalmış işleri RUNNING yapar, deneme sayılarını artırır."""
        async with self._connect() as connection:
            await connection.execute(
                FAIL_ABANDONED_JOBS,
                {
                    "error": ABANDONED_JOB_ERROR,
                    "stale_after": JOB_STALE_AFTER_SECONDS,
                    "max_attempts": JOB_MAX_ATTEMPTS,
                },
            )
            async with connection.cursor(row_factory=class_row(Job)) as cursor:
                await cursor.execute(
                    CLAIM_JOBS, {"limit": limit, "stale_after": JOB_STALE_AFTER_SECONDS}
                )
                return await cursor.fetchall()

    async def heartbeat(self, job: Job) -> bool:
        """İşin son güncelleme zamanını yeniler; iş başkasına geçtiyse False döner."""
        return await self._update_owned(TOUCH_JOB, job)

    async def record_step(self, job: Job, step: str) -> bool:
        """Tamamlanan son adımı yazar; iş başkasına geçtiyse False döner."""
        return await self._update_owned(RECORD_STEP, job, step=step)

    async def complete(self, job: Job) -> bool:
        """İşi DONE yapar; iş başkasına geçtiyse False döner."""
        return await self._update_owned(COMPLETE_JOB, job)

    async def fail(self, job: Job, error: str) -> bool:
        """Hatayı yazar, hakkı varsa işi ileri bir zamana sıraya koyar, yoksa FAILED yapar."""
        return await self._update_owned(
            FAIL_JOB,
            job,
            error=error,
            max_attempts=JOB_MAX_ATTEMPTS,
            retry_delay=JOB_RETRY_DELAY_SECONDS,
        )

    async def _update_owned(self, query: LiteralString, job: Job, **values: object) -> bool:
        """Sorguyu iş hâlâ bu alımdaysa çalıştırır ve satır güncellendiyse True döner."""
        async with self._connect() as connection:
            cursor = await connection.execute(
                query, {"id": job.id, "attempts": job.attempts, **values}
            )
            return cursor.rowcount == 1
