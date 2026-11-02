"""İpucu, anlatım ve sohbetin iç uçları (plan Bölüm 9, 13.5).

POST /internal/hints ipucunu JSON döner. POST /internal/explanations ve POST /internal/chat
cevabı text/event-stream olarak akıtır. Bağlam ve kaynaklar akış başlamadan okunur ve bağlantı
havuza döner; Claude çağrısı sırasında veritabanı bağlantısı tutulmaz. Soru, öğrenci ya da sohbet
bulunamazsa 404, sohbetin son mesajı öğrenciden değilse 409 döner. Bütün uçlar iç token ister.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.security import require_internal_token
from app.constants import SSE_MEDIA_TYPE
from app.db.pool import get_pool
from app.schemas.tutor import ChatRequest, ExplanationRequest, HintRequest, HintResponse
from app.tutor.chat import NoUserMessageError, prepare_chat
from app.tutor.explanation import prepare_explanation
from app.tutor.hint import generate_hint
from app.tutor.stream import PreparedStream, stream_events

router = APIRouter(prefix="/internal", dependencies=[Depends(require_internal_token)])


@router.post("/hints")
async def hint(request: HintRequest) -> HintResponse:
    """Sorunun ipucunu üretir."""
    text = await generate_hint(request.question_id)
    if text is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return HintResponse(hint=text)


@router.post("/explanations")
async def explanation(request: ExplanationRequest) -> StreamingResponse:
    """Neden yanlış anlatımını akış olarak döner."""
    async with get_pool().connection() as connection:
        prepared = await prepare_explanation(connection, request)
    return event_stream(prepared)


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Sohbetin yeni cevabını akış olarak döner."""
    try:
        async with get_pool().connection() as connection:
            prepared = await prepare_chat(connection, request)
    except NoUserMessageError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from error
    return event_stream(prepared)


def event_stream(prepared: PreparedStream | None) -> StreamingResponse:
    """Hazır görevi SSE cevabına çevirir; görev yoksa 404 verir."""
    if prepared is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StreamingResponse(stream_events(prepared), media_type=SSE_MEDIA_TYPE)
