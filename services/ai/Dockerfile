# Yapay zeka servisinin imajı; ai-api ve ai-worker aynı imajı kullanır.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /bin/uv

# PDF'te metni olmayan sayfa ve resimler için Türkçe OCR
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tur \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
