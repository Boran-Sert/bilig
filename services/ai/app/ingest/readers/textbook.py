"""Ders kitabı okuyucusu (hazırlık hattı A5, #129): kaynak PDF'ini bloklara çevirip yazar.

PDF depodan okunur, mevcut kitap okuyucusu (pdf.read_textbook) başlık yollu blokları üretir ve
bloklar content_block tablosuna yazılır. Sayfa sonunda bölünen paragrafı okuyucu tek blok yapar
(ilk sayfasının satırına yazılır); italik "*...*" markdown'da korunur; arama metni başlık yolu
ve markdown'dır. Adım tekrar çalıştırılabilir: ikinci çalışmada kopya blok oluşmaz.
"""

import asyncio
from typing import TYPE_CHECKING

from app.db.queries.content import read_source_title, save_content_blocks
from app.ingest import pdf
from app.storage import source_key

if TYPE_CHECKING:
    from app.ingest.pipeline import IngestContext


async def extract_textbook(source_id: int, context: "IngestContext") -> None:
    """Kitap PDF'ini okuyup bloklarını content_block'a yazar."""
    content = await asyncio.to_thread(context.storage.read, source_key(source_id))
    async with context.connect() as connection:
        title = await read_source_title(connection, source_id)
    reading = await asyncio.to_thread(pdf.read_textbook, content, title)
    async with context.connect() as connection:
        await save_content_blocks(connection, source_id, reading.blocks)
