"""Bozuk font eşlemesini kodla düzeltme (hazırlık hattı A3).

Bazı PDF'lerde fontun karakter eşlemesi bozuk olduğu için metin katmanı yanlış çıkar.
Burada bilinen iki bozukluk için düzeltme adayları üretilir:

- Türkçe kod sayfası karışıklığı: Windows-1254 metni Windows-1252 diye okunmuş
  (ı → ý, ş → þ, ğ → ð, İ → Ý, Ş → Þ, Ğ → Ð).
- Sabit kod kayması: her karakter aynı sayıda kod noktası kaymış
  ("Masal genellikle" → "0DVDO JHQHOOLNOH", 29 kayma).

Hangi adayın işe yaradığına metin katmanı kontrolü karar verir (text_layer.check_page_text):
düzeltilmiş metnin oranı eşiği geçerse sayfa metin yolundan gider. Sayfadaki her karakterin
aynı biçimde bozulduğu varsayılır; yarısı bozuk sayfa düzelmez ve görüntü yoluna düşer.
"""

import sys
from enum import StrEnum

from pydantic import BaseModel

from app.constants import FONT_FIX_FIRST_VISIBLE_CODE, FONT_FIX_MAX_SHIFT

_CODEPAGE_TABLE = str.maketrans("ýþðÝÞÐ", "ışğİŞĞ")
_CODEPAGE_MARKS = frozenset("ýþðÝÞÐ")


class FontFixKind(StrEnum):
    """Düzeltilen bozukluğun türü."""

    TURKISH_CODEPAGE = "TURKISH_CODEPAGE"
    CODE_SHIFT = "CODE_SHIFT"


class FontFix(BaseModel):
    """Metne uygulanacak düzeltme; kod kaymasında kaç kod noktası geri alınacağı."""

    kind: FontFixKind
    shift: int = 0


def candidate_fixes(text: str) -> list[FontFix]:
    """Metin için denenecek düzeltmeleri sırayla döner."""
    fixes = []
    if _CODEPAGE_MARKS & set(text):
        fixes.append(FontFix(kind=FontFixKind.TURKISH_CODEPAGE))
    fixes.extend(
        FontFix(kind=FontFixKind.CODE_SHIFT, shift=shift)
        for shift in range(-FONT_FIX_MAX_SHIFT, FONT_FIX_MAX_SHIFT + 1)
        if shift != 0
    )
    return fixes


def apply_fix(text: str, fix: FontFix) -> str:
    """Düzeltmeyi metne uygular."""
    if fix.kind is FontFixKind.TURKISH_CODEPAGE:
        return text.translate(_CODEPAGE_TABLE)
    return "".join(_shift_character(char, fix.shift) for char in text)


def _shift_character(char: str, shift: int) -> str:
    """Boşluk olmayan karakteri kaydırır; sonuç görünür bir karakter değilse olduğu gibi bırakır."""
    if char.isspace():
        return char
    code = ord(char) + shift
    if code < FONT_FIX_FIRST_VISIBLE_CODE or code > sys.maxunicode or not chr(code).isprintable():
        return char
    return chr(code)
