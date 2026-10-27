"""Geliştirme aracı: ortak bölümü test_reader.py'den book_reader.py'ye birebir kopyalar."""

from pathlib import Path

FOLDER = Path(__file__).parent
START = "# ================================================================== ORTAK BAŞLANGIÇ"
END = "# ================================================================== ORTAK SONU"


def section(text: str) -> str:
    """Dosyanın ortak bölümü (işaretler dahil)."""
    return text[text.index(START) : text.index(END) + len(END)]


def main() -> None:
    """Kitap okuyucudaki ortak bölümü test okuyucudakiyle değiştirir."""
    test = (FOLDER / "test_reader.py").read_text(encoding="utf-8")
    book_path = FOLDER / "book_reader.py"
    book = book_path.read_text(encoding="utf-8")
    synced = book[: book.index(START)] + section(test) + book[book.index(END) + len(END) :]
    book_path.write_text(synced, encoding="utf-8")
    print("ortak bölüm eşitlendi" if synced != book else "ortak bölüm zaten aynı")


if __name__ == "__main__":
    main()
