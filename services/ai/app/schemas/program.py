"""Öğretim programından okunan kazanım ağacının modelleri (hazırlık hattı A1).

Kazanım grubu › kazanım ağacı docs/veritabani.md'deki learning_outcome_group ve
learning_outcome tablolarına yazılır.
"""

from pydantic import BaseModel


class LearningOutcome(BaseModel):
    """Kazanım; açıklama, programda kazanımın altındaki MEB açıklamasıdır (a, b, c maddeleri)."""

    code: str
    title: str
    meb_explanation: str | None


class LearningOutcomeGroup(BaseModel):
    """Kazanım grubu; örneğin A.2, Öyküleyici (anlatmaya bağlı) edebî metinler."""

    code: str
    name: str
    outcomes: list[LearningOutcome]
