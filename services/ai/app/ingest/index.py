"""İndeksleme adımı (hazırlık hattı A9, INDEX).

Kaynağın vektörü olmayan blokları ve soruları ile vektörü olmayan bütün notlar bge-m3 ile vektöre
çevrilip yazılır. Blok ve not için metin arama metnidir (blokta başlık yolu ve markdown, notta ad,
diğer yazımlar ve not), soru için ortak parça, kök ve şıklardır; kazanım eşleştirme de aynı
metinleri kullanır. Bilgi katmanı adımı nota yazım eklediğinde vektörü sildiği için not burada
yeniden hesaplanır. Taslak içerik de indekslenir; arama sadece PUBLISHED
kaydı döndüğü için yayına girmeyen içerik bulunmaz. Kelime araması (BM25) için ayrı iş yoktur:
search_text'in index'ini veritabanı yazarken günceller. Metni değişen bloğun vektörü EXTRACT'ta
silindiği için sonraki INDEX'te yeniden hesaplanır. Model ve okuma ayrı transaction'dadır:
vektör hesaplanırken açık transaction kalmaz.
"""

import asyncio
from typing import TYPE_CHECKING

import structlog

from app.db.queries.index import (
    fetch_blocks_without_embedding,
    fetch_nodes_without_embedding,
    fetch_questions_without_embedding,
    save_block_embeddings,
    save_node_embeddings,
    save_question_embeddings,
)
from app.search.embedding import get_embedding_provider

if TYPE_CHECKING:
    from app.ingest.pipeline import IngestContext


async def index_source(source_id: int, context: "IngestContext") -> None:
    """Kaynağın vektörü olmayan bloklarını, sorularını ve bütün notları vektöre çevirip yazar."""
    async with context.connect() as connection:
        blocks = await fetch_blocks_without_embedding(connection, source_id)
        questions = await fetch_questions_without_embedding(connection, source_id)
        nodes = await fetch_nodes_without_embedding(connection)
    block_vectors = await embed(blocks)
    question_vectors = await embed(questions)
    node_vectors = await embed(nodes)
    async with context.connect() as connection:
        await save_block_embeddings(connection, block_vectors)
        await save_question_embeddings(connection, question_vectors)
        await save_node_embeddings(connection, nodes, node_vectors)
    structlog.get_logger().info(
        "source indexed",
        source_id=source_id,
        blocks=len(blocks),
        questions=len(questions),
        nodes=len(nodes),
    )


async def embed(items: list[tuple[int, str]]) -> list[tuple[int, list[float]]]:
    """Metinleri vektöre çevirip kimlikleriyle eşler; liste boşsa modeli yüklemez."""
    if not items:
        return []
    vectors = await asyncio.to_thread(get_embedding_provider().encode, [text for _, text in items])
    return [(item_id, vector) for (item_id, _), vector in zip(items, vectors, strict=True)]
