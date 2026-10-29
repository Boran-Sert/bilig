"""Öğretim programının ünite tablolarından ünite okumayı ve kural bağlarını test eder (A1)."""

from pathlib import Path

import pytest

from app.ingest.readers.program_units import (
    parse_units,
    read_units,
    unit_group_codes,
    unit_title,
)
from app.schemas.program import CurriculumUnit
from tests.pdf_factory import lines_pdf

PROGRAM_LINES = [
    "3.3. ÜNİTE, SÜRE VE İÇERİK TABLOLARI",
    "9.SINIF",
    "1. ÜNİTE: GİRİŞ                                  I. DÖNEM",
    "SÜRE: 2 HAFTA",
    "OKUMA",
    "1. Edebiyatın tarih ve din ile ilişkisi",
    "2. ÜNİTE: HİKÂYE",
    "10. SINIF",
    "1. ÜNİTE: GİRİŞ",
    "2. ÜNİTE: MEKTUP/E -POSTA",
    "3. ÜNİTE: MASAL/FABL                     II. DÖNEM",
    "Bkz. 4. ÜNİTE: ŞİİR",
    "Bu tablo 12. SINIF için de geçerlidir.",
    "4.ÜNİTE: SOHBET VE FIKRA                 II. DÖNEM",
    "  5. ÜNİTE: GI\N{COMBINING DOT ABOVE}RI\N{COMBINING DOT ABOVE}Ş",
]


def test_parse_units_reads_grade_number_and_title() -> None:
    """Ünite satırları sınıf başlığı altında sırayla okunur; cümle içindekiler sayılmaz."""
    assert parse_units(PROGRAM_LINES) == [
        CurriculumUnit(grade=9, unit_no=1, title="Giriş", group_codes=[]),
        CurriculumUnit(grade=9, unit_no=2, title="Hikâye", group_codes=["A.2"]),
        CurriculumUnit(grade=10, unit_no=1, title="Giriş", group_codes=[]),
        CurriculumUnit(grade=10, unit_no=2, title="Mektup/E-Posta", group_codes=[]),
        CurriculumUnit(grade=10, unit_no=3, title="Masal/Fabl", group_codes=["A.2"]),
        CurriculumUnit(grade=10, unit_no=4, title="Sohbet ve Fıkra", group_codes=[]),
        CurriculumUnit(grade=10, unit_no=5, title="Giriş", group_codes=[]),
    ]


def test_units_before_any_grade_are_ignored() -> None:
    """Sınıf başlığından önce geçen ünite satırı (içindekiler) okunmaz."""
    assert parse_units(["1. ÜNİTE: GİRİŞ", "12. SINIF", "1. ÜNİTE: ŞİİR"]) == [
        CurriculumUnit(grade=12, unit_no=1, title="Şiir", group_codes=["A.1"])
    ]


@pytest.mark.parametrize(
    "lines",
    [["9. SINIF", "2. ÜNİTE: HİKÂYE"], ["9. SINIF", "1. ÜNİTE: GİRİŞ", "1. ÜNİTE: ŞİİR"]],
    ids=["skipped-unit", "repeated-unit"],
)
def test_unit_numbers_must_be_sequential(lines: list[str]) -> None:
    """Atlanan ya da tekrar eden ünite numarası okumayı hatayla durdurur."""
    with pytest.raises(ValueError, match="expected unit"):
        parse_units(lines)


def test_no_units_is_an_error() -> None:
    """Hiç ünite bulunamayan metin hata verir."""
    with pytest.raises(ValueError, match="No curriculum units"):
        parse_units(["9. SINIF", "Okuma"])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("HİKÂYE", "Hikâye"),
        ("ŞİİR", "Şiir"),
        ("ANI (HATIRA)", "Anı (Hatıra)"),
        ("SOHBET VE FIKRA", "Sohbet ve Fıkra"),
        ("MEKTUP/E -POSTA", "Mektup/E-Posta"),
        ("SÖYLEV (NUTUK)", "Söylev (Nutuk)"),
        ("  GÜNLÜK/BLOG ", "Günlük/Blog"),
    ],
)
def test_unit_title_is_turkish_title_case(text: str, expected: str) -> None:
    """Büyük harfli ünite adı kelime kelime Türkçe kurallarıyla başlık düzenine çevrilir."""
    assert unit_title(text) == expected


@pytest.mark.parametrize(
    ("title", "codes"),
    [
        ("Hikâye", ["A.2"]),
        ("Hikaye", ["A.2"]),
        ("Roman", ["A.2"]),
        ("Masal/Fabl", ["A.2"]),
        ("Şiir", ["A.1"]),
        ("Tiyatro", ["A.3"]),
        ("Makale", ["A.4"]),
        ("Deneme", ["A.4"]),
        ("Deneme - Söylev (Nutuk)", ["A.4"]),
        ("Roman ve Şiir", ["A.2", "A.1"]),
        ("Hikâye ve Roman", ["A.2"]),
        ("Giriş", []),
        ("Destan/Efsane", []),
        ("Romantizm", []),
    ],
)
def test_unit_group_codes_follow_plan_rules(title: str, codes: list[str]) -> None:
    """Ünite adındaki tür kazanım grubunu verir; kurala uymayan ünite bağlanmaz."""
    assert unit_group_codes(title) == codes


def test_read_units_reads_generated_pdf(tmp_path: Path) -> None:
    """Testte üretilen PDF'in metin katmanından üniteler okunur."""
    path = tmp_path / "program.pdf"
    path.write_bytes(lines_pdf([["11. SINIF", "1. ÜNİTE: GİRİŞ", "2. ÜNİTE: MAKALE"]]))

    assert [(unit.grade, unit.title, unit.group_codes) for unit in read_units(path)] == [
        (11, "Giriş", []),
        (11, "Makale", ["A.4"]),
    ]
