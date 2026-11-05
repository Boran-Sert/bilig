"""ANALYZE_ANSWER işinin sınıflandırma ve kalıcı kayıt akışını test eder."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from app.db.queries.answer_analysis import AnswerForAnalysis
from app.jobs import analyze_answer
from app.jobs.queue import Job, JobType
from app.llm.tasks import LlmTask
from app.schemas.answer_analysis import ErrorType, ErrorTypeAnalysis
from app.schemas.question import Block, QuestionContent, QuestionOption

Connection = psycopg.AsyncConnection[TupleRow]


class FakePool:
    """Test transaction'ındaki veritabanı bağlantısını havuz arayüzüyle verir."""

    def __init__(self, connection: Connection) -> None:
        """Verilen bağlantıyı saklar."""
        self._connection = connection

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Connection]:
        """Saklanan bağlantıyı verir."""
        yield self._connection


class NoDatabasePool:
    """Veritabanı bağlantısı oluşturmayan işleyici havuzu."""

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[None]:
        """Sahte sorgu işlevleri için boş bağlantı verir."""
        yield None


class FakeClassifier:
    """Görev girdilerini kaydedip sabit hata türü döndürür."""

    def __init__(self) -> None:
        """Boş çağrı listesiyle başlar."""
        self.calls: list[tuple[LlmTask, Mapping[str, object]]] = []

    async def __call__(
        self,
        task: LlmTask,
        variables: Mapping[str, object],
        *,
        output_model: type[ErrorTypeAnalysis],
    ) -> ErrorTypeAnalysis:
        """Çağrıyı kaydeder ve inceleme gerektiren sınıflandırmayı döner."""
        self.calls.append((task, variables))
        assert output_model is ErrorTypeAnalysis
        return ErrorTypeAnalysis(error_type=ErrorType.MISCONCEPTION, needs_review=True)


async def insert_user(connection: Connection, identifier: str) -> int:
    """Test için Bilig kiracısına öğrenci ekler."""
    user_cursor = await connection.execute(
        """
        INSERT INTO app_user (tenant_id, email, display_name, role)
        SELECT id, %s, %s, 'STUDENT' FROM tenant WHERE name = 'Bilig'
        RETURNING id
        """,
        (f"{identifier}@example.test", identifier),
    )
    user_row = await user_cursor.fetchone()
    assert user_row is not None
    return int(user_row[0])


async def insert_unit(connection: Connection, identifier: str) -> int:
    """Sınıflandırma sorusu için ders, program ve ünite oluşturur."""
    subject_cursor = await connection.execute(
        "INSERT INTO subject (code, name) VALUES (%s, %s) RETURNING id",
        (identifier, identifier),
    )
    subject_row = await subject_cursor.fetchone()
    assert subject_row is not None
    curriculum_cursor = await connection.execute(
        """
        INSERT INTO curriculum (subject_id, name, model, year)
        VALUES (%s, %s, 'LEGACY', 2018) RETURNING id
        """,
        (subject_row[0], identifier),
    )
    curriculum_row = await curriculum_cursor.fetchone()
    assert curriculum_row is not None
    unit_cursor = await connection.execute(
        """
        INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
        VALUES (%s, 12, 1, %s) RETURNING id
        """,
        (curriculum_row[0], identifier),
    )
    unit_row = await unit_cursor.fetchone()
    assert unit_row is not None
    return int(unit_row[0])


async def insert_question(connection: Connection, unit_id: int, identifier: str) -> int:
    """İçeriği ve doğru seçeneği belirlenmiş test sorusu oluşturur."""
    question_cursor = await connection.execute(
        """
        INSERT INTO question (
            curriculum_unit_id, origin, content, correct_option, content_hash, status
        )
        VALUES (%s, 'SOURCE', %s, 'B', %s, 'PUBLISHED') RETURNING id
        """,
        (
            unit_id,
            Jsonb(
                {
                    "stem": [{"type": "paragraph", "md": "Soru"}],
                    "options": [
                        {
                            "label": label,
                            "blocks": [{"type": "paragraph", "md": f"Seçenek {label}"}],
                        }
                        for label in ("A", "B", "C", "D", "E")
                    ],
                }
            ),
            identifier.replace("-", "") * 2,
        ),
    )
    question_row = await question_cursor.fetchone()
    assert question_row is not None
    return int(question_row[0])


async def insert_wrong_answer(connection: Connection) -> int:
    """Gerekli bağlı kayıtları oluşturarak yanlış cevap ekler."""
    identifier = str(uuid4())
    user_id = await insert_user(connection, identifier)
    unit_id = await insert_unit(connection, identifier)
    question_id = await insert_question(connection, unit_id, identifier)
    session_cursor = await connection.execute(
        "INSERT INTO study_session (user_id) VALUES (%s) RETURNING id",
        (user_id,),
    )
    session_row = await session_cursor.fetchone()
    assert session_row is not None
    answer_cursor = await connection.execute(
        """
        INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct)
        VALUES (%s, %s, 'A', false) RETURNING id
        """,
        (session_row[0], question_id),
    )
    answer_row = await answer_cursor.fetchone()
    assert answer_row is not None
    return int(answer_row[0])


async def assert_analysis_saved(
    connection: Connection, answer_id: int, classifier: FakeClassifier
) -> None:
    """Kayıt ve kişisel verisiz çağrıyı doğrular."""
    assert len(classifier.calls) == 1
    task, variables = classifier.calls[0]
    assert task == LlmTask.ERROR_TYPE
    assert set(variables) == {"question", "selected_option", "correct_option"}
    assert variables["selected_option"] == "A"
    assert variables["correct_option"] == "B"
    row = await (
        await connection.execute(
            """
            SELECT answer_analysis.error_type, answer_analysis.needs_review,
                student_answer.error_type
            FROM answer_analysis
            JOIN student_answer ON student_answer.id = answer_analysis.student_answer_id
            WHERE answer_analysis.student_answer_id = %s
            """,
            (answer_id,),
        )
    ).fetchone()
    assert row == ("MISCONCEPTION", True, "MISCONCEPTION")


@pytest.mark.asyncio
async def test_handler_saves_analysis_once_without_sending_personal_data(
    db: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """İş hata türünü ve inceleme işaretini kaydeder, tekrarında Claude'u çağırmaz."""
    answer_id = await insert_wrong_answer(db)
    classifier = FakeClassifier()
    pool = FakePool(db)

    monkeypatch.setattr(analyze_answer, "get_pool", lambda: pool)
    monkeypatch.setattr(analyze_answer, "run_task", classifier)
    job = Job(
        id=1,
        job_type=JobType.ANALYZE_ANSWER,
        payload={"studentAnswerId": answer_id},
        last_completed_step=None,
        attempts=1,
    )

    await analyze_answer.run_analyze_answer(job)
    await analyze_answer.run_analyze_answer(job)
    await assert_analysis_saved(db, answer_id, classifier)


@pytest.mark.asyncio
async def test_handler_builds_personal_data_free_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """İşleyici yalnızca soru ve cevap seçeneklerini LLM görevine verir."""
    content = QuestionContent(
        stem=[Block(type="paragraph", md="Soru")],
        options=[
            QuestionOption(label="A", blocks=[Block(type="paragraph", md="Yanlış seçenek")]),
            QuestionOption(label="B", blocks=[Block(type="paragraph", md="Doğru seçenek")]),
        ],
    )
    saved: list[tuple[int, ErrorTypeAnalysis]] = []
    classifier = FakeClassifier()

    async def fetch_answer(_connection: object, _student_answer_id: int) -> AnswerForAnalysis:
        """Sahte yanlış cevabı döner."""
        return AnswerForAnalysis(content=content, selected_option="A", correct_option="B")

    async def save_answer(
        _connection: object, student_answer_id: int, analysis: ErrorTypeAnalysis
    ) -> None:
        """Saklanan sınıflandırmayı kaydeder."""
        saved.append((student_answer_id, analysis))

    monkeypatch.setattr(analyze_answer, "get_pool", NoDatabasePool)
    monkeypatch.setattr(analyze_answer, "fetch_answer_for_analysis", fetch_answer)
    monkeypatch.setattr(analyze_answer, "save_answer_analysis", save_answer)
    monkeypatch.setattr(analyze_answer, "run_task", classifier)
    job = Job(
        id=1,
        job_type=JobType.ANALYZE_ANSWER,
        payload={"studentAnswerId": 73},
        last_completed_step=None,
        attempts=1,
    )

    await analyze_answer.run_analyze_answer(job)

    assert classifier.calls == [
        (
            LlmTask.ERROR_TYPE,
            {
                "question": "Soru\nA) Yanlış seçenek\nB) Doğru seçenek",
                "selected_option": "A",
                "correct_option": "B",
            },
        )
    ]
    assert saved == [(73, ErrorTypeAnalysis(error_type=ErrorType.MISCONCEPTION, needs_review=True))]


def test_handler_is_registered() -> None:
    """ANALYZE_ANSWER türü worker eşlemesinde sınıflandırıcıya bağlanır."""
    from app.jobs.handlers import HANDLERS

    assert HANDLERS[JobType.ANALYZE_ANSWER] is analyze_answer.run_analyze_answer
