"""Servisin değişmeyen değerleri.

Ortama göre değişen değerler burada değil, app/config.py'deki ayarlardadır (plan 13.8).
"""

from pathlib import Path

SERVICE_NAME = "ai"
REQUEST_ID_HEADER = "X-Request-Id"
UVICORN_LOGGERS = ("uvicorn", "uvicorn.access", "uvicorn.error")

DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 10
DB_POOL_OPEN_TIMEOUT_SECONDS = 10.0

PROGRAM_SUBJECT_CODE = "TDE"
PROGRAM_SUBJECT_NAME = "Türk Dili ve Edebiyatı"
PROGRAM_CURRICULUM_NAME = "TDE Öğretim Programı 2018"
PROGRAM_CURRICULUM_MODEL = "LEGACY"
PROGRAM_CURRICULUM_YEAR = 2018
SEARCH_PATH_SEPARATOR = " › "
PAGE_IMAGE_DPI = 150
UNIT_GROUP_KEYWORDS = {  # şapkasız küçük harf
    "hikaye": "A.2",
    "roman": "A.2",
    "masal": "A.2",
    "şiir": "A.1",
    "tiyatro": "A.3",
    "makale": "A.4",
    "deneme": "A.4",
}

TURKISH_LETTERS = frozenset("abcçdefgğhıijklmnoöprsştuüvyzâîû")
TEXT_LAYER_MIN_RATIO = 0.90
TEXT_LAYER_MIN_WORD_LENGTH = 2
TEXT_LAYER_MIN_STEM_LENGTH = 2
FONT_FIX_MAX_SHIFT = 64
FONT_FIX_FIRST_VISIBLE_CODE = 0x21
FONT_FIX_MIN_WORDS = 30

TEXT_SIMILARITY_MIN_RATIO = 0.90
ANSWER_KEY_MIN_ENTRIES = 5

STORAGE_FILE_MODE = 0o644

EMBEDDING_BATCH_SIZE = 32
EMBEDDING_MAX_TOKENS = 2048
RERANKER_MAX_LENGTH = 512

SERVICE_ROOT = Path(__file__).resolve().parents[1]
LLM_TASKS_PATH = SERVICE_ROOT / "llm_tasks.yaml"
