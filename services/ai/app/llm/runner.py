"""Claude'a yapılan bütün çağrıların geçtiği tek giriş noktası: run_task.

Görevin modeli ve prompt dosyası llm_tasks.yaml'dan, prompt metni prompts/tde'den gelir; çağıran
sadece görev adını ve değişkenleri verir. anthropic SDK'sı sadece bu dosyada içe aktarılır.
output_model verilirse yanıt messages.parse ile o Pydantic modeline çevrilir, verilmezse düz metin
döner. Sistem metni önbelleğe alınır. Hata alan isteği SDK kendisi tekrar dener. Her çağrı, sonucu
kullanılamasa bile token, maliyet ve süresiyle llm_call_log'a yazılır. user_id sadece bu kayda
gider; Claude'a kullanıcıya ait bilgi gönderilmez. Alıntı, tool ve akış (stream) henüz yoktur.
"""

import time
from collections.abc import Mapping
from functools import lru_cache
from typing import overload

from anthropic import AsyncAnthropic
from anthropic.types import Message
from pydantic import BaseModel

from app.constants import LLM_MAX_RETRIES, MILLISECONDS_PER_SECOND, PROMPTS_DIR
from app.db.pool import get_pool
from app.db.queries.llm_call_log import LlmCall, save_llm_call
from app.llm.pricing import calculate_cost, get_prices
from app.llm.prompts import render_prompt
from app.llm.tasks import LlmTask, get_task_configs


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
) -> str: ...


@overload
async def run_task[OutputT: BaseModel](
    task: LlmTask,
    variables: Mapping[str, object],
    *,
    output_model: type[OutputT],
    user_id: int | None = None,
) -> OutputT: ...


async def run_task[OutputT: BaseModel](
    task: LlmTask,
    variables: Mapping[str, object],
    *,
    output_model: type[OutputT] | None = None,
    user_id: int | None = None,
) -> OutputT | str:
    """Görevi ayarındaki model ve prompt'la çalıştırır, çağrıyı kaydeder ve sonucu döner."""
    config = get_task_configs()[task]
    prompt = render_prompt(PROMPTS_DIR, config.prompt, variables)
    started = time.perf_counter()
    response = await get_client().messages.parse(
        model=config.model,
        max_tokens=config.max_tokens,
        system=[{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt.user}],
        output_format=output_model,
        timeout=config.timeout_seconds,
    )
    duration_ms = round((time.perf_counter() - started) * MILLISECONDS_PER_SECOND)
    await _save_call(task, config.model, prompt.version, response, duration_ms, user_id)
    if output_model is None:
        return "".join(block.text for block in response.content if block.type == "text")
    if response.parsed_output is None:
        raise ValueError(f"{task} returned no {output_model.__name__} ({response.stop_reason})")
    return response.parsed_output


async def _save_call(
    task: LlmTask,
    model: str,
    prompt_version: int,
    response: Message,
    duration_ms: int,
    user_id: int | None,
) -> None:
    """Çağrının token, maliyet ve süre bilgisini llm_call_log'a yazar."""
    if response._request_id is None:
        raise RuntimeError(f"Claude response for {task} has no request id")
    usage = response.usage
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
        request_id=response._request_id,
        user_id=user_id,
    )
    async with get_pool().connection() as connection:
        await save_llm_call(connection, call)
