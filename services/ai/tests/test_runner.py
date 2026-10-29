"""run_task'ı sahte Claude istemcisi ve gerçek Postgres'le test eder.

Claude'a gerçek çağrı yapılmaz: sahte istemci gelen isteği kaydeder ve hazır yanıt döner. Görev
ayarları, fiyatlar ve prompt klasörü testin kendi değerleriyle değiştirilir; böylece sonuç
repodaki yaml dosyalarına bağlı kalmaz. Kayıt testin transaction'ında llm_call_log'a yazılır ve
test bitince geri alınır.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from psycopg.rows import TupleRow
from pydantic import BaseModel

from app.llm import runner
from app.llm.pricing import PriceTier
from app.llm.runner import run_task
from app.llm.tasks import LlmTask, TaskConfig

Connection = psycopg.AsyncConnection[TupleRow]

HINT_PROMPT = """{# version: 2 #}
{% block system %}İpucu ver. Emin değilsen bunu açıkça söyle.{% endblock %}
{% block user %}Soru: {{ question }}{% endblock %}
"""
SOLVE_PROMPT = """{# version: 5 #}
{% block system %}Soruyu çöz.{% endblock %}
{% block user %}Çöz: {{ question }}{% endblock %}
"""
TASK_CONFIGS = {
    LlmTask.HINT: TaskConfig(
        model="claude-haiku-5-5", prompt="hint.j2", max_tokens=100, timeout_seconds=5
    ),
    LlmTask.ANSWER_SOLVE: TaskConfig(
        model="claude-sonnet-5-5", prompt="solve.j2", max_tokens=200, timeout_seconds=9
    ),
}
PRICE = PriceTier(
    input=Decimal("1"), cache_write=Decimal("1.25"), cache_read=Decimal("0.1"), output=Decimal("5")
)
PRICES = {config.model: [PRICE] for config in TASK_CONFIGS.values()}
VARIABLES = {"question": "Roman nedir?"}

READ_CALL = """
SELECT task, model, prompt_version, input_tokens, output_tokens, cache_read_tokens, cost_usd,
    request_id, user_id, duration_ms >= 0
FROM llm_call_log
WHERE request_id = %(request_id)s
"""
INSERT_STUDENT = """
INSERT INTO app_user (tenant_id, email, display_name)
SELECT id, 'ayse.yilmaz@example.com', 'Ayşe Yılmaz' FROM tenant ORDER BY id LIMIT 1
RETURNING id
"""


class Answer(BaseModel):
    """Sahte görevin JSON çıktısı."""

    choice: str


class FakeMessages:
    """messages.parse çağrılarını kaydeden ve hazır yanıt dönen sahte uç."""

    def __init__(self) -> None:
        """Boş istek listesiyle ve varsayılan yanıtla başlar."""
        self.requests: list[dict[str, object]] = []
        self.response = make_response()

    async def parse(self, **request: object) -> SimpleNamespace:
        """İsteği kaydeder ve hazır yanıtı döner."""
        self.requests.append(request)
        return self.response


class FakePool:
    """Testin transaction'ındaki bağlantıyı veren sahte havuz."""

    def __init__(self, connection: Connection) -> None:
        """Verilen bağlantıyı saklar."""
        self._connection = connection

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Connection]:
        """Saklanan bağlantıyı verir."""
        yield self._connection


def make_response(*, parsed: BaseModel | None = None, request_id: str = "req_1") -> SimpleNamespace:
    """Düşünme ve metin bloğu olan, token sayıları belli bir Claude yanıtı kurar."""
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text="Olay örgüsü olan uzun anlatı."),
        ],
        parsed_output=parsed,
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=1200,
            output_tokens=300,
            cache_read_input_tokens=800,
            cache_creation_input_tokens=100,
        ),
        _request_id=request_id,
    )


@pytest.fixture
def messages(db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeMessages:
    """Sahte istemciyi, test ayarlarını, prompt klasörünü ve testin bağlantısını bağlar."""
    (tmp_path / "hint.j2").write_text(HINT_PROMPT, encoding="utf-8")
    (tmp_path / "solve.j2").write_text(SOLVE_PROMPT, encoding="utf-8")
    fake = FakeMessages()
    monkeypatch.setattr(runner, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "get_task_configs", lambda: TASK_CONFIGS)
    monkeypatch.setattr(runner, "get_prices", lambda: PRICES)
    monkeypatch.setattr(runner, "get_client", lambda: SimpleNamespace(messages=fake))
    monkeypatch.setattr(runner, "get_pool", lambda: FakePool(db))
    return fake


async def insert_student(db: Connection) -> int:
    """Adı ve e-postası olan bir öğrenci ekler ve numarasını döner."""
    row = await (await db.execute(INSERT_STUDENT)).fetchone()
    assert row is not None
    return int(row[0])


async def read_call(db: Connection, request_id: str) -> tuple[object, ...] | None:
    """Verilen request_id'li kaydı okur."""
    cursor = await db.execute(READ_CALL, {"request_id": request_id})
    return await cursor.fetchone()


@pytest.mark.asyncio
async def test_task_name_selects_model_and_prompt(messages: FakeMessages) -> None:
    """Her görev kendi ayarındaki modelle ve kendi prompt dosyasıyla çağrılır."""
    await run_task(LlmTask.HINT, VARIABLES)
    await run_task(LlmTask.ANSWER_SOLVE, VARIABLES)

    hint, solve = messages.requests
    assert (hint["model"], hint["max_tokens"], hint["timeout"]) == ("claude-haiku-5-5", 100, 5)
    assert hint["messages"] == [{"role": "user", "content": "Soru: Roman nedir?"}]
    assert (solve["model"], solve["max_tokens"], solve["timeout"]) == ("claude-sonnet-5-5", 200, 9)
    assert solve["messages"] == [{"role": "user", "content": "Çöz: Roman nedir?"}]


@pytest.mark.asyncio
async def test_system_text_is_cached(messages: FakeMessages) -> None:
    """Prompt'un system bloğu önbellek işaretiyle sistem metni olarak gider."""
    await run_task(LlmTask.HINT, VARIABLES)

    assert messages.requests[0]["system"] == [
        {
            "type": "text",
            "text": "İpucu ver. Emin değilsen bunu açıkça söyle.",
            "cache_control": {"type": "ephemeral"},
        }
    ]


@pytest.mark.asyncio
async def test_output_model_returns_pydantic_object(messages: FakeMessages) -> None:
    """output_model verilince şema isteğe eklenir ve Pydantic nesnesi döner."""
    messages.response = make_response(parsed=Answer(choice="B"))

    answer = await run_task(LlmTask.ANSWER_SOLVE, VARIABLES, output_model=Answer)

    assert answer == Answer(choice="B")
    assert messages.requests[0]["output_format"] is Answer


@pytest.mark.asyncio
async def test_text_result_skips_thinking_blocks(messages: FakeMessages) -> None:
    """output_model verilmezse sadece metin blokları birleştirilip döner."""
    text = await run_task(LlmTask.HINT, VARIABLES)

    assert text == "Olay örgüsü olan uzun anlatı."
    assert messages.requests[0]["output_format"] is None


@pytest.mark.asyncio
async def test_call_is_logged_with_tokens_cost_and_duration(
    messages: FakeMessages, db: Connection
) -> None:
    """Çağrı görev, model, prompt sürümü, token, maliyet, süre ve request_id ile yazılır."""
    await run_task(LlmTask.HINT, VARIABLES)

    expected_cost = Decimal("0.002905")
    assert await read_call(db, "req_1") == (
        "HINT",
        "claude-haiku-5-5",
        2,
        1200,
        300,
        800,
        expected_cost,
        "req_1",
        None,
        True,
    )


@pytest.mark.asyncio
async def test_unparsed_output_is_logged_and_rejected(
    messages: FakeMessages, db: Connection
) -> None:
    """Model şemaya uyan çıktı vermezse çağrı yine kaydedilir ve hata verilir."""
    messages.response = make_response(request_id="req_unparsed")

    with pytest.raises(ValueError, match="Answer"):
        await run_task(LlmTask.ANSWER_SOLVE, VARIABLES, output_model=Answer)

    assert await read_call(db, "req_unparsed") is not None


@pytest.mark.asyncio
async def test_student_is_logged_by_id_only(messages: FakeMessages, db: Connection) -> None:
    """Öğrenci sadece sayısal numarasıyla kayda geçer; istekte kişisel bilgisi yoktur."""
    student_id = await insert_student(db)

    await run_task(LlmTask.HINT, VARIABLES, user_id=student_id)

    request = messages.requests[0]
    assert set(request) == {"model", "max_tokens", "system", "messages", "output_format", "timeout"}
    assert "Ayşe" not in str(request) and "ayse.yilmaz" not in str(request)
    row = await read_call(db, "req_1")
    assert row is not None and row[8] == student_id
