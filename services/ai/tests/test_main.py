"""HTTP uygulamasının açılışını, istek kimliğini ve temel uç noktalarını test eder."""

import uuid
from collections.abc import Iterator

import pytest
import structlog
from fastapi import Request, Response
from fastapi.testclient import TestClient

from app import main
from app.config import DatabaseSettings, SettingsError, get_settings
from app.main import app, request_context

DATABASE_URL = "postgresql://app:secret@localhost:5432/hata_analizi"


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    """Her test ayarları ortam değişkenlerinden yeniden okur."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


@pytest.fixture
def pool_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Havuzun açılıp kapanmasını gerçek bağlantı kurmadan kaydeder."""
    calls: list[str] = []

    async def fake_open(settings: DatabaseSettings) -> None:
        """Açılışı adresiyle kaydeder."""
        calls.append(f"open {settings.database_url}")

    async def fake_close() -> None:
        """Kapanışı kaydeder."""
        calls.append("close")

    monkeypatch.setattr(main, "open_pool", fake_open)
    monkeypatch.setattr(main, "close_pool", fake_close)
    return calls


def test_health_returns_no_content() -> None:
    """Sağlık kontrolü 204 ve boş gövde döner."""
    response = TestClient(app).get("/internal/health")

    assert response.status_code == 204
    assert response.content == b""


def test_startup_opens_and_shutdown_closes_pool(
    monkeypatch: pytest.MonkeyPatch, pool_calls: list[str]
) -> None:
    """Havuz açılışta ayardaki adresle açılır, kapanışta kapanır."""
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)

    with TestClient(app) as client:
        assert pool_calls == [f"open {DATABASE_URL}"]
        assert client.get("/internal/health").status_code == 204

    assert pool_calls == [f"open {DATABASE_URL}", "close"]


def test_startup_stops_with_clear_error_when_setting_missing(
    monkeypatch: pytest.MonkeyPatch, pool_calls: list[str]
) -> None:
    """DATABASE_URL yoksa servis açılırken değişkenin adını söyleyerek durur ve havuz açılmaz."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SettingsError, match="DATABASE_URL is missing"), TestClient(app):
        pass

    assert pool_calls == []


def make_request(headers: list[tuple[bytes, bytes]]) -> Request:
    """Verilen başlıklarla en küçük HTTP isteğini üretir."""
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


@pytest.mark.asyncio
async def test_request_id_header_is_bound_during_request() -> None:
    """X-Request-Id başlığı istek süresince log alanı olarak bağlıdır, sonra temizlenir."""
    seen: dict[str, object] = {}

    async def call_next(_: Request) -> Response:
        """İstek sırasındaki log alanlarını kaydeder."""
        seen.update(structlog.contextvars.get_contextvars())
        return Response(status_code=204)

    response = await request_context(make_request([(b"x-request-id", b"req-7")]), call_next)

    assert response.status_code == 204
    assert seen["requestId"] == "req-7"
    assert structlog.contextvars.get_contextvars() == {}


@pytest.mark.asyncio
async def test_request_id_is_generated_when_header_missing() -> None:
    """Başlık yoksa isteğe yeni bir UUID atanır."""
    seen: dict[str, object] = {}

    async def call_next(_: Request) -> Response:
        """İstek sırasındaki log alanlarını kaydeder."""
        seen.update(structlog.contextvars.get_contextvars())
        return Response(status_code=204)

    await request_context(make_request([]), call_next)

    assert uuid.UUID(str(seen["requestId"]))


@pytest.mark.asyncio
async def test_request_context_is_cleared_when_handler_fails() -> None:
    """İstek hata verse de bağlanan alanlar temizlenir ve hata yutulmaz."""

    async def call_next(_: Request) -> Response:
        """İşleyici hatasını taklit eder."""
        raise ValueError("handler failed")

    with pytest.raises(ValueError, match="handler failed"):
        await request_context(make_request([(b"x-request-id", b"req-8")]), call_next)

    assert structlog.contextvars.get_contextvars() == {}
