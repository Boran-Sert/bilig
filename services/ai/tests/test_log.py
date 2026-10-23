"""JSON log biçimini test eder."""

import json
from collections.abc import Iterator

import pytest
import structlog

from app.config import LogSettings
from app.log import bind_request_id, clear_request_context, configure_logging


@pytest.fixture(autouse=True)
def reset_structlog() -> Iterator[None]:
    """Her testten sonra structlog ayarını ve bağlanmış alanları sıfırlar."""
    yield
    clear_request_context()
    structlog.reset_defaults()


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
