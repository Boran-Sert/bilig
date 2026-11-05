"""Sohbetin okuma tool'ları: search_notes, open_note, get_outcome (plan Bölüm 5, 13.10).

Tool'lar sadece okur; bilgi katmanına yeni bilgi hazırlık hattından ve insan onayıyla girer.
search_notes ve get_outcome düz metin döner: arama listesi alıntılanmaz, model alıntılamak için
notu open_note ile açar. open_note notu ve bağlarının dayandığı yayındaki paragrafları search_result
olarak döner; notun kartı ilk dayanağıdır, dayanağı yoksa not alıntılansa da kart çizilmez.
Bulunamayan not ve kazanım hata sonucudur; eşleşmeyen arama hata değildir. Her tool çağrısı
havuzdan kendi bağlantısını alır ve sonuç dönünce bırakır; Claude çağrısı sırasında bağlantı ve
transaction açık kalmaz.
"""

from collections.abc import Mapping

from psycopg import AsyncConnection

from app.constants import (
    NOTE_HEADER,
    NOTE_LINK_LINE,
    NOTE_REFERENCE,
    NOTE_SEARCH_LIMIT,
    NOTE_SOURCE_LABEL,
    OUTCOME_LINE,
    TUTOR_SOURCE_BLOCK_TYPES,
)
from app.db.pool import get_pool
from app.db.queries.notes import fetch_note_links, fetch_notes
from app.db.queries.tutor import fetch_outcomes_by_code, fetch_source_blocks
from app.llm.prompts import get_tool_prompts
from app.schemas.knowledge import (
    KnowledgeNote,
    NoteLink,
    NoteOpenInput,
    NoteRef,
    NoteSearchInput,
    OutcomeInput,
)
from app.schemas.search import SearchFilters, SearchTarget
from app.schemas.tutor import CitationSource, ToolOutput
from app.search.hybrid import hybrid_search


async def execute_tool(name: str, tool_input: Mapping[str, object]) -> ToolOutput:
    """Adı verilen tool'u havuzdan alınan bağlantıyla çalıştırır."""
    async with get_pool().connection() as connection:
        if name == "search_notes":
            query = NoteSearchInput.model_validate(tool_input).query
            return await search_notes(connection, query)
        if name == "open_note":
            note_id = NoteOpenInput.model_validate(tool_input).note_id
            return await open_note(connection, note_id)
        if name == "get_outcome":
            code = OutcomeInput.model_validate(tool_input).code
            return await get_outcome(connection, code)
    raise ValueError(f"Unknown tool: {name}")


async def search_notes(connection: AsyncConnection, query: str) -> ToolOutput:
    """Sorguya en uygun yayındaki notları numaraları ve bağlarıyla düz metin olarak döner."""
    filters = SearchFilters(target=SearchTarget.KNOWLEDGE_NODE)
    hits = await hybrid_search(connection, query, filters, NOTE_SEARCH_LIMIT, rerank=True)
    notes = await fetch_notes(connection, [hit.id for hit in hits])
    if not notes:
        return ToolOutput(text=get_tool_prompts().messages.no_notes)
    links = await fetch_note_links(connection, [note.id for note in notes])
    return ToolOutput(text="\n\n".join(note_text(note, links) for note in notes))


async def open_note(connection: AsyncConnection, note_id: int) -> ToolOutput:
    """Notu ve bağlarının dayandığı paragrafları alıntılanabilir kaynak olarak döner."""
    notes = await fetch_notes(connection, [note_id])
    if not notes:
        return ToolOutput(text=get_tool_prompts().messages.note_not_found, is_error=True)
    note = notes[0]
    links = await fetch_note_links(connection, [note.id])
    evidence_ids = [link.evidence_block_id for link in links if link.evidence_block_id is not None]
    evidence = await fetch_source_blocks(
        connection, list(dict.fromkeys(evidence_ids)), TUTOR_SOURCE_BLOCK_TYPES
    )
    card = evidence[0] if evidence else None
    source = CitationSource(
        source=NOTE_SOURCE_LABEL.format(id=note.id),
        title=note.name,
        text=note_text(note, links),
        block=card,
    )
    return ToolOutput(sources=[source, *(block.citation_source() for block in evidence)])


async def get_outcome(connection: AsyncConnection, code: str) -> ToolOutput:
    """Kazanımın kodunu, başlığını ve MEB açıklamasını düz metin olarak döner."""
    outcomes = await fetch_outcomes_by_code(connection, code.strip())
    if not outcomes:
        return ToolOutput(text=get_tool_prompts().messages.outcome_not_found, is_error=True)
    texts = []
    for item in outcomes:
        line = OUTCOME_LINE.format(code=item.code, title=item.title)
        texts.append(f"{line}\n{item.meb_explanation}" if item.meb_explanation else line)
    return ToolOutput(text="\n\n".join(texts))


def note_text(note: KnowledgeNote, links: list[NoteLink]) -> str:
    """Notu türü, adı, numarası, kısa metni ve kendi bağlarıyla yazar."""
    lines = [NOTE_HEADER.format(node_type=note.node_type, name=note.name, id=note.id)]
    if note.note_md:
        lines.append(note.note_md)
    lines.extend(
        NOTE_LINK_LINE.format(
            source=reference(link.from_note), relation=link.relation, target=reference(link.to_note)
        )
        for link in links
        if note.id in (link.from_note.id, link.to_note.id)
    )
    return "\n".join(lines)


def reference(note: NoteRef) -> str:
    """Bağdaki notu adı, türü ve numarasıyla yazar."""
    return NOTE_REFERENCE.format(name=note.name, node_type=note.node_type, id=note.id)
