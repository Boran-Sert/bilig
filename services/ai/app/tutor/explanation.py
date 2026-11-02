"""Neden yanlış: alıntılı anlatımın hazırlığı (plan Bölüm 9, "Neden yanlış?" adım adım).

Bağlam soru, öğrencinin şıkkı, doğru şık, sorunun bütün kazanımları ve MEB açıklamaları ile
öğrencinin anlatım tarzıdır. Kaynak araması soru kökü ve doğru şıkla yapılır; sadece sorunun
kazanımlarına bağlı paragraflarda aranır. Soru yayında değilse ya da öğrenci yoksa boş döner.
"""

from psycopg import AsyncConnection

from app.db.queries.tutor import fetch_explain_style, fetch_question
from app.llm.tasks import LlmTask
from app.schemas.tutor import ExplanationRequest, TutorQuestion
from app.tutor.stream import PreparedStream, find_sources


async def prepare_explanation(
    connection: AsyncConnection, request: ExplanationRequest
) -> PreparedStream | None:
    """Anlatımın değişkenlerini ve kaynaklarını toplar."""
    question = await fetch_question(connection, request.question_id)
    style = await fetch_explain_style(connection, request.user_id)
    if question is None or style is None:
        return None
    outcome_ids = [outcome.id for outcome in question.outcomes] or None
    sources = await find_sources(connection, explanation_query(question), outcome_ids)
    variables = {
        "question": question.content.to_text(),
        "selected_option": request.selected_option,
        "correct_option": question.correct_option,
        "outcomes": question.outcomes,
        "style": style.value,
    }
    return PreparedStream(
        task=LlmTask.TOPIC_EXPLAIN, variables=variables, sources=sources, user_id=request.user_id
    )


def explanation_query(question: TutorQuestion) -> str:
    """Soru kökü ve doğru şıktan arama sorgusunu kurar."""
    content = question.content
    correct = next(option for option in content.options if option.label == question.correct_option)
    return "\n".join(block.md for block in [*content.stem, *correct.blocks])
