"""prompts/tde altındaki Jinja2 prompt dosyalarını sürümüyle okur ve değişkenlerle doldurur.

Prompt dosyasının ilk satırı sürümdür: {# version: N #}. Dosyada iki blok bulunur: system bloğu
her çağrıda aynı kalır ve önbelleğe alınır, user bloğu görevin değişkenleriyle dolar. Eksik
değişken boş metin olarak geçmez, hata verir. Sürüm her çağrıyla llm_call_log'a yazılır.
Tool'ların açıklamaları, girdi şemaları ve tool sonuçlarındaki sabit mesajlar da prompt metnidir;
prompts/tde/tools.yaml'dan süreç başına bir kez okunur.
"""

import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict

from app.constants import PROMPT_BLOCKS, PROMPT_VERSION_PATTERN, TOOL_PROMPTS_PATH

_ENVIRONMENT = Environment(undefined=StrictUndefined)


class RenderedPrompt(BaseModel):
    """Doldurulmuş prompt'un sürümü, sistem metni ve kullanıcı mesajı."""

    version: int
    system: str
    user: str


class ToolDefinition(BaseModel):
    """Claude'a verilen tool'un açıklaması ve girdi şeması."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    description: str
    input_schema: dict[str, Any]


class ToolMessages(BaseModel):
    """Tool sonuçlarında modele giden sabit mesajlar."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    no_notes: str
    note_not_found: str
    outcome_not_found: str


class ToolPrompts(BaseModel):
    """Adına göre tool tanımları ve tool mesajları."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tools: dict[str, ToolDefinition]
    messages: ToolMessages


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


def load_tool_prompts(path: Path) -> ToolPrompts:
    """Tool tanımlarını ve mesajlarını okur."""
    return ToolPrompts.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def get_tool_prompts() -> ToolPrompts:
    """Tool tanımlarını bir kez okuyup süreç boyunca aynı nesneyi döner."""
    return load_tool_prompts(TOOL_PROMPTS_PATH)
