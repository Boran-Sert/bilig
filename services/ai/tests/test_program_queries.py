"""Kazanım ağacını veritabanına yazan sorguları sahte bağlantıyla test eder.

Program tabloları core migration'ıyla (#93) gelene kadar CI'da gerçek veritabanı yok. Bu yüzden
burada sorguların sırası, parametreleri, transaction kullanımı ve sayımlar ölçülür. Upsert'ün
gerçek Postgres'teki davranışı (kopya satır, embedding sıfırlama) PR açıklamasında elle denendi.
"""

import re
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.db.queries.program import (
    COUNT_MISSING_LEARNING_OUTCOMES,
    UPSERT_CURRICULUM,
    UPSERT_LEARNING_OUTCOME,
    UPSERT_LEARNING_OUTCOME_GROUP,
    UPSERT_SUBJECT,
    build_search_text,
    save_program,
)
from app.schemas.program import (
    Curriculum,
    LearningOutcome,
    LearningOutcomeGroup,
    Program,
    ProgramSaveSummary,
    Subject,
)

PROGRAM = Program(
    subject=Subject(code="TDE", name="Türk Dili ve Edebiyatı"),
    curriculum=Curriculum(name="TDE Öğretim Programı 2018", model="LEGACY", year=2018),
    groups=[
        LearningOutcomeGroup(
            code="A.1",
            name="Şiir",
            outcomes=[
                LearningOutcome(code="A.1.1", title="Şiiri yorumlar.", meb_explanation="a. Not."),
                LearningOutcome(code="A.1.2", title="Temayı belirler.", meb_explanation=None),
            ],
        ),
        LearningOutcomeGroup(
            code="B",
            name="Yazma",
            outcomes=[LearningOutcome(code="B.1", title="Metin yazar.", meb_explanation=None)],
        ),
    ],
)


class FakeCursor:
    """Tek satır dönen sahte imleç."""

    def __init__(self, row: tuple[Any, ...] | None) -> None:
        """Dönecek satırı saklar."""
        self.row = row

    async def fetchone(self) -> tuple[Any, ...] | None:
        """Saklanan satırı döner."""
        return self.row


class FakeConnection:
    """Çalıştırılan sorguları kaydeden, kimlik ve kazanım sonuçlarını sırayla veren bağlantı."""

    def __init__(self, outcome_rows: list[tuple[bool] | None]) -> None:
        """Kazanım upsert'lerinin döneceği satırları alır."""
        self.calls: list[tuple[str, dict[str, Any], bool]] = []
        self.outcome_rows: Iterator[tuple[bool] | None] = iter(outcome_rows)
        self.next_id = 100
        self.in_transaction = False
        self.transaction_error: BaseException | None = None
        self.fail_on: str | None = None
        self.missing = 0

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Transaction'a girip çıkıldığını ve hatayla çıkılıp çıkılmadığını kaydeder."""
        self.in_transaction = True
        try:
            yield
        except BaseException as error:
            self.transaction_error = error
            raise
        finally:
            self.in_transaction = False

    async def execute(self, query: str, values: dict[str, Any]) -> FakeCursor:
        """Sorguyu kaydeder; kazanım için sıradaki sonucu, diğerleri için yeni kimlik döner."""
        self.calls.append((query, values, self.in_transaction))
        if query is self.fail_on:
            raise RuntimeError("database failed")
        if query is UPSERT_LEARNING_OUTCOME:
            return FakeCursor(next(self.outcome_rows))
        if query is COUNT_MISSING_LEARNING_OUTCOMES:
            return FakeCursor((self.missing,))
        self.next_id += 1
        return FakeCursor((self.next_id,))


@pytest.mark.asyncio
async def test_save_program_writes_tree_in_order_inside_transaction() -> None:
    """Ağaç sırayla yazılır, sonra eksik kazanımlar sayılır; hepsi tek transaction içinde."""
    connection = FakeConnection([(True,), (True,), (True,)])

    await save_program(connection, PROGRAM)

    assert [call[0] for call in connection.calls] == [
        UPSERT_SUBJECT,
        UPSERT_CURRICULUM,
        UPSERT_LEARNING_OUTCOME_GROUP,
        UPSERT_LEARNING_OUTCOME,
        UPSERT_LEARNING_OUTCOME,
        UPSERT_LEARNING_OUTCOME_GROUP,
        UPSERT_LEARNING_OUTCOME,
        COUNT_MISSING_LEARNING_OUTCOMES,
    ]
    assert all(in_transaction for _, _, in_transaction in connection.calls)


@pytest.mark.asyncio
async def test_save_program_links_rows_with_returned_ids() -> None:
    """Her satır bir üstündeki satırın dönen kimliğiyle yazılır."""
    connection = FakeConnection([(True,), (True,), (True,)])

    await save_program(connection, PROGRAM)

    values = [call[1] for call in connection.calls]
    assert values[0] == {"code": "TDE", "name": "Türk Dili ve Edebiyatı"}
    assert values[1] == {
        "subject_id": 101,
        "name": "TDE Öğretim Programı 2018",
        "model": "LEGACY",
        "year": 2018,
    }
    assert values[2] == {"curriculum_id": 102, "code": "A.1", "name": "Şiir"}
    assert [values[3]["group_id"], values[4]["group_id"], values[6]["group_id"]] == [103, 103, 104]
    assert values[3]["code"] == "A.1.1"
    assert values[3]["meb_explanation"] == "a. Not."


@pytest.mark.asyncio
async def test_save_program_sends_search_text_for_each_outcome() -> None:
    """Kazanım satırı ders › grup › başlık yolu ve açıklamadan kurulan arama metniyle yazılır."""
    connection = FakeConnection([(True,), (True,), (True,)])

    await save_program(connection, PROGRAM)

    texts = [call[1]["search_text"] for call in connection.calls if "search_text" in call[1]]
    assert texts == [
        "Türk Dili ve Edebiyatı › Şiir › Şiiri yorumlar.\na. Not.",
        "Türk Dili ve Edebiyatı › Şiir › Temayı belirler.",
        "Türk Dili ve Edebiyatı › Yazma › Metin yazar.",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (
            [(True,), (True,), (False,)],
            ProgramSaveSummary(inserted=2, updated=1, unchanged=0, missing=0),
        ),
        ([None, None, (False,)], ProgramSaveSummary(inserted=0, updated=1, unchanged=2, missing=0)),
    ],
)
async def test_save_program_counts_inserted_updated_and_unchanged(
    rows: list[tuple[bool] | None], expected: ProgramSaveSummary
) -> None:
    """Dönen satıra göre eklenen (xmax = 0), değişen ve hiç dönmeyen (aynı kalan) sayılır."""
    summary = await save_program(FakeConnection(rows), PROGRAM)

    assert summary == expected


@pytest.mark.asyncio
async def test_save_program_reports_outcomes_missing_from_pdf() -> None:
    """Programda olup PDF'te bulunmayan kazanımlar, okunan grup-kod çiftleriyle sayılır."""
    connection = FakeConnection([None, None, None])
    connection.missing = 4

    summary = await save_program(connection, PROGRAM)

    query, values, _ = connection.calls[-1]
    assert query is COUNT_MISSING_LEARNING_OUTCOMES
    assert values == {
        "curriculum_id": 102,
        "group_codes": ["A.1", "A.1", "B"],
        "outcome_codes": ["A.1.1", "A.1.2", "B.1"],
    }
    assert summary == ProgramSaveSummary(inserted=0, updated=0, unchanged=3, missing=4)


@pytest.mark.asyncio
async def test_save_program_rolls_back_on_error() -> None:
    """Yazma sırasında hata olursa transaction hatayla kapanır ve hata yutulmaz."""
    connection = FakeConnection([(True,)])
    connection.fail_on = UPSERT_LEARNING_OUTCOME_GROUP

    with pytest.raises(RuntimeError, match="database failed"):
        await save_program(connection, PROGRAM)

    assert isinstance(connection.transaction_error, RuntimeError)


@pytest.mark.asyncio
async def test_save_program_fails_when_upsert_returns_no_id() -> None:
    """Upsert kimlik dönmezse yazma açık hatayla durur."""
    connection = FakeConnection([])
    connection.next_id = 0

    async def no_row(query: str, values: dict[str, Any]) -> FakeCursor:
        """Hiç satır dönmeyen sorguyu taklit eder."""
        return FakeCursor(None)

    connection.execute = no_row

    with pytest.raises(RuntimeError, match="returned no id"):
        await save_program(connection, PROGRAM)


@pytest.mark.asyncio
async def test_every_query_parameter_is_provided() -> None:
    """Sorgulardaki her %(ad)s parametresi gönderilen değerlerde bulunur."""
    connection = FakeConnection([(True,), (True,), (True,)])

    await save_program(connection, PROGRAM)

    for query, values, _ in connection.calls:
        assert set(re.findall(r"%\((\w+)\)s", query)) <= values.keys()


def test_build_search_text_without_explanation_is_path_only() -> None:
    """Açıklaması olmayan kazanımın arama metni sadece yoldur."""
    outcome = LearningOutcome(code="B.1", title="Metin yazar.", meb_explanation=None)

    assert build_search_text("TDE", "Yazma", outcome) == "TDE › Yazma › Metin yazar."
