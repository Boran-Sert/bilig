"""Embedding arayüzünü sahte modelle test eder; gerçek model indirilmez."""

import math
from collections.abc import Iterator

import pytest
import torch

from app.constants import EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_TOKENS
from app.search import embedding
from app.search.embedding import BgeEmbedding, get_embedding_provider

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


class FakeSentenceTransformer:
    """Yükleme bilgisini ve encode çağrılarını kaydeden sahte model."""

    def __init__(self, name: str, revision: str) -> None:
        """Model adını ve commit'i saklar."""
        self.name = name
        self.revision = revision
        self.max_seq_length = 0
        self.batch_sizes: list[int] = []

    def encode(
        self, texts: list[str], batch_size: int, normalize_embeddings: bool, show_progress_bar: bool
    ) -> torch.Tensor:
        """Metin uzunluğundan vektör üretir; istenirse normalize eder."""
        self.batch_sizes.append(batch_size)
        vectors = torch.tensor([[float(len(text)), 1.0] for text in texts])
        return torch.nn.functional.normalize(vectors) if normalize_embeddings else vectors


def set_model_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Embedding ve reranker ayarlarını ortam değişkeni olarak verir."""
    monkeypatch.setenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
    monkeypatch.setenv("EMBEDDING_REVISION", EMBEDDING_REVISION)
    monkeypatch.setenv("RERANKER_MODEL", RERANKER_MODEL)
    monkeypatch.setenv("RERANKER_REVISION", RERANKER_REVISION)


@pytest.fixture
def loads(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[FakeSentenceTransformer]]:
    """Gerçek model yerine sahtesini yükletir ve her yüklemeyi listeye ekler."""
    created: list[FakeSentenceTransformer] = []

    def load(name: str, revision: str) -> FakeSentenceTransformer:
        """Sahte modeli oluşturur ve kaydeder."""
        created.append(FakeSentenceTransformer(name, revision))
        return created[-1]

    set_model_environment(monkeypatch)
    monkeypatch.setattr(embedding, "SentenceTransformer", load)
    get_embedding_provider.cache_clear()
    yield created
    get_embedding_provider.cache_clear()


def test_encode_returns_normalized_vector_per_text_in_order() -> None:
    """Her metin için sırasıyla bir normalize vektör döner."""
    model = FakeSentenceTransformer(EMBEDDING_MODEL, EMBEDDING_REVISION)

    vectors = BgeEmbedding(model).encode(["kısa", "daha uzun metin"])

    assert len(vectors) == 2
    assert all(math.isclose(math.hypot(*vector), 1.0, rel_tol=1e-6) for vector in vectors)
    assert vectors[0][0] < vectors[1][0]
    assert model.batch_sizes == [EMBEDDING_BATCH_SIZE]


def test_provider_loads_model_once_from_pinned_revision(
    loads: list[FakeSentenceTransformer],
) -> None:
    """Model ayardaki commit'ten bir kez yüklenir; sonraki çağrılar aynı nesneyi döner."""
    first = get_embedding_provider()

    assert get_embedding_provider() is first
    assert len(loads) == 1
    assert (loads[0].name, loads[0].revision) == (EMBEDDING_MODEL, EMBEDDING_REVISION)
    assert loads[0].max_seq_length == EMBEDDING_MAX_TOKENS
