"""Bilgi katmanı çıkarımının (plan A7) modelleri.

EntityExtraction bir paragrafın notlarını (yazar, eser, dönem, akım, tür, kavram) ve aralarındaki
bağları taşır; kuralın bulduğu eser-yazar çiftleri de bu biçimdedir. Bağın uçları ad ve türle
gösterilir. ENTITY_EXTRACT sayfayı bir kerede okur ve PageExtraction döner: her bağ dayandığı
paragrafın numarasını taşır. EntityBlock notların çıkarıldığı paragraf, EntityPage
henüz işlenmemiş sayfadır.
"""

from enum import StrEnum

from pydantic import BaseModel


class NodeType(StrEnum):
    """Notun türü; knowledge_node.node_type ile aynıdır."""

    AUTHOR = "AUTHOR"
    WORK = "WORK"
    PERIOD = "PERIOD"
    MOVEMENT = "MOVEMENT"
    GENRE = "GENRE"
    CONCEPT = "CONCEPT"


class Relation(StrEnum):
    """Bağın türü; knowledge_edge.relation ile aynıdır."""

    WROTE = "WROTE"
    HAS_GENRE = "HAS_GENRE"
    IN_PERIOD = "IN_PERIOD"
    IN_MOVEMENT = "IN_MOVEMENT"
    RELATED = "RELATED"


class ExtractedNode(BaseModel):
    """Paragraftan çıkarılan not: türü, adı ve varsa kısa not metni."""

    node_type: NodeType
    name: str
    note: str | None = None


class ExtractedEdge(BaseModel):
    """İki not arasındaki bağ: uçların türü ve adı ile bağın türü."""

    from_type: NodeType
    from_name: str
    relation: Relation
    to_type: NodeType
    to_name: str


class EntityExtraction(BaseModel):
    """Bir paragrafın notları ve bağları; dayanak kontrolü bu biçimle çalışır."""

    nodes: list[ExtractedNode]
    edges: list[ExtractedEdge]


class PageEdge(ExtractedEdge):
    """Sayfa çıktısındaki bağ: dayandığı paragrafın numarasını da taşır."""

    block_id: int


class PageExtraction(BaseModel):
    """ENTITY_EXTRACT çıktısı: sayfadaki notlar ve paragraf numaralı bağlar."""

    nodes: list[ExtractedNode]
    edges: list[PageEdge]


class EntityBlock(BaseModel):
    """Notları çıkarılacak paragraf: kimliği, başlık yolu ve markdown metni."""

    id: int
    title_path: str
    markdown: str


class EntityPage(BaseModel):
    """Henüz işlenmemiş sayfa: kimliği ve notları çıkarılacak paragrafları."""

    id: int
    blocks: list[EntityBlock]
