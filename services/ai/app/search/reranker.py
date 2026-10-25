"""Arama adaylarını soruya göre yeniden sıralayan Reranker arayüzü ve yerel bge uygulaması.

Model süreç başına bir kez get_reranker ile yüklenir; başka yerde CrossEncoder oluşturulmaz.
Ekran kartı varsa model GPU'da, yoksa CPU'da çalışır; seçilen cihaz log'a yazılır.
"""

from functools import lru_cache
from typing import Protocol

import structlog
import torch
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

from app.config import load_embedding_settings
from app.constants import RERANKER_MAX_LENGTH


class RankedDocument(BaseModel):
    """Yeniden sıralanan adayın girdideki sırası ve skoru."""

    index: int
    score: float


class Reranker(Protocol):
    """Adayları soruya yakınlığına göre yeniden sıralayan arayüz."""

    def rerank(self, query: str, docs: list[str], top_k: int) -> list[RankedDocument]:
        """En iyi top_k adayı skoru yüksekten düşüğe döner."""
        ...


class BgeReranker:
    """bge-reranker-v2-m3 ile soru ve aday çiftlerini skorlar."""

    def __init__(self, model: CrossEncoder) -> None:
        """Yüklenmiş modeli saklar."""
        self._model = model

    def rerank(self, query: str, docs: list[str], top_k: int) -> list[RankedDocument]:
        """Her adayı soruyla birlikte skorlar ve en iyi top_k adayı sıralı döner."""
        pairs = [(query, doc) for doc in docs]
        scores = self._model.predict(pairs, show_progress_bar=False).tolist()
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
        return [RankedDocument(index=index, score=score) for index, score in ranked[:top_k]]


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    """Modeli ekran kartı varsa GPU'da, yoksa CPU'da bir kez yükler ve aynı nesneyi döner."""
    settings = load_embedding_settings()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    structlog.get_logger().info("reranker device selected", device=device)
    model = CrossEncoder(
        settings.reranker_model,
        revision=settings.reranker_revision,
        max_length=RERANKER_MAX_LENGTH,
        device=device,
    )
    return BgeReranker(model)
