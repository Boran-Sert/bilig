"""Profil önerisi (A4, #128): eşleşen profil yoksa Sonnet taslak profil önerir, ekip onaylar.

Akış: PDF'in stil izi ve her stilin birkaç kısa örnek satırı run_task(PROFILE_PROPOSE)'a verilir;
dönen taslak ProfileDraft şemasına ve belgenin gerçek stillerine karşı doğrulanır. Taslak
depolamaya profile_drafts/{id}.yaml olarak yazılır (inceleme ekranı oradan okur), kaynak için
açık bir PROFILE_APPROVAL inceleme kaydı açılır ve kaynak REVIEW durumuna geçer. Adım tekrar
çalışınca yazılı taslak varsa Claude yeniden çağrılmaz, açık kayıt varsa ikincisi açılmaz.
Onaydan sonra işin kaldığı adımdan devam etmesi onay ucunun işidir (#137).
"""

import asyncio

import yaml
from psycopg import AsyncConnection
from pydantic import BaseModel, ConfigDict, model_validator

from app.ingest import profile
from app.jobs.postgres_queue import ConnectionFactory
from app.llm.runner import run_task
from app.llm.tasks import LlmTask
from app.schemas.profile import Profile, StyleCount, StyledLine, StyleRule
from app.storage import FileStorage, source_key

PROPOSAL_MAX_STYLES = 12
PROPOSAL_EXAMPLES_PER_STYLE = 3
PROPOSAL_EXAMPLE_MAX_CHARS = 60
DRAFT_NAME = "draft"

INSERT_PROFILE_APPROVAL = """
INSERT INTO review_item (reason, source_document_id)
SELECT 'PROFILE_APPROVAL', %(source_id)s
WHERE NOT EXISTS (
    SELECT 1 FROM review_item
    WHERE source_document_id = %(source_id)s AND reason = 'PROFILE_APPROVAL' AND status = 'OPEN'
)
"""

SET_REVIEW_STATUS = """
UPDATE source_document SET status = 'REVIEW', updated_at = now() WHERE id = %(source_id)s
"""


class ProfileDraft(BaseModel):
    """Claude'un önerdiği taslak profil: kısa açıklama ve stil kuralları."""

    model_config = ConfigDict(extra="forbid")

    description: str
    styles: list[StyleRule]

    @model_validator(mode="after")
    def check_profile(self) -> "ProfileDraft":
        """Taslak kayıtlı profil kurallarına uymalı: boş olamaz, stil tekrar etmez."""
        self.to_profile(DRAFT_NAME)
        return self

    def to_profile(self, name: str) -> Profile:
        """Taslağı verilen adla Profile'a çevirir."""
        return Profile(name=name, description=self.description, styles=self.styles)


class ProfileProposalError(ValueError):
    """Model, belgede olmayan bir stil önerdi."""


def draft_key(source_id: int) -> str:
    """Taslak profilin depolama anahtarını verir."""
    return f"profile_drafts/{source_id}.yaml"


def build_variables(lines: list[StyledLine], counts: list[StyleCount]) -> dict[str, object]:
    """Prompt değişkenlerini kurar: stil sayımları ve stil başına kısa örnek satırlar."""
    styles = []
    for count in counts[:PROPOSAL_MAX_STYLES]:
        examples = [
            line.text.strip()[:PROPOSAL_EXAMPLE_MAX_CHARS]
            for line in lines
            if line.style == count.style and line.text.strip()
        ][:PROPOSAL_EXAMPLES_PER_STYLE]
        styles.append({**count.style.model_dump(), "chars": count.chars, "examples": examples})
    return {"styles": styles}


def check_draft(draft: ProfileDraft, counts: list[StyleCount]) -> None:
    """Taslaktaki her stilin belgede bulunduğunu doğrular; uydurma stil hata verir."""
    observed = {count.style for count in counts}
    unknown = [rule.style for rule in draft.styles if rule.style not in observed]
    if unknown:
        raise ProfileProposalError(f"Draft has styles not found in the document: {unknown}")


def dump_draft(draft: ProfileDraft) -> bytes:
    """Taslağı profiles/README.md biçiminde YAML'a çevirir."""
    data = draft.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8")


async def open_approval(connection: AsyncConnection, source_id: int) -> None:
    """Açık kayıt yoksa PROFILE_APPROVAL kaydını açar ve kaynağı REVIEW yapar."""
    values = {"source_id": source_id}
    await connection.execute(INSERT_PROFILE_APPROVAL, values)
    await connection.execute(SET_REVIEW_STATUS, values)


async def propose_profile(
    source_id: int, connect: ConnectionFactory, storage: FileStorage
) -> ProfileDraft:
    """Kaynak için taslak profil önerir, yazar ve onay bekleyen inceleme kaydını açar."""
    key = draft_key(source_id)
    if await asyncio.to_thread(storage.exists, key):
        content = await asyncio.to_thread(storage.read, key)
        draft = ProfileDraft.model_validate(yaml.safe_load(content))
    else:
        pdf_content = await asyncio.to_thread(storage.read, source_key(source_id))
        lines = await asyncio.to_thread(profile.read_styled_lines, pdf_content)
        counts = profile.count_styles(lines)
        draft = await run_task(
            LlmTask.PROFILE_PROPOSE,
            build_variables(lines, counts),
            output_model=ProfileDraft,
        )
        check_draft(draft, counts)
        await asyncio.to_thread(storage.write, key, dump_draft(draft))
    async with connect() as connection:
        await open_approval(connection, source_id)
    return draft
