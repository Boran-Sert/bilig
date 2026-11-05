"""Kaynaklı sohbetin hazırlığı (plan Bölüm 9, Sohbet).

Java öğrencinin mesajını kaydettikten sonra sohbetin numarasıyla çağırır; geçmiş tutor_message'dan
okunur ve son mesaj öğrencinin sorusudur. Sohbet bir soru için açıldıysa kaynak araması o sorunun
kazanımlarında, açılmadıysa bütün yayındaki paragraflarda yapılır. Sohbet öğrencinin değilse boş
döner; son mesaj öğrenciden değilse hata verir. Model cevap verirken okuma tool'larını
(app/tutor/tools.py) en fazla llm_tasks.yaml'daki sınır kadar çağırabilir.
"""

from psycopg import AsyncConnection

from app.db.queries.tutor import fetch_conversation, fetch_explain_style, fetch_question
from app.llm.tasks import LlmTask
from app.schemas.tutor import ChatRequest
from app.tutor.stream import PreparedStream, find_sources

USER_ROLE = "USER"


class NoUserMessageError(ValueError):
    """Sohbetin son mesajı öğrenciden değil."""


async def prepare_chat(connection: AsyncConnection, request: ChatRequest) -> PreparedStream | None:
    """Sohbetin geçmişini, son sorusunu ve kaynaklarını toplar."""
    conversation = await fetch_conversation(connection, request.conversation_id, request.user_id)
    style = await fetch_explain_style(connection, request.user_id)
    if conversation is None or style is None:
        return None
    question_id, turns = conversation
    if not turns or turns[-1].role != USER_ROLE:
        raise NoUserMessageError(f"Conversation {request.conversation_id} has no new message")
    question = None if question_id is None else await fetch_question(connection, question_id)
    outcome_ids = None if question is None else [outcome.id for outcome in question.outcomes]
    message = turns[-1].content
    sources = await find_sources(connection, message, outcome_ids or None)
    variables = {
        "question": "" if question is None else question.content.to_text(),
        "correct_option": "" if question is None else question.correct_option,
        "history": turns[:-1],
        "message": message,
        "style": style.value,
    }
    return PreparedStream(
        task=LlmTask.CHAT, variables=variables, sources=sources, user_id=request.user_id
    )
