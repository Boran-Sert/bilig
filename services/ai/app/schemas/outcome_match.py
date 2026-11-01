"""Kazanım eşleştirmenin (plan A8) modelleri.

OutcomeMatch, OUTCOME_MATCH görevinin JSON çıktısıdır: seçilen kazanım kodları ve her biri için
güven. Kazanımlar arasında sıra ya da ağırlık yoktur; güven sadece incelemeye düşme kararında
kullanılır, kayda geçmez. OutcomeCandidate modele aday olarak verilen kazanım, MatchItem
eşleştirilecek soru ya da paragraf, OutcomeChoice kod kontrolünden geçmiş sonuçtur.
"""

from enum import StrEnum

from pydantic import BaseModel


class Confidence(StrEnum):
    """Modelin bir kazanım için verdiği güven."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MatchedOutcome(BaseModel):
    """Modelin seçtiği tek kazanım: kodu ve güveni."""

    code: str
    confidence: Confidence


class OutcomeMatch(BaseModel):
    """OUTCOME_MATCH çıktısı: içeriğin ölçtüğü bütün kazanımlar."""

    outcomes: list[MatchedOutcome]


class ItemKind(StrEnum):
    """Eşleştirilen içeriğin türü."""

    QUESTION = "QUESTION"
    PARAGRAPH = "PARAGRAPH"


class MatchItem(BaseModel):
    """Eşleştirilecek içerik: türü, metni, ünitesi ve soruysa doğru şıkkı."""

    kind: ItemKind
    text: str
    curriculum_unit_id: int | None
    correct_option: str | None = None


class OutcomeCandidate(BaseModel):
    """Aramanın bulduğu aday kazanım: kimliği, kodu, başlığı ve MEB açıklaması."""

    id: int
    code: str
    title: str
    meb_explanation: str | None


class OutcomeChoice(BaseModel):
    """Kontrolden geçen kazanımlar ve sonucun incelemeye düşüp düşmeyeceği."""

    outcomes: list[OutcomeCandidate]
    needs_review: bool
