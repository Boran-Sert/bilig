"""Claude görevlerinin adları ve llm_tasks.yaml'daki görev ayarları.

Her görevin modeli, prompt dosyası, en fazla çıktı token'ı ve zaman aşımı llm_tasks.yaml'dadır;
kodda model adı yazılmaz. Yeni görev için LlmTask'a bir üye, llm_tasks.yaml'a bir kayıt ve
prompts/tde altına prompt dosyası eklenir. Ayar dosyası süreç başına bir kez okunur.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, TypeAdapter

from app.constants import LLM_TASKS_PATH


class LlmTask(StrEnum):
    """Claude'a yaptırılan işlerin adları."""

    DOC_CLASSIFY = "DOC_CLASSIFY"
    UNIT_DETECT = "UNIT_DETECT"
    PAGE_EXTRACT = "PAGE_EXTRACT"
    ENTITY_EXTRACT = "ENTITY_EXTRACT"
    PROFILE_PROPOSE = "PROFILE_PROPOSE"
    OUTCOME_MATCH = "OUTCOME_MATCH"
    ANSWER_SOLVE = "ANSWER_SOLVE"
    HINT = "HINT"
    ERROR_TYPE = "ERROR_TYPE"
    TOPIC_EXPLAIN = "TOPIC_EXPLAIN"
    CHAT = "CHAT"
    QUESTION_GENERATE = "QUESTION_GENERATE"
    QUESTION_VERIFY = "QUESTION_VERIFY"


class TaskConfig(BaseModel):
    """Bir görevin modeli, prompt dosyası, çıktı sınırı ve zaman aşımı."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str
    prompt: str
    max_tokens: int
    timeout_seconds: float


_TASK_CONFIGS = TypeAdapter(dict[LlmTask, TaskConfig])


def load_task_configs(path: Path) -> dict[LlmTask, TaskConfig]:
    """Görev ayarlarını okur; ayarı olmayan görev varsa adlarıyla hata verir."""
    configs = _TASK_CONFIGS.validate_python(yaml.safe_load(path.read_text(encoding="utf-8")))
    missing = sorted(set(LlmTask) - configs.keys())
    if missing:
        raise ValueError(f"Tasks without settings in {path.name}: {', '.join(missing)}")
    return configs


@lru_cache(maxsize=1)
def get_task_configs() -> dict[LlmTask, TaskConfig]:
    """Görev ayarlarını bir kez okuyup süreç boyunca aynı sözlüğü döner."""
    return load_task_configs(LLM_TASKS_PATH)
