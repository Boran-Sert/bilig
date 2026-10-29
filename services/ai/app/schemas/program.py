"""Öğretim programından okunan kazanım ağacının modelleri (hazırlık hattı A1).

Ağaç ders › öğretim programı › kazanım grubu › kazanım biçimindedir ve docs/veritabani.md'deki
subject, curriculum, learning_outcome_group ve learning_outcome tablolarına yazılır. Üniteler
curriculum_unit tablosuna, ünitede işlenen kazanımlar curriculum_unit_outcome tablosuna yazılır.
"""

from typing import Literal

from pydantic import BaseModel


class Subject(BaseModel):
    """Ders; örneğin TDE, Türk Dili ve Edebiyatı."""

    code: str
    name: str


class Curriculum(BaseModel):
    """Öğretim programının sürümü."""

    name: str
    model: Literal["LEGACY", "MAARIF"]
    year: int


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


class Program(BaseModel):
    """Bir öğretim programı PDF'inden okunan kazanım ağacının tamamı."""

    subject: Subject
    curriculum: Curriculum
    groups: list[LearningOutcomeGroup]


class ProgramSaveSummary(BaseModel):
    """Kaç kazanımın eklendiği, değiştiği, aynı kaldığı ve programda olup PDF'te bulunmadığı."""

    inserted: int
    updated: int
    unchanged: int
    missing: int


class CurriculumUnit(BaseModel):
    """Bir sınıfın ünitesi ve ünitenin bağlandığı kazanım grupları (kuralla bulunur)."""

    grade: int
    unit_no: int
    title: str
    group_codes: list[str]


class UnitSaveSummary(BaseModel):
    """Kaç ünite yazıldığı, kaç kazanım bağı eklendiği ve kaçının kaldırıldığı."""

    units: int
    linked: int
    unlinked: int
