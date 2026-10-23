"""Ortam değişkenlerinden ayar okumayı test eder."""

import pytest

from app.config import SettingsError, get_settings, load_settings

DATABASE_URL = "postgresql://app:secret@localhost:5432/hata_analizi"


def test_load_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ortam değişkenleri kendi bloklarına okunur."""
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = load_settings()

    assert str(settings.database.database_url) == DATABASE_URL
    assert settings.log.log_level == "WARNING"


def test_load_settings_uses_default_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    """LOG_LEVEL verilmezse INFO kullanılır."""
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert load_settings().log.log_level == "INFO"


def test_load_settings_names_missing_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Eksik ayar, değişkenin adını söyleyen hatayla durur."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SettingsError, match="DATABASE_URL is missing"):
        load_settings()


def test_load_settings_names_invalid_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hatalı ayar, değişkenin adını söyleyen hatayla durur."""
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("LOG_LEVEL", "LOUD")

    with pytest.raises(SettingsError, match="LOG_LEVEL is invalid"):
        load_settings()


def test_load_settings_rejects_non_postgres_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Postgres olmayan bağlantı adresi kabul edilmez."""
    monkeypatch.setenv("DATABASE_URL", "mysql://app@localhost/db")

    with pytest.raises(SettingsError, match="DATABASE_URL is invalid"):
        load_settings()


def test_get_settings_reads_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ayarlar bir kez okunur; sonraki çağrılar aynı nesneyi döner."""
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    get_settings.cache_clear()

    first = get_settings()
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    assert get_settings() is first
    get_settings.cache_clear()
