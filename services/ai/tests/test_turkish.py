"""Türkçe metin dönüşümlerini test eder."""

import unicodedata

from app.text.turkish import ascii_fold, normalize_nfc, tr_lower, tr_upper


def test_tr_lower_converts_dotted_and_dotless_i() -> None:
    """Büyük İ küçük i'ye, büyük I küçük ı'ya döner."""
    assert tr_lower("İSTANBUL ILIK") == "istanbul ılık"


def test_tr_lower_handles_all_turkish_letters() -> None:
    """Ç, Ğ, Ö, Ş, Ü harfleri doğru küçülür."""
    assert tr_lower("ÇAĞRI ÖĞÜN ŞÜKRÜ") == "çağrı öğün şükrü"


def test_tr_lower_produces_no_combining_dot() -> None:
    """Sonuçta birleşik nokta işareti kalmaz."""
    assert "̇" not in tr_lower("İZMİR")


def test_tr_upper_converts_dotted_and_dotless_i() -> None:
    """Küçük i büyük İ'ye, küçük ı büyük I'ya döner."""
    assert tr_upper("istanbul ılık") == "İSTANBUL ILIK"


def test_tr_lower_and_tr_upper_round_trip() -> None:
    """Türkçe metin küçültülüp büyütülünce aynı kalır."""
    text = "IĞDIR İNEBOLU ÇİĞDEM"

    assert tr_upper(tr_lower(text)) == text


def test_normalize_nfc_joins_combining_marks() -> None:
    """Ayrık yazılmış şapka harfle birleşir."""
    decomposed = "kâtip"

    result = normalize_nfc(decomposed)

    assert result == "kâtip"
    assert unicodedata.is_normalized("NFC", result)


def test_ascii_fold_removes_turkish_marks() -> None:
    """Türkçe harfler ve şapkalı harfler ASCII karşılığına döner."""
    assert ascii_fold("Çağrı Şükrü İğdır öğün kâtip") == "Cagri Sukru Igdir ogun katip"


def test_ascii_fold_keeps_ascii_text() -> None:
    """ASCII metin değişmez."""
    assert ascii_fold("feat/12-test-oturumu") == "feat/12-test-oturumu"
