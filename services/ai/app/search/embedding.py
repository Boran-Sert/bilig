"""Metni vektöre çeviren EmbeddingProvider arayüzü ve yerel bge-m3 uygulaması.

Model süreç başına bir kez get_embedding_provider ile yüklenir; başka yerde SentenceTransformer
oluşturulmaz. Servis HF_HUB_OFFLINE=1 ile çalıştığı için model önceden indirilmiş olmalıdır.
"""

from functools import lru_cache
from typing import Protocol, cast

from sentence_transformers import SentenceTransformer

from app.config import load_embedding_settings
from app.constants import EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_TOKENS


class EmbeddingProvider(Protocol):
    """Metinleri normalize vektörlere çeviren arayüz."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Her metin için aynı sırada bir vektör döner."""
        ...


class BgeEmbedding:
    """bge-m3 ile yerelde 1024 boyutlu normalize vektör üretir."""

    def __init__(self, model: SentenceTransformer) -> None:
        """Yüklenmiş modeli saklar."""
        self._model = model

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Metinleri sabit büyüklükteki gruplarla normalize vektöre çevirir."""
        vectors = self._model.encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return cast(list[list[float]], vectors.tolist())


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Ayardaki modeli sabit commit'ten bir kez yükleyip süreç boyunca aynı nesneyi döner."""
    settings = load_embedding_settings()
    model = SentenceTransformer(settings.embedding_model, revision=settings.embedding_revision)
    model.max_seq_length = EMBEDDING_MAX_TOKENS
    return BgeEmbedding(model)
