"""PDF okumanın dış yüzü: test, kitap ve düz metin PDF'lerini ortak formata çevirir.

İçeride iki ayrı tek dosyalık motor çalışır: soru motoru (question_reader.py) ve kitap motoru
(book_reader.py); ikisi PDF'i aynı ortak bölümle okur (harf ve stil, görünürlük, bozuk harf
onarımı, OCR, okuma sırası). Okuma sırasında onarılmış her sayfa metni hazırlık hattının metin
katmanı kontrolüne (text_layer.py, font_fix.py) sorulur: Türkçe kök oranı düşükse font
düzeltmesi uygulanır, o da yetmezse sayfa OCR'la da okunur ve oranı yüksek okuma kalır.

    from app.ingest import pdf

    reading = pdf.read_questions(pdf_bytes)        # testlere bölünmüş ParsedQuestion'lar
    book = pdf.read_textbook(pdf_bytes, "TDE 12 Ders Kitabı")
    lines = pdf.read_lines(path)                   # program, ünite tablosu, cevap anahtarı
    png = pdf.render_page(pdf_bytes, page_no=3)    # sayfa görüntüsü

Girdi dosya yolu ya da PDF'in baytlarıdır. PDFium aynı anda birden çok iş parçacığından
kullanılamadığı için çağrılar bir kilitle sıraya girer; çalışan bunları asyncio.to_thread ile
çağırır. Ayar verilmezse kök listesi IngestSettings'ten, Tesseract ayarları PdfSettings'ten okunur.
"""

import io
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import pypdfium2 as pdfium

from app.config import load_ingest_settings, load_pdf_settings
from app.constants import FONT_FIX_MIN_WORDS, PAGE_IMAGE_DPI
from app.ingest.font_fix import FontFixKind, apply_fix
from app.ingest.pdf import book_reader, question_reader
from app.ingest.pdf.convert import to_lines, to_page_reports, to_tests, to_textbook
from app.ingest.text_layer import check_page_text, extract_words, load_word_list
from app.schemas.pdf import QuestionReading, TextbookReading

PdfSource = question_reader.PdfSource
Review = tuple[float, bool, Callable[[str], str] | None, str | None]

_ENGINE_LOCK = threading.Lock()


class PdfReadError(ValueError):
    """PDF açılamadı: bozuk, şifreli ya da PDF değil."""


class OcrError(RuntimeError):
    """Tesseract çalıştırılamadı ya da hata verdi."""


@dataclass(frozen=True)
class ReaderOptions:
    """Okuma ayarları: metin katmanı kontrolünün kök listesi ve Tesseract ayarları."""

    known_words: frozenset[str]
    tesseract_cmd: str = "tesseract"
    ocr_cache_dir: Path | None = None

    @classmethod
    def from_settings(cls) -> "ReaderOptions":
        """Ayarları ortam değişkenlerinden okur (WORD_LIST_PATH, TESSERACT_CMD, OCR_CACHE_DIR)."""
        pdf_settings = load_pdf_settings()
        return cls(
            known_words=load_word_list(load_ingest_settings().word_list_path),
            tesseract_cmd=pdf_settings.tesseract_cmd,
            ocr_cache_dir=pdf_settings.ocr_cache_dir,
        )


def read_questions(source: PdfSource, options: ReaderOptions | None = None) -> QuestionReading:
    """Test PDF'inin sorularını plan 13.6 biçiminde, testlere bölünmüş olarak okur."""
    options = options or ReaderOptions.from_settings()
    ocr = question_reader.OcrSettings(options.tesseract_cmd, options.ocr_cache_dir)

    def check(text: str) -> question_reader.TextReview | None:
        """Sayfa metnini soru motorunun karar biçiminde değerlendirir."""
        review = review_text(text, options.known_words)
        return question_reader.TextReview(*review) if review else None

    with _reading():
        pages = question_reader.read_document(source, ocr, check)
        questions, _ = question_reader.parse(pages)
    return QuestionReading(tests=to_tests(questions), pages=to_page_reports(pages))


def read_textbook(
    source: PdfSource, source_title: str, options: ReaderOptions | None = None
) -> TextbookReading:
    """Ders kitabı ya da konu anlatımı PDF'ini başlık yollu bloklar olarak okur."""
    with _reading():
        pages = _read_book_pages(source, options)
        blocks = book_reader.read_book(pages)
    return TextbookReading(blocks=to_textbook(blocks, source_title), pages=to_page_reports(pages))


def read_lines(source: PdfSource, options: ReaderOptions | None = None) -> list[str]:
    """PDF'in görünen satırlarını okuma sırasıyla, paragraf arasında boş satırla verir."""
    with _reading():
        pages = _read_book_pages(source, options)
        return to_lines(book_reader.reading_order(pages))


def render_page(source: PdfSource, page_no: int, dpi: int = PAGE_IMAGE_DPI) -> bytes:
    """Sayfayı (1'den sayılır) verilen çözünürlükte PNG olarak çizer."""
    with _reading():
        document = pdfium.PdfDocument(source)
        try:
            page = document[page_no - 1]
            image = page.render(scale=dpi / 72).to_pil()
            page.close()
        finally:
            document.close()
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def review_text(text: str, known_words: frozenset[str]) -> Review | None:
    """Sayfa metnini Türkçe kök listesiyle ölçer; kısa sayfada (30 kelimeden az) karar vermez."""
    if len(extract_words(text)) < FONT_FIX_MIN_WORDS:
        return None
    result = check_page_text(text, known_words)
    if result.fix is None:
        return result.ratio, result.ok, None, None
    name = result.fix.kind.value
    if result.fix.kind is FontFixKind.CODE_SHIFT:
        name = f"{name}_{result.fix.shift}"
    return result.ratio, result.ok, partial(apply_fix, fix=result.fix), name


def _read_book_pages(source: PdfSource, options: ReaderOptions | None) -> list[book_reader.PageIR]:
    """Kitap motoruyla sayfaları metin katmanı kontrolünden geçirerek okur."""
    options = options or ReaderOptions.from_settings()
    ocr = book_reader.OcrSettings(options.tesseract_cmd, options.ocr_cache_dir)

    def check(text: str) -> book_reader.TextReview | None:
        """Sayfa metnini kitap motorunun karar biçiminde değerlendirir."""
        review = review_text(text, options.known_words)
        return book_reader.TextReview(*review) if review else None

    return book_reader.read_document(source, ocr, check)


@contextmanager
def _reading() -> Iterator[None]:
    """PDFium çağrılarını sıraya koyar; kütüphane hatalarını dış yüzün hatalarına çevirir."""
    with _ENGINE_LOCK:
        try:
            yield
        except pdfium.PdfiumError as error:
            raise PdfReadError(f"Cannot read PDF: {error}") from error
        except (question_reader.OcrError, book_reader.OcrError) as error:
            raise OcrError(str(error)) from error
