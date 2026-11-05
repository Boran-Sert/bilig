"""İş türünü onu çalıştıran fonksiyona bağlayan sözlük (plan 13.12).

Yeni iş türü için sözlüğe tek satır eklenir: JobType.INGEST_SOURCE: run_ingest. Fonksiyon işi
alır; yarıda kalmış işte last_completed_step'ten sonraki adımdan devam eder. Sözlükte olmayan tür
çalışan tarafından hata olarak işaretlenir.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from app.ingest.pipeline import run_ingest
from app.jobs.analyze_answer import run_analyze_answer
from app.jobs.queue import Job, JobType

JobHandler = Callable[[Job], Coroutine[Any, Any, None]]

HANDLERS: dict[JobType, JobHandler] = {
    JobType.INGEST_SOURCE: run_ingest,
    JobType.ANALYZE_ANSWER: run_analyze_answer,
}
