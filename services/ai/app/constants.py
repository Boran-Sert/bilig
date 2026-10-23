"""Servisin değişmeyen değerleri.

Ortama göre değişen değerler burada değil, app/config.py'deki ayarlardadır (plan 13.8).
"""

SERVICE_NAME = "ai"
REQUEST_ID_HEADER = "X-Request-Id"

DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 10
DB_POOL_OPEN_TIMEOUT_SECONDS = 10.0

TURKISH_LETTERS = frozenset("abcçdefgğhıijklmnoöprsştuüvyzâîû")
WORD_LIST_FILE = "data/turkce_kelimeler.txt"
TEXT_LAYER_MIN_RATIO = 0.90
TEXT_LAYER_MIN_WORD_LENGTH = 2
TEXT_LAYER_MIN_STEM_LENGTH = 2
