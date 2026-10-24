"""Yapay zeka servisinin HTTP uygulaması.

Java servisinin çağırdığı iç uç noktalar /internal altında durur ve dışarı açılmaz.
Açılışta ayarlar okunur, log kurulur ve veritabanı havuzu açılır; kapanışta havuz kapanır.
Her isteğin X-Request-Id başlığı o isteğin log kayıtlarına requestId olarak bağlanır.
Başlatma: python -m uvicorn app.main:app (Windows'ta --reload ile; services/ai/AGENTS.md).
"""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.config import get_settings
from app.constants import REQUEST_ID_HEADER
from app.db.pool import close_pool, open_pool
from app.log import bind_request_id, clear_request_context, configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Açılışta log ve veritabanı havuzunu hazırlar, kapanışta havuzu kapatır."""
    settings = get_settings()
    configure_logging(settings.log)
    await open_pool(settings.database)
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(title="ai", lifespan=lifespan)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """İsteğin kimliğini log kayıtlarına bağlar; başlık yoksa yeni kimlik üretir."""
    bind_request_id(request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4()))
    try:
        return await call_next(request)
    finally:
        clear_request_context()


@app.get("/internal/health", status_code=204)
async def health() -> None:
    """Servisin ayakta olduğunu boş cevapla bildirir."""
