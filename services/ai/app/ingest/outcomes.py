"""Kazanım eşleştirme adımı (hazırlık hattı A8, OUTCOMES).

Kaynağın soruları ve paragrafları ölçtükleri bütün kazanımlara bağlanır. Adaylar ünitenin
kazanımlarından hybrid_search ile bulunur (reranker kapalı; sorularda 16, paragraflarda 5 aday).
Ünitenin bağlı kazanımı yoksa (Giriş, Söylev) ya da ünitesi bilinmiyorsa bütün kazanımlarda
aranır. Seçimi OUTCOME_MATCH yapar; kod, kodların adaylardan geldiğini ve en az bir kazanım
kaldığını kontrol eder. Herhangi bir kazanımın güveni orta ya da düşükse, aday dışı kod geldiyse
ya da geçerli kazanım kalmadıysa içerik LOW_CONFIDENCE ile incelemeye düşer; düşmeyen içerik
güven eşiğini geçmiştir ve doğrudan yayına alınır (PUBLISHED). Bağlar MODEL olarak
yazılır; sıra ya da ağırlık yoktur. Bağı ya da inceleme kaydı olan içerik atlanır, bu yüzden adım
ikinci kez çalışınca kopya bağ ve ikinci model çağrısı olmaz. Vektörü olmayan kazanımların
vektörü önce hesaplanır. Havuz bağlantısı autocommit olmadığı için her okuma ve yazma kendi
transaction'ında yapılır: her içeriğin sonucu ayrı commit edilir, Claude çağrısı sırasında açık
transaction kalmaz ve yarıda kalan iş, eşlenmiş içerikler için modeli tekrar çağırmaz.
"""

import asyncio

import structlog
from psycopg import AsyncConnection

from app.constants import OUTCOME_PARAGRAPH_CANDIDATES, OUTCOME_QUESTION_CANDIDATES
from app.db.queries.outcomes import (
    fetch_candidates,
    fetch_outcomes_without_embedding,
    fetch_unmatched_items,
    open_review,
    publish_item,
    save_links,
    save_outcome_embeddings,
)
from app.llm.runner import run_task
from app.llm.tasks import LlmTask
from app.schemas.outcome_match import (
    Confidence,
    ItemKind,
    MatchItem,
    OutcomeCandidate,
    OutcomeChoice,
    OutcomeMatch,
)
from app.schemas.search import SearchFilters, SearchTarget
from app.search.embedding import get_embedding_provider
from app.search.hybrid import hybrid_search

CANDIDATE_LIMITS = {
    ItemKind.QUESTION: OUTCOME_QUESTION_CANDIDATES,
    ItemKind.PARAGRAPH: OUTCOME_PARAGRAPH_CANDIDATES,
}


async def match_source_outcomes(connection: AsyncConnection, source_document_id: int) -> None:
    """Kaynağın eşlenmemiş sorularını ve paragraflarını kazanımlara bağlar."""
    async with connection.transaction():
        await embed_missing_outcomes(connection)
    async with connection.transaction():
        items = await fetch_unmatched_items(connection, source_document_id)
    review_count = 0
    for item_id, item in items:
        choice = await match_outcomes(connection, item)
        async with connection.transaction():
            await save_choice(connection, item.kind, item_id, choice)
        review_count += choice.needs_review
    structlog.get_logger().info(
        "outcomes matched",
        source_document_id=source_document_id,
        items=len(items),
        review=review_count,
    )


async def embed_missing_outcomes(connection: AsyncConnection) -> None:
    """Vektörü olmayan kazanımların vektörünü arama metninden hesaplayıp yazar."""
    outcomes = await fetch_outcomes_without_embedding(connection)
    if not outcomes:
        return
    texts = [text for _, text in outcomes]
    vectors = await asyncio.to_thread(get_embedding_provider().encode, texts)
    embeddings = [
        (outcome_id, vector) for (outcome_id, _), vector in zip(outcomes, vectors, strict=True)
    ]
    await save_outcome_embeddings(connection, embeddings)


async def match_outcomes(connection: AsyncConnection, item: MatchItem) -> OutcomeChoice:
    """İçeriğin ölçtüğü kazanımları adaylar arasından seçtirir ve sonucu kontrol eder."""
    async with connection.transaction():
        candidates = await find_candidates(connection, item)
    variables = {
        "kind": item.kind.value,
        "text": item.text,
        "correct_option": item.correct_option,
        "candidates": candidates,
    }
    match = await run_task(LlmTask.OUTCOME_MATCH, variables, output_model=OutcomeMatch)
    return check_match(match, candidates)


async def find_candidates(connection: AsyncConnection, item: MatchItem) -> list[OutcomeCandidate]:
    """Ünitenin kazanımlarından adayları bulur; ünitede kazanım yoksa bütün kazanımlarda arar."""
    limit = CANDIDATE_LIMITS[item.kind]
    filters = SearchFilters(
        target=SearchTarget.LEARNING_OUTCOME, curriculum_unit_id=item.curriculum_unit_id
    )
    hits = await hybrid_search(connection, item.text, filters, limit, rerank=False)
    if not hits and item.curriculum_unit_id is not None:
        filters = SearchFilters(target=SearchTarget.LEARNING_OUTCOME)
        hits = await hybrid_search(connection, item.text, filters, limit, rerank=False)
    return await fetch_candidates(connection, [hit.id for hit in hits])


def check_match(match: OutcomeMatch, candidates: list[OutcomeCandidate]) -> OutcomeChoice:
    """Aday dışı ve tekrar eden kodları atar; güveni yüksek olmayan ya da boş sonucu işaretler."""
    by_code = {candidate.code: candidate for candidate in candidates}
    chosen: dict[str, OutcomeCandidate] = {}
    needs_review = False
    for outcome in match.outcomes:
        candidate = by_code.get(outcome.code)
        if candidate is None:
            needs_review = True
            continue
        chosen[outcome.code] = candidate
        needs_review = needs_review or outcome.confidence is not Confidence.HIGH
    return OutcomeChoice(outcomes=list(chosen.values()), needs_review=needs_review or not chosen)


async def save_choice(
    connection: AsyncConnection, kind: ItemKind, item_id: int, choice: OutcomeChoice
) -> None:
    """Seçilen kazanımları bağlar; incelemeye düşene kayıt açar, düşmeyeni yayına alır."""
    if choice.outcomes:
        await save_links(connection, kind, item_id, [outcome.id for outcome in choice.outcomes])
    if choice.needs_review:
        await open_review(connection, kind, item_id)
    else:
        await publish_item(connection, kind, item_id)
