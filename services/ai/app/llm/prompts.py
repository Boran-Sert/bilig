"""prompts/tde altındaki Jinja2 prompt dosyalarını sürümüyle okur ve değişkenlerle doldurur.

Prompt dosyasının ilk satırı sürümdür: {# version: N #}. Dosyada iki blok bulunur: system bloğu
her çağrıda aynı kalır ve önbelleğe alınır, user bloğu görevin değişkenleriyle dolar. Eksik
değişken boş metin olarak geçmez, hata verir. Sürüm her çağrıyla llm_call_log'a yazılır.
"""

import re
from collections.abc import Mapping
from pathlib import Path

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel

from app.constants import PROMPT_BLOCKS, PROMPT_VERSION_PATTERN

_ENVIRONMENT = Environment(undefined=StrictUndefined)


class RenderedPrompt(BaseModel):
    """Doldurulmuş prompt'un sürümü, sistem metni ve kullanıcı mesajı."""

    version: int
    system: str
    user: str


def render_prompt(directory: Path, name: str, variables: Mapping[str, object]) -> RenderedPrompt:
    """Prompt dosyasını okur, sürümünü alır ve bloklarını değişkenlerle doldurur."""
    source = (directory / name).read_text(encoding="utf-8")
    version = prompt_version(name, source)
    template = _ENVIRONMENT.from_string(source)
    context = template.new_context(dict(variables))
    blocks = {block: "".join(render(context)).strip() for block, render in template.blocks.items()}
    missing = [block for block in PROMPT_BLOCKS if block not in blocks]
    if missing:
        raise ValueError(f"Prompt {name} has no block: {', '.join(missing)}")
    return RenderedPrompt(version=version, system=blocks["system"], user=blocks["user"])


def prompt_version(name: str, source: str) -> int:
    """Prompt metninin ilk satırındaki sürümü döner; sürüm satırı yoksa hata verir."""
    version = re.fullmatch(PROMPT_VERSION_PATTERN, source.partition("\n")[0])
    if version is None:
        raise ValueError(f"Prompt {name} must start with a version line")
    return int(version[1])
