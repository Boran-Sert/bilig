"""Bilgi katmanı adımı (hazırlık hattı A7, ENTITIES).

Kaynağın işlenmemiş sayfaları sırayla okunur; her sayfanın reddedilmemiş bilgi, alıntı ve metin
paragrafları tek ENTITY_EXTRACT çağrısıyla gider. Model notları ve bağları çıkarır, her bağa
dayandığı paragrafın numarasını yazar; Bilgi Köşesi tablosu da ona bırakılır. Kural, markdown'daki
"*Eser* (Yazar)" ve "*Eser* [Yazar (okunuş)]" kalıplarından eser ve yazar notunu ve yazardan
esere WROTE bağını çıkarır. Parantezdeki yazının her kelimesi büyük harfle başlamıyorsa
("roman", "Tarihî roman") ya da yazıda rakam varsa yazar sayılmaz. Dayanak kontrolü her bağı
kendi paragrafında yapar: not, adı paragrafta bir kelimenin başından başlayarak geçiyorsa
tutulur; Türkçe ekler için sonu açıktır ("tarihî roman", "tarihî romandır"da geçer). İki ucu
tutulan notlarda olmayan ya da sayfada olmayan paragrafa dayanan bağ atılır; kalan bağ yayına
girer. Not sadece kalan bir bağın ucuysa yazılır. Adlar ad anahtarıyla karşılaştırılır: NFC,
Türkçe küçük harf, aksansız, noktalama yerine boşluk.

Anahtar aynı türde bir yazımla birebir eşleşirse aynı not kullanılır; eşleşmezse yeni not açılır.
Yeni notun anahtarı aynı türdeki bir yazıma rapidfuzz ile en az NAME_MERGE_REVIEW_SCORE kadar
benziyorsa NAME_MERGE incelemesi açılır; not o sırada da yayındadır. Her yeni yazım nota eklenir.
Her sayfanın sonucu ve sayfanın işlendi işareti (source_page.entities_extracted_at) aynı
transaction'da commit edilir; Claude çağrısı sırasında açık transaction yoktur. İşaretli sayfa,
sonucu boş çıksa da, adım tekrar çalışınca modele gitmez.
"""

import re

import structlog
from psycopg import AsyncConnection
from rapidfuzz import fuzz, process

from app.constants import NAME_MERGE_REVIEW_SCORE
from app.db.queries.knowledge import (
    add_alias,
    fetch_aliases,
    fetch_entity_pages,
    fill_note,
    find_node,
    insert_edge,
    insert_node,
    lock_node_key,
    mark_page_extracted,
    open_node_review,
    refresh_search_text,
)
from app.llm.runner import run_task
from app.llm.tasks import LlmTask
from app.schemas.entity_extract import (
    EntityExtraction,
    EntityPage,
    ExtractedEdge,
    ExtractedNode,
    NodeType,
    PageExtraction,
    Relation,
)
from app.text.turkish import ascii_fold, normalize_nfc, tr_lower

WORK_AUTHOR = re.compile(
    r"(?<!\*)\*([^*\n]+)\*(?!\*)\s*"
    r"(?:\(([^()\[\]\n]+)\)|\[([^()\[\]\n]+?)\s*\([^()\n]*\)\])"
)
NON_WORD = re.compile(r"[^a-z0-9]+")

type NodeKey = tuple[NodeType, str]


def name_key(text: str) -> str:
    """Adı karşılaştırma anahtarına çevirir: küçük harf, aksansız, tek boşluklu."""
    folded = ascii_fold(tr_lower(normalize_nfc(text)))
    return NON_WORD.sub(" ", folded).strip()


def looks_like_name(text: str) -> bool:
    """Yazının rakamsız olup her kelimesinin büyük harfle başlayıp başlamadığını döner."""
    words = text.split()
    has_digit = any(char.isdigit() for char in text)
    return bool(words) and not has_digit and all(word[0].isupper() for word in words)


def rule_entities(markdown: str) -> EntityExtraction:
    """Eser-yazar kalıplarından eser ve yazar notlarını ve WROTE bağlarını çıkarır."""
    nodes: list[ExtractedNode] = []
    edges: list[ExtractedEdge] = []
    for match in WORK_AUTHOR.finditer(markdown):
        work = match[1].strip()
        author = (match[2] or match[3]).strip()
        if not looks_like_name(author):
            continue
        nodes += [
            ExtractedNode(node_type=NodeType.WORK, name=work),
            ExtractedNode(node_type=NodeType.AUTHOR, name=author),
        ]
        edges.append(
            ExtractedEdge(
                from_type=NodeType.AUTHOR,
                from_name=author,
                relation=Relation.WROTE,
                to_type=NodeType.WORK,
                to_name=work,
            )
        )
    return EntityExtraction(nodes=nodes, edges=edges)


def check_evidence(extraction: EntityExtraction, text: str) -> EntityExtraction:
    """Adı metinde geçmeyen notları, uçları tutulmayan bağları ve bağsız kalan notları atar."""
    padded = f" {name_key(text)} "
    nodes: dict[NodeKey, ExtractedNode] = {}
    for node in extraction.nodes:
        key = (node.node_type, name_key(node.name))
        if not key[1] or f" {key[1]}" not in padded:
            continue
        if key not in nodes or (node.note and not nodes[key].note):
            nodes[key] = node
    edges: dict[tuple[NodeKey, Relation, NodeKey], ExtractedEdge] = {}
    for edge in extraction.edges:
        source = (edge.from_type, name_key(edge.from_name))
        target = (edge.to_type, name_key(edge.to_name))
        if source in nodes and target in nodes:
            edges.setdefault((source, edge.relation, target), edge)
    linked = {key for source, _, target in edges for key in (source, target)}
    kept = [node for key, node in nodes.items() if key in linked]
    return EntityExtraction(nodes=kept, edges=list(edges.values()))


def similar_node(key: str, aliases: list[tuple[int, str]]) -> tuple[int, float] | None:
    """İnceleme eşiğini geçen en benzer yazımın notunu ve puanını döner; yoksa boştur."""
    if not aliases:
        return None
    _, score, index = process.extractOne(key, [alias for _, alias in aliases], scorer=fuzz.ratio)
    if score < NAME_MERGE_REVIEW_SCORE:
        return None
    return aliases[index][0], score


async def extract_source_entities(connection: AsyncConnection, source_document_id: int) -> None:
    """Kaynağın işlenmemiş sayfalarından notları ve bağları çıkarıp yazar."""
    async with connection.transaction():
        pages = await fetch_entity_pages(connection, source_document_id)
    edge_count = 0
    for page in pages:
        extractions = await extract_page(page)
        async with connection.transaction():
            for block_id, extraction in extractions.items():
                edge_count += await save_extraction(connection, block_id, extraction)
            await mark_page_extracted(connection, page.id)
    structlog.get_logger().info(
        "entities extracted",
        source_document_id=source_document_id,
        pages=len(pages),
        edges=edge_count,
    )


async def extract_page(page: EntityPage) -> dict[int, EntityExtraction]:
    """Sayfayı tek çağrıyla okur; her paragrafın kural ve model bağlarını kontrolden geçirir."""
    variables = {"blocks": [block.model_dump() for block in page.blocks]}
    found = await run_task(LlmTask.ENTITY_EXTRACT, variables, output_model=PageExtraction)
    extractions: dict[int, EntityExtraction] = {}
    for block in page.blocks:
        rule = rule_entities(block.markdown)
        model_edges = [
            ExtractedEdge.model_validate(edge.model_dump(exclude={"block_id"}))
            for edge in found.edges
            if edge.block_id == block.id
        ]
        combined = EntityExtraction(nodes=rule.nodes + found.nodes, edges=rule.edges + model_edges)
        extractions[block.id] = check_evidence(combined, block.markdown)
    return extractions


async def save_extraction(
    connection: AsyncConnection, block_id: int, extraction: EntityExtraction
) -> int:
    """Notları ve bağları yazar ve yeni yazılan bağ sayısını döner."""
    node_ids: dict[NodeKey, int] = {}
    for node in extraction.nodes:
        node_ids[(node.node_type, name_key(node.name))] = await save_node(connection, node)
    saved = 0
    for edge in extraction.edges:
        from_id = node_ids[(edge.from_type, name_key(edge.from_name))]
        to_id = node_ids[(edge.to_type, name_key(edge.to_name))]
        if from_id == to_id:
            continue
        if await insert_edge(connection, from_id, to_id, edge.relation, block_id) is not None:
            saved += 1
    return saved


async def save_node(connection: AsyncConnection, node: ExtractedNode) -> int:
    """Notu aynı anahtarlı notla birleştirir ya da yenisini açar; yazımı ve notu ekler."""
    key = name_key(node.name)
    await lock_node_key(connection, node.node_type, key)
    node_id = await find_node(connection, node.node_type, key)
    if node_id is None:
        similar = similar_node(key, await fetch_aliases(connection, node.node_type))
        node_id = await insert_node(connection, node.node_type, node.name)
        if similar is not None:
            await open_node_review(connection, node_id, *similar)
    await add_alias(connection, node_id, key, node.name)
    if node.note:
        await fill_note(connection, node_id, node.note)
    await refresh_search_text(connection, node_id)
    return node_id
