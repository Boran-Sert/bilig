"""Geliştirme aracı: PDF motorlarının ortak bölümünü test motorundan kitap motoruna kopyalar.

İki motor (app/ingest/pdf/question_reader.py ve book_reader.py) tek dosyalık ayrı sistemlerdir;
içe aktarmalar ve ORTAK BAŞLANGIÇ ile ORTAK SONU arasındaki bölüm ikisinde birebir aynıdır.
Ortak bölümde değişiklik test motorunda yapılır, sonra bu araç çalıştırılır:
uv run python scripts/sync_pdf_shared.py
"""

from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "app" / "ingest" / "pdf"
END = "# ================================================================== ORTAK SONU"
IMPORTS = "from __future__ import annotations"
TEST_ONLY_IMPORTS = (
    "from itertools import combinations\n",
    "from app.text.turkish import tr_lower\n",
)


def shared(text: str) -> str:
    """Dosyanın içe aktarmalarla başlayıp ortak bölümün sonuna kadar süren kısmı."""
    return text[text.index(IMPORTS) : text.index(END) + len(END)]


def book_shared(test: str) -> str:
    """Test motorunun ortak kısmından kitap motorunda kullanılmayan içe aktarmaları atar."""
    text = shared(test)
    for line in TEST_ONLY_IMPORTS:
        text = text.replace(line, "")
    return text


def main() -> None:
    """Kitap motorundaki ortak kısmı test motorundakiyle değiştirir."""
    test = (FOLDER / "question_reader.py").read_text(encoding="utf-8")
    book_path = FOLDER / "book_reader.py"
    book = book_path.read_text(encoding="utf-8")
    start, end = book.index(IMPORTS), book.index(END) + len(END)
    synced = book[:start] + book_shared(test) + book[end:]
    book_path.write_text(synced, encoding="utf-8")
    print("shared section synced" if synced != book else "shared section already identical")


if __name__ == "__main__":
    main()
