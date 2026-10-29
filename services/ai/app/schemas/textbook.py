"""Ders kitabından okunan blokların modeli (hazırlık hattı A5, plan 13.6).

Blok content_block tablosunun bir satırıdır: tür (block_type), markdown, başlık yolu, ilk
sayfası ve o sayfadaki sırası (position). Başlık yolu kaynak adı ve üstteki başlıklardır
("TDE 12 Ders Kitabı › ŞİİR › Cumhuriyet Dönemi Halk Şiiri"); arama metni başlık yolu ve
markdown'dır. Modeller Fatih'in kitap okuyucusundan (#129) aynen alındı.
"""

from typing import Literal

from pydantic import BaseModel

BlockType = Literal["BILGI", "ALINTI", "ETKINLIK", "METIN", "BASLIK"]


class TextbookBlock(BaseModel):
    """Kitaptan okunan blok: tür, markdown, başlık yolu, ilk sayfası, sırası ve sayfaları."""

    block_type: BlockType
    markdown: str
    title_path: str
    page_no: int
    position: int
    pages: list[int]

    @property
    def search_text(self) -> str:
        """Arama metni: başlık yolu ve markdown."""
        return f"{self.title_path}\n{self.markdown}"
