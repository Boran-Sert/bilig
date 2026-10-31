"""Ortak arama: servisteki bütün aramalar hybrid_search'ten geçer (plan 13.11).

Sorgu NFC'ye çevrilir, çünkü kayıtlı metinler NFC'dir. Vektör ve BM25 aramaları ayrı çalışır ve
RRF ile birleşir: kayıt girdiği her listede 1 / (RRF_K + sıra) puan alır, puanlar toplanır.
Kosinüs uzaklığı ile BM25 puanı farklı ölçekte olduğu için puan yerine sıra kullanılır; eşit
puanda önce görülen önce gelir. İlk RRF_RESULT_LIMIT aday istenirse reranker'a gider. Sonuçtaki
skor RRF puanı ya da reranker skorudur. Modeller event loop'u kilitlemesin diye thread'de çalışır.
"""

import asyncio

from psycopg import AsyncConnection

from app.constants import RRF_K, RRF_RESULT_LIMIT
from app.schemas.search import SearchFilters, SearchHit
from app.search.bm25 import search_bm25
from app.search.embedding import get_embedding_provider
from app.search.reranker import get_reranker
from app.search.vector import search_vector
from app.text.turkish import normalize_nfc


async def hybrid_search(
    connection: AsyncConnection, query: str, filters: SearchFilters, top_k: int, rerank: bool
) -> list[SearchHit]:
    """Sorguya en uygun top_k kaydı vektör ve BM25 sonuçlarını birleştirerek döner."""
    query = normalize_nfc(query)
    embeddings = await asyncio.to_thread(get_embedding_provider().encode, [query])
    vector_hits = await search_vector(connection, embeddings[0], filters)
    bm25_hits = await search_bm25(connection, query, filters)
    candidates = fuse_rrf([vector_hits, bm25_hits])[:RRF_RESULT_LIMIT]
    if not rerank or not candidates:
        return candidates[:top_k]
    texts = [hit.text for hit in candidates]
    ranked = await asyncio.to_thread(get_reranker().rerank, query, texts, top_k)
    return [candidates[item.index].model_copy(update={"score": item.score}) for item in ranked]


def fuse_rrf(result_lists: list[list[SearchHit]]) -> list[SearchHit]:
    """Sıralı listeleri RRF puanıyla birleştirir; puanı yüksek kayıt önce gelir."""
    scores: dict[int, float] = {}
    hits: dict[int, SearchHit] = {}
    for results in result_lists:
        for rank, hit in enumerate(results, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1 / (RRF_K + rank)
            hits.setdefault(hit.id, hit)
    ordered = sorted(scores, key=lambda hit_id: scores[hit_id], reverse=True)
    return [hits[hit_id].model_copy(update={"score": scores[hit_id]}) for hit_id in ordered]
