"""Ortak aramanın modelleri (plan 13.11).

Arama tek tabloda yapılır: content_block, learning_outcome ya da knowledge_node. content_block ve
knowledge_node aramasında sadece PUBLISHED kayıt döner; learning_outcome'da durum kolonu yoktur.
Verilmeyen filtre sonucu daraltmaz. knowledge_node'un ünite ve kazanım bağı olmadığı için ona
filtre verilemez.
"""

from enum import StrEnum

from pydantic import BaseModel, model_validator


class SearchTarget(StrEnum):
    """Aramanın yapıldığı tablo."""

    CONTENT_BLOCK = "CONTENT_BLOCK"
    LEARNING_OUTCOME = "LEARNING_OUTCOME"
    KNOWLEDGE_NODE = "KNOWLEDGE_NODE"


class SearchFilters(BaseModel):
    """Aramanın tablosu ve sonucu ünite ya da kazanımlarla daraltan filtreler."""

    target: SearchTarget
    curriculum_unit_id: int | None = None
    learning_outcome_ids: list[int] | None = None

    @model_validator(mode="after")
    def reject_knowledge_node_filters(self) -> "SearchFilters":
        """knowledge_node aramasına verilen filtreyi reddeder; sessizce yok sayılmaz."""
        has_filter = self.curriculum_unit_id is not None or self.learning_outcome_ids is not None
        if self.target is SearchTarget.KNOWLEDGE_NODE and has_filter:
            raise ValueError("knowledge_node search does not support filters")
        return self


class SearchHit(BaseModel):
    """Arama sonucu: kaydın kimliği, arama metni ve skoru."""

    id: int
    text: str
    score: float
