"""HTTP uygulamasının temel uç noktalarını test eder."""

import pytest
from fastapi.testclient import TestClient

from app.config import SettingsError, get_settings
from app.main import app


def test_health_returns_no_content() -> None:
    """Sağlık kontrolü 204 ve boş gövde döner."""
    response = TestClient(app).get("/internal/health")

    assert response.status_code == 204
    assert response.content == b""


def test_startup_stops_with_clear_error_when_setting_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DATABASE_URL yoksa servis açılırken değişkenin adını söyleyerek durur."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(SettingsError, match="DATABASE_URL is missing"), TestClient(app):
        pass

    get_settings.cache_clear()
