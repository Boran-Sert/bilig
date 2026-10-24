"""Türkçe metin dönüşümleri.

Python'un düz lower() ve upper() metodları İ/i ve I/ı çiftlerini yanlış çevirir
("İ".lower() birleşik noktalı "i̇" üretir). Servisteki bütün Türkçe büyük-küçük harf
dönüşümleri ve NFC normalleştirmesi bu dosyadan yapılır (plan 13.9).
"""

import unicodedata

_LOWER_SPECIAL = str.maketrans({"I": "ı", "İ": "i"})
_UPPER_SPECIAL = str.maketrans({"i": "İ", "ı": "I"})
_ASCII_SPECIAL = str.maketrans({"ı": "i"})


def tr_lower(text: str) -> str:
    """Metni Türkçe kurallarıyla küçük harfe çevirir."""
    return text.translate(_LOWER_SPECIAL).lower()


def tr_upper(text: str) -> str:
    """Metni Türkçe kurallarıyla büyük harfe çevirir."""
    return text.translate(_UPPER_SPECIAL).upper()


def normalize_nfc(text: str) -> str:
    """Metni Unicode NFC biçimine getirir; ayrık yazılmış şapka ve noktalar birleşir."""
    return unicodedata.normalize("NFC", text)


def ascii_fold(text: str) -> str:
    """Metni harf işaretlerini atarak ASCII'ye çevirir; dosya ve branch adı gibi alanlar içindir."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_ASCII_SPECIAL))
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_marks.encode("ascii", "ignore").decode("ascii")
