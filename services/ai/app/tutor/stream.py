"""Anlatım ve sohbetin ortak parçaları: kaynak arama ve olay akışı (plan Bölüm 9, 13.5).

Kaynaklar sorunun kazanımlarına bağlı yayındaki paragraflarda hybrid_search ile aranır; bütün
adaylar reranker'dan geçer, bilgi, alıntı ve metin blokları arasından ilk TUTOR_SOURCE_LIMIT tanesi
alınır; etkinlikler ve başlıklar alınmaz. Her paragraf Claude'a ayrı bir search_result olarak gider;
başlığı "Kitap · s. 174" biçimindedir. Tool'u olan görevde (sohbet) model ayrıca okuma tool'larını
çağırabilir. Olaylar SSE biçiminde yazılır: delta {text}, citation {blockId, sourceTitle, page},
done {} ve error (Problem Details). Alıntı kartı her zaman veritabanından okunmuş paragraftan
çizilir: paragraf alıntısı kendisinden, not alıntısı notun ilk dayanağından; dayanağı olmayan not
için kart çizilmez. Aynı paragraf bir cevapta bir kez alıntılanır. Akış hata verirse hata log'a
yazılır ve error olayıyla biter; Java yarım cevabı kaydetmez.
"""

from collections.abc import AsyncIterator, Mapping
from http import HTTPStatus

import structlog
from psycopg import AsyncConnection
from pydantic import BaseModel

from app.constants import (
    RRF_RESULT_LIMIT,
    TUTOR_SOURCE_BLOCK_TYPES,
    TUTOR_SOURCE_LIMIT,
)
from app.db.queries.tutor import fetch_source_blocks
from app.llm.runner import stream_task
from app.llm.tasks import LlmTask
from app.schemas.search import SearchFilters, SearchTarget
from app.schemas.tutor import (
    CitationEvent,
    DeltaEvent,
    ProblemEvent,
    SourceBlock,
    StreamCitation,
)
from app.search.hybrid import hybrid_search
from app.tutor.tools import execute_tool

STREAM_FAILED = ProblemEvent(title="AI stream failed", status=HTTPStatus.SERVICE_UNAVAILABLE)


class PreparedStream(BaseModel):
    """Akışa hazır görev: adı, prompt değişkenleri ve kaynak paragraflar."""

    task: LlmTask
    variables: Mapping[str, object]
    sources: list[SourceBlock]
    user_id: int


async def find_sources(
    connection: AsyncConnection, query: str, outcome_ids: list[int] | None
) -> list[SourceBlock]:
    """Sorguya en uygun yayındaki bilgi, alıntı ve metin paragraflarını sırasıyla döner."""
    filters = SearchFilters(target=SearchTarget.CONTENT_BLOCK, learning_outcome_ids=outcome_ids)
    hits = await hybrid_search(connection, query, filters, RRF_RESULT_LIMIT, rerank=True)
    blocks = await fetch_source_blocks(
        connection, [hit.id for hit in hits], TUTOR_SOURCE_BLOCK_TYPES
    )
    return blocks[:TUTOR_SOURCE_LIMIT]


async def stream_events(prepared: PreparedStream) -> AsyncIterator[str]:
    """Görevi çalıştırır ve parçalarını SSE olayları olarak verir."""
    sources = [block.citation_source() for block in prepared.sources]
    cited: set[int] = set()
    try:
        async for part in stream_task(
            prepared.task,
            prepared.variables,
            sources,
            user_id=prepared.user_id,
            execute_tool=execute_tool,
        ):
            if not isinstance(part, StreamCitation):
                yield sse("delta", DeltaEvent(text=part.text).model_dump_json(by_alias=True))
                continue
            block = part.source.block
            if block is None or block.block_id in cited:
                continue
            cited.add(block.block_id)
            event = CitationEvent(
                block_id=block.block_id, source_title=block.source_title, page=block.page_no
            )
            yield sse("citation", event.model_dump_json(by_alias=True))
    except Exception:
        structlog.get_logger().exception("tutor stream failed", task=prepared.task)
        yield sse("error", STREAM_FAILED.model_dump_json(by_alias=True))
        return
    yield sse("done", "{}")


def sse(name: str, data: str) -> str:
    """Olayı SSE metnine çevirir."""
    return f"event: {name}\ndata: {data}\n\n"
