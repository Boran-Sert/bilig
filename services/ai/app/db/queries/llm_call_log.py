"""Claude çağrılarını llm_call_log tablosuna yazan sorgu.

Her run_task çağrısı bir satır yazar: görev, model, prompt sürümü, token sayıları, tahmini maliyet,
süre ve Anthropic'in request_id'si. user_id öğrencinin sayısal numarasıdır; çağrı bir öğrenci için
yapılmadıysa boştur. Tablo core'un Flyway migration'larıyla kurulur.
"""

from decimal import Decimal

from psycopg import AsyncConnection
from pydantic import BaseModel

from app.llm.tasks import LlmTask

INSERT_LLM_CALL = """
INSERT INTO llm_call_log (
    task, model, prompt_version, input_tokens, output_tokens, cache_read_tokens,
    cost_usd, duration_ms, request_id, user_id
)
VALUES (
    %(task)s, %(model)s, %(prompt_version)s, %(input_tokens)s, %(output_tokens)s,
    %(cache_read_tokens)s, %(cost_usd)s, %(duration_ms)s, %(request_id)s, %(user_id)s
)
"""


class LlmCall(BaseModel):
    """llm_call_log'a yazılan tek Claude çağrısının bilgileri."""

    task: LlmTask
    model: str
    prompt_version: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_usd: Decimal
    duration_ms: int
    request_id: str
    user_id: int | None


async def save_llm_call(connection: AsyncConnection, call: LlmCall) -> None:
    """Çağrının kaydını yazar."""
    await connection.execute(INSERT_LLM_CALL, call.model_dump())
