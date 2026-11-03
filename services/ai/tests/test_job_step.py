"""PostgresJobQueue.record_step'i gerçek Postgres'te test eder (#120).

Yardımcılar test_postgres_queue.py'den gelir; işler db fixture'ının geri alınan transaction'ında
çalışır.
"""

from datetime import timedelta

import pytest

from app.ingest.steps import IngestStep
from tests.test_postgres_queue import (
    PAST,
    STALE_AGE,
    Connection,
    add_job,
    make_queue,
    running_job,
)

READ_STEP = "SELECT last_completed_step, status FROM background_job WHERE id = %s"


async def read_step(connection: Connection, job_id: int) -> tuple[str | None, str]:
    """İşin tamamlanan son adımını ve durumunu okur."""
    cursor = await connection.execute(READ_STEP, (job_id,))
    row = await cursor.fetchone()
    assert row is not None
    return row[0], row[1]


@pytest.mark.asyncio
async def test_record_step_saves_step_and_keeps_job_running(db: Connection) -> None:
    """Yazılan adım işe işlenir, iş RUNNING kalır."""
    queue = make_queue(db)
    await add_job(db)
    [job] = await queue.claim(1)

    assert await queue.record_step(job, IngestStep.REGISTERED)
    assert await read_step(db, job.id) == ("REGISTERED", "RUNNING")


@pytest.mark.asyncio
async def test_failed_job_resumes_after_recorded_step(db: Connection) -> None:
    """Adım yazıldıktan sonra hata veren iş tekrar alınınca adım işle birlikte gelir."""
    queue = make_queue(db)
    await add_job(db)
    [job] = await queue.claim(1)
    await queue.record_step(job, IngestStep.EXTRACT)
    await queue.fail(job, "ValueError: bad page")
    await db.execute("UPDATE background_job SET run_after = %s WHERE id = %s", (PAST, job.id))

    [retried] = await queue.claim(1)

    assert retried.id == job.id
    assert retried.last_completed_step == IngestStep.EXTRACT
    assert retried.attempts == job.attempts + 1


@pytest.mark.asyncio
async def test_previous_owner_cannot_record_step(db: Connection) -> None:
    """İş başkasına geçince eski sahibi adım yazamaz."""
    queue = make_queue(db)
    job_id = await add_job(db, status="RUNNING", attempts=1, age=STALE_AGE)
    [new_owner] = await queue.claim(1)

    assert not await queue.record_step(running_job(job_id, attempts=1), IngestStep.INDEX)
    assert await read_step(db, job_id) == (None, "RUNNING")
    assert await queue.record_step(new_owner, IngestStep.REGISTERED)


@pytest.mark.asyncio
async def test_record_step_refreshes_heartbeat(db: Connection) -> None:
    """Adım yazmak heartbeat gibi işin son güncelleme zamanını yeniler."""
    queue = make_queue(db)
    job_id = await add_job(db, status="RUNNING", attempts=1, age=timedelta(minutes=4))

    assert await queue.record_step(running_job(job_id, attempts=1), IngestStep.REGISTERED)
    cursor = await db.execute(
        "SELECT now() - updated_at FROM background_job WHERE id = %s", (job_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == timedelta(0)


@pytest.mark.asyncio
async def test_record_step_ignores_finished_job(db: Connection) -> None:
    """Bitmiş işe adım yazılmaz."""
    queue = make_queue(db)
    await add_job(db)
    [job] = await queue.claim(1)
    await queue.complete(job)

    assert not await queue.record_step(job, IngestStep.INDEX)
    assert await read_step(db, job.id) == (None, "DONE")
