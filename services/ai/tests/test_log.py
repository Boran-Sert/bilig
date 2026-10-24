"""Uygulamanın ve standart logging kullanan kütüphanelerin JSON log biçimini test eder."""

import json
import logging
import logging.config

import pytest
import structlog
from uvicorn.config import LOGGING_CONFIG

from app.config import LogSettings
from app.log import bind_request_id, clear_request_context, configure_logging


def test_log_is_single_line_json_with_common_fields(capsys: pytest.CaptureFixture[str]) -> None:
    """Kayıt tek satırlık JSON'dur ve ortak alanları taşır."""
    configure_logging(LogSettings(log_level="INFO"))
    bind_request_id("req-42")

    structlog.get_logger().info("page checked", page_no=3)

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["message"] == "page checked"
    assert record["level"] == "INFO"
    assert record["service"] == "ai"
    assert record["requestId"] == "req-42"
    assert record["page_no"] == 3
    assert "timestamp" in record


def test_log_keeps_turkish_characters(capsys: pytest.CaptureFixture[str]) -> None:
    """Türkçe karakterler kaçış dizisine çevrilmeden yazılır."""
    configure_logging(LogSettings(log_level="INFO"))

    structlog.get_logger().info("source registered", title="Türk Dili ve Edebiyatı")

    assert "Türk Dili ve Edebiyatı" in capsys.readouterr().out


def test_log_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    """Ayardaki seviyenin altındaki kayıtlar yazılmaz."""
    configure_logging(LogSettings(log_level="WARNING"))

    structlog.get_logger().info("hidden")
    structlog.get_logger().warning("shown")

    output = capsys.readouterr().out
    assert "hidden" not in output
    assert json.loads(output)["level"] == "WARNING"


def test_exception_log_stays_on_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    """Hata izi içeren kayıt da tek satırdır ve izi exception alanında taşır."""
    configure_logging(LogSettings(log_level="INFO"))

    try:
        raise ValueError("broken page")
    except ValueError:
        structlog.get_logger().exception("page failed")

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["level"] == "ERROR"
    assert "ValueError: broken page" in record["exception"]


def test_cleared_request_context_is_not_logged(capsys: pytest.CaptureFixture[str]) -> None:
    """Temizlenen istek kimliği sonraki kayıtlara eklenmez."""
    configure_logging(LogSettings(log_level="INFO"))
    bind_request_id("req-1")
    clear_request_context()

    structlog.get_logger().info("after request")

    assert "requestId" not in json.loads(capsys.readouterr().out)


def test_uvicorn_access_log_is_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Erişim kaydı, uvicorn kendi log ayarını kurduktan sonra da ortak alanlı JSON yazılır."""
    logging.config.dictConfig(LOGGING_CONFIG)
    configure_logging(LogSettings(log_level="INFO"))

    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "127.0.0.1:5000", "GET", "/internal/health", "1.1", 204
    )

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["message"] == '127.0.0.1:5000 - "GET /internal/health HTTP/1.1" 204'
    assert record["level"] == "INFO"
    assert record["service"] == "ai"
    assert "timestamp" in record


def test_library_log_carries_request_id_and_exception(capsys: pytest.CaptureFixture[str]) -> None:
    """Standart logging kaydı istek kimliğini ve hata izini tek satırda taşır."""
    configure_logging(LogSettings(log_level="INFO"))
    bind_request_id("req-7")

    try:
        raise ConnectionError("server closed")
    except ConnectionError:
        logging.getLogger("psycopg.pool").exception("connection lost")

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["message"] == "connection lost"
    assert record["level"] == "ERROR"
    assert record["requestId"] == "req-7"
    assert "ConnectionError: server closed" in record["exception"]


def test_library_log_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    """Kendi seviyesini INFO yapan uvicorn logger'ı da ayardaki seviyenin altını yazmaz."""
    logging.config.dictConfig(LOGGING_CONFIG)
    configure_logging(LogSettings(log_level="WARNING"))

    logging.getLogger("uvicorn.access").info("hidden request")
    logging.getLogger("uvicorn.error").warning("shown warning")

    output = capsys.readouterr().out
    assert "hidden request" not in output
    assert json.loads(output)["message"] == "shown warning"


def test_uvicorn_follows_debug_level(capsys: pytest.CaptureFixture[str]) -> None:
    """DEBUG ayarında uvicorn'un kendine koyduğu INFO seviyesi kalkar, ayrıntı kaydı yazılır."""
    logging.config.dictConfig(LOGGING_CONFIG)
    configure_logging(LogSettings(log_level="DEBUG"))

    logging.getLogger("uvicorn.error").debug("debug detail")

    assert json.loads(capsys.readouterr().out)["level"] == "DEBUG"


def test_configure_twice_writes_each_record_once(capsys: pytest.CaptureFixture[str]) -> None:
    """Ayar iki kez kurulsa da kök logger'da tek handler kalır ve kayıt bir kez yazılır."""
    configure_logging(LogSettings(log_level="INFO"))
    configure_logging(LogSettings(log_level="INFO"))

    logging.getLogger("library").info("once")

    assert len(logging.root.handlers) == 1
    assert len(capsys.readouterr().out.splitlines()) == 1
