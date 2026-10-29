"""İş kuyruğu sözleşmesi (plan 13.12).

Çalışan sadece JobQueue'yu bilir; şimdiki uygulama PostgresJobQueue'dur. İşin durumu her zaman
background_job tablosunda kalır. attempts her alımda bir artar ve o alımın sahiplik numarasıdır:
heartbeat, complete ve fail sadece iş hâlâ aynı numarayla çalışıyorsa yazar, değilse False döner.
Böylece iş başka çalışana geçtiyse eski çalışan durumu ezemez. İş türleri Java'daki JobType ile
aynıdır.
"""

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, JsonValue


class JobType(StrEnum):
    """background_job.job_type kolonunun kabul ettiği iş türleri."""

    INGEST_SOURCE = "INGEST_SOURCE"
    BUILD_PROGRAM = "BUILD_PROGRAM"
    EXTRACT_ENTITIES = "EXTRACT_ENTITIES"
    MATCH_OUTCOMES = "MATCH_OUTCOMES"
    EMBED = "EMBED"
    GENERATE_QUESTIONS = "GENERATE_QUESTIONS"
    ANALYZE_ANSWER = "ANALYZE_ANSWER"


class Job(BaseModel):
    """Çalışanın aldığı iş; attempts bu alımın sahiplik numarasıdır."""

    id: int
    job_type: JobType
    payload: dict[str, JsonValue]
    last_completed_step: str | None
    attempts: int


class JobQueue(Protocol):
    """İş kuyruğu sözleşmesi; çalışan sadece bunu bilir."""

    async def enqueue(self, job_type: JobType, payload: BaseModel) -> int:
        """Yeni işi kaydeder ve sıraya koyar."""

    async def claim(self, limit: int) -> list[Job]:
        """Sıradaki işleri alır ve başkası almasın diye kilitler."""

    async def heartbeat(self, job: Job) -> bool:
        """İşin hâlâ çalıştığını bildirir; iş başkasına geçtiyse False döner."""

    async def complete(self, job: Job) -> bool:
        """İşi bitmiş olarak işaretler; iş başkasına geçtiyse False döner."""

    async def fail(self, job: Job, error: str) -> bool:
        """İşi hatalı işaretler, hakkı varsa sıraya koyar; iş başkasına geçtiyse False döner."""
