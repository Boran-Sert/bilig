"""Metin katmanı kontrolünü test eder.

Test PDF'leri burada üretilir; içindeki metinler bu test için yazılmıştır, hiçbir kitaptan
alınmamıştır. Sağlam PDF Türkçe harfleri taşıyan gömülü bir fontla, bozuk PDF'ler ise Türkçe
harfleri kodlayamayan standart Helvetica fontuyla ya da kaymış karakter kodlarıyla yazılır.
"""

import unicodedata
from pathlib import Path

import pymupdf
import pytest

from app.constants import TEXT_LAYER_MIN_RATIO, TURKISH_LETTERS
from app.ingest import text_layer
from app.ingest.text_layer import (
    check_page,
    extract_words,
    is_known_word,
    load_word_list,
    measure_text,
    page_text,
)
from tests.word_list import KNOWN_WORDS, REPOSITORY_WORD_LIST

PARAGRAPH = (
    "Tarihî romanlar konusunu geçmişte yaşanmış olaylardan alır. Yazar, dönemin havasını "
    "yansıtmak için belgelere başvurur ve kahramanlarını bu ortamın içinde yaşatır. "
    "Öğrenciler İstanbul'daki kütüphanede şiir kitaplarını ılık bir öğleden sonra okudular."
)
SHIFTED_PARAGRAPH = "".join(chr(ord(char) - 29) if char.isalpha() else char for char in PARAGRAPH)


def saved_page(write: str, text: str) -> pymupdf.Page:
    """Metni verilen yolla yeni bir PDF'e yazar, PDF'i kaydedip ilk sayfasını açar."""
    document = pymupdf.open()
    page = document.new_page()
    if write == "embedded":
        page.insert_htmlbox(pymupdf.Rect(50, 50, 550, 800), text)
    else:
        page.insert_text((50, 72), text, fontname="helv")
    return pymupdf.open("pdf", document.tobytes())[0]


def test_sound_pdf_page_takes_text_path() -> None:
    """Türkçe harfleri doğru çıkan sayfa metin yoluna gider."""
    result = check_page(saved_page("embedded", f"<p>{PARAGRAPH}</p>"), KNOWN_WORDS)

    assert result.ok
    assert result.ratio == 1.0


def test_pdf_page_with_lost_turkish_letters_takes_image_path() -> None:
    """Fontu Türkçe harfleri kodlayamayan sayfa görüntü yoluna düşer."""
    page = saved_page("helvetica", PARAGRAPH)

    result = check_page(page, KNOWN_WORDS)

    assert "ş" not in page.get_text()
    assert not result.ok


def test_shifted_codes_have_low_ratio() -> None:
    """Karakter kodları kaymış metnin ("Masal" yerine "0DVDO") düzeltmeden önceki oranı düşüktür."""
    result = measure_text(SHIFTED_PARAGRAPH, KNOWN_WORDS)

    assert not result.ok
    assert result.ratio < 0.2


def test_empty_pdf_page_takes_image_path() -> None:
    """Metin katmanı olmayan (taranmış) sayfanın oranı sıfırdır."""
    document = pymupdf.open()
    document.new_page()

    result = check_page(pymupdf.open("pdf", document.tobytes())[0], KNOWN_WORDS)

    assert result.ratio == 0.0
    assert not result.ok


def test_word_split_by_hyphen_across_lines_is_joined() -> None:
    """Satır sonunda tireyle bölünen kelime tek kelime olarak ölçülür."""
    page = saved_page("embedded", "<p>Divan şiiri araş-<br>tırmacıları bu konuyu inceledi.</p>")

    assert "araştırmacıları" in extract_words(page_text(page))


def test_uppercase_turkish_text_is_measured_with_turkish_lowercase() -> None:
    """Büyük harfli başlık Türkçe kurala göre küçültülerek ölçülür (İ → i, I → ı)."""
    assert measure_text("ROMAN TÜRLERİ VE ÖZELLİKLERİ, ILIK BİR İKLİM", KNOWN_WORDS).ratio == 1.0


def test_mojibake_text_is_rejected() -> None:
    """Windows-1252 ile yanlış okunmuş Türkçe metin (ı → ý, ş → þ) bilinmeyen sayılır."""
    broken = PARAGRAPH.encode("cp1254").decode("cp1252")

    assert not measure_text(broken, KNOWN_WORDS).ok


def test_ratio_at_threshold_takes_text_path() -> None:
    """Oran tam eşikteyse metin yolu seçilir, altındaysa seçilmez."""
    known = int(TEXT_LAYER_MIN_RATIO * 10)

    at_threshold = measure_text(" ".join(["roman"] * known + ["qqqq"] * (10 - known)), KNOWN_WORDS)
    below = measure_text(" ".join(["roman"] * (known - 1) + ["qqqq"] * (11 - known)), KNOWN_WORDS)

    assert at_threshold.ratio == pytest.approx(TEXT_LAYER_MIN_RATIO)
    assert at_threshold.ok
    assert not below.ok


def test_extract_words_skips_numbers_letters_and_suffixes() -> None:
    """Sayılar, tek harfli parçalar ve kesme işaretinden sonraki ekler sayılmaz."""
    words = extract_words("174 A) 3. «Devlet Ana» Kemal Tahir'in romanıdır; Tahir’e göre…")

    assert words == ["devlet", "ana", "kemal", "tahir", "romanıdır", "tahir", "göre"]


def test_extract_words_keeps_inner_broken_characters() -> None:
    """Kelimenin içindeki bozuk karakter atılmaz; kelime bilinmeyen sayılır."""
    words = extract_words("A·açlar·n gölgesinde")

    assert words == ["a·açlar·n", "gölgesinde"]
    assert not is_known_word(words[0], KNOWN_WORDS)


def test_is_known_word_accepts_suffixed_word_by_stem() -> None:
    """Ek almış kelime listedeki kökle tanınır."""
    known_words = frozenset({"roman", "kitab"})

    assert is_known_word("romanlarından", known_words)
    assert is_known_word("kitabı", known_words)
    assert not is_known_word("kalem", known_words)


def test_is_known_word_rejects_letters_outside_turkish_alphabet() -> None:
    """Türk alfabesi dışında harf taşıyan kelime, kökü listede olsa da bilinmeyen sayılır."""
    assert not is_known_word("romaný", frozenset({"roman"}))


def test_is_known_word_matches_whole_word_shorter_than_stem_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kök sınırından kısa kelime listede birebir varsa bilinir."""
    monkeypatch.setattr(text_layer, "TEXT_LAYER_MIN_STEM_LENGTH", 3)

    assert is_known_word("ve", frozenset({"ve"}))
    assert not is_known_word("vey", frozenset({"ve"}))


def test_is_known_word_does_not_match_single_letter_stem() -> None:
    """Tek harfli bir önek kök sayılmaz."""
    assert not is_known_word("obzt", frozenset({"o"}))


def test_word_list_is_clean() -> None:
    """Kök listesi boş değil; her satır Türk alfabesinde, küçük harf, NFC ve en az iki harf."""
    assert len(KNOWN_WORDS) > 70_000
    for word in KNOWN_WORDS:
        assert len(word) >= 2
        assert set(word) <= TURKISH_LETTERS
        assert unicodedata.is_normalized("NFC", word)
    assert {
        "roman",
        "şiir",
        "tiyatro",
        "kazanım",
        "git",
        "kitab",
        "orhan",
        "vb",
        "diy",
    } <= KNOWN_WORDS


def test_word_list_file_is_sorted_without_duplicates() -> None:
    """Liste dosyası README'de anlatıldığı gibi tekrarsız ve sıralıdır."""
    lines = REPOSITORY_WORD_LIST.read_text(encoding="utf-8").splitlines()

    assert lines == sorted(set(lines))


def test_extract_words_splits_joined_spellings() -> None:
    """Eğik çizgi, tire, nokta ve uzun tireyle birleşik yazımlar parçalarına ayrılır."""
    assert extract_words("ve/veya e-posta 1.Şiir masal–fabl") == [
        "ve",
        "veya",
        "posta",
        "şiir",
        "masal",
        "fabl",
    ]


def test_extract_words_skips_roman_numerals_and_quoted_suffixes() -> None:
    """Romen rakamları sayılmaz; kapanan tırnaktan sonraki ek atılır."""
    words = extract_words("I, II ve III. öncüllerden hangisi “Çerçeve”nin IV. bölümünde DİL")

    assert words == ["ve", "öncüllerden", "hangisi", "çerçeve", "bölümünde", "dil"]


def test_extract_words_skips_web_addresses_and_soft_hyphens() -> None:
    """Web ve e-posta adresleri sayılmaz; yumuşak tire kelimeyi bölmez."""
    words = extract_words("Kaynak: www.ornek.com.tr https://ornek.org yazar@ornek.com edebi­yat")

    assert words == ["kaynak", "edebiyat"]


def test_extract_words_splits_words_joined_by_punctuation() -> None:
    """Boşluksuz virgül, noktalı virgül ve iki noktayla bitişen kelimeler ayrılır."""
    assert extract_words("ey,mavi deniz;rüzgâr ses:söz") == [
        "ey",
        "mavi",
        "deniz",
        "rüzgâr",
        "ses",
        "söz",
    ]


def test_is_known_word_accepts_circumflex_spelling() -> None:
    """Şapkalı yazım, listede şapkasız kökü varsa tanınır."""
    known_words = frozenset({"lale", "hikaye"})

    assert is_known_word("lâlesidir", known_words)
    assert is_known_word("hikâyeler", known_words)


def test_load_word_list_reads_given_file(tmp_path: Path) -> None:
    """Liste verilen dosyadan okunur; boş satırlar ve kenar boşlukları atılır."""
    path = tmp_path / "kelimeler.txt"
    path.write_text("roman\n\n  şiir \n", encoding="utf-8")

    assert load_word_list(path) == frozenset({"roman", "şiir"})


def test_load_word_list_names_missing_file(tmp_path: Path) -> None:
    """Dosya yoksa hata, aranan yolu söyler."""
    path = tmp_path / "yok.txt"

    with pytest.raises(FileNotFoundError, match="yok.txt"):
        load_word_list(path)


def test_load_word_list_rejects_empty_file(tmp_path: Path) -> None:
    """Boş liste dosyası, bütün sayfaları sessizce görüntü yoluna düşürmek yerine hata verir."""
    path = tmp_path / "bos.txt"
    path.write_text("\n  \n", encoding="utf-8")

    with pytest.raises(ValueError, match="bos.txt"):
        load_word_list(path)
