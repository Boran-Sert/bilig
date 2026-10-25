"""Embedding ve reranker modellerini ayardaki sabit commit'ten HF_HOME'a indirir.

HF_HUB_OFFLINE=0 verilerek python -m scripts.download_models ile bir kez çalıştırılır.
Modeller servisin kullandığı fonksiyonlarla yüklendiği için sadece gereken dosyalar iner ve
yüklenebildikleri de denenmiş olur. Önbellekte olan dosya yeniden indirilmez.
transformers'ın safetensors dönüştürme denemesi kapatılır; açık kalırsa bge-m3 için sabit
commit yerine açık bir PR'dan fazladan bir ağırlık dosyası iner.
"""

import os

import structlog

from app.config import LogSettings
from app.log import configure_logging
from app.search.embedding import get_embedding_provider
from app.search.reranker import get_reranker


def main() -> None:
    """İki modeli indirip yükler ve hazır olduklarını log'a yazar."""
    configure_logging(LogSettings())
    os.environ["DISABLE_SAFETENSORS_CONVERSION"] = "1"
    get_embedding_provider()
    get_reranker()
    structlog.get_logger().info("models ready")


if __name__ == "__main__":
    main()
