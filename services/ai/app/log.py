"""structlog ile JSON log ayarı.

Her kayıt tek satırlık bir JSON nesnesidir ve Java servisiyle aynı ortak alanları taşır:
timestamp, level, service, requestId, message (plan 13.14). requestId, isteğin başında
bind_request_id ile bağlanır ve aynı istekteki bütün kayıtlara kendiliğinden eklenir.
"""

import logging
import sys

import structlog
from structlog.typing import EventDict, WrappedLogger

from app.config import LogSettings
from app.constants import SERVICE_NAME


def configure_logging(settings: LogSettings) -> None:
    """Log çıktısını JSON biçimi ve ayardaki seviyeyle kurar."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _uppercase_level,
            _add_service,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.format_exc_info,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level]
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )


def bind_request_id(request_id: str) -> None:
    """İsteğin kimliğini bu isteğin bütün log kayıtlarına bağlar."""
    structlog.contextvars.bind_contextvars(requestId=request_id)


def clear_request_context() -> None:
    """İstek bitince bağlanmış alanları temizler."""
    structlog.contextvars.clear_contextvars()


def _uppercase_level(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Seviye adını Java tarafıyla aynı biçimde büyük harfe çevirir."""
    event_dict["level"] = event_dict["level"].upper()
    return event_dict


def _add_service(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Kayda servis adını ekler."""
    event_dict["service"] = SERVICE_NAME
    return event_dict
