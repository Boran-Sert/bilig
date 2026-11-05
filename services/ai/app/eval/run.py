"""LLM görevlerinin kontrol setlerinde doğruluk ölçümü.

Komutlar: uv run python -m app.eval.run --task OUTCOME_MATCH ve
uv run python -m app.eval.run --task ERROR_TYPE. Her görev gerçek Claude çağrısı yapar, sonuçları
model ve prompt sürümüyle data/eval altına yazar ve CI'da çalışmaz. OUTCOME_MATCH, program ve
ünitelerin veritabanında yüklü olmasını ister; vektörü olmayan kazanımların vektörü
hesaplanır, soru ve bağ yazılmaz.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from psycopg import AsyncConnection
from pydantic import BaseModel

from app.config import LogSettings, get_settings
from app.constants import (
    CONTROL_SET_GRADE,
    CONTROL_SET_PATH,
    CONTROL_SET_UNIT_TITLES,
    ERROR_TYPE_CONTROL_SET_PATH,
    EVAL_OUTPUT_DIR,
    PROGRAM_CURRICULUM_NAME,
    PROGRAM_SUBJECT_CODE,
    PROMPTS_DIR,
)
from app.db.pool import close_pool, open_pool
from app.db.queries.outcomes import question_item
from app.eval import error_type
from app.ingest.outcomes import embed_missing_outcomes, match_outcomes
from app.llm.prompts import prompt_version
from app.llm.tasks import LlmTask, get_task_configs
from app.log import configure_logging
from app.schemas.question import Block, OptionLabel, QuestionContent, QuestionOption

SELECT_UNITS = """
SELECT curriculum_unit.title, curriculum_unit.id
FROM curriculum_unit
JOIN curriculum ON curriculum.id = curriculum_unit.curriculum_id
JOIN subject ON subject.id = curriculum.subject_id
WHERE subject.code = %(subject_code)s
    AND curriculum.name = %(curriculum_name)s
    AND curriculum_unit.grade = %(grade)s
"""


class ControlQuestion(BaseModel):
    """Kontrol setinin bir sorusu ve insanın işaretlediği kazanımlar."""

    id: str
    unit: str
    stem: str
    options: dict[OptionLabel, str]
    correct: OptionLabel
    outcomes: list[str]


class QuestionScore(BaseModel):
    """Bir sorunun beklenen ve seçilen kazanımları, kesinliği ve duyarlılığı."""

    id: str
    expected: list[str]
    predicted: list[str]
    precision: float
    recall: float
    needs_review: bool


class EvalReport(BaseModel):
    """Ölçümün görevi, modeli, prompt sürümü, ortalamaları ve soru sonuçları."""

    task: LlmTask
    model: str
    prompt_version: int
    created_at: datetime
    precision: float
    recall: float
    questions: list[QuestionScore]


def main(argv: list[str] | None = None) -> None:
    """Komut satırından ölçümü çalıştırır, sonucu ekrana ve dosyaya yazar."""
    parser = argparse.ArgumentParser(description="Measure AI tasks on their control sets.")
    parser.add_argument(
        "--task", type=LlmTask, choices=[LlmTask.OUTCOME_MATCH, LlmTask.ERROR_TYPE], required=True
    )
    parser.add_argument("--control-set", type=Path)
    parser.add_argument("--output-dir", type=Path, default=EVAL_OUTPUT_DIR)
    arguments = parser.parse_args(argv)
    configure_logging(LogSettings())
    if arguments.task == LlmTask.ERROR_TYPE:
        evaluate_error_types(
            arguments.control_set or ERROR_TYPE_CONTROL_SET_PATH, arguments.output_dir
        )
        return
    evaluate_outcomes(arguments.control_set or CONTROL_SET_PATH, arguments.output_dir)


def evaluate_error_types(control_set: Path, output_dir: Path) -> None:
    """Hata türü kontrol setini çalıştırır ve sınıflandırma raporunu yazar."""
    questions = error_type.read_control_set(control_set)
    scores = asyncio.run(
        error_type.score_questions(questions), loop_factory=asyncio.SelectorEventLoop
    )
    report = error_type.build_report(error_type.now_utc(), scores)
    path = error_type.write_report(report, output_dir)
    error_type.print_report(report, path)


def evaluate_outcomes(control_set: Path, output_dir: Path) -> None:
    """Kazanım kontrol setini çalıştırır ve eşleştirme raporunu yazar."""
    questions = read_control_set(control_set)
    scores = asyncio.run(score_questions(questions), loop_factory=asyncio.SelectorEventLoop)
    report = build_report(LlmTask.OUTCOME_MATCH, datetime.now(UTC), scores)
    path = write_report(report, output_dir)
    print_report(report, path)


def read_control_set(path: Path) -> list[ControlQuestion]:
    """Kontrol setini satır satır okur."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ControlQuestion.model_validate_json(line) for line in lines]


async def score_questions(questions: list[ControlQuestion]) -> list[QuestionScore]:
    """Her soruyu eşleştirmeden geçirir ve işaretlenen kazanımlarla karşılaştırır."""
    pool = await open_pool(get_settings().database)
    try:
        async with pool.connection() as connection:
            await embed_missing_outcomes(connection)
            unit_ids = await fetch_unit_ids(connection)
            return [await score_question(connection, item, unit_ids) for item in questions]
    finally:
        await close_pool()


async def fetch_unit_ids(connection: AsyncConnection) -> dict[str, int]:
    """Kontrol setinin ünite adlarını programdaki 12. sınıf ünitelerinin kimliklerine çevirir."""
    values = {
        "subject_code": PROGRAM_SUBJECT_CODE,
        "curriculum_name": PROGRAM_CURRICULUM_NAME,
        "grade": CONTROL_SET_GRADE,
    }
    cursor = await connection.execute(SELECT_UNITS, values)
    by_title = {row[0]: row[1] for row in await cursor.fetchall()}
    missing = sorted(set(CONTROL_SET_UNIT_TITLES.values()) - by_title.keys())
    if missing:
        raise ValueError(f"Units not found in curriculum: {', '.join(missing)}")
    return {unit: by_title[title] for unit, title in CONTROL_SET_UNIT_TITLES.items()}


async def score_question(
    connection: AsyncConnection, question: ControlQuestion, unit_ids: dict[str, int]
) -> QuestionScore:
    """Soruyu pipeline'daki metinle eşleştirir ve sonucunu puanlar."""
    content = QuestionContent(
        stem=[Block(type="paragraph", md=question.stem)],
        options=[
            QuestionOption(label=label, blocks=[Block(type="paragraph", md=text)])
            for label, text in question.options.items()
        ],
    )
    item = question_item(content, question.correct, unit_ids[question.unit])
    choice = await match_outcomes(connection, item)
    predicted = [outcome.code for outcome in choice.outcomes]
    return score(question.id, question.outcomes, predicted, choice.needs_review)


def score(
    question_id: str, expected: list[str], predicted: list[str], needs_review: bool
) -> QuestionScore:
    """Seçilen kazanımların kesinliğini ve duyarlılığını hesaplar."""
    correct = len(set(expected) & set(predicted))
    return QuestionScore(
        id=question_id,
        expected=expected,
        predicted=predicted,
        precision=correct / len(set(predicted)) if predicted else 0.0,
        recall=correct / len(set(expected)),
        needs_review=needs_review,
    )


def build_report(task: LlmTask, created_at: datetime, scores: list[QuestionScore]) -> EvalReport:
    """Soru sonuçlarının ortalamasını görevin modeli ve prompt sürümüyle birleştirir."""
    config = get_task_configs()[task]
    source = (PROMPTS_DIR / config.prompt).read_text(encoding="utf-8")
    return EvalReport(
        task=task,
        model=config.model,
        prompt_version=prompt_version(config.prompt, source),
        created_at=created_at,
        precision=sum(item.precision for item in scores) / len(scores),
        recall=sum(item.recall for item in scores) / len(scores),
        questions=scores,
    )


def write_report(report: EvalReport, directory: Path) -> Path:
    """Sonucu görev adı ve zamanla adlandırılmış JSON dosyasına yazar."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report.task.lower()}-{report.created_at:%Y%m%dT%H%M%SZ}.json"
    path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def print_report(report: EvalReport, path: Path) -> None:
    """Soru sonuçlarını ve ortalamaları ekrana yazar."""
    for item in report.questions:
        review = " review" if item.needs_review else ""
        print(
            f"{item.id}  P={item.precision:.2f} R={item.recall:.2f}  "
            f"expected={','.join(item.expected)}  predicted={','.join(item.predicted)}{review}"
        )
    print(f"\n{report.task} · {report.model} · prompt v{report.prompt_version}")
    print(f"mean precision: {report.precision:.3f}")
    print(f"mean recall: {report.recall:.3f}")
    print(f"report: {path}")


if __name__ == "__main__":
    main()
