"""Kaynak profili: profilleri okuma, stil sayımı, profil bulma ve uygulama (hazırlık hattı A4).

Stil sayımı stil başına harf sayısını, ilk farklı örnek metinleri ve geçtiği ilk sayfaları verir;
harf sayıları ve sıra (harf sayısı, eşitlikte stilin alanları) satırların yazım sırasından
bağımsızdır, aynı PDF her seferinde aynı sonucu verir. Kayıtlı profillerden, kurallarının
belgedeki harflerin en az PROFILE_MATCH_MIN_COVERAGE kadarını kapsadığı en yüksek kapsamlı profil
seçilir; hiçbiri yetmezse profil önerisi istenir (#128). Profil uygulanırken satırın türünü
satırda en çok harf tutan stile uyan ilk kural belirler; kurala uymayan satır METIN olur, IGNORE
satırı atılır. İtalik ve kalın parçalar *...* ve **...** olarak korunur; sadece eşleşen kural
italik ya da kalını açıkça istiyorsa (kalın başlık) o işaret konmaz. Edebiyat'ta italik eser
adıdır, satırın çoğunu tutsa da kaybolmaz.
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
    ProfiledLine,
    SourceProfile,
    StyleCount,
    StyledLine,
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


def apply_profile(page: pymupdf.Page, profile: SourceProfile) -> list[ProfiledLine]:
    """Sayfanın satırlarını profile göre blok türüne ve markdown metne çevirir."""
    profiled = []
    for line in styled_lines(page):
        dominant = dominant_span_index(line)
        span = line.spans[dominant]
        rule = rule_for(span.style, profile)
        target = rule.block_type if rule else "METIN"
        if target == "IGNORE":
            continue
        profiled.append(
            ProfiledLine(
                page_no=line.page_no,
                block_type=target,
                markdown=line_markdown(line, rule.match if rule else None),
                style=span.style,
                box_bbox=span.box_bbox,
                bbox=line.bbox,
            )
        )
    return profiled


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


def dominant_span_index(line: StyledLine) -> int:
    """Satırda en çok harf tutan stilin ilk parçasının yerini döner; eşitlikte önceki kazanır."""
    characters: Counter[TextStyle] = Counter()
    for span in line.spans:
        characters[span.style] += len(span.text.strip())
    dominant = max(characters, key=lambda style: characters[style])
    return next(index for index, span in enumerate(line.spans) if span.style == dominant)


def line_markdown(line: StyledLine, match: StyleMatch | None) -> str:
    """Satırı markdown'a çevirir; aynı işaretli komşu parçalar tek işaret çifti alır."""
    keep_bold = match is not None and match.bold is True
    keep_italic = match is not None and match.italic is True
    runs: list[tuple[str, str]] = []
    for span in line.spans:
        text = span.text.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")
        if not text.strip() and runs:
            runs[-1] = (runs[-1][0], runs[-1][1] + text)
            continue
        mark = ("**" if span.style.bold and not keep_bold else "") + (
            "*" if span.style.italic and not keep_italic else ""
        )
        if runs and runs[-1][0] == mark:
            runs[-1] = (mark, runs[-1][1] + text)
        else:
            runs.append((mark, text))
    return " ".join("".join(wrap(mark, text) for mark, text in runs).split())


def wrap(mark: str, text: str) -> str:
    """Metnin çevresindeki boşluğu dışarıda bırakarak işaret çiftiyle sarar."""
    core = text.strip()
    if not mark or not core:
        return text
    before = " " if text[0].isspace() else ""
    after = " " if text[-1].isspace() else ""
    return f"{before}{mark}{core}{mark[::-1]}{after}"


def style_sort_key(style: TextStyle) -> tuple[str, float, bool, bool, str, str]:
    """Stilleri her seferinde aynı sırada dizmek için anahtar verir."""
    return (style.font, style.size, style.bold, style.italic, style.color, style.box or "")
