"""Hazırlık hattının adım sırasını ve kaldığı yerden devam etmeyi test eder."""

import pytest

from app.ingest.steps import IngestStep, remaining_steps

ORDER = [
    "REGISTERED",
    "EXTRACT",
    "VALIDATE",
    "ENTITIES",
    "OUTCOMES",
    "INDEX",
]


def test_steps_follow_the_contract_order() -> None:
    """Adımlar issue'daki ve Java'daki sırayla tanımlıdır."""
    assert [step.value for step in IngestStep] == ORDER


def test_new_job_runs_every_step() -> None:
    """Hiç adımı tamamlanmamış iş bütün adımları çalıştırır."""
    assert remaining_steps(None) == list(IngestStep)


@pytest.mark.parametrize(
    ("last_completed_step", "expected"),
    [
        ("REGISTERED", ORDER[1:]),
        ("EXTRACT", ["VALIDATE", "ENTITIES", "OUTCOMES", "INDEX"]),
        ("OUTCOMES", ["INDEX"]),
        ("INDEX", []),
    ],
)
def test_job_resumes_after_last_completed_step(
    last_completed_step: str, expected: list[str]
) -> None:
    """Yarıda kalan iş tamamlanan son adımdan sonrakiyle devam eder."""
    assert remaining_steps(last_completed_step) == [IngestStep(step) for step in expected]


@pytest.mark.parametrize("last_completed_step", ["", "registered", "OCR", "PROFILE"])
def test_unknown_step_is_an_error(last_completed_step: str) -> None:
    """Tanınmayan adım adı baştan başlatmaz, hata verir."""
    with pytest.raises(ValueError, match="Unknown ingest step"):
        remaining_steps(last_completed_step)
