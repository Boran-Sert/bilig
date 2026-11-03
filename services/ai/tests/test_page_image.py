"""Görüntü yolunu (#142) sahte run_task ile sınar; Claude'a gerçek çağrı yapılmaz.

Sahte run_task görev adına göre hazır yanıt verir ve aldığı görüntüyü kaydeder. Sayfa görüntüsü
testin geçici depolamasına yazılır.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.ingest.readers import page_image
from app.ingest.readers.page_image import extract_page_image, needs_image_path
from app.llm.tasks import LlmTask
from app.schemas.page_extract import ExtractedBlock, PageExtraction
from app.schemas.pdf import PageReport
from app.storage import LocalFileStorage, page_image_key

TEXT = "Roman, olay örgüsü içinde kişileri anlatan uzun bir yazı türüdür."
GOOD = PageExtraction(blocks=[ExtractedBlock(block_type="METIN", markdown=TEXT)])
BAD = PageExtraction(blocks=[ExtractedBlock(block_type="METIN", markdown="Rornan olay orgusu")])
EMPTY = PageExtraction(blocks=[])
UNSURE = PageExtraction(blocks=GOOD.blocks, unreadable=True)


class FakeRunTask:
    """Görev başına hazır yanıt döner ve çağrıları kaydeder."""

    def __init__(self, answers: dict[LlmTask, PageExtraction]) -> None:
        """Yanıtları saklar, çağrı listesini boş başlatır."""
        self.answers = answers
        self.calls: list[tuple[LlmTask, Mapping[str, object], Sequence[bytes]]] = []

    async def __call__(
        self,
        task: LlmTask,
        variables: Mapping[str, object],
        *,
        output_model: type[BaseModel],
        images: Sequence[bytes] = (),
    ) -> PageExtraction:
        """Çağrıyı kaydeder ve görevin yanıtını döner."""
        assert output_model is PageExtraction
        self.calls.append((task, variables, images))
        return self.answers[task]


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    """Kaynak 7'nin 3. sayfa görüntüsü yazılı depolama."""
    storage = LocalFileStorage(tmp_path)
    storage.write(page_image_key(7, 3), b"png-bytes")
    return storage


def install(monkeypatch: pytest.MonkeyPatch, answers: dict[LlmTask, PageExtraction]) -> FakeRunTask:
    """Sahte run_task'ı bağlar."""
    fake = FakeRunTask(answers)
    monkeypatch.setattr(page_image, "run_task", fake)
    return fake


def test_only_weak_text_layer_pages_take_image_path() -> None:
    """Sadece LOW_TEXT_LAYER notlu sayfa görüntü yoluna girer."""
    weak = PageReport(page_no=1, source="OCR", notes=["LOW_TEXT_LAYER"], text_ratio=0.2)
    fine = PageReport(page_no=2, source="TEXT", notes=[], text_ratio=0.9)

    assert needs_image_path(weak)
    assert not needs_image_path(fine)


@pytest.mark.asyncio
async def test_haiku_result_is_kept_when_checks_pass(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """Haiku çıktısı kontrolü geçerse Sonnet çağrılmaz; görüntü Claude'a gider."""
    fake = install(monkeypatch, {LlmTask.PAGE_EXTRACT: GOOD})

    result = await extract_page_image(storage, 7, 3, "Test Kitabı", TEXT)

    assert result.passed and result.task is LlmTask.PAGE_EXTRACT and result.blocks == GOOD.blocks
    assert [call[0] for call in fake.calls] == [LlmTask.PAGE_EXTRACT]
    assert fake.calls[0][1] == {"source_title": "Test Kitabı", "page_no": 3}
    assert fake.calls[0][2] == [b"png-bytes"]


@pytest.mark.asyncio
async def test_sonnet_runs_when_haiku_fails_checks(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """Haiku çıktısı metin katmanına benzemezse Sonnet'e geçilir ve onun sonucu döner."""
    fake = install(monkeypatch, {LlmTask.PAGE_EXTRACT: BAD, LlmTask.PAGE_EXTRACT_FALLBACK: GOOD})

    result = await extract_page_image(storage, 7, 3, "Test Kitabı", TEXT)

    assert result.passed and result.task is LlmTask.PAGE_EXTRACT_FALLBACK
    assert [call[0] for call in fake.calls] == [
        LlmTask.PAGE_EXTRACT,
        LlmTask.PAGE_EXTRACT_FALLBACK,
    ]


@pytest.mark.asyncio
async def test_unsure_model_output_does_not_pass(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """Model okuduğundan emin değilse (unreadable) metin tutsa bile sonuç geçmez."""
    fake = install(monkeypatch, {LlmTask.PAGE_EXTRACT: UNSURE, LlmTask.PAGE_EXTRACT_FALLBACK: GOOD})

    result = await extract_page_image(storage, 7, 3, "Test Kitabı", TEXT)

    assert result.passed and result.task is LlmTask.PAGE_EXTRACT_FALLBACK
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_result_is_not_passed_when_both_models_fail(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """İki model de boş ya da benzemeyen çıktı verirse passed=False döner."""
    install(monkeypatch, {LlmTask.PAGE_EXTRACT: EMPTY, LlmTask.PAGE_EXTRACT_FALLBACK: BAD})

    result = await extract_page_image(storage, 7, 3, "Test Kitabı", TEXT)

    assert not result.passed and result.task is LlmTask.PAGE_EXTRACT_FALLBACK


@pytest.mark.asyncio
async def test_without_text_layer_any_filled_output_passes(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """Metin katmanı yoksa dolu çıktı yeterlidir; boş çıktı geçmez."""
    install(monkeypatch, {LlmTask.PAGE_EXTRACT: BAD})
    assert (await extract_page_image(storage, 7, 3, "Test Kitabı")).passed

    install(monkeypatch, {LlmTask.PAGE_EXTRACT: EMPTY, LlmTask.PAGE_EXTRACT_FALLBACK: EMPTY})
    assert not (await extract_page_image(storage, 7, 3, "Test Kitabı")).passed
