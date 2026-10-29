"""Öğretim programının ünite tablolarından üniteler (hazırlık hattı A1).

Programın "Ünite, süre ve içerik tabloları" bölümünde her ünite "1. ÜNİTE: GİRİŞ" satırıyla
başlar; sınıf, sayfanın üstündeki "9. SINIF" satırından gelir. Program Word'den üretildiği için
bu satırlar metin katmanında sağlamdır ve düzenli ifadeyle okunur. Veritabanında ünitenin sadece
sınıfı, sırası ve adı tutulduğu için tablonun geri kalanı (süre, dönem, metin sayıları) okunmaz.
Ünite kazanım gruplarına adındaki türle bağlanır (plan A1): Hikâye, Roman, Masal → A.2;
Şiir → A.1; Tiyatro → A.3; Makale, Deneme → A.4. Tür, ünite adının kelimelerinden biri olmalıdır
("Romanı" bağlanmaz); şapkalı harf şapkasız da eşleşir. Kurala uymayan ünite (Giriş, Mektup)
kazanıma bağlanmaz.

Komut: uv run python -m app.ingest.readers.program_units <pdf> [--dry-run]
Önce kazanımlar yüklenmiş olmalıdır (app.ingest.readers.program).
"""

import argparse
import asyncio
import re
from collections.abc import Iterable
from pathlib import Path

import structlog

from app.config import LogSettings, get_settings
from app.constants import PROGRAM_CURRICULUM_NAME, PROGRAM_SUBJECT_CODE, UNIT_GROUP_KEYWORDS
from app.db.pool import close_pool, open_pool
from app.db.queries.program import save_units
from app.ingest import pdf
from app.log import configure_logging
from app.schemas.program import CurriculumUnit
from app.text.turkish import normalize_nfc, tr_lower, tr_upper

_GRADE = re.compile(r"^\s*(9|10|11|12)\. ?SINIF\s*$")
_UNIT = re.compile(r"^\s*(\d{1,2})\.\s*ÜNİTE\s*:\s*(.+?)(?:\s{2,}|$)")
_WORD_PART = re.compile(r"([ /(-]+)")
_HYPHEN_SPACES = re.compile(r"\s*-\s*")
_LOWER_WORDS = frozenset({"ve"})
_CIRCUMFLEX_FOLD = str.maketrans("âîû", "aiu")


def main(argv: list[str] | None = None) -> None:
    """Komut satırından program PDF'inin ünitelerini okur; --dry-run yoksa veritabanına yazar."""
    parser = argparse.ArgumentParser(description="Read curriculum units from a curriculum PDF.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="do not write to the database")
    arguments = parser.parse_args(argv)
    configure_logging(LogSettings())
    units = read_units(arguments.pdf)
    structlog.get_logger().info(
        "units parsed",
        units=[f"{unit.grade}.{unit.unit_no} {unit.title} {unit.group_codes}" for unit in units],
    )
    if not arguments.dry_run:
        asyncio.run(_save(units), loop_factory=asyncio.SelectorEventLoop)


def read_units(path: Path) -> list[CurriculumUnit]:
    """Program PDF'ini okuyup bütün sınıfların ünitelerini döner."""
    lines = pdf.read_lines(path)
    return parse_units(lines)


def parse_units(lines: Iterable[str]) -> list[CurriculumUnit]:
    """Program metninin satırlarından üniteleri sınıf ve sıra bilgisiyle çıkarır."""
    units: list[CurriculumUnit] = []
    grade: int | None = None
    for line in lines:
        text = normalize_nfc(line)
        if grade_match := _GRADE.search(text):
            grade = int(grade_match[1])
        unit_match = _UNIT.match(text)
        if not unit_match or grade is None:
            continue
        unit_no = int(unit_match[1])
        expected = sum(unit.grade == grade for unit in units) + 1
        if unit_no != expected:
            raise ValueError(f"Grade {grade} unit {unit_no} found, expected unit {expected}")
        title = unit_title(unit_match[2])
        units.append(
            CurriculumUnit(
                grade=grade, unit_no=unit_no, title=title, group_codes=unit_group_codes(title)
            )
        )
    if not units:
        raise ValueError("No curriculum units found in program text")
    return units


def unit_title(text: str) -> str:
    """Büyük harfli ünite adını kelime kelime Türkçe başlık düzenine çevirir."""
    parts = _WORD_PART.split(_HYPHEN_SPACES.sub("-", text.strip()))
    words = [part if _WORD_PART.fullmatch(part) else _title_word(part) for part in parts]
    return "".join(words)


def _title_word(word: str) -> str:
    """Kelimeyi ilk harfi büyük, gerisi küçük yazar; bağlaçları küçük bırakır."""
    lower = tr_lower(word)
    return lower if lower in _LOWER_WORDS else tr_upper(lower[:1]) + lower[1:]


def unit_group_codes(title: str) -> list[str]:
    """Ünite adındaki türlere göre bağlanacağı kazanım gruplarını sırayla döner."""
    words = re.findall(r"\w+", tr_lower(title).translate(_CIRCUMFLEX_FOLD))
    codes: list[str] = []
    for word in words:
        code = UNIT_GROUP_KEYWORDS.get(word)
        if code and code not in codes:
            codes.append(code)
    return codes


async def _save(units: list[CurriculumUnit]) -> None:
    """Üniteleri ve kazanım bağlarını yazar, sonucu log'a yazar."""
    pool = await open_pool(get_settings().database)
    try:
        async with pool.connection() as connection:
            summary = await save_units(
                connection, PROGRAM_SUBJECT_CODE, PROGRAM_CURRICULUM_NAME, units
            )
    finally:
        await close_pool()
    structlog.get_logger().info("units saved", **summary.model_dump())


if __name__ == "__main__":
    main()
