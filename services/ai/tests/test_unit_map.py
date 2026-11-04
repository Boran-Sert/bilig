"""Test adından ünite bulmayı (#130) kural metniyle ve gerçek Postgres'le sınar.

Kural dosyası testte de okunur: repodaki data/unit_map.txt gerçek ÖDSGM test adlarını doğru
üniteye götürmelidir. Veritabanı testi kendi müfredatını ve kaynağını yazar, test bitince geri
alınır.
"""

import psycopg
import pytest
from psycopg.rows import TupleRow

from app.constants import PROGRAM_CURRICULUM_NAME, PROGRAM_SUBJECT_CODE, REPOSITORY_DATA_DIR
from app.db.queries.unit import fetch_unit_id
from app.ingest.unit_map import UnitMapError, find_unit_title, load_unit_map, parse_unit_map

Connection = psycopg.AsyncConnection[TupleRow]

PROGRAM_SEED = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES (%(subject_code)s, 'Türk Dili ve Edebiyatı')
    ON CONFLICT (code) DO UPDATE SET code = EXCLUDED.code
    RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, %(curriculum_name)s, 'LEGACY', 2018 FROM subject_row
    ON CONFLICT (subject_id, name) DO UPDATE SET name = EXCLUDED.name
    RETURNING id
), unit_rows AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT curriculum_row.id, unit.grade, 91, unit.title
    FROM curriculum_row, (VALUES (12, 'Işık'), (11, 'Gölge')) AS unit (grade, title)
    RETURNING id
), user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Ünite Testi' FROM tenant
    RETURNING id
)
INSERT INTO source_document (title, sha256, file_path, uploaded_by, grade)
SELECT 'Müfredatsız Test', repeat(%(hash)s, 64), 'sources/0.pdf', user_row.id, %(grade)s
FROM user_row
RETURNING id
"""

SEED = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('UNITE', 'Ünite Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Ünite Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), unit_rows AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT curriculum_row.id, 12, unit.unit_no, unit.title
    FROM curriculum_row, (VALUES (1, 'Giriş'), (2, 'Şiir'), (3, 'Işık')) AS unit (unit_no, title)
    RETURNING id
), user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Ünite Testi' FROM tenant
    RETURNING id
)
INSERT INTO source_document (curriculum_id, title, sha256, file_path, uploaded_by)
SELECT curriculum_row.id, 'ÖDSGM 12 Şiir Kazanım Testi 1', repeat('d', 64), 'sources/0.pdf',
    user_row.id
FROM curriculum_row, user_row
RETURNING id
"""


def test_parse_skips_comments_and_blank_lines() -> None:
    """Boş satırlar ve # ile başlayan satırlar atlanır; kurallar sırasını korur."""
    rules = parse_unit_map("# not\n\nşiir = Şiir\n roman=Roman \n")

    assert [(rule.keyword, rule.unit_title) for rule in rules] == [
        ("şiir", "Şiir"),
        ("roman", "Roman"),
    ]


@pytest.mark.parametrize("line", ["şiir", "= Şiir", "şiir ="])
def test_parse_reports_broken_line_with_its_number(line: str) -> None:
    """Anahtarı ya da ünite adı eksik satır numarasıyla hata verir."""
    with pytest.raises(UnitMapError, match="line 2"):
        parse_unit_map(f"roman = Roman\n{line}\n")


@pytest.mark.parametrize(
    ("source_title", "expected"),
    [
        ("ÖDSGM 12 Roman Kazanım Testi 3", "Roman"),
        ("ÖDSGM 12 Hikaye Kazanım Testi 1", "Hikâye"),
        ("ÖDSGM 12 HİKÂYE Kazanım Testi 1", "Hikâye"),
        ("ÖDSGM 12 Deneme - Söylev (Nutuk) Kazanım Testi 2", "Deneme"),
        ("ÖDSGM 12 Söylev (Nutuk) Kazanım Testi 1", "Söylev (Nutuk)"),
        ("ÖDSGM 12 Giriş Kazanım Testi 1", "Giriş"),
        ("Bilinmeyen Yayınevi Denemesi", None),
    ],
)
def test_repository_map_finds_unit_of_real_test_names(
    source_title: str, expected: str | None
) -> None:
    """Repodaki kural dosyası gerçek test adlarını doğru üniteye götürür."""
    assert (
        find_unit_title(source_title, load_unit_map(REPOSITORY_DATA_DIR / "unit_map.txt"))
        == expected
    )


def test_longest_matching_keyword_wins() -> None:
    """Birden çok anahtar uyarsa en uzunu seçilir."""
    rules = parse_unit_map("deneme = Deneme\ndeneme - söylev = Söylev\n")

    assert find_unit_title("12 Deneme - Söylev Testi", rules) == "Söylev"


@pytest.mark.asyncio
async def test_unit_is_found_by_title_with_turkish_letters(db: Connection) -> None:
    """Ünite adı Türkçe harf kurallarıyla bulunur; olmayan ad boş döner."""
    row = await (await db.execute(SEED)).fetchone()
    assert row is not None
    source_id = int(row[0])

    assert await fetch_unit_id(db, source_id, "şiir") is not None
    assert await fetch_unit_id(db, source_id, "IŞIK") is not None
    assert await fetch_unit_id(db, source_id, "Roman") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("grade", "found", "missing"), [(None, "ışık", "Gölge"), (11, "gölge", "Işık")]
)
async def test_source_without_curriculum_uses_program_units_of_its_grade(
    db: Connection, grade: int | None, found: str, missing: str
) -> None:
    """Müfredatı boş kaynak programın ünitelerinde arar; sınıfı boşsa 12. sınıf ünitesini alır."""
    values = {
        "subject_code": PROGRAM_SUBJECT_CODE,
        "curriculum_name": PROGRAM_CURRICULUM_NAME,
        "hash": "e" if grade is None else "f",
        "grade": grade,
    }
    row = await (await db.execute(PROGRAM_SEED, values)).fetchone()
    assert row is not None
    source_id = int(row[0])

    assert await fetch_unit_id(db, source_id, found) is not None
    assert await fetch_unit_id(db, source_id, missing) is None
