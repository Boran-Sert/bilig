"""Geliştirici komutu: PDF'i dış yüzle okuyup sonucu JSON olarak yazar.

uv run python -m app.ingest.pdf questions <pdf>
uv run python -m app.ingest.pdf book <pdf> --title "TDE 12 Ders Kitabı"
uv run python -m app.ingest.pdf lines <pdf>
Ayarlar ortam değişkenlerinden okunur (WORD_LIST_PATH, TESSERACT_CMD, OCR_CACHE_DIR).
"""

import argparse
import json
import sys
from pathlib import Path

from app.ingest import pdf


def main(argv: list[str] | None = None) -> None:
    """Komut satırından PDF'i okur ve sonucu standart çıktıya JSON olarak yazar."""
    parser = argparse.ArgumentParser(description="Read a PDF with the ingest PDF readers.")
    parser.add_argument("mode", choices=["questions", "book", "lines"])
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--title", default="", help="source title for the book heading path")
    arguments = parser.parse_args(argv)
    if arguments.mode == "questions":
        output = pdf.read_questions(arguments.pdf).model_dump_json(indent=2)
    elif arguments.mode == "book":
        output = pdf.read_textbook(arguments.pdf, arguments.title).model_dump_json(indent=2)
    else:
        output = json.dumps(pdf.read_lines(arguments.pdf), ensure_ascii=False, indent=2)
    sys.stdout.write(output + "\n")


if __name__ == "__main__":
    main()
