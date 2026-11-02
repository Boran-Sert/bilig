"""İpucu, anlatım ve sohbet uçlarını sahte hazırlık ve sahte Claude akışıyla test eder.

Veritabanına ve Claude'a gidilmez: havuz, hazırlık fonksiyonları ve stream_task testin sahte
nesneleriyle değiştirilir. Uçların token kontrolü, durum kodları ve SSE olayları ölçülür.
"""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from app.api import tutor as api
from app.llm.tasks import LlmTask
from app.main import app
from app.schemas.tutor import CitationSource, SourceBlock, StreamCitation, StreamText
from app.tutor import stream
from app.tutor.chat import NoUserMessageError
from app.tutor.stream import PreparedStream

TOKEN = {"X-Internal-Token": "test-internal-token"}
EXPLANATION = {"userId": 3, "questionId": 42, "selectedOption": "A"}
CHAT = {"conversationId": 9, "userId": 3}
SOURCES = [
    SourceBlock(
        block_id=101, source_title="TDE 12", page_no=174, title_path="Roman", markdown="Tarihî."
    ),
    SourceBlock(
        block_id=102, source_title="TDE 12", page_no=175, title_path="Roman", markdown="Tahlil."
    ),
]
PREPARED = PreparedStream(task=LlmTask.TOPIC_EXPLAIN, variables={}, sources=SOURCES, user_id=3)


class FakePool:
    """Bağlantı yerine boş değer veren sahte havuz."""

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[None]:
        """Boş bağlantı verir."""
        yield None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Havuzu sahtesiyle değiştirir ve uygulamaya istemci açar."""
    monkeypatch.setattr(api, "get_pool", FakePool)
    return TestClient(app)


def use_prepared(monkeypatch: pytest.MonkeyPatch, prepared: PreparedStream | None) -> None:
    """Anlatım ve sohbet hazırlığını hazır sonuçla değiştirir."""

    async def fake_prepare(*_: object) -> PreparedStream | None:
        """Hazır sonucu döner."""
        return prepared

    monkeypatch.setattr(api, "prepare_explanation", fake_prepare)
    monkeypatch.setattr(api, "prepare_chat", fake_prepare)


def use_stream(monkeypatch: pytest.MonkeyPatch, *, fail: bool = False) -> list[object]:
    """stream_task yerine metin, iki kez aynı alıntı ve metin akıtan sahte akışı koyar."""
    calls: list[object] = []

    async def fake_stream(
        task: LlmTask,
        variables: Mapping[str, object],
        sources: list[CitationSource],
        *,
        user_id: int | None = None,
    ) -> AsyncIterator[StreamText | StreamCitation]:
        """Hazır parçaları verir; istenirse arada hata verir."""
        calls.append(sources)
        yield StreamText(text="Küçük Ağa ")
        if fail:
            raise RuntimeError("stream broke")
        yield StreamCitation(source_index=1)
        yield StreamCitation(source_index=1)
        yield StreamText(text="tarihî romandır.")

    monkeypatch.setattr(stream, "stream_task", fake_stream)
    return calls


@pytest.mark.parametrize(
    ("path", "body"),
    [("/internal/hints", {"questionId": 42}), ("/internal/explanations", EXPLANATION)],
)
@pytest.mark.parametrize("headers", [{}, {"X-Internal-Token": "wrong"}])
def test_request_without_valid_token_is_rejected(
    client: TestClient, path: str, body: dict[str, object], headers: dict[str, str]
) -> None:
    """Token yoksa ya da yanlışsa istek 401 ile reddedilir."""
    assert client.post(path, json=body, headers=headers).status_code == 401


def test_hint_returns_camel_case_body(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """İpucu {"hint": ...} olarak döner."""

    async def fake_hint(question_id: int) -> str:
        """Soru numarasını ipucuna koyar."""
        return f"Soru {question_id} için ipucu"

    monkeypatch.setattr(api, "generate_hint", fake_hint)

    response = client.post("/internal/hints", json={"questionId": 42}, headers=TOKEN)

    assert response.status_code == 200
    assert response.json() == {"hint": "Soru 42 için ipucu"}


def test_hint_of_unknown_question_is_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yayında olmayan sorunun ipucu 404 döner."""

    async def fake_hint(question_id: int) -> None:
        """Soru bulunamadı."""

    monkeypatch.setattr(api, "generate_hint", fake_hint)

    assert client.post("/internal/hints", json={"questionId": 42}, headers=TOKEN).status_code == 404


def test_explanation_streams_delta_citation_and_done(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Metin ve alıntı olayları sırayla gelir, aynı alıntı bir kez gider, akış done ile biter."""
    use_prepared(monkeypatch, PREPARED)
    calls = use_stream(monkeypatch)

    response = client.post("/internal/explanations", json=EXPLANATION, headers=TOKEN)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == (
        'event: delta\ndata: {"text":"Küçük Ağa "}\n\n'
        'event: citation\ndata: {"blockId":102,"sourceTitle":"TDE 12","page":175}\n\n'
        'event: delta\ndata: {"text":"tarihî romandır."}\n\n'
        "event: done\ndata: {}\n\n"
    )
    assert calls == [
        [
            CitationSource(source="TDE 12 · s. 174", title="Roman", text="Tarihî."),
            CitationSource(source="TDE 12 · s. 175", title="Roman", text="Tahlil."),
        ]
    ]


def test_failed_stream_ends_with_error_event(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Akış koparsa error olayı gider ve done gönderilmez."""
    use_prepared(monkeypatch, PREPARED)
    use_stream(monkeypatch, fail=True)

    response = client.post("/internal/explanations", json=EXPLANATION, headers=TOKEN)

    assert response.text.endswith(
        'event: error\ndata: {"title":"AI stream failed","status":503}\n\n'
    )
    assert "event: done" not in response.text


def test_explanation_of_unknown_question_is_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Soru ya da öğrenci bulunamazsa akış başlamadan 404 döner."""
    use_prepared(monkeypatch, None)

    response = client.post("/internal/explanations", json=EXPLANATION, headers=TOKEN)

    assert response.status_code == 404


def test_chat_streams_answer(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sohbet cevabı da aynı olaylarla akar."""
    use_prepared(monkeypatch, PREPARED.model_copy(update={"task": LlmTask.CHAT}))
    use_stream(monkeypatch)

    response = client.post("/internal/chat", json=CHAT, headers=TOKEN)

    assert response.status_code == 200
    assert response.text.endswith("event: done\ndata: {}\n\n")


def test_chat_without_new_message_is_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Son mesajı öğrenciden olmayan sohbet 409 döner."""

    async def fake_prepare(*_: object) -> PreparedStream:
        """Yeni mesaj yok."""
        raise NoUserMessageError("no new message")

    monkeypatch.setattr(api, "prepare_chat", fake_prepare)

    assert client.post("/internal/chat", json=CHAT, headers=TOKEN).status_code == 409
