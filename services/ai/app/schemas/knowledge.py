"""Bilgi katmanının notları, bağları ve sohbet tool'larının girdileri (plan Bölüm 5, A7).

Not knowledge_node satırıdır; bağ knowledge_edge satırıdır ve iki ucunun adı ve türüyle gelir.
Tool girdileri Claude'un tool_use bloğundaki input'tur; şemaları prompts/tde/tools.yaml'dadır.
"""

from pydantic import BaseModel


class NoteRef(BaseModel):
    """Notun numarası, türü ve adı."""

    id: int
    node_type: str
    name: str


class KnowledgeNote(NoteRef):
    """Yayındaki not ve kısa metni."""

    note_md: str | None


class NoteLink(BaseModel):
    """İki ucu da yayında olan yayındaki bağ ve dayandığı paragraf."""

    from_note: NoteRef
    to_note: NoteRef
    relation: str
    evidence_block_id: int | None


class NoteSearchInput(BaseModel):
    """search_notes girdisi."""

    query: str


class NoteOpenInput(BaseModel):
    """open_note girdisi."""

    note_id: int


class OutcomeInput(BaseModel):
    """get_outcome girdisi."""

    code: str
