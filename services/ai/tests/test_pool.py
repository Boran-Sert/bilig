"""Veritabanı havuzunun açılıp kapanmasını sahte havuzla test eder.

Gerçek bağlantı açılmaz; havuzun hangi ayarlarla kurulduğu ve yaşam döngüsü ölçülür.
Gerçek Postgres'e bağlanan test #97'nin db fixture'ıyla eklenir.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.config import DatabaseSettings
from app.constants import DB_POOL_MAX_SIZE, DB_POOL_MIN_SIZE, DB_POOL_OPEN_TIMEOUT_SECONDS
from app.db import pool as pool_module
from app.db.pool import close_pool, get_pool, open_pool

DATABASE_URL = "postgresql://app:secret@localhost:5432/hata_analizi"


class FakePool:
    """AsyncConnectionPool yerine geçen, çağrıları kaydeden sahte havuz."""

    instances: list["FakePool"] = []

    def __init__(self, conninfo: str, **kwargs: Any) -> None:
        """Kurulum argümanlarını kaydeder."""
        self.conninfo = conninfo
        self.kwargs = kwargs
        self.open_calls: list[tuple[bool, float]] = []
        self.closed = False
        FakePool.instances.append(self)

    async def open(self, wait: bool = False, timeout: float = 30.0) -> None:
        """Açılış çağrısını kaydeder."""
        self.open_calls.append((wait, timeout))

    async def close(self) -> None:
        """Kapanışı kaydeder."""
        self.closed = True


@pytest.fixture(autouse=True)
def fake_pool(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Gerçek havuzu sahtesiyle değiştirir ve her testi kapalı havuzla başlatır."""
    FakePool.instances = []
    monkeypatch.setattr(pool_module, "AsyncConnectionPool", FakePool)
    monkeypatch.setattr(pool_module, "_pool", None)
    yield


def settings() -> DatabaseSettings:
    """Test için veritabanı ayarı üretir."""
    return DatabaseSettings(database_url=DATABASE_URL)


@pytest.mark.asyncio
async def test_open_pool_uses_settings_and_waits_for_connections() -> None:
    """Havuz ayardaki adresle, sabit boyutlarla kurulur ve bağlantılar beklenerek açılır."""
    pool = await open_pool(settings())

    assert isinstance(pool, FakePool)
    assert pool.conninfo == DATABASE_URL
    assert pool.kwargs["min_size"] == DB_POOL_MIN_SIZE
    assert pool.kwargs["max_size"] == DB_POOL_MAX_SIZE
    assert pool.kwargs["open"] is False
    assert pool.kwargs["configure"] is pool_module._configure_connection
    assert pool.open_calls == [(True, DB_POOL_OPEN_TIMEOUT_SECONDS)]


@pytest.mark.asyncio
async def test_get_pool_returns_open_pool() -> None:
    """Açık havuz get_pool ile alınır."""
    pool = await open_pool(settings())

    assert get_pool() is pool


def test_get_pool_fails_before_open() -> None:
    """Havuz açılmadan get_pool anlaşılır hata verir."""
    with pytest.raises(RuntimeError, match="not open"):
        get_pool()


@pytest.mark.asyncio
async def test_open_pool_twice_fails() -> None:
    """Açık havuz ikinci kez açılamaz ve ikinci havuz kurulmaz."""
    await open_pool(settings())

    with pytest.raises(RuntimeError, match="already open"):
        await open_pool(settings())
    assert len(FakePool.instances) == 1


@pytest.mark.asyncio
async def test_close_pool_closes_and_forgets_pool() -> None:
    """Kapanan havuz bir daha get_pool ile alınamaz."""
    pool = await open_pool(settings())

    await close_pool()

    assert isinstance(pool, FakePool)
    assert pool.closed
    with pytest.raises(RuntimeError, match="not open"):
        get_pool()


@pytest.mark.asyncio
async def test_close_pool_without_open_pool_does_nothing() -> None:
    """Açık havuz yokken close_pool hata vermez."""
    await close_pool()


@pytest.mark.asyncio
async def test_failed_open_leaves_no_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Açılış hata verirse havuz açık sayılmaz."""

    async def failing_open(self: FakePool, wait: bool = False, timeout: float = 30.0) -> None:
        """Bağlantı kurulamamış gibi hata verir."""
        raise TimeoutError("could not connect")

    monkeypatch.setattr(FakePool, "open", failing_open)

    with pytest.raises(TimeoutError):
        await open_pool(settings())
    with pytest.raises(RuntimeError, match="not open"):
        get_pool()


@pytest.mark.asyncio
async def test_configure_connection_registers_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    """Her yeni bağlantıya vector tipi tanıtılır."""
    registered: list[object] = []

    async def fake_register(connection: object) -> None:
        """Tanıtılan bağlantıyı kaydeder."""
        registered.append(connection)

    monkeypatch.setattr(pool_module, "register_vector_async", fake_register)
    connection = object()

    await pool_module._configure_connection(connection)

    assert registered == [connection]
