"""Profil önerisini (A4, #128) sahte run_task ve gerçek Postgres'le test eder.

Claude'a çağrı yapılmaz: sahte run_task gelen değişkenleri kaydeder ve testin taslağını döner.
Örnek PDF test_profile.py'deki gibi kendi ürettiğimiz küçük dosyadır. Veritabanı testi kendi
kaynak satırını yazar ve test bitince geri alınır.
"""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import TupleRow
from pydantic import BaseModel, ValidationError

from app.constants import PROMPTS_DIR
from app.ingest import profile_propose
from app.ingest.profile_propose import ProfileDraft, ProfileProposalError
from app.llm.prompts import render_prompt
from app.llm.tasks import LlmTask, get_task_configs
from app.storage import LocalFileStorage, source_key
from tests.test_profile import SAMPLE_PDF

Connection = psycopg.AsyncConnection[TupleRow]

BODY = {"font": "LiberationSans", "size": 10}
HEADING = {"font": "LiberationSans-Bold", "size": 18, "bold": True}


def make_draft(*styles: tuple[dict[str, Any], str]) -> ProfileDraft:
    """Verilen stil ve blok türlerinden taslak üretir."""
    return ProfileDraft.model_validate(
        {
            "description": "Örnek düzen",
            "styles": [{"style": style, "block_type": block} for style, block in styles],
        }
    )


class FakeRunTask:
    """run_task yerine geçer; çağrıları kaydeder ve verilen taslağı döner."""

    def __init__(self, draft: ProfileDraft) -> None:
        """Taslağı saklar, çağrı listesini boş başlatır."""
        self.draft = draft
        self.calls: list[tuple[LlmTask, Mapping[str, object]]] = []

    async def __call__(
        self, task: LlmTask, variables: Mapping[str, object], *, output_model: type[BaseModel]
    ) -> ProfileDraft:
        """Çağrıyı kaydeder ve taslağı döner."""
        assert output_model is ProfileDraft
        self.calls.append((task, variables))
        return self.draft


class FakeConnection:
    """execute çağrılarını kaydeden sahte bağlantı."""

    def __init__(self) -> None:
        """Boş çağrı listesiyle başlar."""
        self.calls: list[str] = []

    async def execute(self, query: str, params: dict[str, Any]) -> None:
        """Sorguyu kaydeder."""
        self.calls.append(query)


def fake_connect(connection: Any) -> Any:
    """Verilen bağlantıyı veren bağlantı fabrikası üretir."""

    @asynccontextmanager
    async def connect() -> AsyncIterator[Any]:
        yield connection

    return connect


def storage_with_pdf(tmp_path: Path, source_id: int) -> LocalFileStorage:
    """Örnek PDF'i yazılmış depolama döner."""
    storage = LocalFileStorage(tmp_path / "storage")
    storage.write(source_key(source_id), SAMPLE_PDF)
    return storage


def test_prompt_renders_and_task_is_registered() -> None:
    """Prompt değişkenlerle dolar ve görev ayar dosyasında kayıtlıdır."""
    config = get_task_configs()[LlmTask.PROFILE_PROPOSE]
    variables = {
        "styles": [
            {**HEADING, "italic": False, "box_color": None, "chars": 5, "examples": ["Roman"]}
        ]
    }

    prompt = render_prompt(PROMPTS_DIR, config.prompt, variables)

    assert prompt.version >= 1
    assert "LiberationSans-Bold" in prompt.user
    assert "example: Roman" in prompt.user


def test_draft_must_follow_profile_rules() -> None:
    """Boş ya da stili tekrar eden taslak şemaya uymaz."""
    with pytest.raises(ValidationError):
        make_draft()
    with pytest.raises(ValidationError, match="repeats"):
        make_draft((BODY, "METIN"), (BODY, "BILGI"))


@pytest.mark.asyncio
async def test_proposal_sends_style_trace_and_short_examples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Claude'a stil sayımı ve kısa örnek satırlar gider; taslak depolamaya yazılır."""
    fake = FakeRunTask(make_draft((HEADING, "BASLIK"), (BODY, "METIN")))
    monkeypatch.setattr(profile_propose, "run_task", fake)
    storage = storage_with_pdf(tmp_path, 5)
    connection = FakeConnection()

    draft = await profile_propose.propose_profile(5, fake_connect(connection), storage)

    task, variables = fake.calls[0]
    styles: Any = variables["styles"]
    assert task is LlmTask.PROFILE_PROPOSE
    assert len(styles) == 4
    assert all(len(example) <= 60 for style in styles for example in style["examples"])
    assert all(len(style["examples"]) <= 3 for style in styles)
    assert draft == fake.draft
    assert storage.exists(profile_propose.draft_key(5))
    assert len(connection.calls) == 2


@pytest.mark.asyncio
async def test_unknown_style_in_draft_is_rejected_and_not_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Belgede olmayan stil öneren taslak reddedilir; yazılmaz, inceleme açılmaz."""
    invented = {"font": "Palatino", "size": 11}
    monkeypatch.setattr(profile_propose, "run_task", FakeRunTask(make_draft((invented, "METIN"))))
    storage = storage_with_pdf(tmp_path, 6)
    connection = FakeConnection()

    with pytest.raises(ProfileProposalError):
        await profile_propose.propose_profile(6, fake_connect(connection), storage)

    assert not storage.exists(profile_propose.draft_key(6))
    assert connection.calls == []


@pytest.mark.asyncio
async def test_rerun_reuses_saved_draft_without_calling_claude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yazılı taslak varsa Claude ikinci kez çağrılmaz ve aynı taslak döner."""
    fake = FakeRunTask(make_draft((HEADING, "BASLIK"), (BODY, "METIN")))
    monkeypatch.setattr(profile_propose, "run_task", fake)
    storage = storage_with_pdf(tmp_path, 7)

    first = await profile_propose.propose_profile(7, fake_connect(FakeConnection()), storage)
    second = await profile_propose.propose_profile(7, fake_connect(FakeConnection()), storage)

    assert len(fake.calls) == 1
    assert second == first


SEED_SOURCE = """
WITH user_row AS (
    INSERT INTO app_user (tenant_id, display_name)
    SELECT min(id), 'Profil Önerisi Testi' FROM tenant
    RETURNING id
)
INSERT INTO source_document (title, sha256, file_path, uploaded_by, status)
SELECT 'Profil Önerisi Testi', repeat('p', 64), '/data/sources/0.pdf', id, 'PROCESSING'
FROM user_row
RETURNING id
"""


@pytest.mark.asyncio
async def test_review_opens_once_and_source_waits_in_review(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İnceleme kaydı açılır, kaynak REVIEW olur; tekrar çalışınca kopya kayıt oluşmaz."""
    cursor = await db.execute(SEED_SOURCE)
    row = await cursor.fetchone()
    assert row is not None
    source_id = row[0]
    monkeypatch.setattr(
        profile_propose,
        "run_task",
        FakeRunTask(make_draft((HEADING, "BASLIK"), (BODY, "METIN"))),
    )
    storage = storage_with_pdf(tmp_path, source_id)

    for _ in range(2):
        await profile_propose.propose_profile(source_id, fake_connect(db), storage)

    reviews = await db.execute(
        "SELECT status FROM review_item WHERE source_document_id = %s AND reason = %s",
        (source_id, "PROFILE_APPROVAL"),
    )
    sources = await db.execute("SELECT status FROM source_document WHERE id = %s", (source_id,))
    assert await reviews.fetchall() == [("OPEN",)]
    assert await sources.fetchall() == [("REVIEW",)]
