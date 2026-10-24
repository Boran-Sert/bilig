"""Bütün testlerde ortak fikstürler.

configure_logging kök logger'ın handler'larını değiştirdiği için, onu çağıran testte pytest'in
caplog'u kayıt görmez; bu testler çıktıyı capsys ile okur.
"""

import logging
from collections.abc import Iterator

import pytest
import structlog

from app.constants import UVICORN_LOGGERS
from app.log import clear_request_context


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """Her testten sonra structlog'u, kök logger'ı ve uvicorn logger'larını eski hâline getirir."""
    root_handlers, root_level = logging.root.handlers[:], logging.root.level
    uvicorn_loggers = [logging.getLogger(name) for name in UVICORN_LOGGERS]
    uvicorn_state = [(log.handlers[:], log.propagate, log.level) for log in uvicorn_loggers]
    yield
    clear_request_context()
    structlog.reset_defaults()
    logging.root.handlers[:] = root_handlers
    logging.root.setLevel(root_level)
    for log, (handlers, propagate, level) in zip(uvicorn_loggers, uvicorn_state, strict=True):
        log.handlers[:] = handlers
        log.propagate = propagate
        log.setLevel(level)
