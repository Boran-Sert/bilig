"""Profil testlerinin ortak örnek PDF'i ve örnek profili.

Sayfada kalın 14 puan başlık, mavi bilgi kutusundaki metin, italik eser adlı gövde metni
(10 puan), mavi sayfa numarası (8 puan) ve sadece boşluktan oluşan bir satır vardır. Örnek profil
bu stilleri BASLIK, BILGI, METIN ve IGNORE'a eşler.
"""

import pymupdf
import yaml

from app.schemas.profile import SourceProfile, TextStyle

INFO_BOX = pymupdf.Rect(40, 140, 560, 260)
HEADING = (pymupdf.Rect(50, 40, 550, 140), '<p style="font-size:14px"><b>Roman Türleri</b></p>')
BODY_HTML = [
    (
        pymupdf.Rect(50, 150, 550, 250),
        '<p style="font-size:10px">Tarihî roman konusunu tarihten alır.</p>',
    ),
    (
        pymupdf.Rect(50, 300, 550, 400),
        '<p style="font-size:10px">Yakup Kadri <i>Kiralık Konak</i> romanını 1922\'de yazdı.</p>',
    ),
    (pymupdf.Rect(50, 780, 550, 840), '<p style="font-size:8px;color:#0000ff">174</p>'),
]

PROFILE_YAML = """
name: ornek_kitap
description: Testte üretilen PDF'in profili.
rules:
  - match: {size: 8, color: "#0000ff"}
    block_type: IGNORE
  - match: {size: 14, bold: true}
    block_type: BASLIK
  - match: {box: "#d9ebff"}
    block_type: BILGI
  - match: {size: 10, boxed: false}
    block_type: METIN
"""


def charis(
    variant: str = "", size: float = 10, color: str = "#000000", box: str | None = None
) -> TextStyle:
    """Örnek PDF'teki CharisSIL fontunun bir stilini kurar."""
    return TextStyle(
        font=f"CharisSIL{variant}",
        size=size,
        bold=variant == "-Bold",
        italic=variant == "-Italic",
        color=color,
        box=box,
    )


def build_document(pages: int = 1, heading_last: bool = False) -> pymupdf.Document:
    """Örnek sayfaları üretir; istenirse başlık sayfaya en son yazılır, yeri aynı kalır."""
    document = pymupdf.open()
    parts = [*BODY_HTML, HEADING] if heading_last else [HEADING, *BODY_HTML]
    for _ in range(pages):
        page = document.new_page()
        page.draw_rect(INFO_BOX, color=None, fill=(0.85, 0.92, 1.0))
        for rect, html in parts:
            page.insert_htmlbox(rect, html)
        page.insert_text((50, 600), "   ", fontsize=10)
    return document


def sample_profile(**changes: object) -> SourceProfile:
    """Örnek profili okur; verilen alanlar değiştirilir."""
    return SourceProfile.model_validate({**yaml.safe_load(PROFILE_YAML), **changes})
