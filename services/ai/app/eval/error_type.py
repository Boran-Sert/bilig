"""ERROR_TYPE görevinin sınıflandırma doğruluğunu ölçer."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from app.constants import PROMPTS_DIR
from app.llm.prompts import prompt_version
from app.llm.runner import run_task
from app.llm.tasks import LlmTask, get_task_configs
from app.schemas.answer_analysis import ErrorType, ErrorTypeAnalysis
from app.schemas.question import OptionLabel


class ErrorTypeControlQuestion(BaseModel):
    """İnsan tarafından etiketlenmiş sentetik hata türü kontrol sorusunu taşır."""

    id: str
    question: str
    options: dict[OptionLabel, str]
    correct_option: OptionLabel
    selected_option: OptionLabel
    expected_error_type: ErrorType


class ErrorTypeScore(BaseModel):
    """Kontrol sorusunun beklenen ve tahmin edilen hata türünü karşılaştırır."""

    id: str
    expected: ErrorType
    predicted: ErrorType
    correct: bool


class ErrorTypeEvalReport(BaseModel):
    """Görev, model, prompt sürümü ve soru bazlı doğruluk ölçümünü taşır."""

    task: LlmTask
    model: str
    prompt_version: int
    created_at: datetime
    accuracy: float
    questions: list[ErrorTypeScore]


def read_control_set(path: Path) -> list[ErrorTypeControlQuestion]:
    """Kontrol setini satır satır okuyup doğrular."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ErrorTypeControlQuestion.model_validate_json(line) for line in lines]


async def score_questions(
    questions: list[ErrorTypeControlQuestion],
) -> list[ErrorTypeScore]:
    """Soruları gerçek ERROR_TYPE görevine gönderip insan etiketleriyle karşılaştırır."""
    scores = []
    for question in questions:
        options = "\n".join(f"{label}) {text}" for label, text in question.options.items())
        analysis = await run_task(
            LlmTask.ERROR_TYPE,
            {
                "question": f"{question.question}\n{options}",
                "correct_option": question.correct_option,
                "selected_option": question.selected_option,
            },
            output_model=ErrorTypeAnalysis,
        )
        scores.append(score(question.id, question.expected_error_type, analysis.error_type))
    return scores


def score(question_id: str, expected: ErrorType, predicted: ErrorType) -> ErrorTypeScore:
    """Soru için kategori tahmininin doğru olup olmadığını hesaplar."""
    return ErrorTypeScore(
        id=question_id, expected=expected, predicted=predicted, correct=expected == predicted
    )


def build_report(created_at: datetime, scores: list[ErrorTypeScore]) -> ErrorTypeEvalReport:
    """Soru sonuçlarının doğruluğunu model ve prompt sürümüyle raporlar."""
    config = get_task_configs()[LlmTask.ERROR_TYPE]
    source = (PROMPTS_DIR / config.prompt).read_text(encoding="utf-8")
    return ErrorTypeEvalReport(
        task=LlmTask.ERROR_TYPE,
        model=config.model,
        prompt_version=prompt_version(config.prompt, source),
        created_at=created_at,
        accuracy=sum(item.correct for item in scores) / len(scores),
        questions=scores,
    )


def write_report(report: ErrorTypeEvalReport, directory: Path) -> Path:
    """Ölçümü görev ve zaman damgası içeren JSON dosyasına yazar."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report.task.lower()}-{report.created_at:%Y%m%dT%H%M%SZ}.json"
    path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def print_report(report: ErrorTypeEvalReport, path: Path) -> None:
    """Soru tahminlerini, doğruluk oranını ve rapor yolunu ekrana yazar."""
    for question in report.questions:
        print(f"{question.id}  expected={question.expected}  predicted={question.predicted}")
    print(f"\n{report.task} · {report.model} · prompt v{report.prompt_version}")
    print(f"accuracy: {report.accuracy:.3f}")
    print(f"report: {path}")


def now_utc() -> datetime:
    """Rapor zaman damgasını UTC olarak döner."""
    return datetime.now(UTC)
