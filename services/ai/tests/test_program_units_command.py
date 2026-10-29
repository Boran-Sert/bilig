"""Ünite okuma komutunu ve veritabanına yazma adımını sahte havuzla test eder."""

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path

import pymupdf
import pytest
import structlog

from app.config import get_settings
from app.constants import PROGRAM_CURRICULUM_NAME, PROGRAM_SUBJECT_CODE
from app.ingest.readers import program_units
from app.schemas.program import CurriculumUnit, UnitSaveSummary

UNIT = CurriculumUnit(grade=12, unit_no=1, title="Şiir", group_codes=["A.1"])


@pytest.fixture
def program_pdf(tmp_path: Path) -> Path:
    """İki üniteli küçük bir program PDF'i yazar."""
    path = tmp_path / "program.pdf"
    document = pymupdf.open()
    html = "<p>12. SINIF</p><p>1. ÜNİTE: ŞİİR</p><p>2. ÜNİTE: ROMAN</p>"
    document.new_page().insert_htmlbox(pymupdf.Rect(50, 50, 500, 300), html)
    document.save(path)
    return path


@pytest.fixture
def pool_events(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Havuzun açılıp kapanmasını gerçek bağlantı kurmadan kaydeder."""
    events: list[str] = []

    class FakePool:
        """Bağlantı veren sahte havuz."""

        @asynccontextmanager
        async def connection(self) -> AsyncIterator[str]:
            """Sahte bağlantı verir."""
            yield "connection"

    async def fake_open(settings: object) -> FakePool:
        """Havuzun açıldığını kaydeder."""
        events.append("open")
        return FakePool()

    async def fake_close() -> None:
        """Havuzun kapandığını kaydeder."""
        events.append("close")

    monkeypatch.setenv("DATABASE_URL", "postgresql://app:secret@localhost:5432/hata_analizi")
    get_settings.cache_clear()
    monkeypatch.setattr(program_units, "open_pool", fake_open)
    monkeypatch.setattr(program_units, "close_pool", fake_close)
    yield events
    get_settings.cache_clear()


def test_dry_run_logs_units_and_writes_nothing(
    program_pdf: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run üniteleri gruplarıyla log'a yazar, veritabanına dokunmaz."""

    async def fail_save(units: list[CurriculumUnit]) -> None:
        """Yazma çağrılırsa testi düşürür."""
        raise AssertionError("dry run must not write")

    monkeypatch.setattr(program_units, "_save", fail_save)

    program_units.main([str(program_pdf), "--dry-run"])

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["message"] == "units parsed"
    assert record["units"] == ["12.1 Şiir ['A.1']", "12.2 Roman ['A.2']"]


def test_command_without_dry_run_saves_units(
    program_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--dry-run verilmezse okunan üniteler veritabanına yazılır."""
    saved: list[list[CurriculumUnit]] = []

    async def record_save(units: list[CurriculumUnit]) -> None:
        """Yazılacak üniteleri kaydeder."""
        saved.append(units)

    monkeypatch.setattr(program_units, "_save", record_save)

    program_units.main([str(program_pdf)])

    assert [[unit.title for unit in units] for units in saved] == [["Şiir", "Roman"]]


@pytest.mark.asyncio
async def test_save_writes_to_program_curriculum_and_logs_summary(
    pool_events: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Üniteler sabitlerdeki ders ve programa yazılır, özet log'a gider, havuz kapanır."""
    calls: list[tuple[str, str]] = []
    summary = UnitSaveSummary(units=1, linked=13, unlinked=0)

    async def fake_save(
        connection: str, subject_code: str, curriculum_name: str, units: list[CurriculumUnit]
    ) -> UnitSaveSummary:
        """Çağrıyı kaydedip hazır özeti döner."""
        calls.append((subject_code, curriculum_name))
        return summary

    monkeypatch.setattr(program_units, "save_units", fake_save)

    with structlog.testing.capture_logs() as logs:
        await program_units._save([UNIT])

    assert calls == [(PROGRAM_SUBJECT_CODE, PROGRAM_CURRICULUM_NAME)]
    assert logs == [{"event": "units saved", "log_level": "info", **summary.model_dump()}]
    assert pool_events == ["open", "close"]


@pytest.mark.asyncio
async def test_save_closes_pool_even_when_writing_fails(
    pool_events: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yazma hata verse de havuz kapanır ve hata yutulmaz."""

    async def failing_save(*arguments: object) -> UnitSaveSummary:
        """Yazma hatasını taklit eder."""
        raise RuntimeError("write failed")

    monkeypatch.setattr(program_units, "save_units", failing_save)

    with pytest.raises(RuntimeError, match="write failed"):
        await program_units._save([UNIT])

    assert pool_events == ["open", "close"]
