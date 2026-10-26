"""Kaynak profilinin, stil sayımının ve stilli satırların modelleri (hazırlık hattı A4).

Stil, PyMuPDF'in metin parçası için verdiği font, boyut, kalınlık, italiklik ve renkle parçanın
içinde durduğu dolgulu kutunun rengidir. Profil bir kitap ya da seri için bir kez yazılan stil →
blok türü kurallarıdır; dosyaları profiles/*.yaml, biçimi profiles/README.md. Kural alanlarında
boş (None) değer "her değer" demektir; böylece modelin bütün alanları dolu ürettiği öneriler
(#128) de, elle yazılan kısa kurallar da aynı anlamı taşır.
"""

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.constants import PROFILE_SIZE_STEP

BlockType = Literal["BILGI", "ALINTI", "ETKINLIK", "METIN", "BASLIK"]
RuleTarget = BlockType | Literal["IGNORE"]
BoundingBox = tuple[float, float, float, float]

_HEX_COLOR = re.compile(r"^#[0-9a-f]{6}$")


class TextStyle(BaseModel):
    """Bir metin parçasının görünümü; renkler küçük harfli #rrggbb, kutu yoksa box boştur."""

    model_config = ConfigDict(frozen=True)

    font: str
    size: float
    bold: bool
    italic: bool
    color: str
    box: str | None


class StyledSpan(BaseModel):
    """Satırdaki bir metin parçası, stili ve içinde durduğu kutunun sınırları."""

    text: str
    style: TextStyle
    box_bbox: BoundingBox | None


class StyledLine(BaseModel):
    """Sayfadaki bir satırın parçaları, sayfa sırası (1'den) ve konumu."""

    spans: list[StyledSpan]
    page_no: int
    bbox: BoundingBox


class StyleMatch(BaseModel):
    """Kuralın aradığı stil alanları; boş alan her değerle eşleşir, en az bir alan dolu olur."""

    model_config = ConfigDict(extra="forbid")

    font: str | None = None
    size: float | None = None
    bold: bool | None = None
    italic: bool | None = None
    color: str | None = None
    box: str | None = None
    boxed: bool | None = None

    @field_validator("size")
    @classmethod
    def size_on_step(cls, size: float | None) -> float | None:
        """Boyutun stil sayımındaki yuvarlamayla eşleşebilir olduğunu denetler."""
        if size is not None and (size / PROFILE_SIZE_STEP) % 1:
            raise ValueError(f"size must be a multiple of {PROFILE_SIZE_STEP}")
        return size

    @field_validator("color", "box")
    @classmethod
    def lowercase_hex(cls, color: str | None) -> str | None:
        """Rengin stil sayımındaki gibi küçük harfli #rrggbb olduğunu denetler."""
        if color is not None and not _HEX_COLOR.match(color):
            raise ValueError("color must be lowercase #rrggbb")
        return color

    @model_validator(mode="after")
    def not_empty(self) -> Self:
        """Her şeyle eşleşen boş kuralı reddeder."""
        if not self.model_dump(exclude_none=True):
            raise ValueError("match must set at least one field")
        return self


class StyleRule(BaseModel):
    """Eşleşen stildeki satırın blok türü; IGNORE satırı atar (sayfa başlığı, numarası)."""

    model_config = ConfigDict(extra="forbid")

    match: StyleMatch
    block_type: RuleTarget


class SourceProfile(BaseModel):
    """Bir kitap ya da serinin profili; kurallar sırayla denenir, ilk eşleşen kazanır."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    rules: list[StyleRule]
