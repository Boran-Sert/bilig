"""Program okuma komutunu ve veritabanına yazma adımını sahte havuzla test eder."""

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import structlog

from app.config import get_settings
from app.constants import PROGRAM_CURRICULUM_NAME, PROGRAM_SUBJECT_CODE, PROGRAM_SUBJECT_NAME
from app.ingest.readers import program as program_reader
from app.ingest.readers.program import read_program
from app.schemas.program import Curriculum, Program, ProgramSaveSummary, Subject
from tests.test_program_reader import write_program_pdf

SUBJECT = Subject(code="TDE", name="Türk Dili ve Edebiyatı")
CURRICULUM = Curriculum(name="TDE Öğretim Programı 2018", model="LEGACY", year=2018)


@pytest.fixture(scope="module")
def program_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Test programını geçici klasöre PDF olarak yazar."""
    return write_program_pdf(tmp_path_factory.mktemp("program") / "program.pdf")


def test_read_program_adds_subject_and_curriculum(program_pdf: Path) -> None:
    """Program, sabitlerdeki ders ve program sürümüyle birlikte okunur."""
    program = read_program(program_pdf)

    assert program.subject == Subject(code=PROGRAM_SUBJECT_CODE, name=PROGRAM_SUBJECT_NAME)
    assert program.curriculum.name == PROGRAM_CURRICULUM_NAME
    assert program.curriculum.model == "LEGACY"
    assert [group.code for group in program.groups] == ["A.1", "A.2", "B", "C.1", "C.2"]


def test_dry_run_logs_counts_and_writes_nothing(
    program_pdf: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run grup başına kazanım sayısını log'a yazar, veritabanına dokunmaz."""

    async def fail_save(program: Program) -> None:
        """Yazma çağrılırsa testi düşürür."""
        raise AssertionError("dry run must not write")

    monkeypatch.setattr(program_reader, "_save", fail_save)

    program_reader.main([str(program_pdf), "--dry-run"])

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["message"] == "program parsed"
    assert record["outcomes"] == {"A.1": 3, "A.2": 1, "B": 2, "C.1": 1, "C.2": 1}


def test_command_without_dry_run_saves_program(
    program_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--dry-run verilmezse okunan program veritabanına yazılır."""
    saved: list[Program] = []

    async def record_save(program: Program) -> None:
        """Yazılacak programı kaydeder."""
        saved.append(program)

    monkeypatch.setattr(program_reader, "_save", record_save)

    program_reader.main([str(program_pdf)])

    assert len(saved) == 1
    assert saved[0].curriculum.name == PROGRAM_CURRICULUM_NAME


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
    monkeypatch.setattr(program_reader, "open_pool", fake_open)
    monkeypatch.setattr(program_reader, "close_pool", fake_close)
    yield events
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_save_closes_pool_even_when_writing_fails(
    pool_events: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yazma hata verse de havuz kapanır ve hata yutulmaz."""

    async def failing_save(connection: str, program: Program) -> None:
        """Yazma hatasını taklit eder."""
        raise RuntimeError("write failed")

    monkeypatch.setattr(program_reader, "save_program", failing_save)

    with pytest.raises(RuntimeError, match="write failed"):
        await program_reader._save(Program(subject=SUBJECT, curriculum=CURRICULUM, groups=[]))

    assert pool_events == ["open", "close"]


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [0, 2])
async def test_save_logs_summary_and_warns_about_missing_outcomes(
    pool_events: list[str], monkeypatch: pytest.MonkeyPatch, missing: int
) -> None:
    """Yazma özeti log'a gider; PDF'te olmayan kazanım varsa ayrıca uyarı yazılır."""
    summary = ProgramSaveSummary(inserted=1, updated=0, unchanged=3, missing=missing)

    async def fake_save(connection: str, program: Program) -> ProgramSaveSummary:
        """Hazır özeti döner."""
        return summary

    monkeypatch.setattr(program_reader, "save_program", fake_save)

    with structlog.testing.capture_logs() as logs:
        await program_reader._save(Program(subject=SUBJECT, curriculum=CURRICULUM, groups=[]))

    assert logs[0] == {"event": "program saved", "log_level": "info", **summary.model_dump()}
    warning = {"event": "outcomes missing from pdf", "log_level": "warning", "missing": missing}
    assert logs[1:] == ([warning] if missing else [])
    assert pool_events == ["open", "close"]
