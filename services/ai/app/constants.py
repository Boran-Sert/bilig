"""Servisin değişmeyen değerleri.

Ortama göre değişen değerler burada değil, app/config.py'deki ayarlardadır (plan 13.8).
"""

SERVICE_NAME = "ai"
REQUEST_ID_HEADER = "X-Request-Id"

DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 10
DB_POOL_OPEN_TIMEOUT_SECONDS = 10.0

SEARCH_PATH_SEPARATOR = " › "
