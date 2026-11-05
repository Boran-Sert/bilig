"""llm_tasks.yaml'daki görev ayarlarının okunmasını test eder."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.constants import LLM_TASKS_PATH
from app.llm.tasks import LlmTask, load_task_configs

HINT_SETTINGS = "HINT:\n  model: m\n  prompt: hint.j2\n  max_tokens: 10\n  timeout_seconds: 5\n"


def test_repository_file_covers_every_task() -> None:
    """Repodaki ayar dosyası her görev için bir ayar verir."""
    assert set(load_task_configs(LLM_TASKS_PATH)) == set(LlmTask)


def test_missing_task_is_reported_by_name(tmp_path: Path) -> None:
    """Ayarı olmayan görevler hata mesajında adlarıyla geçer."""
    path = tmp_path / "llm_tasks.yaml"
    path.write_text(HINT_SETTINGS, encoding="utf-8")

    with pytest.raises(ValueError, match="DOC_CLASSIFY") as error:
        load_task_configs(path)

    assert "HINT" not in str(error.value)


def test_unknown_task_is_rejected(tmp_path: Path) -> None:
    """LlmTask'ta olmayan görev adı kabul edilmez."""
    path = tmp_path / "llm_tasks.yaml"
    path.write_text(HINT_SETTINGS.replace("HINT", "UNKNOWN"), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_task_configs(path)


def test_chat_reads_notes_with_three_tool_calls() -> None:
    """Sohbet üç okuma tool'unu en fazla üç çağrıyla kullanır."""
    chat = load_task_configs(LLM_TASKS_PATH)[LlmTask.CHAT]

    assert chat.tools == ("search_notes", "open_note", "get_outcome")
    assert chat.max_tool_calls == 3


def test_other_tasks_have_no_tools() -> None:
    """Sohbet dışındaki görevlere tool verilmez."""
    configs = load_task_configs(LLM_TASKS_PATH)

    others = [config for task, config in configs.items() if task is not LlmTask.CHAT]
    assert all(config.tools == () and config.max_tool_calls == 0 for config in others)
