"""Kaynak profili: profilleri okuma, stil sayımı ve kayıtlı profili bulma (hazırlık hattı A4).

Stil sayımı stil başına harf sayısını, ilk farklı örnek metinleri ve geçtiği ilk sayfaları verir;
harf sayıları ve sıra (harf sayısı, eşitlikte stilin alanları) satırların yazım sırasından
bağımsızdır, aynı PDF her seferinde aynı sonucu verir. Kayıtlı profillerden, kurallarının
belgedeki harflerin en az PROFILE_MATCH_MIN_COVERAGE kadarını kapsadığı en yüksek kapsamlı profil
seçilir; hiçbiri yetmezse profil önerisi istenir (#128). Kurallar sırayla denenir, stile uyan ilk
kural kazanır; kuralda boş bırakılan alan her değerle eşleşir.
"""

from collections import Counter
from pathlib import Path

import pymupdf
import yaml
from pydantic import ValidationError

from app.constants import (
    PROFILE_MATCH_MIN_COVERAGE,
    PROFILE_STYLE_PAGE_COUNT,
    PROFILE_STYLE_SAMPLE_COUNT,
)
from app.ingest.styles import styled_lines
from app.schemas.profile import (
    SourceProfile,
    StyleCount,
    StyleMatch,
    StyleRule,
    TextStyle,
)


def load_profiles(directory: Path) -> list[SourceProfile]:
    """Klasördeki profilleri dosya adı sırasıyla okur; profil adı dosya adıyla aynı olmalıdır."""
    if not directory.is_dir():
        raise FileNotFoundError(f"Profile directory {directory} does not exist")
    profiles = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            profile = SourceProfile.model_validate(yaml.safe_load(path.read_text("utf-8")))
        except (yaml.YAMLError, ValidationError) as error:
            raise ValueError(f"Invalid profile {path.name}: {error}") from error
        if profile.name != path.stem:
            raise ValueError(f"Profile name {profile.name!r} does not match file {path.name}")
        profiles.append(profile)
    return profiles


def count_styles(document: pymupdf.Document) -> list[StyleCount]:
    """Belgedeki stilleri harf sayısı, örnek metinleri ve sayfalarıyla sayar."""
    characters: Counter[TextStyle] = Counter()
    samples: dict[TextStyle, list[str]] = {}
    pages: dict[TextStyle, list[int]] = {}
    for page in document.pages():
        for line in styled_lines(page):
            for span in line.spans:
                text = span.text.strip()
                if not text:
                    continue
                characters[span.style] += len(text)
                add_first(samples.setdefault(span.style, []), text, PROFILE_STYLE_SAMPLE_COUNT)
                add_first(pages.setdefault(span.style, []), line.page_no, PROFILE_STYLE_PAGE_COUNT)
    counts = [
        StyleCount(style=style, characters=count, samples=samples[style], pages=pages[style])
        for style, count in characters.items()
    ]
    return sorted(counts, key=lambda count: (-count.characters, style_sort_key(count.style)))


def add_first[T](values: list[T], value: T, limit: int) -> None:
    """Değer listede yoksa ve liste dolmadıysa sona ekler."""
    if value not in values and len(values) < limit:
        values.append(value)


def find_profile(counts: list[StyleCount], profiles: list[SourceProfile]) -> SourceProfile | None:
    """Belgeyi yeterince kapsayan profillerden kapsamı en yüksek olanı döner, eşitlikte ilkini."""
    best: SourceProfile | None = None
    best_coverage = 0.0
    for profile in profiles:
        coverage = profile_coverage(counts, profile)
        if coverage >= PROFILE_MATCH_MIN_COVERAGE and coverage > best_coverage:
            best, best_coverage = profile, coverage
    return best


def profile_coverage(counts: list[StyleCount], profile: SourceProfile) -> float:
    """Profilin bir kuralına uyan stillerin belgedeki harf payını verir."""
    total = sum(count.characters for count in counts)
    if total == 0:
        return 0.0
    covered = sum(count.characters for count in counts if rule_for(count.style, profile))
    return covered / total


def rule_for(style: TextStyle, profile: SourceProfile) -> StyleRule | None:
    """Stile uyan ilk kuralı döner; uyan kural yoksa boş döner."""
    return next((rule for rule in profile.rules if matches(style, rule.match)), None)


def matches(style: TextStyle, match: StyleMatch) -> bool:
    """Kuralda dolu her alan stilde aynıysa doğru döner; boxed kutunun olup olmadığına bakar."""
    wanted = match.model_dump(exclude_none=True)
    boxed = wanted.pop("boxed", None)
    if boxed is not None and (style.box is not None) != boxed:
        return False
    return all(getattr(style, field) == value for field, value in wanted.items())


def style_sort_key(style: TextStyle) -> tuple[str, float, bool, bool, str, str]:
    """Stilleri her seferinde aynı sırada dizmek için anahtar verir."""
    return (style.font, style.size, style.bold, style.italic, style.color, style.box or "")
