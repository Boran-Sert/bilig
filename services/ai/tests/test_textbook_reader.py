"""Ders kitabı okuyucusunu ve content_block yazımını test eder (#129).

Kitap kendi ürettiğimiz küçük PDF'lerle kurulur. Okuma testleri veritabanı istemez; yazma
testleri gerçek Postgres'te, geri alınan transaction'da çalışır: sayfa sonunda bölünen
paragrafın tek blok olması, italiğin korunması, arama metni ve adımın iki kez çalışınca kopya
blok üretmemesi.
"""

from pathlib import Path

import psycopg
import pytest
from psycopg.rows import TupleRow

from app.db.queries.content import save_content_blocks
from app.ingest import pdf
from app.ingest.pdf import ReaderOptions
from app.ingest.readers import page_image
from app.ingest.readers.textbook import extract_textbook
from app.schemas.page_extract import ExtractedBlock, PageExtraction
from app.schemas.pdf import PageReport, TextbookReading
from app.schemas.textbook import TextbookBlock
from app.storage import page_image_key, source_key
from tests.pdf_factory import Text, make_pdf
from tests.test_pipeline import make_context, make_source
from tests.word_list import KNOWN_WORDS

Connection = psycopg.AsyncConnection[TupleRow]

TITLE = "Test Kaynağı"
OPTIONS = ReaderOptions(known_words=KNOWN_WORDS)

READ_BLOCKS = """
SELECT source_page.page_no, content_block.position, content_block.block_type,
       content_block.markdown, content_block.search_text, content_block.status
FROM content_block JOIN source_page ON source_page.id = content_block.source_page_id
WHERE source_page.source_document_id = %s
ORDER BY source_page.page_no, content_block.position
"""

SPLIT_START = "Bu paragraf ilk sayfada başlar ve *Tutunamayanlar* adlı eserle birlikte"
SPLIT_END = "ikinci sayfada tamamlanır."


def build_book() -> bytes:
    """Başlık, sayfa sonunda bölünen paragraf ve ikinci sayfada ayrı bir paragraf içeren kitap."""
    first = [
        Text("**Cumhuriyet Dönemi**", 56, 72, 18),
        Text(SPLIT_START, 56, 780, 10),
        Text("sürer, sayfanın sonuna kadar uzanır ve devam eder", 56, 795, 10),
    ]
    second = [
        Text(SPLIT_END, 56, 72, 10),
        Text("Yeni bir paragraf ise bu sayfanın ortasında başlar", 56, 102, 10),
        Text("ve iki satır sürer, sonra burada biter.", 56, 117, 10),
    ]
    return make_pdf([first, second])


def read_blocks() -> list[TextbookBlock]:
    """Test kitabını kitap okuyucusuyla okur."""
    return pdf.read_textbook(build_book(), TITLE, OPTIONS).blocks


async def stored_blocks(db: Connection, source_id: int) -> list[tuple[object, ...]]:
    """Kaynağın yazılmış bloklarını sayfa ve sıra düzeniyle döner."""
    cursor = await db.execute(READ_BLOCKS, (source_id,))
    return await cursor.fetchall()


async def prepare_source(db: Connection, tmp_path: Path) -> int:
    """Kaynağı, PDF'ini ve iki sayfa satırını kurar; kaynağın numarasını döner."""
    source_id = await make_source(db)
    context = make_context(db, tmp_path)
    context.storage.write(source_key(source_id), build_book())
    for page_no in (1, 2):
        await db.execute(
            "INSERT INTO source_page (source_document_id, page_no) VALUES (%s, %s)",
            (source_id, page_no),
        )
    return source_id


def test_paragraph_split_across_pages_is_one_block() -> None:
    """İki sayfaya bölünen paragraf tek blok olur ve ilk sayfasında yer alır."""
    blocks = read_blocks()

    split = [block for block in blocks if "Tutunamayanlar" in block.markdown]
    assert len(split) == 1
    assert split[0].pages == [1, 2]
    assert split[0].page_no == 1
    assert split[0].markdown.endswith(SPLIT_END)


def test_italic_is_kept_and_search_text_has_title_path() -> None:
    """İtalik eser adı *...* kalır; arama metni başlık yolu ve markdown'dır."""
    block = next(block for block in read_blocks() if "Tutunamayanlar" in block.markdown)

    assert "*Tutunamayanlar*" in block.markdown
    assert block.title_path == "Test Kaynağı › Cumhuriyet Dönemi"
    assert block.search_text == f"{block.title_path}\n{block.markdown}"


@pytest.mark.asyncio
async def test_extract_writes_blocks_with_search_text(db: Connection, tmp_path: Path) -> None:
    """Adım blokları ilk sayfalarının satırına yazar; durum DRAFT, arama metni yoluyla başlar."""
    source_id = await prepare_source(db, tmp_path)

    await extract_textbook(source_id, make_context(db, tmp_path))

    rows = await stored_blocks(db, source_id)
    assert [row[:3] for row in rows if row[0] == 1] == [
        (1, 0, "BASLIK"),
        (1, 1, "METIN"),
    ]
    split = rows[1]
    assert "*Tutunamayanlar*" in str(split[3]) and str(split[3]).endswith(SPLIT_END)
    assert split[4] == f"Test Kaynağı › Cumhuriyet Dönemi\n{split[3]}"
    assert {row[5] for row in rows} == {"DRAFT"}


@pytest.mark.asyncio
async def test_extract_twice_creates_no_duplicate_blocks(db: Connection, tmp_path: Path) -> None:
    """Adım iki kez çalışınca blok sayısı ve içerik aynı kalır."""
    source_id = await prepare_source(db, tmp_path)
    context = make_context(db, tmp_path)

    await extract_textbook(source_id, context)
    first = await stored_blocks(db, source_id)
    await extract_textbook(source_id, context)

    assert await stored_blocks(db, source_id) == first
    assert len(first) == len(read_blocks())


@pytest.mark.asyncio
async def test_changed_text_clears_embedding_and_unchanged_keeps_it(
    db: Connection, tmp_path: Path
) -> None:
    """Metni değişen bloğun embedding'i silinir; değişmeyenin embedding'i kalır."""
    source_id = await prepare_source(db, tmp_path)
    blocks = read_blocks()
    await save_content_blocks(db, source_id, blocks)
    await db.execute(
        "UPDATE content_block SET embedding = array_fill(0.5, ARRAY[1024])::vector"
        " WHERE source_page_id IN (SELECT id FROM source_page WHERE source_document_id = %s)",
        (source_id,),
    )
    changed = blocks[1].model_copy(update={"markdown": "Değişti."})

    await save_content_blocks(db, source_id, [blocks[0], changed])

    cursor = await db.execute(
        "SELECT position, embedding IS NOT NULL, markdown FROM content_block"
        " JOIN source_page ON source_page.id = source_page_id"
        " WHERE source_document_id = %s AND page_no = 1 ORDER BY position",
        (source_id,),
    )
    assert await cursor.fetchall() == [(0, True, blocks[0].markdown), (1, False, "Değişti.")]


@pytest.mark.asyncio
async def test_block_on_unregistered_page_raises(db: Connection, tmp_path: Path) -> None:
    """Sayfa kaydı olmayan sayfaya blok yazılamaz."""
    source_id = await make_source(db)

    with pytest.raises(LookupError, match="no page 1"):
        await save_content_blocks(db, source_id, read_blocks()[:1])


READ_REVIEW_DETAIL = """
SELECT reason, detail FROM review_item WHERE source_document_id = %s AND status = 'OPEN'
"""


@pytest.mark.asyncio
async def test_empty_book_with_weak_page_opens_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hiç blok çıkmayan ve metin katmanı bozuk sayfası olan kitap incelemeye düşer."""
    source_id = await prepare_source(db, tmp_path)
    page = PageReport(page_no=2, source="TEXT", notes=["UNDECODED_GLYPHS"], text_ratio=0.5)
    reading = TextbookReading(blocks=[], pages=[page])
    monkeypatch.setattr(pdf, "read_textbook", lambda _content, _title: reading)

    await extract_textbook(source_id, make_context(db, tmp_path))

    [(reason, detail)] = await (await db.execute(READ_REVIEW_DETAIL, (source_id,))).fetchall()
    page_id = await (
        await db.execute(
            "SELECT id FROM source_page WHERE source_document_id = %s AND page_no = 2",
            (source_id,),
        )
    ).fetchone()
    assert page_id is not None
    assert reason == "VALIDATION_FAILED"
    assert detail == {
        "problems": [
            {"code": "UNDECODED_GLYPHS", "pageNo": 2, "pageId": page_id[0]},
            {"code": "NO_CONTENT"},
        ]
    }


@pytest.mark.asyncio
async def test_weak_page_read_from_image_replaces_blocks_without_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Metin katmanı bozuk sayfa görüntüden okunursa blokları değişir, inceleme açılmaz."""
    source_id = await prepare_source(db, tmp_path)
    context = make_context(db, tmp_path)
    context.storage.write(page_image_key(source_id, 2), b"png-bytes")
    page = PageReport(page_no=2, source="TEXT", notes=["LOW_TEXT_LAYER"], text_ratio=0.3)
    engine_block = TextbookBlock(
        block_type="METIN",
        markdown="Bzk mtn",
        title_path=TITLE,
        page_no=2,
        position=0,
        pages=[2],
    )
    reading = TextbookReading(blocks=[engine_block], pages=[page])
    monkeypatch.setattr(pdf, "read_textbook", lambda _content, _title: reading)
    extraction = PageExtraction(blocks=[ExtractedBlock(block_type="METIN", markdown="Düz metin")])

    async def fake_run_task(*_args: object, **_kwargs: object) -> PageExtraction:
        """Haiku'nun okumasını taklit eder."""
        return extraction

    monkeypatch.setattr(page_image, "run_task", fake_run_task)

    await extract_textbook(source_id, context)

    markdowns = [row[3] for row in await stored_blocks(db, source_id)]
    assert markdowns == ["Düz metin"]
    assert await (await db.execute(READ_REVIEW_DETAIL, (source_id,))).fetchall() == []
