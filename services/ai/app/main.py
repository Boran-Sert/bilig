"""Yapay zeka servisinin HTTP uygulaması.

Java servisinin çağırdığı iç uç noktalar /internal altında durur ve dışarı açılmaz.
Başlatma: python -m uvicorn app.main:app
"""

from fastapi import FastAPI

app = FastAPI(title="ai")


@app.get("/internal/health", status_code=204)
async def health() -> None:
    """Servisin ayakta olduğunu boş cevapla bildirir."""
