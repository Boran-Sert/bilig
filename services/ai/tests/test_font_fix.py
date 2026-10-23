"""Bozuk font eşlemesini kodla düzeltmeyi test eder.

Bozuk metinler burada üretilir: metin, bozuk fontlu bir PDF'ten çıkacağı biçimde (kod
sayfası karışıklığı ya da sabit kod kayması) bozulur. Metinler bu test için yazılmıştır.
"""

from app.ingest.font_fix import FontFix, FontFixKind, apply_fix, candidate_fixes

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
