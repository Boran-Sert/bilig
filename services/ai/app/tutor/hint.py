"""Soru ipucu (plan Bölüm 9, İpucu).

İpucu yayındaki soru için HINT göreviyle üretilir; kaydetmek Java'nın işidir. Doğru şık modele
sadece neyin söylenmeyeceğini bilsin diye verilir; prompt doğru şıkkı ve metnini yazmayı yasaklar.
Soru yayında değilse boş döner.
"""

from app.db.pool import get_pool
from app.db.queries.tutor import fetch_question
from app.llm.runner import run_task
from app.llm.tasks import LlmTask


async def generate_hint(question_id: int) -> str | None:
    """Yayındaki sorunun ipucunu üretir."""
    async with get_pool().connection() as connection:
        question = await fetch_question(connection, question_id)
    if question is None:
        return None
    variables = {
        "question": question.content.to_text(),
        "correct_option": question.correct_option,
    }
    return await run_task(LlmTask.HINT, variables)
