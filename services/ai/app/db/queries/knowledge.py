"""Bilgi katmanı adımının sorguları (hazırlık hattı A7).

Kaynağın işlenmemiş sayfalarının reddedilmemiş bilgi, alıntı ve metin paragrafları sayfa ve sıra
düzeniyle okunur; sayfa işlenince source_page.entities_extracted_at doldurulur ve sayfa bir daha
okunmaz. Notun her yazımı
knowledge_node_alias'ta normalize anahtarıyla durur; notun kendi adı da bir yazımdır. Not ve bağ
yayında (PUBLISHED) yazılır. Aynı not, yazım, bağ ve açık inceleme kaydı ikinci kez eklenmez;
aynı anda çalışan iki iş aynı adı arayıp açmasın diye ad anahtarı transaction kilidiyle tutulur.
NAME_MERGE kaydının ayrıntısında benzer notun kimliği ve benzerlik puanı durur. Arama metni ad,
diğer yazımlar ve nottan kurulur; değişince vektör silinir ki INDEX adımı yeniden hesaplasın.
Tablolar core'un Flyway migration'larıyla kurulur.
"""

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.schemas.entity_extract import EntityBlock, EntityPage, NodeType, Relation

SELECT_ENTITY_BLOCKS = """
SELECT source_page.id, content_block.id, content_block.title_path, content_block.markdown
FROM content_block
JOIN source_page ON source_page.id = content_block.source_page_id
WHERE source_page.source_document_id = %(source_document_id)s
    AND source_page.entities_extracted_at IS NULL
    AND content_block.block_type IN ('BILGI', 'ALINTI', 'METIN')
    AND content_block.status <> 'REJECTED'
ORDER BY source_page.page_no, content_block.position
"""

LOCK_NODE_KEY = """
SELECT pg_advisory_xact_lock(hashtext(%(node_type)s || ':' || %(normalized_alias)s))
"""

MARK_PAGE_EXTRACTED = """
UPDATE source_page SET entities_extracted_at = now() WHERE id = %(page_id)s
"""

SELECT_NODE_BY_ALIAS = """
SELECT knowledge_node.id
FROM knowledge_node_alias
JOIN knowledge_node ON knowledge_node.id = knowledge_node_alias.knowledge_node_id
WHERE knowledge_node.node_type = %(node_type)s
    AND knowledge_node_alias.normalized_alias = %(normalized_alias)s
ORDER BY knowledge_node.id
LIMIT 1
"""

SELECT_ALIASES = """
SELECT knowledge_node_alias.knowledge_node_id, knowledge_node_alias.normalized_alias
FROM knowledge_node_alias
JOIN knowledge_node ON knowledge_node.id = knowledge_node_alias.knowledge_node_id
WHERE knowledge_node.node_type = %(node_type)s
ORDER BY knowledge_node_alias.knowledge_node_id, knowledge_node_alias.normalized_alias
"""

INSERT_NODE = """
INSERT INTO knowledge_node (node_type, name, status, search_text)
VALUES (%(node_type)s, %(name)s, 'PUBLISHED', %(name)s)
ON CONFLICT (node_type, name) DO UPDATE SET name = EXCLUDED.name
RETURNING id
"""

INSERT_ALIAS = """
INSERT INTO knowledge_node_alias (knowledge_node_id, normalized_alias, alias)
VALUES (%(node_id)s, %(normalized_alias)s, %(alias)s)
ON CONFLICT DO NOTHING
"""

FILL_NOTE = """
UPDATE knowledge_node SET note_md = %(note)s, updated_at = now()
WHERE id = %(node_id)s AND note_md IS NULL
"""

REFRESH_SEARCH_TEXT = """
UPDATE knowledge_node
SET search_text = refreshed.text, embedding = NULL, updated_at = now()
FROM (
    SELECT concat_ws(
        ' ',
        node.name,
        (
            SELECT string_agg(alias.alias, ' ' ORDER BY alias.alias)
            FROM knowledge_node_alias AS alias
            WHERE alias.knowledge_node_id = node.id AND alias.alias <> node.name
        ),
        node.note_md
    ) AS text
    FROM knowledge_node AS node
    WHERE node.id = %(node_id)s
) AS refreshed
WHERE knowledge_node.id = %(node_id)s AND knowledge_node.search_text <> refreshed.text
"""

INSERT_EDGE = """
INSERT INTO knowledge_edge (from_node_id, to_node_id, relation, evidence_content_block_id,
    status)
VALUES (%(from_node_id)s, %(to_node_id)s, %(relation)s, %(block_id)s, 'PUBLISHED')
ON CONFLICT (from_node_id, to_node_id, relation) DO NOTHING
RETURNING id
"""

INSERT_NODE_REVIEW = """
INSERT INTO review_item (reason, knowledge_node_id, detail)
SELECT 'NAME_MERGE', %(node_id)s, %(detail)s
WHERE NOT EXISTS (
    SELECT 1 FROM review_item
    WHERE knowledge_node_id = %(node_id)s AND reason = 'NAME_MERGE' AND status = 'OPEN'
)
"""


async def fetch_entity_pages(
    connection: AsyncConnection, source_document_id: int
) -> list[EntityPage]:
    """Kaynağın işlenmemiş sayfalarını paragraflarıyla, sayfa ve sıra düzeniyle döner."""
    cursor = await connection.execute(
        SELECT_ENTITY_BLOCKS, {"source_document_id": source_document_id}
    )
    pages: dict[int, EntityPage] = {}
    for page_id, block_id, title_path, markdown in await cursor.fetchall():
        page = pages.setdefault(page_id, EntityPage(id=page_id, blocks=[]))
        page.blocks.append(EntityBlock(id=block_id, title_path=title_path, markdown=markdown))
    return list(pages.values())


async def lock_node_key(
    connection: AsyncConnection, node_type: NodeType, normalized_alias: str
) -> None:
    """Aynı tür ve anahtardaki notu transaction sonuna kadar başka işe kapatır."""
    values = {"node_type": node_type, "normalized_alias": normalized_alias}
    await connection.execute(LOCK_NODE_KEY, values)


async def mark_page_extracted(connection: AsyncConnection, page_id: int) -> None:
    """Sayfayı bilgi katmanı adımında işlenmiş olarak işaretler."""
    await connection.execute(MARK_PAGE_EXTRACTED, {"page_id": page_id})


async def find_node(
    connection: AsyncConnection, node_type: NodeType, normalized_alias: str
) -> int | None:
    """Yazımı birebir eşleşen aynı türdeki notun kimliğini döner."""
    values = {"node_type": node_type, "normalized_alias": normalized_alias}
    cursor = await connection.execute(SELECT_NODE_BY_ALIAS, values)
    row = await cursor.fetchone()
    return None if row is None else int(row[0])


async def fetch_aliases(connection: AsyncConnection, node_type: NodeType) -> list[tuple[int, str]]:
    """Türdeki bütün notların kimliğini ve normalize yazımlarını döner."""
    cursor = await connection.execute(SELECT_ALIASES, {"node_type": node_type})
    return [(row[0], row[1]) for row in await cursor.fetchall()]


async def insert_node(connection: AsyncConnection, node_type: NodeType, name: str) -> int:
    """Notu yazar ve kimliğini döner; aynı tür ve adla not varsa onun kimliğini döner."""
    values = {"node_type": node_type, "name": name}
    cursor = await connection.execute(INSERT_NODE, values)
    row = await cursor.fetchone()
    if row is None:
        raise RuntimeError("Upsert returned no id")
    return int(row[0])


async def add_alias(
    connection: AsyncConnection, node_id: int, normalized_alias: str, alias: str
) -> None:
    """Nota yazım ekler; aynı normalize yazım varsa eklemez."""
    values = {"node_id": node_id, "normalized_alias": normalized_alias, "alias": alias}
    await connection.execute(INSERT_ALIAS, values)


async def fill_note(connection: AsyncConnection, node_id: int, note: str) -> None:
    """Notu boş olan kaydın notunu doldurur."""
    await connection.execute(FILL_NOTE, {"node_id": node_id, "note": note})


async def refresh_search_text(connection: AsyncConnection, node_id: int) -> None:
    """Arama metnini ad, yazımlar ve nottan yeniden kurar; değiştiyse vektörü siler."""
    await connection.execute(REFRESH_SEARCH_TEXT, {"node_id": node_id})


async def insert_edge(
    connection: AsyncConnection,
    from_node_id: int,
    to_node_id: int,
    relation: Relation,
    block_id: int,
) -> int | None:
    """Bağı dayanağıyla yazar ve kimliğini döner; aynı bağ varsa boş döner."""
    values = {
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "relation": relation,
        "block_id": block_id,
    }
    cursor = await connection.execute(INSERT_EDGE, values)
    row = await cursor.fetchone()
    return None if row is None else int(row[0])


async def open_node_review(
    connection: AsyncConnection, node_id: int, candidate_node_id: int, score: float
) -> None:
    """Not için benzer notu ve puanı taşıyan açık NAME_MERGE kaydı yoksa açar."""
    detail = Jsonb({"candidateNodeId": candidate_node_id, "score": score})
    await connection.execute(INSERT_NODE_REVIEW, {"node_id": node_id, "detail": detail})
