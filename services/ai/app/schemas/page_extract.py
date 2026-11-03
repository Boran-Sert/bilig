"""Görüntü yolunun çıktısı: Claude'un sayfa görüntüsünden okuduğu bloklar (#142).

Blok türü ve markdown ortak formattır; başlık yolu ve sıra kitap okuyucudaki gibi sonradan,
sayfaların birleştirilmesinde verilir.
"""

from pydantic import BaseModel

from app.schemas.textbook import BlockType


class ExtractedBlock(BaseModel):
    """Sayfa görüntüsünden okunan blok: tür ve markdown."""

    block_type: BlockType
    markdown: str


class PageExtraction(BaseModel):
    """Sayfanın okuma sırasındaki blokları; model emin değilse unreadable doludur."""

    blocks: list[ExtractedBlock]
    unreadable: bool = False
