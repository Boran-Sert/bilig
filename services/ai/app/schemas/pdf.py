"""PDF okumanın sonuçları: sayfa raporları, testlere bölünmüş sorular ve kitap blokları.

Sayfa raporu bir sayfanın nasıl okunduğunu söyler: metin katmanından (TEXT), OCR'la (OCR) ya da
boş (EMPTY); notlar onarılan harfleri (REPAIRED_GLYPHS), çözülemeyenleri (UNDECODED_GLYPHS),
OCR'la okunan resimleri (IMAGE_OCR), uygulanan font düzeltmesini (FONT_FIX_...), OCR'ın yerini
aldığı (TEXT_LAYER_REPLACED) ya da zayıf kalan (LOW_TEXT_LAYER) metin katmanını gösterir.
text_ratio sayfa metninin Türkçe kök listesindeki kelime payıdır; kısa sayfada ölçülmez. Test
okumasında kökünde soru olmadığı için atılan şık kümelerinin sayfaları da döner.
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas.question import ParsedQuestion
from app.schemas.textbook import TextbookBlock

PageSource = Literal["TEXT", "OCR", "EMPTY"]


class PageReport(BaseModel):
    """Bir sayfanın kaynağı, okuma notları ve Türkçe kelime oranı."""

    page_no: int
    source: PageSource
    notes: list[str]
    text_ratio: float | None


class QuestionReading(BaseModel):
    """Test PDF'inden okunanlar: testler, sayfa raporları ve atılan şık kümelerinin sayfaları."""

    tests: list[list[ParsedQuestion]]
    pages: list[PageReport]
    not_multiple_choice_pages: list[int] = []


class TextbookReading(BaseModel):
    """Kitap PDF'inden okunan bloklar ve sayfa raporları."""

    blocks: list[TextbookBlock]
    pages: list[PageReport]
