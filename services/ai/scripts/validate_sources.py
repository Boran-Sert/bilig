"""Gerçek kaynaklarla hazırlık hattı doğrulaması (A5, #158).

python -m scripts.validate_sources --textbook kitap.pdf --test test.pdf komutu verilen PDF'leri
hattın kayıtlı adımlarından (REGISTERED, EXTRACT) geçirir ve kaynak başına bir rapor yazar:
sayfa kaynakları ve okuma notları, blok ve soru sayıları, açılan inceleme kayıtları ve bulunan
sorunlar. Bu adımlar Claude çağırmaz; Claude'lu adımlar (görüntü yolu, kazanım eşleştirme) hatta
henüz bağlı olmadığı için burada sahte bir çıktıya da gerek yoktur. Her şey tek transaction'da
yazılır ve sonunda geri alınır, veritabanında kayıt kalmaz; PDF'ler repoya konmaz. Test PDF'lerinin
adı ünite adını taşımalıdır (data/unit_map.txt); ünite tabloları geçici olarak bu dosyadan kurulur.
Aynı dosya daha önce yüklenmiş olsa da çakışmasın diye kayda rastgele tuzlu bir sha256 yazılır.
Veritabanı adresi DATABASE_URL'den okunur.
"""

import argparse
import asyncio
import hashlib
import os
import tempfile
from collections import Counter
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import psycopg
from psycopg.rows import TupleRow
from pydantic import BaseModel

from app.config import load_ingest_settings
from app.ingest import pdf
from app.ingest.pipeline import IngestContext, register_source
from app.ingest.readers.test import extract_tests
from app.ingest.readers.textbook import extract_textbook
from app.ingest.unit_map import load_unit_map
from app.jobs.postgres_queue import PostgresJobQueue
from app.schemas.pdf import PageReport
from app.storage import LocalFileStorage, source_key

Connection = psycopg.AsyncConnection[TupleRow]
SourceKind = Literal["TEXTBOOK", "TEST"]

SEED_CURRICULUM = """
WITH subject_row AS (
    INSERT INTO subject (code, name) VALUES ('DOGRULAMA', 'Doğrulama') RETURNING id
), curriculum_row AS (
    INSERT INTO curriculum (subject_id, name, model, year)
    SELECT id, 'Doğrulama Programı', 'LEGACY', 2018 FROM subject_row
    RETURNING id
), unit_rows AS (
    INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
    SELECT curriculum_row.id, 12, row_number() OVER (), title
    FROM curriculum_row, unnest(%(titles)s::text[]) AS title
)
SELECT id FROM curriculum_row
"""
INSERT_SOURCE = """
WITH user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Doğrulama' FROM tenant
    RETURNING id
)
INSERT INTO source_document (curriculum_id, kind, title, sha256, file_path, uploaded_by)
SELECT %(curriculum_id)s, %(kind)s, %(title)s, %(sha256)s, 'sources/0.pdf', user_row.id
FROM user_row
RETURNING id
"""
COUNT_PAGES = "SELECT count(*) FROM source_page WHERE source_document_id = %s"
COUNT_BLOCKS = """
SELECT content_block.block_type, count(*) FROM content_block
JOIN source_page ON source_page.id = content_block.source_page_id
WHERE source_page.source_document_id = %s GROUP BY 1
"""
COUNT_QUESTIONS = """
SELECT count(DISTINCT exam_question.question_id), count(DISTINCT exam.id) FROM exam
LEFT JOIN exam_question ON exam_question.exam_id = exam.id
WHERE exam.source_document_id = %s
"""
READ_REVIEWS = "SELECT reason FROM review_item WHERE source_document_id = %s ORDER BY reason"


class SourceReport(BaseModel):
    """Bir kaynağın doğrulama sonucu: okuma özeti, yazılanlar ve bulunan sorunlar."""

    title: str
    kind: SourceKind
    pages: int
    page_sources: dict[str, int]
    notes: dict[str, int]
    blocks: dict[str, int]
    questions: int
    exams: int
    reviews: list[str]
    problems: list[str]


async def fetch_id(connection: Connection, query: str, params: Mapping[str, object]) -> int:
    """Sorguyu çalıştırıp dönen ilk satırın ilk değerini sayı olarak verir."""
    row = await (await connection.execute(query, params)).fetchone()
    if row is None:
        raise RuntimeError("Query returned no row")
    return int(row[0])


async def count_rows(connection: Connection, query: str, source_id: int) -> list[TupleRow]:
    """Sorguyu kaynak numarasıyla çalıştırıp bütün satırları döner."""
    return await (await connection.execute(query, (source_id,))).fetchall()


def read_page_reports(content: bytes, kind: SourceKind) -> list[PageReport]:
    """PDF'i kaynak türünün okuyucusuyla okuyup sayfa raporlarını verir."""
    if kind == "TEXTBOOK":
        return pdf.read_textbook(content, "Doğrulama").pages
    return pdf.read_questions(content).pages


def find_problems(report: SourceReport) -> list[str]:
    """Raporda dikkat gerektiren durumları metin olarak sıralar."""
    problems = [f"inceleme kaydı: {reason}" for reason in report.reviews]
    if report.pages == 0:
        problems.append("hiç sayfa kaydedilmedi")
    if report.page_sources.get("EMPTY"):
        problems.append(f"{report.page_sources['EMPTY']} sayfa boş okundu")
    if report.notes.get("LOW_TEXT_LAYER"):
        problems.append(f"{report.notes['LOW_TEXT_LAYER']} sayfanın metin katmanı zayıf")
    if report.kind == "TEXTBOOK" and not report.blocks:
        problems.append("hiç blok yazılmadı")
    if report.kind == "TEST" and not report.questions:
        problems.append("hiç soru yazılmadı")
    return problems


async def validate_source(
    connection: Connection, path: Path, kind: SourceKind, curriculum_id: int, storage_dir: Path
) -> SourceReport:
    """PDF'i hattın adımlarından geçirir ve raporunu çıkarır."""
    content = path.read_bytes()
    params = {
        "curriculum_id": curriculum_id,
        "kind": kind,
        "title": path.stem,
        "sha256": hashlib.sha256(content + os.urandom(16)).hexdigest(),
    }
    source_id = await fetch_id(connection, INSERT_SOURCE, params)
    context = make_context(connection, storage_dir)
    context.storage.write(source_key(source_id), content)
    await register_source(source_id, context)
    await (extract_textbook if kind == "TEXTBOOK" else extract_tests)(source_id, context)
    reports = await asyncio.to_thread(read_page_reports, content, kind)
    counts = (await count_rows(connection, COUNT_QUESTIONS, source_id))[0]
    report = SourceReport(
        title=path.stem,
        kind=kind,
        pages=int((await count_rows(connection, COUNT_PAGES, source_id))[0][0]),
        page_sources=dict(Counter(page.source for page in reports)),
        notes=dict(Counter(note for page in reports for note in page.notes)),
        blocks={
            str(row[0]): int(row[1])
            for row in await count_rows(connection, COUNT_BLOCKS, source_id)
        },
        questions=int(counts[0]),
        exams=int(counts[1]),
        reviews=[str(row[0]) for row in await count_rows(connection, READ_REVIEWS, source_id)],
        problems=[],
    )
    return report.model_copy(update={"problems": find_problems(report)})


def make_context(connection: Connection, storage_dir: Path) -> IngestContext:
    """Aynı bağlantıyı ve geçici klasörü kullanan hat bağlamını kurar."""

    @asynccontextmanager
    async def connect() -> AsyncIterator[Connection]:
        """Verilen bağlantıyı döner."""
        yield connection

    return IngestContext(
        connect=connect, queue=PostgresJobQueue(connect), storage=LocalFileStorage(storage_dir)
    )


def format_report(report: SourceReport) -> str:
    """Raporu markdown olarak yazar."""
    lines = [f"## {report.title} ({report.kind})", ""]
    lines.append(
        f"- sayfa: {report.pages}; kaynaklar: {report.page_sources}; notlar: {report.notes}"
    )
    if report.kind == "TEXTBOOK":
        lines.append(f"- bloklar: {report.blocks}")
    else:
        lines.append(f"- test: {report.exams}; yazılan soru: {report.questions}")
    lines.append("- sorunlar:" + ("" if report.problems else " yok"))
    lines.extend(f"  - {problem}" for problem in report.problems)
    return "\n".join(lines)


async def run(textbooks: list[Path], tests: list[Path]) -> list[SourceReport]:
    """PDF'leri tek transaction'da doğrular; sonunda geri alır."""
    sources: list[tuple[Path, SourceKind]] = [(path, "TEXTBOOK") for path in textbooks]
    sources += [(path, "TEST") for path in tests]
    titles = sorted(
        {rule.unit_title for rule in load_unit_map(load_ingest_settings().unit_map_path)}
    )
    reports: list[SourceReport] = []
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as connection:
        curriculum_id = await fetch_id(connection, SEED_CURRICULUM, {"titles": titles})
        with tempfile.TemporaryDirectory() as storage_dir:
            for path, kind in sources:
                reports.append(
                    await validate_source(connection, path, kind, curriculum_id, Path(storage_dir))
                )
        await connection.rollback()
    return reports


def main() -> None:
    """Komut satırı argümanlarını okuyup raporları yazar."""
    parser = argparse.ArgumentParser(description="Hazırlık hattını gerçek PDF'lerle doğrular.")
    parser.add_argument("--textbook", type=Path, action="append", default=[])
    parser.add_argument("--test", type=Path, action="append", default=[])
    arguments = parser.parse_args()
    for report in asyncio.run(
        run(arguments.textbook, arguments.test), loop_factory=asyncio.SelectorEventLoop
    ):
        print(format_report(report))


if __name__ == "__main__":
    main()
