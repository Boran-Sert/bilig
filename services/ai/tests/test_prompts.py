"""Prompt dosyalarının sürümüyle okunmasını ve doldurulmasını test eder."""

from pathlib import Path

import pytest
from jinja2.exceptions import UndefinedError

from app.constants import LLM_TASKS_PATH, PROMPTS_DIR, TOOL_PROMPTS_PATH
from app.llm.prompts import RenderedPrompt, load_tool_prompts, render_prompt
from app.llm.tasks import load_task_configs
from app.schemas.tutor import ChatTurn, OutcomeInfo

PROMPT = """{# version: 3 #}
{% block system %}
Sen bir edebiyat öğretmenisin. Emin değilsen bunu açıkça söyle.
{% endblock %}
{% block user %}
Soru: {{ question }}
{% endblock %}
"""


def write_prompt(directory: Path, text: str) -> str:
    """Prompt metnini klasöre yazar ve dosya adını döner."""
    (directory / "hint.j2").write_text(text, encoding="utf-8")
    return "hint.j2"


def test_renders_both_blocks_with_version(tmp_path: Path) -> None:
    """Sürüm ilk satırdan alınır, user bloğu değişkenle dolar."""
    name = write_prompt(tmp_path, PROMPT)

    prompt = render_prompt(tmp_path, name, {"question": "Roman nedir?"})

    assert prompt == RenderedPrompt(
        version=3,
        system="Sen bir edebiyat öğretmenisin. Emin değilsen bunu açıkça söyle.",
        user="Soru: Roman nedir?",
    )


def test_prompt_without_version_line_is_rejected(tmp_path: Path) -> None:
    """İlk satırı sürüm olmayan prompt kullanılmaz."""
    name = write_prompt(tmp_path, PROMPT.replace("{# version: 3 #}", "{# sürüm yok #}"))

    with pytest.raises(ValueError, match="version"):
        render_prompt(tmp_path, name, {"question": "Roman nedir?"})


def test_missing_variable_is_rejected(tmp_path: Path) -> None:
    """Verilmeyen değişken boş metin olarak geçmez."""
    name = write_prompt(tmp_path, PROMPT)

    with pytest.raises(UndefinedError):
        render_prompt(tmp_path, name, {})


def test_prompt_without_system_block_is_rejected(tmp_path: Path) -> None:
    """System bloğu olmayan prompt adıyla birlikte hata verir."""
    name = write_prompt(tmp_path, PROMPT.replace("block system", "block other"))

    with pytest.raises(ValueError, match="system"):
        render_prompt(tmp_path, name, {"question": "Roman nedir?"})


TUTOR_VARIABLES = {
    "hint.j2": {"question": "Hangisi tarihî romandır?", "correct_option": "B"},
    "topic_explain.j2": {
        "question": "Hangisi tarihî romandır?",
        "selected_option": "A",
        "correct_option": "B",
        "outcomes": [
            OutcomeInfo(id=1, code="A.2.15", title="Yazar ve eserler", meb_explanation=None)
        ],
        "style": "STEP_BY_STEP",
    },
    "chat.j2": {
        "question": "",
        "correct_option": "",
        "history": [ChatTurn(role="ASSISTANT", content="Küçük Ağa tarihî romandır.")],
        "message": "Devlet Ana da tarihî roman mı?",
        "style": "SIMPLE",
    },
}


@pytest.mark.parametrize("name", list(TUTOR_VARIABLES))
def test_tutor_prompts_render_with_code_variables(name: str) -> None:
    """Repodaki ipucu, anlatım ve sohbet prompt'ları kodun verdiği değişkenlerle dolar."""
    prompt = render_prompt(PROMPTS_DIR, name, TUTOR_VARIABLES[name])

    assert prompt.version >= 1
    assert "not sure" in prompt.system


def test_chat_prompt_explains_tools_and_limit() -> None:
    """Sohbet prompt'u üç tool'u ve en fazla üç çağrı kuralını anlatır, kaynak göstermeyi ister."""
    prompt = render_prompt(PROMPTS_DIR, "chat.j2", TUTOR_VARIABLES["chat.j2"])

    assert prompt.version >= 2
    for name in ("search_notes", "open_note", "get_outcome"):
        assert name in prompt.system
    assert "at most three tool calls" in prompt.system
    assert "cite" in prompt.system


def test_hint_prompt_forbids_revealing_answer() -> None:
    """İpucu prompt'u doğru şıkkı ve metnini yazmayı yasaklar."""
    prompt = render_prompt(PROMPTS_DIR, "hint.j2", TUTOR_VARIABLES["hint.j2"])

    assert "Never reveal the correct answer" in prompt.system
    assert "do not reveal it" in prompt.user


def test_tool_schemas_are_strict() -> None:
    """Her tool şeması nesnedir, bütün alanları zorunludur ve fazladan alan kabul etmez."""
    tools = load_tool_prompts(TOOL_PROMPTS_PATH).tools

    for definition in tools.values():
        schema = definition.input_schema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["required"] == list(schema["properties"])


def test_every_task_tool_is_defined() -> None:
    """Görev ayarlarında adı geçen her tool'un açıklaması ve şeması vardır."""
    tools = load_tool_prompts(TOOL_PROMPTS_PATH).tools

    names = {name for config in load_task_configs(LLM_TASKS_PATH).values() for name in config.tools}
    assert names <= set(tools)
