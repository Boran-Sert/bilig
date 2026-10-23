"""Servisin değişmeyen değerleri.

Ortama göre değişen değerler burada değil, app/config.py'deki ayarlardadır (plan 13.8).
"""

SERVICE_NAME = "ai"
REQUEST_ID_HEADER = "X-Request-Id"

DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 10
DB_POOL_OPEN_TIMEOUT_SECONDS = 10.0

PROGRAM_SUBJECT_CODE = "TDE"
PROGRAM_SUBJECT_NAME = "Türk Dili ve Edebiyatı"
PROGRAM_CURRICULUM_NAME = "TDE Öğretim Programı 2018"
PROGRAM_CURRICULUM_MODEL = "LEGACY"
PROGRAM_CURRICULUM_YEAR = 2018
SEARCH_PATH_SEPARATOR = " › "
