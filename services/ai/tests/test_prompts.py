"""Prompt dosyalarının sürümüyle okunmasını ve doldurulmasını test eder."""

from pathlib import Path

import pytest
from jinja2.exceptions import UndefinedError

from app.constants import PROMPTS_DIR
from app.llm.prompts import RenderedPrompt, render_prompt
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


def test_hint_prompt_forbids_revealing_answer() -> None:
    """İpucu prompt'u doğru şıkkı ve metnini yazmayı yasaklar."""
    prompt = render_prompt(PROMPTS_DIR, "hint.j2", TUTOR_VARIABLES["hint.j2"])

    assert "Never reveal the correct answer" in prompt.system
    assert "do not reveal it" in prompt.user
