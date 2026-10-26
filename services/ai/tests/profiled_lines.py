"""Test okuyucusu testlerinin elle kurulan satırları.

Satırların konumu tam verilir: sol sütun 40-280 arasıdır, sağ kenara kadar dolu satır 280'de
biter; yazı boyutu 10, sayfa genişliği A4.
"""

from app.schemas.profile import ProfiledLine, TextStyle

PAGE_WIDTH = 595.0
BODY = TextStyle(font="Serif", size=10, bold=False, italic=False, color="#000000", box=None)


def line(text: str, top: float, left: float = 40.0, right: float = 280.0) -> ProfiledLine:
    """Verilen yerde tek satır kurar; sağ kenarı verilmezse satır sütunun sonuna kadar doludur."""
    return ProfiledLine(
        page_no=1,
        block_type="METIN",
        markdown=text,
        style=BODY,
        box_bbox=None,
        bbox=(left, top, right, top + 12),
    )


def options(top: float) -> list[ProfiledLine]:
    """Beş şık satırı kurar; ilki sütunun sağ kenarını belirleyecek kadar uzundur."""
    return [
        line(f"{label}) {label}", top + 14 * index, 52, 280 if label == "A" else 90)
        for index, label in enumerate("ABCDE")
    ]
