"""PostgresJobQueue'yu gerçek Postgres'te test eder (#114).

Tablo core'un migration'larıyla kurulur. Testlerin çoğu db fixture'ının geri alınan transaction'ında
çalışır; orada now() sabittir, bu yüzden süreler tam değerle karşılaştırılır. İki çalışanın aynı işi
alamadığını ölçen testler ayrı bağlantılar kullanır: diğer bağlantı satırı görebilsin diye işler
commit edilir ve test bitince silinir. Yerel veritabanında gerçek işler olabileceği için test
işlerinin run_after'ı 2000 yılındadır (sırada en öndedir) ve testler sadece kendi işlerine bakar.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
import pytest_asyncio
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.jobs.postgres_queue import ABANDONED_JOB_ERROR, PostgresJobQueue
from app.jobs.queue import Job, JobType

Connection = psycopg.AsyncConnection[TupleRow]

PAST = datetime(2000, 1, 1, tzinfo=UTC)
STALE_AGE = timedelta(minutes=10)
WORKER_COUNT = 4
COMMITTED_JOB_COUNT = 10
LOCK_WAIT_LIMIT_SECONDS = 5

INSERT_JOB = """
INSERT INTO background_job (job_type, payload, status, attempts, run_after, updated_at)
VALUES ('INGEST_SOURCE', %(payload)s, %(status)s, %(attempts)s, %(run_after)s, now() - %(age)s)
RETURNING id
"""

READ_JOB = """
SELECT status, attempts, last_error, run_after - now()
FROM background_job
WHERE id = %s
"""


class SourcePayload(BaseModel):
    """Testte kuyruğa konan iş verisi."""

    source_id: int = Field(alias="sourceId")


def make_queue(connection: Connection) -> PostgresJobQueue:
    """Her çağrıda aynı bağlantıyı kullanan kuyruk kurar."""

    @asynccontextmanager
    async def connect() -> AsyncIterator[Connection]:
        """Verilen bağlantıyı döner."""
        yield connection

    return PostgresJobQueue(connect)


def running_job(job_id: int, attempts: int) -> Job:
    """Belirtilen alım numarasıyla çalışan işi kurar."""
    return Job(
        id=job_id,
        job_type=JobType.INGEST_SOURCE,
        payload={"sourceId": 12},
        last_completed_step=None,
        attempts=attempts,
    )


async def add_job(
    connection: Connection,
    *,
    status: str = "QUEUED",
    attempts: int = 0,
    run_after: datetime = PAST,
    age: timedelta = timedelta(0),
) -> int:
    """İşi SQL ile ekler ve numarasını döner; age son güncellemeden bu yana geçen süredir."""
    values = {
        "payload": Jsonb({"sourceId": 12}),
        "status": status,
        "attempts": attempts,
        "run_after": run_after,
        "age": age,
    }
    cursor = await connection.execute(INSERT_JOB, values)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def read_job(connection: Connection, job_id: int) -> tuple[str, int, str | None, timedelta]:
    """İşin durumunu, deneme sayısını, hatasını ve run_after'ın now()'a uzaklığını okur."""
    cursor = await connection.execute(READ_JOB, (job_id,))
    row = await cursor.fetchone()
    assert row is not None
    return row[0], row[1], row[2], row[3]


async def claimed_ids(queue: PostgresJobQueue) -> set[int]:
    """Alınabilecek bütün işleri alır ve numaralarını döner."""
    return {job.id for job in await queue.claim(100)}


@pytest.mark.asyncio
async def test_enqueue_saves_queued_job_with_camel_case_payload(db: Connection) -> None:
    """Kuyruğa konan iş QUEUED olarak, payload'ı Java'daki gibi camelCase yazılır."""
    job_id = await make_queue(db).enqueue(JobType.INGEST_SOURCE, SourcePayload(sourceId=12))

    cursor = await db.execute(
        "SELECT job_type, status, attempts, payload FROM background_job WHERE id = %s", (job_id,)
    )
    assert await cursor.fetchone() == ("INGEST_SOURCE", "QUEUED", 0, {"sourceId": 12})


@pytest.mark.asyncio
async def test_claim_marks_job_running_and_counts_attempt(db: Connection) -> None:
    """Alınan iş RUNNING olur ve deneme sayısı bir artar."""
    job_id = await add_job(db)

    claimed = await make_queue(db).claim(1)

    assert claimed == [running_job(job_id, attempts=1)]
    assert (await read_job(db, job_id))[:2] == ("RUNNING", 1)


@pytest.mark.asyncio
async def test_claim_skips_job_until_run_after(db: Connection) -> None:
    """run_after'ı gelmemiş iş alınmaz."""
    job_id = await add_job(db, run_after=datetime.now(UTC) + timedelta(hours=1))

    assert job_id not in await claimed_ids(make_queue(db))


@pytest.mark.asyncio
async def test_complete_marks_job_done(db: Connection) -> None:
    """Biten iş DONE olur."""
    queue = make_queue(db)
    await add_job(db)
    [job] = await queue.claim(1)

    assert await queue.complete(job)
    assert (await read_job(db, job.id))[0] == "DONE"


@pytest.mark.asyncio
async def test_fail_requeues_job_and_delays_next_attempt(db: Connection) -> None:
    """Hakkı olan hatalı iş sıraya döner, hatası yazılır ve bir dakika sonraya atılır."""
    queue = make_queue(db)
    await add_job(db)
    [job] = await queue.claim(1)

    assert await queue.fail(job, "ValueError: bad page")
    assert await read_job(db, job.id) == (
        "QUEUED",
        1,
        "ValueError: bad page",
        timedelta(seconds=60),
    )


@pytest.mark.asyncio
async def test_fail_on_last_attempt_marks_job_failed(db: Connection) -> None:
    """Üçüncü denemesinde hata veren iş FAILED olur."""
    queue = make_queue(db)
    await add_job(db, attempts=2)
    [job] = await queue.claim(1)

    assert await queue.fail(job, "ValueError: bad page")
    assert (await read_job(db, job.id))[:3] == ("FAILED", 3, "ValueError: bad page")


@pytest.mark.asyncio
async def test_claim_takes_back_job_without_heartbeat(db: Connection) -> None:
    """Beş dakikadır heartbeat atmayan çalışan iş tekrar alınır."""
    job_id = await add_job(db, status="RUNNING", attempts=1, age=STALE_AGE)

    claimed = await make_queue(db).claim(1)

    assert claimed == [running_job(job_id, attempts=2)]


@pytest.mark.asyncio
async def test_claim_leaves_job_with_recent_heartbeat(db: Connection) -> None:
    """Az önce heartbeat atmış çalışan iş alınmaz."""
    job_id = await add_job(db, status="RUNNING", attempts=1, age=timedelta(minutes=4))

    assert job_id not in await claimed_ids(make_queue(db))


@pytest.mark.asyncio
async def test_claim_fails_job_stopped_on_last_attempt(db: Connection) -> None:
    """Son denemesinde takılan iş tekrar alınmaz, FAILED olur."""
    job_id = await add_job(db, status="RUNNING", attempts=3, age=STALE_AGE)

    assert job_id not in await claimed_ids(make_queue(db))
    assert (await read_job(db, job_id))[:3] == ("FAILED", 3, ABANDONED_JOB_ERROR)


@pytest.mark.asyncio
async def test_previous_owner_cannot_change_job_taken_back(db: Connection) -> None:
    """İş başkasına geçince eski sahibi durumunu değiştiremez."""
    queue = make_queue(db)
    job_id = await add_job(db, status="RUNNING", attempts=1, age=STALE_AGE)
    [new_owner] = await queue.claim(1)
    previous_owner = running_job(job_id, attempts=1)

    assert not await queue.heartbeat(previous_owner)
    assert not await queue.complete(previous_owner)
    assert not await queue.fail(previous_owner, "ValueError: late")
    assert (await read_job(db, job_id))[:3] == ("RUNNING", 2, None)
    assert await queue.heartbeat(new_owner)


@pytest.mark.asyncio
async def test_heartbeat_keeps_job_from_being_taken_back(db: Connection) -> None:
    """Heartbeat atılan iş tekrar alınmaz."""
    queue = make_queue(db)
    job_id = await add_job(db, status="RUNNING", attempts=1, age=STALE_AGE)

    assert await queue.heartbeat(running_job(job_id, attempts=1))
    assert job_id not in await claimed_ids(queue)


@pytest_asyncio.fixture
async def committed_job_ids(database_url: str) -> AsyncIterator[list[int]]:
    """Diğer bağlantılar görebilsin diye işleri commit eder, test bitince siler."""
    async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as connection:
        job_ids = [
            await add_job(connection, run_after=PAST + timedelta(seconds=order))
            for order in range(COMMITTED_JOB_COUNT)
        ]
        try:
            yield job_ids
        finally:
            await connection.execute("DELETE FROM background_job WHERE id = ANY(%s)", (job_ids,))


@pytest.mark.asyncio
async def test_claim_skips_job_locked_by_another_worker(
    database_url: str, committed_job_ids: list[int]
) -> None:
    """Başka çalışanın kilitlediği iş beklenmeden atlanır."""
    first, second = committed_job_ids[:2]
    async with AsyncExitStack() as stack:
        other = await stack.enter_async_context(await psycopg.AsyncConnection.connect(database_url))
        worker = await stack.enter_async_context(
            await psycopg.AsyncConnection.connect(database_url)
        )
        await stack.enter_async_context(other.transaction(force_rollback=True))
        await stack.enter_async_context(worker.transaction(force_rollback=True))
        await other.execute("SELECT id FROM background_job WHERE id = %s FOR UPDATE", (first,))

        claimed = await asyncio.wait_for(make_queue(worker).claim(1), LOCK_WAIT_LIMIT_SECONDS)

    assert [job.id for job in claimed] == [second]


@pytest.mark.asyncio
async def test_concurrent_claims_never_return_same_job(
    database_url: str, committed_job_ids: list[int]
) -> None:
    """Aynı anda iş alan çalışanlara hiçbir iş iki kez verilmez."""
    async with AsyncExitStack() as stack:
        workers = [
            await stack.enter_async_context(await psycopg.AsyncConnection.connect(database_url))
            for _ in range(WORKER_COUNT)
        ]
        for worker in workers:
            await stack.enter_async_context(worker.transaction(force_rollback=True))

        results = await asyncio.wait_for(
            asyncio.gather(*(make_queue(worker).claim(COMMITTED_JOB_COUNT) for worker in workers)),
            LOCK_WAIT_LIMIT_SECONDS,
        )

    claimed = [job.id for jobs in results for job in jobs if job.id in committed_job_ids]
    assert sorted(claimed) == committed_job_ids
