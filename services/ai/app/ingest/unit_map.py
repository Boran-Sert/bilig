"""Test adından ünite bulma (hazırlık hattı A5, #130).

Kural dosyası (data/unit_map.txt) satır başına "anahtar = ünite adı" tutar; boş satırlar ve #
ile başlayan satırlar atlanır. Kaynak adında anahtar aranır: büyük-küçük harf ve Türkçe harf
işaretleri önemsizdir ("Hikâye" ile "hikaye" aynıdır); birden çok anahtar uyarsa en uzunu
kazanır, eşitlikte dosyadaki ilki. Hiçbiri uymazsa ünite bulunamaz ve soru yazılmaz. Dosya
değişince kod değişmez; ünite adı curriculum_unit.title ile aynı yazılmalıdır.
"""

from pathlib import Path

from pydantic import BaseModel

from app.text.turkish import ascii_fold, tr_lower

SEPARATOR = "="
COMMENT_MARK = "#"


class UnitRule(BaseModel):
    """Bir kural: kaynak adında aranacak anahtar ve bulununca verilecek ünite adı."""

    keyword: str
    unit_title: str


class UnitMapError(ValueError):
    """Eşleştirme dosyasında biçimi bozuk bir satır var."""


def comparable(text: str) -> str:
    """Karşılaştırma için küçük harfe ve işaretsiz harfe çevirir."""
    return ascii_fold(tr_lower(text)).strip()


def parse_unit_map(text: str) -> list[UnitRule]:
    """Kural dosyasının metnini kurallara çevirir; bozuk satırı numarasıyla bildirir."""
    rules = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_MARK):
            continue
        keyword, separator, unit_title = stripped.rpartition(SEPARATOR)
        if not separator or not keyword.strip() or not unit_title.strip():
            raise UnitMapError(f"Invalid unit map line {number}: {stripped!r}")
        rules.append(UnitRule(keyword=keyword.strip(), unit_title=unit_title.strip()))
    return rules


def load_unit_map(path: Path) -> list[UnitRule]:
    """Kural dosyasını okur."""
    return parse_unit_map(path.read_text(encoding="utf-8"))


def find_unit_title(source_title: str, rules: list[UnitRule]) -> str | None:
    """Kaynak adına uyan en uzun anahtarın ünite adını verir; uyan yoksa boş döner."""
    title = comparable(source_title)
    matches = [rule for rule in rules if comparable(rule.keyword) in title]
    if not matches:
        return None
    return max(matches, key=lambda rule: len(comparable(rule.keyword))).unit_title
