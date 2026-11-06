"""ANALYZE_ANSWER işini sınıflandırır ve sonucu veritabanına kaydeder."""

from pydantic import BaseModel, ConfigDict, Field

from app.db.pool import get_pool
from app.db.queries.answer_analysis import fetch_answer_for_analysis, save_answer_analysis
from app.jobs.queue import Job
from app.llm.runner import run_task
from app.llm.tasks import LlmTask
from app.schemas.answer_analysis import ErrorTypeAnalysis


class AnalyzeAnswerPayload(BaseModel):
    """Java'dan gelen yanlış cevap kimliğini camelCase biçiminde taşır."""

    model_config = ConfigDict(populate_by_name=True)

    student_answer_id: int = Field(alias="studentAnswerId")


async def run_analyze_answer(job: Job) -> None:
    """Yanlış cevabı kişisel veri göndermeden sınıflandırır ve sonucunu kaydeder."""
    payload = AnalyzeAnswerPayload.model_validate(job.payload)
    async with get_pool().connection() as connection:
        answer = await fetch_answer_for_analysis(connection, payload.student_answer_id)
    if answer is None:
        return

    analysis = await run_task(
        LlmTask.ERROR_TYPE,
        {
            "question": answer.content.to_text(),
            "selected_option": answer.selected_option,
            "correct_option": answer.correct_option,
        },
        output_model=ErrorTypeAnalysis,
        user_id=answer.user_id,
    )
    async with get_pool().connection() as connection:
        await save_answer_analysis(connection, payload.student_answer_id, analysis)
