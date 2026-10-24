"""Servisin tek async veritabanı bağlantı havuzu.

Havuz uygulama açılırken open_pool ile açılır, kapanırken close_pool ile kapanır;
bağlantı isteyen kod get_pool() kullanır. Her yeni bağlantıya pgvector'ün vector tipi
tanıtılır, bu yüzden veritabanında vector eklentisi kurulu olmalıdır (core migration'ı kurar).
"""

from pgvector.psycopg import register_vector_async
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.config import DatabaseSettings
from app.constants import DB_POOL_MAX_SIZE, DB_POOL_MIN_SIZE, DB_POOL_OPEN_TIMEOUT_SECONDS

_pool: AsyncConnectionPool | None = None


async def open_pool(settings: DatabaseSettings) -> AsyncConnectionPool:
    """Havuzu açar ve ilk bağlantılar kurulana kadar bekler; adres yanlışsa hata verir."""
    global _pool
    if _pool is not None:
        raise RuntimeError("Database pool is already open")
    pool = AsyncConnectionPool(
        str(settings.database_url),
        min_size=DB_POOL_MIN_SIZE,
        max_size=DB_POOL_MAX_SIZE,
        configure=_configure_connection,
        open=False,
    )
    await pool.open(wait=True, timeout=DB_POOL_OPEN_TIMEOUT_SECONDS)
    _pool = pool
    return pool


async def close_pool() -> None:
    """Açık havuzu kapatır; havuz açık değilse bir şey yapmaz."""
    global _pool
    if _pool is None:
        return
    pool, _pool = _pool, None
    await pool.close()


def get_pool() -> AsyncConnectionPool:
    """Açık havuzu döner; havuz açılmadan çağrılırsa hata verir."""
    if _pool is None:
        raise RuntimeError("Database pool is not open; call open_pool first")
    return _pool


async def _configure_connection(connection: AsyncConnection) -> None:
    """Yeni bağlantıya vector tipini tanıtır."""
    await register_vector_async(connection)
