"""Hazırlık hattının adımları (plan Bölüm 6, 13.12).

Yüklenen her kaynak bu adımları bu sırayla geçer; sıra Java'daki IngestStep ile aynıdır.
background_job.last_completed_step tamamlanan son adımın adını taşır; yarıda kalan iş, ondan
sonraki adımdan devam eder. Adı tanınmayan kayıt hatadır: sessizce baştan başlamak, yapılmış
adımları ikinci kez çalıştırır.
"""

from enum import StrEnum


class IngestStep(StrEnum):
    """Hazırlık hattının adımları, çalışma sırasıyla."""

    REGISTERED = "REGISTERED"
    TEXT_LAYER = "TEXT_LAYER"
    PROFILE = "PROFILE"
    EXTRACT = "EXTRACT"
    VALIDATE = "VALIDATE"
    ENTITIES = "ENTITIES"
    OUTCOMES = "OUTCOMES"
    INDEX = "INDEX"


def remaining_steps(last_completed_step: str | None) -> list[IngestStep]:
    """Tamamlanan son adımdan sonra çalışacak adımları sırayla döner; hiç adım yoksa hepsini."""
    steps = list(IngestStep)
    if last_completed_step is None:
        return steps
    try:
        done = IngestStep(last_completed_step)
    except ValueError as error:
        raise ValueError(f"Unknown ingest step {last_completed_step!r}") from error
    return steps[steps.index(done) + 1 :]
