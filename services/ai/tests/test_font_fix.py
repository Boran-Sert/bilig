"""Bozuk font eşlemesini kodla düzeltmeyi test eder.

Bozuk sayfalar burada üretilir: metin, bozuk fontlu bir PDF'ten çıkacağı biçimde (kod
sayfası karışıklığı ya da sabit kod kayması) PDF'e yazılır. Metinler bu test için yazılmıştır.
"""

import random
import string

import pymupdf
import pytest

from app.constants import FONT_FIX_MIN_WORDS
from app.ingest import text_layer
from app.ingest.font_fix import FontFix, FontFixKind, apply_fix, candidate_fixes
from app.ingest.text_layer import TextLayerResult, check_page, find_font_fix, measure_text

PARAGRAPH = (
    "Masal, olağanüstü olayların anlatıldığı kısa bir türdür. Kahramanlar çoğu zaman bir "
    "yolculuğa çıkar, şaşırtıcı engellerle karşılaşır ve sonunda iyilik ödüllendirilir. "
    "Öğretmen, ılık bir sonbahar gününde öğrencilerine İstanbul'da geçen bir masal okudu."
)
SHIFT = 29


def garble(text: str, shift: int) -> str:
    """Metni bozuk fontun çıkaracağı gibi kaydırır; görünmez sonuçlanan karakter kaybolur."""
    garbled = []
    for char in text:
        code = ord(char) - shift
        if char.isspace():
            garbled.append(char)
        elif code >= 0x21 and chr(code).isprintable():
            garbled.append(chr(code))
    return "".join(garbled)


def to_cp1252(text: str) -> str:
    """Windows-1254 metni Windows-1252 diye okunmuş gibi bozar (ı → ý)."""
    return text.encode("cp1254").decode("cp1252")


def saved_page(text: str) -> pymupdf.Page:
    """Metni gömülü fontla yeni bir PDF'e yazar, PDF'i kaydedip ilk sayfasını açar."""
    document = pymupdf.open()
    document.new_page().insert_htmlbox(pymupdf.Rect(50, 50, 550, 800), f"<p>{text}</p>")
    return pymupdf.open("pdf", document.tobytes())[0]


def fail_if_called(text: str) -> list[FontFix]:
    """Düzeltme denenmemesi gereken yerde çağrılırsa testi düşürür."""
    raise AssertionError("font fixes must not be tried")


def test_codepage_fix_restores_turkish_letters() -> None:
    """Kod sayfası düzeltmesi ý, þ, ð ve büyük karşılıklarını Türkçe harflere çevirir."""
    fix = FontFix(kind=FontFixKind.TURKISH_CODEPAGE)

    assert apply_fix("Yazýlý sýnav, þiir, doðru; ÝZMÝR ÞEHÝR ÐÐ", fix) == (
        "Yazılı sınav, şiir, doğru; İZMİR ŞEHİR ĞĞ"
    )


def test_shift_fix_restores_plan_example() -> None:
    """Plandaki örnek ("0DVDO JHQHOOLNOH") 29 kayma geri alınınca düzelir."""
    fix = FontFix(kind=FontFixKind.CODE_SHIFT, shift=SHIFT)

    assert apply_fix("0DVDO JHQHOOLNOH", fix) == "Masal genellikle"


def test_shift_fix_restores_turkish_letters_and_keeps_whitespace() -> None:
    """Kayma Türkçe harflerde de geri alınır; boşluk ve satır sonları korunur."""
    fix = FontFix(kind=FontFixKind.CODE_SHIFT, shift=SHIFT)
    text = "Şiir ılık\nöğün\tçağ"

    assert apply_fix(garble(text, SHIFT), fix) == text


def test_shift_fix_leaves_character_when_result_is_invisible() -> None:
    """Kaydırma sonucu görünmez karakter olacaksa karakter olduğu gibi kalır."""
    fix = FontFix(kind=FontFixKind.CODE_SHIFT, shift=-40)

    assert apply_fix("A!", fix) == "A!"


def test_candidates_include_codepage_only_when_marks_present() -> None:
    """Kod sayfası adayı sadece metinde ý, þ, ð gibi işaretler varsa denenir."""
    with_marks = candidate_fixes("yazýlý")
    without_marks = candidate_fixes("0DVDO")

    assert with_marks[0].kind is FontFixKind.TURKISH_CODEPAGE
    assert all(fix.kind is FontFixKind.CODE_SHIFT for fix in without_marks)
    assert len(with_marks) == len(without_marks) + 1


def test_candidates_cover_both_directions_without_zero_shift() -> None:
    """Kayma adayları iki yönü de kapsar, sıfır kayma denenmez."""
    shifts = {fix.shift for fix in candidate_fixes("0DVDO")}

    assert SHIFT in shifts
    assert -SHIFT in shifts
    assert 0 not in shifts


def test_shifted_page_is_fixed_and_takes_text_path() -> None:
    """Kodları 29 kaymış sayfa düzeltilir, metin yoluna gider ve düzeltme sonuçta taşınır."""
    page = saved_page(garble(PARAGRAPH, SHIFT))

    result = check_page(page)

    assert measure_text(text_layer.page_text(page)).ratio < 0.2
    assert result.ok
    assert result.ratio >= 0.9
    assert result.fix == FontFix(kind=FontFixKind.CODE_SHIFT, shift=SHIFT)


def test_codepage_page_is_fixed_and_takes_text_path() -> None:
    """ı → ý bozukluğu olan sayfa kod sayfası düzeltmesiyle metin yoluna gider."""
    result = check_page(saved_page(to_cp1252(PARAGRAPH)))

    assert result.ok
    assert result.fix == FontFix(kind=FontFixKind.TURKISH_CODEPAGE)


def test_sound_page_is_not_changed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sağlam sayfaya düzeltme denenmez ve sonuçta düzeltme yoktur."""
    monkeypatch.setattr(text_layer, "candidate_fixes", fail_if_called)

    result = check_page(saved_page(PARAGRAPH))

    assert result.ok
    assert result.fix is None


def test_page_without_text_is_not_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Metni olmayan sayfaya düzeltme denenmez; doğrudan görüntü yoluna düşer."""
    monkeypatch.setattr(text_layer, "candidate_fixes", fail_if_called)
    document = pymupdf.open()
    document.new_page()

    result = check_page(pymupdf.open("pdf", document.tobytes())[0])

    assert not result.ok
    assert result.fix is None


def test_page_with_lost_letters_stays_on_image_path() -> None:
    """Harfleri kaybolmuş (ş → ·) sayfa kodla düzelmez ve görüntü yoluna düşer."""
    lost = "".join("·" if char in "ğĞşŞıİ" else char for char in PARAGRAPH)

    result = check_page(saved_page(lost))

    assert not result.ok
    assert result.fix is None


def test_find_font_fix_returns_none_when_nothing_passes() -> None:
    """Hiçbir düzeltme eşiği geçirmezse sonuç yoktur."""
    lost = "".join("·" if char in "ğĞşŞıİ" else char for char in PARAGRAPH)

    assert find_font_fix(lost) is None


def test_find_font_fix_skips_short_text() -> None:
    """Kısa metinde düzeltme denenmez; kaymış ama az kelimeli metin düzeltilmez."""
    short = garble("Masal olağanüstü olayları anlatır", SHIFT)

    assert len(short.split()) < FONT_FIX_MIN_WORDS
    assert find_font_fix(short) is None


def test_find_font_fix_finds_no_shift_for_random_text() -> None:
    """Yeterince uzun rastgele metin hiçbir kaymayla Türkçeye dönmez."""
    generator = random.Random(7)
    alphabet = string.ascii_letters + string.digits + ".,;:!?"
    words = [
        "".join(generator.choice(alphabet) for _ in range(generator.randint(2, 9)))
        for _ in range(FONT_FIX_MIN_WORDS)
    ]

    assert find_font_fix(" ".join(words)) is None


def test_find_font_fix_prefers_highest_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Eşiği geçen düzeltmelerden oranı en yüksek olan seçilir."""
    weaker = FontFix(kind=FontFixKind.CODE_SHIFT, shift=1)
    stronger = FontFix(kind=FontFixKind.CODE_SHIFT, shift=2)
    outputs = {
        weaker.shift: " ".join(["roman"] * 19 + ["qqqq"]),
        stronger.shift: "roman şiir",
    }
    monkeypatch.setattr(text_layer, "candidate_fixes", lambda _: [weaker, stronger])
    monkeypatch.setattr(text_layer, "apply_fix", lambda _, fix: outputs[fix.shift])

    long_text = " ".join(["bozuk"] * FONT_FIX_MIN_WORDS)

    assert find_font_fix(long_text) == TextLayerResult(ratio=1.0, ok=True, fix=stronger)
