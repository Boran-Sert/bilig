"""Bütün testlerde ortak fikstürler.

configure_logging kök logger'ın handler'larını değiştirdiği için, onu çağıran testte pytest'in
caplog'u kayıt görmez; bu testler çıktıyı capsys ile okur.

Veritabanı testleri core'un migration'larıyla kurulmuş gerçek Postgres'e bağlanır. PDF dış yüzü
ayar verilmeyince kök listesini WORD_LIST_PATH'ten okur; testlerde bu repodaki listedir.
İç uç noktaların token'ı (INTERNAL_TOKEN) testlerde sabit bir değerdir.
Her test kendi transaction'ında çalışır ve test bitince yaptığı her şey geri alınır.
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Callable, Iterator, Mapping

import psycopg
import pytest
import pytest_asyncio
import structlog
from psycopg.rows import TupleRow

from app.constants import UVICORN_LOGGERS
from app.log import clear_request_context
from tests.word_list import REPOSITORY_WORD_LIST

os.environ.setdefault("WORD_LIST_PATH", str(REPOSITORY_WORD_LIST))
os.environ.setdefault("INTERNAL_TOKEN", "test-internal-token")


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


def pytest_asyncio_loop_factories() -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    """Async testleri psycopg'nin Windows'ta da desteklediği selector döngüsüyle çalıştırır."""
    return {"selector": asyncio.SelectorEventLoop}


@pytest.fixture
def database_url() -> str:
    """Test veritabanının adresini DATABASE_URL ortam değişkeninden okur."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("DATABASE_URL is not set; see services/ai/AGENTS.md")
    return url


@pytest_asyncio.fixture
async def db(database_url: str) -> AsyncIterator[psycopg.AsyncConnection[TupleRow]]:
    """Testi kendi transaction'ında çalıştırır ve test bitince geri alır."""
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        async with connection.transaction(force_rollback=True):
            yield connection
