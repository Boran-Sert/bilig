"""stream_task'in tool döngüsünü SDK'nın gerçek tool runner'ı ve sahte HTTP cevaplarıyla test eder.

Claude'a gidilmez: istemci, her istekte sıradaki hazır turu SSE olarak akıtan sahte bir taşıyıcıyla
kurulur; böylece döngüyü SDK'nın kendisi çalıştırır ve giden istek gövdeleri okunabilir. Tool'lar
çağrıları kaydeden sahte çalıştırıcıyla çalışır. Tool tanımları repodaki prompts/tde/tools.yaml'dan
gelir; görev ayarı, fiyatlar ve prompt klasörü testin kendi değerleridir. Her turun kaydı testin
transaction'ında llm_call_log'a yazılır ve test bitince geri alınır.
"""

import json
from collections.abc import Mapping
from pathlib import Path

import httpx2
import psycopg
import pytest
from anthropic import AsyncAnthropic
from psycopg.rows import TupleRow

from app.llm import runner
from app.llm.runner import stream_task
from app.llm.tasks import LlmTask, TaskConfig
from app.schemas.tutor import CitationSource, SourceBlock, StreamCitation, StreamText, ToolOutput
from tests.test_runner import PRICE, FakePool, read_call

Connection = psycopg.AsyncConnection[TupleRow]

CHAT_PROMPT = """{# version: 2 #}
{% block system %}Notlara bak. Emin değilsen bunu açıkça söyle.{% endblock %}
{% block user %}Soru: {{ message }}{% endblock %}
"""
VARIABLES = {"message": "Küçük Ağa'yı kim yazdı?"}
PARAGRAPH = CitationSource(source="TDE 12 · s. 174", title="Roman", text="Tarihî roman.")
EVIDENCE = SourceBlock(
    block_id=55, source_title="TDE 12", page_no=88, title_path="Roman", markdown="Küçük Ağa."
)
NOTE = CitationSource(source="kb://note/7", title="Tarık Buğra", text="AUTHOR · Tarık Buğra")


def chat_config(max_tool_calls: int) -> dict[LlmTask, TaskConfig]:
    """Üç okuma tool'u ve verilen çağrı sınırıyla sohbet görev ayarını kurar."""
    return {
        LlmTask.CHAT: TaskConfig(
            model="claude-sonnet-5-5",
            prompt="chat.j2",
            max_tokens=300,
            timeout_seconds=9,
            tools=("search_notes", "open_note", "get_outcome"),
            max_tool_calls=max_tool_calls,
        )
    }


def sse(events: list[dict[str, object]]) -> bytes:
    """Olayları Messages API'nin SSE biçimine çevirir."""
    return "".join(
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
    ).encode("utf-8")


def turn(blocks: list[list[dict[str, object]]], stop_reason: str) -> bytes:
    """Verilen blok olaylarıyla ve bitiş nedeniyle bir cevap turu akışı kurar."""
    message = {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "content": [],
        "stop_reason": None,
        "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 1},
    }
    events: list[dict[str, object]] = [{"type": "message_start", "message": message}]
    for index, block in enumerate(blocks):
        events += [{**event, "index": index} for event in block]
    events += [
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": 20},
        },
        {"type": "message_stop"},
    ]
    return sse(events)


def text_block(text: str, cited_index: int | None = None) -> list[dict[str, object]]:
    """Metin bloğu olaylarını kurar; istenirse arkasına bir search_result alıntısı ekler."""
    events: list[dict[str, object]] = [
        {"type": "content_block_start", "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}},
    ]
    if cited_index is not None:
        citation = {
            "type": "search_result_location",
            "cited_text": "Küçük Ağa.",
            "search_result_index": cited_index,
            "source": "TDE 12 · s. 88",
            "title": "Roman",
            "start_block_index": 0,
            "end_block_index": 1,
        }
        events.append(
            {
                "type": "content_block_delta",
                "delta": {"type": "citations_delta", "citation": citation},
            }
        )
    return [*events, {"type": "content_block_stop"}]


def tool_block(tool_id: str, name: str, tool_input: dict[str, object]) -> list[dict[str, object]]:
    """Tool çağrısı bloğu olaylarını kurar."""
    start = {"type": "tool_use", "id": tool_id, "name": name, "input": {}}
    delta = {"type": "input_json_delta", "partial_json": json.dumps(tool_input)}
    return [
        {"type": "content_block_start", "content_block": start},
        {"type": "content_block_delta", "delta": delta},
        {"type": "content_block_stop"},
    ]


class FakeClaude:
    """İstekleri kaydeden ve hazır turları sırayla akıtan sahte Messages API."""

    def __init__(self, turns: list[bytes]) -> None:
        """Akıtılacak turları saklar."""
        self.turns = turns
        self.requests: list[dict[str, object]] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        """İsteği kaydeder ve sıradaki turu kendi request id'siyle döner."""
        self.requests.append(json.loads(request.content))
        headers = {"content-type": "text/event-stream", "request-id": f"req_{len(self.requests)}"}
        return httpx2.Response(200, headers=headers, content=self.turns[len(self.requests) - 1])


class FakeTools:
    """Tool çağrılarını kaydeden ve hazır sonuç dönen sahte çalıştırıcı."""

    def __init__(self, outputs: Mapping[str, ToolOutput]) -> None:
        """Tool adına göre dönülecek sonuçları saklar."""
        self.outputs = outputs
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def __call__(self, name: str, tool_input: Mapping[str, object]) -> ToolOutput:
        """Çağrıyı kaydeder ve hazır sonucu döner."""
        self.calls.append((name, dict(tool_input)))
        return self.outputs[name]


@pytest.fixture
def use_claude(db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> type[FakeClaude]:
    """Prompt klasörünü, fiyatları ve testin bağlantısını bağlar; sahte API kurucusunu verir."""
    (tmp_path / "chat.j2").write_text(CHAT_PROMPT, encoding="utf-8")
    monkeypatch.setattr(runner, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "get_prices", lambda: {"claude-sonnet-5-5": [PRICE]})
    monkeypatch.setattr(runner, "get_pool", lambda: FakePool(db))
    return FakeClaude


def connect(monkeypatch: pytest.MonkeyPatch, fake: FakeClaude, max_tool_calls: int) -> None:
    """İstemciyi sahte API'ye, görev ayarını verilen çağrı sınırına bağlar."""
    transport = httpx2.MockTransport(fake.handle)
    client = AsyncAnthropic(
        api_key="test", max_retries=0, http_client=httpx2.AsyncClient(transport=transport)
    )
    monkeypatch.setattr(runner, "get_client", lambda: client)
    monkeypatch.setattr(runner, "get_task_configs", lambda: chat_config(max_tool_calls))


@pytest.mark.asyncio
async def test_opened_note_is_cited_by_its_index_after_first_sources(
    use_claude: type[FakeClaude], db: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Açılan notun paragrafı ilk kaynaklardan sonraki sırasıyla alıntılanır; her tur kaydedilir."""
    paragraph = EVIDENCE.citation_source()
    fake = use_claude(
        [
            turn([tool_block("toolu_1", "open_note", {"note_id": 7})], "tool_use"),
            turn([text_block("Tarık Buğra yazdı.", cited_index=2)], "end_turn"),
        ]
    )
    connect(monkeypatch, fake, max_tool_calls=3)
    tools = FakeTools({"open_note": ToolOutput(sources=[NOTE, paragraph])})

    parts = [
        part async for part in stream_task(LlmTask.CHAT, VARIABLES, [PARAGRAPH], execute_tool=tools)
    ]

    assert parts == [StreamText(text="Tarık Buğra yazdı."), StreamCitation(source=paragraph)]
    assert tools.calls == [("open_note", {"note_id": 7})]
    first, second = fake.requests
    assert first["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert [tool["name"] for tool in first["tools"]] == ["search_notes", "open_note", "get_outcome"]
    assert all(tool["strict"] for tool in first["tools"])
    result = second["messages"][-1]["content"][0]
    assert result["type"] == "tool_result"
    assert [block["source"] for block in result["content"]] == ["kb://note/7", "TDE 12 · s. 88"]
    assert await read_call(db, "req_1") is not None
    assert await read_call(db, "req_2") is not None


@pytest.mark.asyncio
async def test_last_request_after_limit_cannot_call_tools(
    use_claude: type[FakeClaude], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Çağrı sınırı dolunca son istek tool_choice none ile gider ve model cevap verir."""
    fake = use_claude(
        [
            turn([tool_block("toolu_1", "search_notes", {"query": "Küçük Ağa"})], "tool_use"),
            turn([tool_block("toolu_2", "get_outcome", {"code": "A.2.7"})], "tool_use"),
            turn([text_block("Bulduklarım bunlar.")], "end_turn"),
        ]
    )
    connect(monkeypatch, fake, max_tool_calls=2)
    tools = FakeTools(
        {
            "search_notes": ToolOutput(text="AUTHOR · Tarık Buğra"),
            "get_outcome": ToolOutput(text="A"),
        }
    )

    parts = [part async for part in stream_task(LlmTask.CHAT, VARIABLES, [], execute_tool=tools)]

    assert parts == [StreamText(text="Bulduklarım bunlar.")]
    assert [request["tool_choice"]["type"] for request in fake.requests] == ["auto", "auto", "none"]
    assert len(tools.calls) == 2


@pytest.mark.asyncio
async def test_tool_error_goes_back_as_error_result(
    use_claude: type[FakeClaude], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hata dönen tool modele is_error sonucu olarak gider, alıntı listesine bir şey eklemez."""
    fake = use_claude(
        [
            turn([tool_block("toolu_1", "open_note", {"note_id": 9})], "tool_use"),
            turn([text_block("Not bulunamadı.", cited_index=0)], "end_turn"),
        ]
    )
    connect(monkeypatch, fake, max_tool_calls=3)
    missing = ToolOutput(text="There is no published note with this id.", is_error=True)
    tools = FakeTools({"open_note": missing})

    parts = [
        part async for part in stream_task(LlmTask.CHAT, VARIABLES, [PARAGRAPH], execute_tool=tools)
    ]

    result = fake.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True
    assert parts[-1] == StreamCitation(source=PARAGRAPH)


@pytest.mark.asyncio
async def test_tool_task_without_executor_is_rejected(
    use_claude: type[FakeClaude], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tool kullanan görev çalıştırıcı verilmeden başlatılamaz."""
    connect(monkeypatch, use_claude([]), max_tool_calls=3)

    with pytest.raises(ValueError, match="no tool executor"):
        async for _ in stream_task(LlmTask.CHAT, VARIABLES, []):
            pass
