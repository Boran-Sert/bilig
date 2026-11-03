"""Doğrulama script'ini (#158) kendi ürettiğimiz kitap ve test PDF'leriyle sınar.

PDF'ler geçici klasöre yazılır; veritabanı testi kendi transaction'ında çalışır ve geri alınır.
"""

from pathlib import Path

import psycopg
import pytest
from psycopg.rows import TupleRow

from scripts.validate_sources import SourceReport, find_problems, format_report, validate_source
from tests.pdf_factory import lines_pdf
from tests.test_pdf_reader import FIRST_TEST
from tests.test_textbook_reader import build_book

Connection = psycopg.AsyncConnection[TupleRow]

SEED_UNITS = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('DOGRTEST', 'Doğrulama Testi') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Doğrulama Testi Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), unit_row AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT id, 12, 1, 'Roman' FROM curriculum_row
)
SELECT id FROM curriculum_row
"""


def make_report(**changes: object) -> SourceReport:
    """Sorunsuz bir kitap raporu kurar; verilen alanlar değiştirilir."""
    fields: dict[str, object] = {
        "title": "kitap",
        "kind": "TEXTBOOK",
        "pages": 2,
        "page_sources": {"TEXT": 2},
        "notes": {},
        "blocks": {"METIN": 3},
        "questions": 0,
        "exams": 0,
        "reviews": [],
        "problems": [],
    }
    return SourceReport.model_validate(fields | changes)


def test_clean_report_has_no_problems() -> None:
    """Sayfaları okunmuş, blokları yazılmış kitapta sorun yoktur."""
    assert find_problems(make_report()) == []


def test_weak_pages_and_review_items_are_reported() -> None:
    """Boş sayfa, zayıf metin katmanı, inceleme kaydı ve boş sonuç sorun olarak yazılır."""
    report = make_report(
        page_sources={"TEXT": 1, "EMPTY": 1},
        notes={"LOW_TEXT_LAYER": 2},
        blocks={},
        reviews=["VALIDATION_FAILED"],
    )

    assert find_problems(report) == [
        "inceleme kaydı: VALIDATION_FAILED",
        "1 sayfa boş okundu",
        "2 sayfanın metin katmanı zayıf",
        "hiç blok yazılmadı",
    ]


@pytest.mark.asyncio
async def test_textbook_and_test_are_validated_end_to_end(db: Connection, tmp_path: Path) -> None:
    """Kitap blok, test soru üretir; rapor sayıları ve markdown çıktısı doğrudur."""
    book_path = tmp_path / "kitap.pdf"
    book_path.write_bytes(build_book())
    test_path = tmp_path / "ÖDSGM 12 Roman Kazanım Testi 1.pdf"
    test_path.write_bytes(lines_pdf([FIRST_TEST]))
    row = await (await db.execute(SEED_UNITS)).fetchone()
    assert row is not None
    curriculum_id = int(row[0])

    book = await validate_source(db, book_path, "TEXTBOOK", curriculum_id, tmp_path)
    test = await validate_source(db, test_path, "TEST", curriculum_id, tmp_path)

    assert book.pages == 2 and sum(book.blocks.values()) == 3 and book.problems == []
    assert test.questions == 3 and test.exams == 1 and test.problems == []
    assert "## ÖDSGM 12 Roman Kazanım Testi 1 (TEST)" in format_report(test)
