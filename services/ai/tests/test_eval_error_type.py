"""Hata türü kontrol setinin puanlamasını ve rapor biçimini test eder."""

import json
from datetime import UTC, datetime
from pathlib import Path

from app.constants import ERROR_TYPE_CONTROL_SET_PATH, PROMPTS_DIR
from app.eval.error_type import build_report, read_control_set, score, write_report
from app.llm.prompts import render_prompt
from app.llm.tasks import LlmTask, get_task_configs
from app.schemas.answer_analysis import ErrorType

CREATED_AT = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def test_control_set_covers_every_error_type() -> None:
    """Sentetik kontrol setinde dört hata türünün her biri bulunur."""
    questions = read_control_set(ERROR_TYPE_CONTROL_SET_PATH)

    assert {question.expected_error_type for question in questions} == set(ErrorType)


def test_score_compares_expected_and_predicted_types() -> None:
    """Kategori tahmininin doğruluğunu tek soru için hesaplar."""
    result = score("sample-1", ErrorType.READING, ErrorType.READING)

    assert result.correct
    assert score("sample-2", ErrorType.READING, ErrorType.ATTENTION).correct is False


def test_error_type_prompt_renders_with_task_settings() -> None:
    """Görev prompt'u soru bağlamını ve inceleme işaretini tamamlayarak üretir."""
    config = get_task_configs()[LlmTask.ERROR_TYPE]

    prompt = render_prompt(
        PROMPTS_DIR,
        config.prompt,
        {"question": "Özgün soru", "correct_option": "B", "selected_option": "A"},
    )

    assert "Özgün soru" in prompt.user
    assert "Doğru seçenek: B" in prompt.user
    assert "needs_review" in prompt.system


def test_report_includes_prompt_metadata_and_accuracy(tmp_path: Path) -> None:
    """Rapor prompt sürümünü ve sınıflandırma doğruluğunu JSON'a yazar."""
    scores = [
        score("sample-1", ErrorType.READING, ErrorType.READING),
        score("sample-2", ErrorType.KNOWLEDGE, ErrorType.ATTENTION),
    ]

    report = build_report(CREATED_AT, scores)
    path = write_report(report, tmp_path)

    assert report.accuracy == 0.5
    assert report.prompt_version == 1
    assert path.name == "error_type-20261104T120000Z.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["questions"][1]["predicted"] == "ATTENTION"
