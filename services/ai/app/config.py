"""Ortam değişkenlerinden okunan servis ayarları.

Her özelliğin ayarları kendi bloğundadır; yeni ayar kendi bloğuna eklenir ve
.env.example'a yazılır. Ayar sadece ortam değişkeninden okunur, .env dosyası okunmaz.
Eksik ya da hatalı ayarda servis açılırken hangi değişkenin sorunlu olduğunu söyleyen
SettingsError ile durur. Sadece bir sürecin kullandığı blok (IngestSettings) Settings'e
konmaz, kendi load_ fonksiyonuyla okunur.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, PostgresDsn, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsError(RuntimeError):
    """Eksik ya da hatalı ortam değişkenlerini adlarıyla bildirir."""


class DatabaseSettings(BaseSettings):
    """Veritabanı bağlantı ayarları."""

    model_config = SettingsConfigDict(extra="ignore")

    database_url: PostgresDsn


class LogSettings(BaseSettings):
    """Log ayarları."""

    model_config = SettingsConfigDict(extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class IngestSettings(BaseSettings):
    """ai-worker'ın hazırlık hattı ayarları; ai-api kullanmadığı için Settings'te değildir."""

    model_config = SettingsConfigDict(extra="ignore")

    word_list_path: Path


class Settings(BaseModel):
    """Servisin bütün ayar blokları."""

    database: DatabaseSettings
    log: LogSettings


def load_settings() -> Settings:
    """Ayarları ortam değişkenlerinden okur; sorun varsa değişken adlarıyla hata verir."""
    try:
        return Settings(database=DatabaseSettings(), log=LogSettings())
    except ValidationError as error:
        raise SettingsError(_describe_errors(error)) from error


def load_ingest_settings() -> IngestSettings:
    """Hazırlık hattı ayarlarını okur; sorun varsa değişken adlarıyla hata verir."""
    try:
        return IngestSettings()
    except ValidationError as error:
        raise SettingsError(_describe_errors(error)) from error


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Ayarları bir kez okuyup süreç boyunca aynı nesneyi döner."""
    return load_settings()


def _describe_errors(error: ValidationError) -> str:
    """Doğrulama hatalarını ortam değişkeni adlarıyla tek satırlık mesaja çevirir."""
    problems = []
    for detail in error.errors():
        variable = str(detail["loc"][0]).upper()
        reason = "is missing" if detail["type"] == "missing" else f"is invalid: {detail['msg']}"
        problems.append(f"{variable} {reason}")
    return "Invalid configuration: " + "; ".join(problems)
