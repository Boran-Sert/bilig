"""Kaynak profili: profil dosyalarını okuma ve stile uyan kuralı bulma (hazırlık hattı A4).

Profiller profiles/*.yaml dosyalarıdır; biçimi profiles/README.md. Kurallar sırayla denenir,
stile uyan ilk kural kazanır. Kuralda boş bırakılan alan her değerle eşleşir; boxed alanı metnin
bir kutunun içinde olup olmadığına bakar. Bozuk profil, dosya adıyla birlikte hata verir.
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.schemas.profile import SourceProfile, StyleMatch, StyleRule, TextStyle


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
