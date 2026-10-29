"""Prompt dosyalarının sürümüyle okunmasını ve doldurulmasını test eder."""

from pathlib import Path

import pytest
from jinja2.exceptions import UndefinedError

from app.llm.prompts import RenderedPrompt, render_prompt

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
