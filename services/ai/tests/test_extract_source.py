"""EXTRACT adımını baştan sona dener: kayıt, profil önerisi (sahte Claude) ve kitap blokları.

Claude'a çağrı yapılmaz: sahte run_task belgenin kendi stillerinden taslak üretir. Kaynak PDF'i
test_textbook_reader.py'deki kendi ürettiğimiz kitaptır; test kendi transaction'ında çalışır.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import psycopg
import pytest
from psycopg.rows import TupleRow
from pydantic import BaseModel

from app.ingest import profile_propose
from app.ingest.pipeline import STEPS, run_steps
from app.ingest.profile_propose import ProfileDraft
from app.llm.tasks import LlmTask
from app.storage import source_key
from tests.test_pipeline import make_context, make_job, make_source
from tests.test_textbook_reader import build_book

Connection = psycopg.AsyncConnection[TupleRow]

COUNT_BLOCKS = "SELECT count(*) FROM content_block"
COUNT_APPROVALS = """
SELECT count(*) FROM review_item
WHERE source_document_id = %s AND reason = 'PROFILE_APPROVAL' AND status = 'OPEN'
"""
READ_STATUS = "SELECT status FROM source_document WHERE id = %s"
HEADING_MIN_SIZE = 15


async def fake_run_task(
    task: LlmTask, variables: Mapping[str, object], *, output_model: type[BaseModel]
) -> ProfileDraft:
    """Belgedeki stillerden taslak üretir: büyük yazı başlık, kalanı metin."""
    assert task is LlmTask.PROFILE_PROPOSE
    styles = cast(list[dict[str, object]], variables["styles"])
    rules = [
        {
            "style": {key: style[key] for key in ("font", "size", "bold", "italic", "box_color")},
            "block_type": "BASLIK" if float(str(style["size"])) >= HEADING_MIN_SIZE else "METIN",
        }
        for style in styles
    ]
    return ProfileDraft.model_validate({"description": "Test düzeni", "styles": rules})


async def count(db: Connection, query: str, *params: object) -> int:
    """Sorgunun tek sayısını döner."""
    cursor = await db.execute(query, params)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.asyncio
async def test_run_steps_extracts_blocks_and_opens_profile_approval(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İş baştan sona çalışır: 3 blok yazılır, öneri açılır; tekrar çalışınca kopya olmaz."""
    monkeypatch.setattr(profile_propose, "run_task", fake_run_task)
    source_id = await make_source(db)
    context = make_context(db, tmp_path)
    context.storage.write(source_key(source_id), build_book())
    before = await count(db, COUNT_BLOCKS)

    for _ in range(2):
        job = await make_job(db, source_id)
        await run_steps(job, context, STEPS)

    assert await count(db, COUNT_BLOCKS) - before == 3
    assert await count(db, COUNT_APPROVALS, source_id) == 1
    assert (await (await db.execute(READ_STATUS, (source_id,))).fetchone()) == ("REVIEW",)
