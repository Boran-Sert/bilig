"""Eşleştirme ölçümünün hesabını ve rapor dosyasını sahte sonuçlarla test eder.

Claude'a ve veritabanına gidilmez; soru sonuçları elle kurulur. Görev ayarı ve prompt sürümü
repodaki llm_tasks.yaml ve outcome_match.j2'den okunur.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.constants import CONTROL_SET_PATH, CONTROL_SET_UNIT_TITLES
from app.eval.run import build_report, read_control_set, score, write_report
from app.llm.tasks import LlmTask

CREATED_AT = datetime(2026, 11, 1, 9, 30, tzinfo=UTC)


def test_exact_match_scores_one() -> None:
    """Beklenenle aynı kazanımlar seçilince kesinlik ve duyarlılık 1'dir."""
    result = score("ks-001", ["A.2.7", "A.2.8"], ["A.2.8", "A.2.7"], needs_review=False)

    assert (result.precision, result.recall) == (1.0, 1.0)


def test_extra_outcome_lowers_precision_only() -> None:
    """Fazladan seçilen kazanım kesinliği düşürür, duyarlılığı değiştirmez."""
    result = score("ks-001", ["A.2.7"], ["A.2.7", "A.2.3", "A.2.8", "A.2.9"], needs_review=True)

    assert result.precision == pytest.approx(0.25)
    assert result.recall == 1.0
    assert result.needs_review


def test_missing_outcome_lowers_recall_only() -> None:
    """Seçilmeyen doğru kazanım duyarlılığı düşürür, kesinliği değiştirmez."""
    result = score("ks-001", ["A.2.3", "A.2.7", "A.2.8"], ["A.2.7"], needs_review=False)

    assert result.precision == 1.0
    assert result.recall == pytest.approx(1 / 3)


def test_empty_prediction_scores_zero() -> None:
    """Hiç kazanım seçilmezse kesinlik ve duyarlılık sıfırdır."""
    result = score("ks-001", ["A.1.5"], [], needs_review=True)

    assert (result.precision, result.recall) == (0.0, 0.0)


def test_report_averages_question_scores() -> None:
    """Toplam kesinlik ve duyarlılık soru sonuçlarının ortalamasıdır."""
    scores = [
        score("ks-001", ["A.2.7"], ["A.2.7"], needs_review=False),
        score("ks-002", ["A.2.7", "A.2.8"], ["A.2.7", "A.2.3"], needs_review=False),
        score("ks-003", ["A.1.5"], [], needs_review=True),
    ]

    report = build_report(LlmTask.OUTCOME_MATCH, CREATED_AT, scores)

    assert report.precision == pytest.approx((1 + 0.5 + 0) / 3)
    assert report.recall == pytest.approx((1 + 0.5 + 0) / 3)
    assert report.model.startswith("claude-")
    assert report.prompt_version >= 1


def test_report_is_written_as_json(tmp_path: Path) -> None:
    """Rapor görev adı ve zamanla adlandırılan dosyaya bütün soru sonuçlarıyla yazılır."""
    scores = [score("ks-001", ["A.2.7"], ["A.2.7"], needs_review=False)]
    report = build_report(LlmTask.OUTCOME_MATCH, CREATED_AT, scores)

    path = write_report(report, tmp_path / "eval")

    assert path.name == "outcome_match-20261101T093000Z.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["precision"] == 1.0
    assert saved["questions"][0]["predicted"] == ["A.2.7"]


def test_control_set_units_are_mapped() -> None:
    """Kontrol setindeki her ünite programdaki bir üniteye çevrilir."""
    questions = read_control_set(CONTROL_SET_PATH)

    assert {question.unit for question in questions} <= CONTROL_SET_UNIT_TITLES.keys()
