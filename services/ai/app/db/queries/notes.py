"""Sohbet tool'larının bilgi katmanından okuduğu sorgular (plan Bölüm 5, A7).

Modele sadece yayındaki (PUBLISHED) not ve bağ gider; bağın iki ucu da yayında olmalıdır. Bağlar
kayıt sırasıyla gelir, böylece notun "ilk" dayanağı her çağrıda aynıdır. Bu dosya sadece okur;
bilgi katmanına hazırlık hattı ve insan onayı yazar.
"""

from psycopg import AsyncConnection

from app.schemas.knowledge import KnowledgeNote, NoteLink, NoteRef

SELECT_PUBLISHED_NOTES = """
SELECT id, node_type, name, note_md
FROM knowledge_node
WHERE id = ANY(%(ids)s) AND status = 'PUBLISHED'
"""

SELECT_PUBLISHED_LINKS = """
SELECT from_node.id, from_node.node_type, from_node.name, to_node.id, to_node.node_type,
    to_node.name, knowledge_edge.relation, knowledge_edge.evidence_content_block_id
FROM knowledge_edge
JOIN knowledge_node AS from_node ON from_node.id = knowledge_edge.from_node_id
JOIN knowledge_node AS to_node ON to_node.id = knowledge_edge.to_node_id
WHERE knowledge_edge.status = 'PUBLISHED'
    AND from_node.status = 'PUBLISHED'
    AND to_node.status = 'PUBLISHED'
    AND (knowledge_edge.from_node_id = ANY(%(ids)s) OR knowledge_edge.to_node_id = ANY(%(ids)s))
ORDER BY knowledge_edge.id
"""


async def fetch_notes(connection: AsyncConnection, note_ids: list[int]) -> list[KnowledgeNote]:
    """Yayındaki notları verilen kimlik sırasıyla döner."""
    cursor = await connection.execute(SELECT_PUBLISHED_NOTES, {"ids": note_ids})
    found = {
        row[0]: KnowledgeNote(id=row[0], node_type=row[1], name=row[2], note_md=row[3])
        for row in await cursor.fetchall()
    }
    return [found[note_id] for note_id in note_ids if note_id in found]


async def fetch_note_links(connection: AsyncConnection, note_ids: list[int]) -> list[NoteLink]:
    """Notlara giren ve çıkan yayındaki bağları kayıt sırasıyla döner."""
    cursor = await connection.execute(SELECT_PUBLISHED_LINKS, {"ids": note_ids})
    return [
        NoteLink(
            from_note=NoteRef(id=row[0], node_type=row[1], name=row[2]),
            to_note=NoteRef(id=row[3], node_type=row[4], name=row[5]),
            relation=row[6],
            evidence_block_id=row[7],
        )
        for row in await cursor.fetchall()
    ]
