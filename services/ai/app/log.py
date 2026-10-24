"""structlog ile JSON log ayarı.

Her kayıt tek satırlık bir JSON nesnesidir ve Java servisiyle aynı ortak alanları taşır:
timestamp, level, service, requestId, message (plan 13.14). requestId, isteğin başında
bind_request_id ile bağlanır ve aynı istekteki bütün kayıtlara kendiliğinden eklenir.
uvicorn ve psycopg_pool gibi standart logging kullanan kütüphanelerin kayıtları da aynı
işlemcilerden geçip aynı JSON biçimiyle yazılır. Ayar lifespan'de kurulduğu için uvicorn'un
açılıştaki ilk iki satırı düz metindir ve uvicorn'a verilen --log-level yerine LOG_LEVEL geçerlidir.
"""

import logging
import sys

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

from app.config import LogSettings
from app.constants import SERVICE_NAME, UVICORN_LOGGERS


def configure_logging(settings: LogSettings) -> None:
    """Uygulama ve standart logging kayıtlarını JSON biçimi ve ayardaki seviyeyle kurar."""
    level = logging.getLevelNamesMapping()[settings.log_level]
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _uppercase_level,
        _add_service,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        structlog.processors.format_exc_info,
    ]
    rendering: list[Processor] = [
        structlog.processors.EventRenamer("message"),
        structlog.processors.JSONRenderer(ensure_ascii=False),
    ]
    structlog.configure(
        processors=[*shared, *rendering],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.WriteLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    _route_standard_logging(level, shared, rendering)


def bind_request_id(request_id: str) -> None:
    """İsteğin kimliğini bu isteğin bütün log kayıtlarına bağlar."""
    structlog.contextvars.bind_contextvars(requestId=request_id)


def clear_request_context() -> None:
    """İstek bitince bağlanmış alanları temizler."""
    structlog.contextvars.clear_contextvars()


def _route_standard_logging(
    level: int, shared: list[Processor], rendering: list[Processor]
) -> None:
    """Kök logger'a JSON yazan tek handler kurar ve uvicorn logger'larını ona bağlar."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *rendering],
        )
    )
    logging.basicConfig(handlers=[handler], level=level, force=True)
    for name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.setLevel(logging.NOTSET)
        uvicorn_logger.propagate = True


def _uppercase_level(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Seviye adını Java tarafıyla aynı biçimde büyük harfe çevirir."""
    event_dict["level"] = event_dict["level"].upper()
    return event_dict


def _add_service(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Kayda servis adını ekler."""
    event_dict["service"] = SERVICE_NAME
    return event_dict
