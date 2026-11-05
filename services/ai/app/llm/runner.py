"""Claude'a yapılan bütün çağrıların geçtiği tek giriş noktası: run_task.

Görevin modeli ve prompt dosyası llm_tasks.yaml'dan, prompt metni prompts/tde'den gelir; çağıran
sadece görev adını ve değişkenleri verir. anthropic SDK'sı sadece bu dosyada içe aktarılır.
output_model verilirse yanıt messages.parse ile o Pydantic modeline çevrilir, verilmezse düz metin
döner. Sistem metni önbelleğe alınır. Hata alan isteği SDK kendisi tekrar dener. Her çağrı, sonucu
kullanılamasa bile token, maliyet ve süresiyle llm_call_log'a yazılır. user_id sadece bu kayda
gider; Claude'a kullanıcıya ait bilgi gönderilmez. stream_task alıntılı serbest metin görevleri
içindir: kaynaklar search_result bloğu olarak gider, metin ve alıntılar geldikçe verilir, çağrı
akış bitince kaydedilir. Akış yarıda koparsa token bilgisi gelmediği için kayıt yazılmaz.
Görüntü (PNG) verilirse mesaja metnin önünde eklenir. Görevin tool'ları varsa (sohbet) stream_task
SDK'nın tool runner'ıyla (beta) çalışır: tanımlar prompts/tde/tools.yaml'dan gelir, her cevap
turu ayrı kaydedilir, bir turda en fazla bir tool çağrılır ve çağrı sınırı dolunca son istek
tool_choice none ile gider. Alıntı sırası, istekte gönderilen bütün search_result'ların (önce ilk
kaynaklar, sonra tool sonuçları) birikmiş listesine göredir.
"""

import base64
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Mapping, Sequence
from functools import lru_cache
from typing import overload

from anthropic import AsyncAnthropic, beta_async_tool
from anthropic.lib.tools import BetaAsyncFunctionTool, ToolError
from anthropic.types import (
    ImageBlockParam,
    MessageParam,
    SearchResultBlockParam,
    TextBlockParam,
    Usage,
)
from anthropic.types.beta import BetaSearchResultBlockParam, BetaUsage
from anthropic.types.beta.message_create_params import ParseMessageCreateParamsBase
from pydantic import BaseModel

from app.constants import IMAGE_MEDIA_TYPE, LLM_MAX_RETRIES, MILLISECONDS_PER_SECOND, PROMPTS_DIR
from app.db.pool import get_pool
from app.db.queries.llm_call_log import LlmCall, save_llm_call
from app.llm.pricing import calculate_cost, get_prices
from app.llm.prompts import get_tool_prompts, render_prompt
from app.llm.tasks import LlmTask, get_task_configs
from app.schemas.tutor import CitationSource, StreamCitation, StreamText, ToolOutput

type ToolExecutor = Callable[[str, Mapping[str, object]], Awaitable[ToolOutput]]
type ToolFunction = Callable[..., Coroutine[None, None, list[BetaSearchResultBlockParam] | str]]


@lru_cache(maxsize=1)
def get_client() -> AsyncAnthropic:
    """Anthropic istemcisini süreç başına bir kez kurar; anahtar ANTHROPIC_API_KEY'den okunur."""
    return AsyncAnthropic(max_retries=LLM_MAX_RETRIES)


@overload
async def run_task(
    task: LlmTask,
    variables: Mapping[str, object],
    *,
    output_model: None = None,
    user_id: int | None = None,
    images: Sequence[bytes] = (),
) -> str: ...


@overload
async def run_task[OutputT: BaseModel](
    task: LlmTask,
    variables: Mapping[str, object],
    *,
    output_model: type[OutputT],
    user_id: int | None = None,
    images: Sequence[bytes] = (),
) -> OutputT: ...


async def run_task[OutputT: BaseModel](
    task: LlmTask,
    variables: Mapping[str, object],
    *,
    output_model: type[OutputT] | None = None,
    user_id: int | None = None,
    images: Sequence[bytes] = (),
) -> OutputT | str:
    """Görevi ayarındaki model ve prompt'la çalıştırır, çağrıyı kaydeder ve sonucu döner."""
    config = get_task_configs()[task]
    prompt = render_prompt(PROMPTS_DIR, config.prompt, variables)
    started = time.perf_counter()
    response = await get_client().messages.parse(
        model=config.model,
        max_tokens=config.max_tokens,
        system=[{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}],
        messages=[user_message(prompt.user, images)],
        output_format=output_model,
        timeout=config.timeout_seconds,
    )
    duration_ms = round((time.perf_counter() - started) * MILLISECONDS_PER_SECOND)
    await _save_call(
        task,
        config.model,
        prompt.version,
        response.usage,
        response._request_id,
        duration_ms,
        user_id,
    )
    if output_model is None:
        return "".join(block.text for block in response.content if block.type == "text")
    if response.parsed_output is None:
        raise ValueError(f"{task} returned no {output_model.__name__} ({response.stop_reason})")
    return response.parsed_output


def user_message(text: str, images: Sequence[bytes]) -> MessageParam:
    """Kullanıcı mesajını kurar; görüntü varsa PNG blokları metnin önüne konur."""
    if not images:
        return {"role": "user", "content": text}
    content: list[ImageBlockParam | TextBlockParam] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": IMAGE_MEDIA_TYPE,
                "data": base64.b64encode(image).decode("ascii"),
            },
        }
        for image in images
    ]
    content.append({"type": "text", "text": text})
    return {"role": "user", "content": content}


async def stream_task(
    task: LlmTask,
    variables: Mapping[str, object],
    sources: list[CitationSource],
    *,
    user_id: int | None = None,
    execute_tool: ToolExecutor | None = None,
) -> AsyncIterator[StreamText | StreamCitation]:
    """Görevi kaynaklarla akış olarak çalıştırır; görevin tool'u varsa tool döngüsüyle çalışır."""
    config = get_task_configs()[task]
    if config.tools:
        if execute_tool is None:
            raise ValueError(f"{task} uses tools but got no tool executor")
        async for part in _stream_with_tools(task, variables, sources, execute_tool, user_id):
            yield part
        return
    prompt = render_prompt(PROMPTS_DIR, config.prompt, variables)
    content: list[SearchResultBlockParam | TextBlockParam] = [*search_results(sources)]
    content.append({"type": "text", "text": prompt.user})
    started = time.perf_counter()
    async with get_client().messages.stream(
        model=config.model,
        max_tokens=config.max_tokens,
        system=[{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": content}],
        timeout=config.timeout_seconds,
    ) as stream:
        async for event in stream:
            if event.type == "text":
                yield StreamText(text=event.text)
            elif event.type == "citation" and event.citation.type == "search_result_location":
                yield StreamCitation(source=sources[event.citation.search_result_index])
        message = await stream.get_final_message()
        duration_ms = round((time.perf_counter() - started) * MILLISECONDS_PER_SECOND)
        await _save_call(
            task,
            config.model,
            prompt.version,
            message.usage,
            stream.request_id,
            duration_ms,
            user_id,
        )


async def _stream_with_tools(
    task: LlmTask,
    variables: Mapping[str, object],
    sources: list[CitationSource],
    execute_tool: ToolExecutor,
    user_id: int | None,
) -> AsyncIterator[StreamText | StreamCitation]:
    """Görevi SDK'nın tool döngüsüyle çalıştırır; çağrı sınırı dolunca son cevabı tool'suz ister."""
    config = get_task_configs()[task]
    prompt = render_prompt(PROMPTS_DIR, config.prompt, variables)
    sent = list(sources)
    content: list[SearchResultBlockParam | TextBlockParam] = [*search_results(sources)]
    content.append({"type": "text", "text": prompt.user})
    runner = get_client().beta.messages.tool_runner(
        model=config.model,
        max_tokens=config.max_tokens,
        system=[{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": content}],
        tools=[_runnable_tool(name, execute_tool, sent) for name in config.tools],
        tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        max_iterations=config.max_tool_calls + 1,
        stream=True,
        thread=False,
        timeout=config.timeout_seconds,
    )
    tool_calls = 0
    async for stream in runner:
        started = time.perf_counter()
        async for event in stream:
            if event.type == "text":
                yield StreamText(text=event.text)
            elif event.type == "citation" and event.citation.type == "search_result_location":
                yield StreamCitation(source=sent[event.citation.search_result_index])
        message = await stream.get_final_message()
        duration_ms = round((time.perf_counter() - started) * MILLISECONDS_PER_SECOND)
        await _save_call(
            task,
            config.model,
            prompt.version,
            message.usage,
            stream.request_id,
            duration_ms,
            user_id,
        )
        tool_calls += sum(block.type == "tool_use" for block in message.content)
        if tool_calls >= config.max_tool_calls:
            runner.set_messages_params(_without_tool_use)


def _runnable_tool(
    name: str, execute_tool: ToolExecutor, sent: list[CitationSource]
) -> BetaAsyncFunctionTool[ToolFunction]:
    """Tool'u tools.yaml'daki tanımıyla SDK'nın çalıştıracağı tool'a çevirir."""
    definition = get_tool_prompts().tools[name]

    async def call(**tool_input: object) -> list[BetaSearchResultBlockParam] | str:
        """Tool'u çalıştırır; kaynaklarını alıntı listesine ekler, hatayı hata sonucu yapar."""
        output = await execute_tool(name, tool_input)
        if output.is_error:
            raise ToolError(output.text)
        sent.extend(output.sources)
        return search_results(output.sources) if output.sources else output.text

    return beta_async_tool(
        call,
        name=name,
        description=definition.description,
        input_schema=definition.input_schema,
        strict=True,
    )


def _without_tool_use(
    params: ParseMessageCreateParamsBase[None],
) -> ParseMessageCreateParamsBase[None]:
    """Sonraki isteğin tool çağırmadan cevap vermesini ister."""
    return {**params, "tool_choice": {"type": "none"}}


def search_results(sources: list[CitationSource]) -> list[SearchResultBlockParam]:
    """Kaynakları alıntısı açık search_result bloklarına çevirir."""
    return [
        {
            "type": "search_result",
            "source": source.source,
            "title": source.title,
            "content": [{"type": "text", "text": source.text}],
            "citations": {"enabled": True},
        }
        for source in sources
    ]


async def _save_call(
    task: LlmTask,
    model: str,
    prompt_version: int,
    usage: Usage | BetaUsage,
    request_id: str | None,
    duration_ms: int,
    user_id: int | None,
) -> None:
    """Çağrının token, maliyet ve süre bilgisini llm_call_log'a yazar."""
    if request_id is None:
        raise RuntimeError(f"Claude response for {task} has no request id")
    cache_read_tokens = usage.cache_read_input_tokens or 0
    cost = calculate_cost(
        get_prices()[model],
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=usage.cache_creation_input_tokens or 0,
    )
    call = LlmCall(
        task=task,
        model=model,
        prompt_version=prompt_version,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=cache_read_tokens,
        cost_usd=cost,
        duration_ms=duration_ms,
        request_id=request_id,
        user_id=user_id,
    )
    async with get_pool().connection() as connection:
        await save_llm_call(connection, call)
