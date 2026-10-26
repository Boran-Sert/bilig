"""Stil sayımını ve kayıtlı profili bulmayı test eder (hazırlık hattı A4)."""

import pymupdf
import pytest

from app.ingest.profile import count_styles, find_profile, profile_coverage
from app.schemas.profile import StyleCount, TextStyle
from tests.profile_pdf import build_document, charis, sample_profile

BODY = charis()


def style_count(style: TextStyle, characters: int) -> StyleCount:
    """Elle stil sayımı satırı kurar."""
    return StyleCount(style=style, characters=characters, samples=[], pages=[])


def test_count_styles_reports_each_style_by_characters() -> None:
    """Her stil harf sayısıyla, en çok harf tutan başta; sadece boşluk olan stil sayılmaz."""
    counts = count_styles(build_document())

    assert [(count.style, count.characters) for count in counts] == [
        (charis(box="#d9ebff"), 36),
        (BODY, 34),
        (charis("-Bold", size=14), 13),
        (charis("-Italic"), 13),
        (charis(size=8, color="#0000ff"), 3),
    ]
    assert counts[1].samples == ["Yakup Kadri", "romanını 1922'de yazdı."]


def test_count_styles_is_stable_across_runs_and_writing_order() -> None:
    """Tekrar sayınca, diske yazıp açınca ve satırların yazım sırası değişince sonuç aynıdır."""
    document = build_document(pages=3)
    first = count_styles(document)

    assert count_styles(document) == first
    assert count_styles(pymupdf.open("pdf", document.tobytes())) == first
    assert count_styles(build_document(pages=3, heading_last=True)) == first
    assert sum(count.characters for count in first) == 3 * 99


def test_count_styles_keeps_distinct_samples_and_first_pages() -> None:
    """Her sayfada tekrar eden metin bir kez örnek olur; ilk üç sayfa kaydedilir."""
    counts = count_styles(build_document(pages=5))

    heading = next(count for count in counts if count.style.bold)
    assert heading.samples == ["Roman Türleri"]
    assert heading.pages == [1, 2, 3]
    assert next(count for count in counts if count.style == BODY).samples == [
        "Yakup Kadri",
        "romanını 1922'de yazdı.",
    ]


def test_count_styles_skips_styles_seen_only_as_whitespace() -> None:
    """Sadece boşluk taşıyan kalın parça stil olarak sayılmaz."""
    document = pymupdf.open()
    html = '<p style="font-size:10px">Ders<b> </b>okur.</p>'
    document.new_page().insert_htmlbox(pymupdf.Rect(50, 50, 500, 150), html)

    assert [(count.style, count.characters) for count in count_styles(document)] == [(BODY, 9)]


def test_profile_coverage_counts_matched_characters() -> None:
    """Kapsam, bir kurala uyan stillerin harflerinin bütün harflere oranıdır."""
    counts = count_styles(build_document())
    without_body = sample_profile(rules=sample_profile().rules[:3])

    assert profile_coverage(counts, sample_profile()) == 1.0
    assert profile_coverage(counts, without_body) == pytest.approx(52 / 99)
    assert profile_coverage([], sample_profile()) == 0.0


def test_find_profile_picks_best_covering_profile() -> None:
    """Yeterince kapsayan profillerden kapsamı en yüksek olan seçilir, eşitlikte ilk sıradaki."""
    counts = count_styles(build_document())
    full = sample_profile()
    partial = sample_profile(name="kismi", rules=full.rules[:3])
    twin = sample_profile(name="ikiz")

    assert find_profile(counts, [partial, full]) is full
    assert find_profile(counts, [full, twin]) is full
    assert find_profile(counts, [partial]) is None
    assert find_profile(counts, []) is None


def test_find_profile_accepts_coverage_at_threshold() -> None:
    """Kapsamı tam eşikte olan profil seçilir, eşiğin altındaki seçilmez."""
    other = BODY.model_copy(update={"size": 9.0})
    profile = sample_profile(rules=[{"match": {"size": 10}, "block_type": "METIN"}])
    at_threshold = [style_count(BODY, 90), style_count(other, 10)]
    below = [style_count(BODY, 89), style_count(other, 11)]

    assert find_profile(at_threshold, [profile]) is profile
    assert find_profile(below, [profile]) is None
