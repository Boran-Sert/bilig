"""Görüntü yolunun çıktısı: Claude'un sayfa görüntüsünden okuduğu bloklar (#142).

Blok türü ve markdown ortak formattır; kitap motoru gibi yalnız başlık, bilgi kutusu ve metin
üretilir. Başlık yolu ve sıra sayfa kitabın bloklarına eklenirken verilir.
"""

from typing import Literal

from pydantic import BaseModel

PageBlockType = Literal["BASLIK", "BILGI", "METIN"]


class ExtractedBlock(BaseModel):
    """Sayfa görüntüsünden okunan blok: tür ve markdown."""

    block_type: PageBlockType
    markdown: str


class PageExtraction(BaseModel):
    """Sayfanın okuma sırasındaki blokları; model emin değilse unreadable doludur."""

    blocks: list[ExtractedBlock]
    unreadable: bool = False
