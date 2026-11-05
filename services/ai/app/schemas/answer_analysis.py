"""Cevap hata türü sınıflandırmasının yapılandırılmış sonucunu tanımlar."""

from enum import StrEnum

from pydantic import BaseModel


class ErrorType(StrEnum):
    """Öğrenci cevabının hata türünü tanımlar."""

    KNOWLEDGE = "KNOWLEDGE"
    MISCONCEPTION = "MISCONCEPTION"
    ATTENTION = "ATTENTION"
    READING = "READING"


class ErrorTypeAnalysis(BaseModel):
    """Sınıflandırma sonucunu ve insan incelemesi gerekip gerekmediğini taşır."""

    error_type: ErrorType
    needs_review: bool
