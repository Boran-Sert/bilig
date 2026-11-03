"""Kaynak profili (A4): stil sayımı, stile göre profil bulma ve profili satırlara uygulama.

Profil bir kitap ya da serinin görünüm kurallarıdır (profiles/*.yaml, biçimi profiles/README.md).
Akış: PDF'in satırları stilleriyle okunur (font, boyut, kalın, italik, metnin durduğu kutunun
rengi); stiller harf sayısıyla sayılır (stil izi); kayıtlı profillerden stilleri belgenin
harflerinin yeterli payını kapsayan en iyisi seçilir; seçilen profil satırları stil -> blok türü
kuralıyla sınıflar. Eşleşme yoksa profil adı boş kalır ve adım öneri ister (#128, kapsam dışı).
Sayım belgenin harflerinden ve sıralı anahtarlardan yapılır, aynı PDF her seferinde aynı sonucu
verir. Çalışan run_profile_step'i hazırlık hattının adımı olarak çağırır; kaynağa profil adı
yazılır (source_document.profile_name).
"""

import asyncio
from collections import Counter
from pathlib import Path

import yaml
from psycopg import AsyncConnection
from pydantic import ValidationError

from app.ingest import pdf
from app.ingest.pdf import book_reader
from app.jobs.postgres_queue import ConnectionFactory
from app.schemas.profile import (
    ClassifiedLine,
    Profile,
    ProfileMatch,
    StyleCount,
    StyledLine,
    StyleKey,
)
from app.storage import FileStorage, source_key

PROFILE_DIR = Path(__file__).resolve().parents[2] / "profiles"
PROFILE_SUFFIX = ".yaml"
PROFILE_MATCH_MIN_SHARE = 0.85

SET_PROFILE_NAME = """
UPDATE source_document
SET profile_name = %(profile_name)s, updated_at = now()
WHERE id = %(source_id)s
"""


class ProfileError(ValueError):
    """Profil dosyası okunamadı ya da biçimi yanlış."""


def load_profiles(directory: Path = PROFILE_DIR) -> list[Profile]:
    """Klasördeki profil dosyalarını ada göre sıralı okur; dosya adı (uzantısız) profil adıdır."""
    profiles = []
    for path in sorted(directory.glob(f"*{PROFILE_SUFFIX}")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            profile = Profile.model_validate({"name": path.stem, **data})
        except (yaml.YAMLError, ValidationError, TypeError) as error:
            raise ProfileError(f"Invalid profile {path.name}: {error}") from error
        profiles.append(profile)
    return profiles


def read_styled_lines(source: pdf.PdfSource) -> list[StyledLine]:
    """PDF'in satırlarını stilleriyle okur."""
    with pdf._reading():
        pages = book_reader.read_document(source, book_reader.ocr_settings())
    return styled_lines(pages)


def styled_lines(pages: list[book_reader.PageIR]) -> list[StyledLine]:
    """Sayfa satırlarını stil sayımlarıyla birlikte StyledLine'a çevirir."""
    result = []
    for page in pages:
        boxes = filled_boxes(page)
        for line in page.lines:
            counts = count_line(line, box_color_of(line, boxes))
            result.append(
                StyledLine(
                    page_no=page.page_no,
                    text=line.text,
                    style=counts[0].style,
                    counts=counts,
                )
            )
    return result


def filled_boxes(page: book_reader.PageIR) -> list[book_reader.Shape]:
    """Sayfadaki dolgulu kutuları verir; sayfayı kaplayan zemin kutuları sayılmaz."""
    limit = page.width * page.height * book_reader.BOX_MAX_PAGE_SHARE
    return [
        shape
        for shape in page.shapes
        if shape.kind == "BOX"
        and shape.fill
        and (shape.x1 - shape.x0) * (shape.y1 - shape.y0) <= limit
    ]


def box_color_of(line: book_reader.Line, boxes: list[book_reader.Shape]) -> str | None:
    """Satırı içeren en küçük kutunun dolgu rengini verir; kutuda değilse boş döner."""
    holders = [box for box in boxes if book_reader.inside(line, box)]
    if not holders:
        return None
    smallest = min(holders, key=lambda box: (box.x1 - box.x0) * (box.y1 - box.y0))
    return smallest.fill


def count_line(line: book_reader.Line, box_color: str | None) -> list[StyleCount]:
    """Satırın stillerini harf sayısıyla verir; en çok harfli stil başta gelir."""
    tally: Counter[StyleKey] = Counter()
    for word in line.words:
        font = word.font.split("+", 1)[-1]
        style = StyleKey(
            font=font, size=word.size, bold=word.bold, italic=word.italic, box_color=box_color
        )
        tally[style] += len(word.text)
    return sort_counts(tally)


def sort_counts(tally: Counter[StyleKey]) -> list[StyleCount]:
    """Sayımları çoktan aza, eşitlikte stil anahtarına göre sıralar."""
    ordered = sorted(tally.items(), key=lambda item: (-item[1], item[0].sort_key()))
    return [StyleCount(style=style, chars=chars) for style, chars in ordered]


def count_styles(lines: list[StyledLine]) -> list[StyleCount]:
    """Belgedeki stilleri harf sayısıyla verir (stil izi); sıra her çalışmada aynıdır."""
    tally: Counter[StyleKey] = Counter()
    for line in lines:
        for count in line.counts:
            tally[count.style] += count.chars
    return sort_counts(tally)


def match_profile(counts: list[StyleCount], profiles: list[Profile]) -> ProfileMatch:
    """Stilleri belge harflerinin yeterli payını kapsayan en iyi profili bulur; yoksa boş döner."""
    total = sum(count.chars for count in counts)
    best = ProfileMatch(profile_name=None, share=0.0)
    if total == 0:
        return best
    for profile in profiles:
        known = {rule.style for rule in profile.styles}
        share = sum(count.chars for count in counts if count.style in known) / total
        if share >= PROFILE_MATCH_MIN_SHARE and share > best.share:
            best = ProfileMatch(profile_name=profile.name, share=share)
    return best


def apply_profile(profile: Profile, lines: list[StyledLine]) -> list[ClassifiedLine]:
    """Satırları baskın stillerine göre blok türüne çevirir; profilde olmayan stil boş kalır."""
    return [
        ClassifiedLine(
            page_no=line.page_no,
            text=line.text,
            style=line.style,
            block_type=profile.block_type_of(line.style),
        )
        for line in lines
    ]


async def save_profile_name(
    connection: AsyncConnection, source_id: int, profile_name: str | None
) -> None:
    """Kaynağın profil adını yazar; eşleşme yoksa boşaltır, adım tekrar çalışınca aynı kalır."""
    await connection.execute(
        SET_PROFILE_NAME, {"source_id": source_id, "profile_name": profile_name}
    )


async def run_profile_step(
    source_id: int,
    connect: ConnectionFactory,
    storage: FileStorage,
    profiles: list[Profile] | None = None,
) -> ProfileMatch:
    """Kaynağın profilini bulup adını yazar; eşleşme yoksa boş sonuç döner (öneri #128)."""
    content = await asyncio.to_thread(storage.read, source_key(source_id))
    lines = await asyncio.to_thread(read_styled_lines, content)
    registered = profiles if profiles is not None else await asyncio.to_thread(load_profiles)
    match = match_profile(count_styles(lines), registered)
    async with connect() as connection:
        await save_profile_name(connection, source_id, match.profile_name)
    return match
