"""Görüntü yolunu (#142) sahte run_task ile sınar; Claude'a gerçek çağrı yapılmaz.

Sahte run_task görev adına göre hazır yanıt verir ve aldığı görüntüyü kaydeder. Sayfa görüntüsü
testin geçici depolamasına yazılır.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.ingest.readers import page_image
from app.ingest.readers.page_image import (
    PageImageResult,
    extract_page_image,
    needs_image_path,
    read_weak_pages,
    replace_page_blocks,
)
from app.llm.tasks import LlmTask
from app.schemas.page_extract import ExtractedBlock, PageExtraction
from app.schemas.pdf import PageReport
from app.schemas.textbook import TextbookBlock
from app.storage import LocalFileStorage, page_image_key

TEXT = "Roman, olay örgüsü içinde kişileri anlatan uzun bir yazı türüdür."
GOOD = PageExtraction(blocks=[ExtractedBlock(block_type="METIN", markdown=TEXT)])
EMPTY = PageExtraction(blocks=[])
UNSURE = PageExtraction(blocks=GOOD.blocks, unreadable=True)
WEAK = PageReport(page_no=3, source="TEXT", notes=["LOW_TEXT_LAYER"], text_ratio=0.2)
FINE = PageReport(page_no=2, source="TEXT", notes=[], text_ratio=0.95)


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


def block(page_no: int, position: int, title_path: str, block_type: str = "METIN") -> TextbookBlock:
    """Kitap motorunun verdiği gibi bir blok kurar."""
    return TextbookBlock.model_validate(
        {
            "block_type": block_type,
            "markdown": f"Blok {page_no}-{position}",
            "title_path": title_path,
            "page_no": page_no,
            "position": position,
            "pages": [page_no],
        }
    )


def test_only_weak_text_layer_pages_take_image_path() -> None:
    """Sadece LOW_TEXT_LAYER notlu sayfa görüntü yoluna girer."""
    assert needs_image_path(WEAK)
    assert not needs_image_path(FINE)


@pytest.mark.asyncio
async def test_haiku_result_is_kept_when_checks_pass(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """Haiku çıktısı kontrolü geçerse Sonnet çağrılmaz; görüntü Claude'a gider."""
    fake = install(monkeypatch, {LlmTask.PAGE_EXTRACT: GOOD})

    result = await extract_page_image(storage, 7, 3, "Test Kitabı")

    assert result.passed and result.task is LlmTask.PAGE_EXTRACT and result.blocks == GOOD.blocks
    assert [call[0] for call in fake.calls] == [LlmTask.PAGE_EXTRACT]
    assert fake.calls[0][1] == {"source_title": "Test Kitabı", "page_no": 3}
    assert fake.calls[0][2] == [b"png-bytes"]


@pytest.mark.asyncio
@pytest.mark.parametrize("haiku", [EMPTY, UNSURE])
async def test_sonnet_runs_when_haiku_is_empty_or_unsure(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage, haiku: PageExtraction
) -> None:
    """Haiku boş döner ya da emin olmadığını söylerse Sonnet'e geçilir ve onun sonucu döner."""
    fake = install(monkeypatch, {LlmTask.PAGE_EXTRACT: haiku, LlmTask.PAGE_EXTRACT_FALLBACK: GOOD})

    result = await extract_page_image(storage, 7, 3, "Test Kitabı")

    assert result.passed and result.task is LlmTask.PAGE_EXTRACT_FALLBACK
    assert [call[0] for call in fake.calls] == [
        LlmTask.PAGE_EXTRACT,
        LlmTask.PAGE_EXTRACT_FALLBACK,
    ]


@pytest.mark.asyncio
async def test_result_is_not_passed_when_both_models_fail(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """İki model de boş ya da emin olmayan çıktı verirse passed=False döner."""
    install(monkeypatch, {LlmTask.PAGE_EXTRACT: EMPTY, LlmTask.PAGE_EXTRACT_FALLBACK: UNSURE})

    result = await extract_page_image(storage, 7, 3, "Test Kitabı")

    assert not result.passed and result.task is LlmTask.PAGE_EXTRACT_FALLBACK


def test_replaced_page_keeps_neighbours_and_takes_path_from_previous_block() -> None:
    """Sayfanın blokları değişir, sıra 0'dan başlar; başlık önceki yolun altına eklenir."""
    path = "Kitap › ROMAN"
    blocks = [block(2, 0, path), block(3, 0, path), block(3, 1, path), block(4, 0, path)]
    result = PageImageResult(
        page_no=3,
        blocks=[
            ExtractedBlock(block_type="BASLIK", markdown="Tarihî Roman"),
            ExtractedBlock(block_type="METIN", markdown=TEXT),
        ],
        task=LlmTask.PAGE_EXTRACT,
        passed=True,
    )

    replaced = replace_page_blocks(blocks, result, "Kitap")

    assert [(b.page_no, b.position, b.block_type) for b in replaced] == [
        (2, 0, "METIN"),
        (3, 0, "BASLIK"),
        (3, 1, "METIN"),
        (4, 0, "METIN"),
    ]
    assert [b.title_path for b in replaced[1:3]] == [f"{path} › Tarihî Roman"] * 2
    assert replaced[2].search_text == f"{path} › Tarihî Roman\n{TEXT}"


@pytest.mark.asyncio
async def test_only_weak_pages_are_sent_and_failed_page_keeps_engine_blocks(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """Sağlam sayfa Claude'a gitmez; okunamayan zayıf sayfanın motor blokları kalır."""
    fake = install(monkeypatch, {LlmTask.PAGE_EXTRACT: EMPTY, LlmTask.PAGE_EXTRACT_FALLBACK: EMPTY})
    blocks = [block(2, 0, "Kitap"), block(3, 0, "Kitap")]

    result, fixed = await read_weak_pages(storage, 7, "Kitap", blocks, [FINE, WEAK])

    assert result == blocks and fixed == set()
    assert [call[1]["page_no"] for call in fake.calls] == [3, 3]


@pytest.mark.asyncio
async def test_read_weak_page_replaces_its_blocks(
    monkeypatch: pytest.MonkeyPatch, storage: LocalFileStorage
) -> None:
    """Görüntüden okunan zayıf sayfanın blokları değişir ve sayfa düzelmiş sayılır."""
    install(monkeypatch, {LlmTask.PAGE_EXTRACT: GOOD})
    blocks = [block(2, 0, "Kitap"), block(3, 0, "Kitap")]

    result, fixed = await read_weak_pages(storage, 7, "Kitap", blocks, [FINE, WEAK])

    assert [(b.page_no, b.markdown) for b in result] == [(2, "Blok 2-0"), (3, TEXT)]
    assert fixed == {3}
