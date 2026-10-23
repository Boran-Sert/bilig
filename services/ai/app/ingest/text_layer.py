"""Metin katmanı kontrolü (hazırlık hattı A3).

Bir PDF sayfasının metin katmanı sağlam mı, ona bakar: sayfadaki kelimelerin ne kadarı
Türkçe kök listesinde (data/turkce_kelimeler.txt) bir kökle başlıyor. Oran eşiği geçerse
sayfa metin yolundan, geçmezse görüntü yolundan işlenir.

Türkçe eklemeli bir dil olduğu için kelimenin kendisi değil, listedeki bir kökle başlayıp
başlamadığı aranır ("romanlarından" → "roman"). Türk alfabesi dışında harf taşıyan kelime
(ý, þ, ð gibi kodlama bozuklukları) bilinmeyen sayılır. Kesme işaretinden ya da kapanan
tırnaktan sonraki ekler, tek harfli parçalar, sayılar ve Romen rakamları hesaba katılmaz;
"ve/veya", "e-posta", "1.Şiir" gibi birleşik yazımlar parçalarına ayrılır.
"""

import re
from functools import lru_cache
from pathlib import Path

import pymupdf
from pydantic import BaseModel

from app.constants import (
    TEXT_LAYER_MIN_RATIO,
    TEXT_LAYER_MIN_STEM_LENGTH,
    TEXT_LAYER_MIN_WORD_LENGTH,
    TURKISH_LETTERS,
    WORD_LIST_FILE,
)
from app.text.turkish import normalize_nfc, tr_lower

_EDGE_NON_WORD = re.compile(r"^\W+|\W+$")
_SUFFIX_MARK = re.compile(r"['’\"”]")
_JOINER = re.compile(r"[/.\-–]")
_ROMAN_NUMERAL = re.compile(r"^[IVXLCDM]+$")
_REPOSITORY_ROOT_DEPTH = 4


class TextLayerResult(BaseModel):
    """Sayfadaki bilinen kelime oranı ve metin yolunun seçilip seçilmediği."""

    ratio: float
    ok: bool


def check_page(page: pymupdf.Page) -> TextLayerResult:
    """Sayfanın metin katmanının metin yolu için yeterince sağlam olup olmadığını ölçer."""
    return measure_text(page_text(page))


def page_text(page: pymupdf.Page) -> str:
    """Sayfanın metin katmanını, satır sonunda tireyle bölünen kelimeleri birleştirerek okur."""
    text: str = page.get_text("text", flags=pymupdf.TEXTFLAGS_TEXT | pymupdf.TEXT_DEHYPHENATE)
    return text


def measure_text(text: str) -> TextLayerResult:
    """Metindeki kelimelerin kök listesinde bulunma oranını hesaplar."""
    words = extract_words(text)
    if not words:
        return TextLayerResult(ratio=0.0, ok=False)
    known_words = load_word_list()
    ratio = sum(is_known_word(word, known_words) for word in words) / len(words)
    return TextLayerResult(ratio=ratio, ok=ratio >= TEXT_LAYER_MIN_RATIO)


def extract_words(text: str) -> list[str]:
    """Metni oranı hesaplanacak kelimelere böler ve Türkçe küçük harfe çevirir."""
    words = []
    for raw in normalize_nfc(text).split():
        stem_part = _SUFFIX_MARK.split(_EDGE_NON_WORD.sub("", raw))[0]
        for part in _JOINER.split(stem_part):
            word = _EDGE_NON_WORD.sub("", part)
            if _is_countable(word):
                words.append(tr_lower(word))
    return words


def _is_countable(word: str) -> bool:
    """Parça sayı, tek harf ya da Romen rakamı değil de bir kelimeyse doğru döner."""
    return (
        len(word) >= TEXT_LAYER_MIN_WORD_LENGTH
        and any(char.isalpha() for char in word)
        and not _ROMAN_NUMERAL.match(word)
    )


def is_known_word(word: str, known_words: frozenset[str]) -> bool:
    """Kelime Türk alfabesindeyse ve listedeki bir kökle başlıyorsa doğru döner."""
    if not set(word) <= TURKISH_LETTERS:
        return False
    if word in known_words:
        return True
    return any(
        word[:end] in known_words
        for end in range(len(word) - 1, TEXT_LAYER_MIN_STEM_LENGTH - 1, -1)
    )


@lru_cache(maxsize=1)
def load_word_list() -> frozenset[str]:
    """Türkçe kök listesini repodaki dosyadan bir kez okur."""
    path = Path(__file__).resolve().parents[_REPOSITORY_ROOT_DEPTH] / WORD_LIST_FILE
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip() for line in lines if line.strip())
