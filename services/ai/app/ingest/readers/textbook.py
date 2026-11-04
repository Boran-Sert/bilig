"""Ders kitabı okuyucusu (hazırlık hattı A5, #129, #269): kaynak PDF'ini bloklara çevirip yazar.

PDF depodan okunur, mevcut kitap okuyucusu (pdf.read_textbook) başlık yollu blokları üretir ve
bloklar content_block tablosuna yazılır. Sayfa sonunda bölünen paragrafı okuyucu tek blok yapar
(ilk sayfasının satırına yazılır); italik "*...*" markdown'da korunur; arama metni başlık yolu
ve markdown'dır. Kitaptan hiç blok çıkmazsa ya da metin katmanı bozuk kalan veya harfi
çözülemeyen sayfa varsa kaynak için ayrıntılı VALIDATION_FAILED inceleme kaydı açılır. Adım
tekrar çalıştırılabilir: ikinci çalışmada kopya blok ve kayıt oluşmaz.
"""

import asyncio
from typing import TYPE_CHECKING

from app.db.queries.content import save_content_blocks
from app.db.queries.review import open_source_review
from app.db.queries.source import fetch_source_title
from app.ingest import pdf
from app.ingest.validators import page_problems
from app.schemas.review import SourceProblem
from app.storage import source_key

if TYPE_CHECKING:
    from app.ingest.pipeline import IngestContext


async def extract_textbook(source_id: int, context: "IngestContext") -> None:
    """Kitap PDF'ini okuyup bloklarını content_block'a yazar; sorun varsa inceleme kaydı açar."""
    content = await asyncio.to_thread(context.storage.read, source_key(source_id))
    async with context.connect() as connection:
        title = await fetch_source_title(connection, source_id)
    reading = await asyncio.to_thread(pdf.read_textbook, content, title)
    problems = page_problems(reading.pages)
    if not reading.blocks:
        problems.append(SourceProblem(code="NO_CONTENT"))
    async with context.connect() as connection:
        await save_content_blocks(connection, source_id, reading.blocks)
        if problems:
            await open_source_review(connection, source_id, "VALIDATION_FAILED", problems)
