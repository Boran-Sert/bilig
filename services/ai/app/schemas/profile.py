"""Stilli satırların modelleri (hazırlık hattı A4).

Stil, PyMuPDF'in metin parçası için verdiği font, boyut, kalınlık, italiklik ve renkle parçanın
içinde durduğu dolgulu kutunun rengidir. Satırlar app/ingest/styles.py'de üretilir; kaynak
profilinin sayımı ve uygulaması bunları kullanır.
"""

from pydantic import BaseModel, ConfigDict

BoundingBox = tuple[float, float, float, float]


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
