"""Reranker arayüzünü sahte modelle test eder; gerçek model indirilmez."""

from collections.abc import Iterator

import pytest
import torch
from structlog.testing import capture_logs

from app.constants import RERANKER_MAX_LENGTH
from app.search import reranker
from app.search.reranker import BgeReranker, get_reranker
from tests.test_embedding import RERANKER_MODEL, RERANKER_REVISION, set_model_environment

SCORES = {"Roman türleri": 0.1, "Olay örgüsü": 0.9, "Yazım kuralları": 0.5, "Kişiler": 0.7}


class FakeCrossEncoder:
    """Yükleme bilgisini ve skorlanan çiftleri kaydeden sahte model."""

    def __init__(self, name: str, revision: str, max_length: int, device: str) -> None:
        """Model adını, commit'i, uzunluk sınırını ve cihazı saklar."""
        self.name = name
        self.revision = revision
        self.max_length = max_length
        self.device = device
        self.pairs: list[tuple[str, str]] = []

    def predict(self, pairs: list[tuple[str, str]], show_progress_bar: bool) -> torch.Tensor:
        """Her çift için adayın sabit skorunu döner."""
        self.pairs.extend(pairs)
        return torch.tensor([SCORES[doc] for _, doc in pairs])


@pytest.fixture
def loads(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[FakeCrossEncoder]]:
    """Gerçek model yerine sahtesini yükletir ve her yüklemeyi listeye ekler."""
    created: list[FakeCrossEncoder] = []

    def load(name: str, revision: str, max_length: int, device: str) -> FakeCrossEncoder:
        """Sahte modeli oluşturur ve kaydeder."""
        created.append(FakeCrossEncoder(name, revision, max_length, device))
        return created[-1]

    set_model_environment(monkeypatch)
    monkeypatch.setattr(reranker, "CrossEncoder", load)
    get_reranker.cache_clear()
    yield created
    get_reranker.cache_clear()


def test_rerank_returns_top_k_in_score_order() -> None:
    """En yüksek skorlu top_k aday, girdideki sırasıyla birlikte büyükten küçüğe döner."""
    model = FakeCrossEncoder(RERANKER_MODEL, RERANKER_REVISION, RERANKER_MAX_LENGTH, "cpu")

    ranked = BgeReranker(model).rerank("Roman nedir?", list(SCORES), top_k=2)

    assert [document.index for document in ranked] == [1, 3]
    assert ranked[0].score == pytest.approx(0.9)
    assert model.pairs == [("Roman nedir?", doc) for doc in SCORES]


def test_reranker_loads_model_once_from_pinned_revision(loads: list[FakeCrossEncoder]) -> None:
    """Model ayardaki commit'ten sabit uzunluk sınırıyla bir kez yüklenir."""
    first = get_reranker()

    assert get_reranker() is first
    assert len(loads) == 1
    assert (loads[0].name, loads[0].revision) == (RERANKER_MODEL, RERANKER_REVISION)
    assert loads[0].max_length == RERANKER_MAX_LENGTH


@pytest.mark.parametrize(("cuda", "device"), [(True, "cuda"), (False, "cpu")])
def test_reranker_device_follows_cuda_and_is_logged(
    loads: list[FakeCrossEncoder], monkeypatch: pytest.MonkeyPatch, cuda: bool, device: str
) -> None:
    """Ekran kartı varsa GPU, yoksa CPU seçilir ve seçim log'a yazılır."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: cuda)

    with capture_logs() as logs:
        get_reranker()

    assert loads[0].device == device
    assert {"event": "reranker device selected", "device": device, "log_level": "info"} in logs
