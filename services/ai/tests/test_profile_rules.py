"""Profil kuralı modelini, kural eşleştirmeyi ve profil dosyalarını okumayı test eder (A4)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ingest.profile import load_profiles, matches, rule_for
from app.schemas.profile import StyleMatch
from tests.profile_pdf import PROFILE_YAML, charis, sample_profile

BODY = charis()


@pytest.mark.parametrize(
    "fields",
    [{}, {"size": 10.3}, {"color": "#D9EBFF"}, {"box": "d9ebff"}, {"sise": 10}],
    ids=["empty", "size-off-step", "uppercase-color", "color-without-hash", "unknown-field"],
)
def test_style_match_rejects_rules_that_could_never_match(fields: dict[str, object]) -> None:
    """Boş, yuvarlamayla eşleşemeyecek ya da yazım hatalı kural kabul edilmez."""
    with pytest.raises(ValidationError):
        StyleMatch.model_validate(fields)


def test_style_match_accepts_null_fields_as_any_value() -> None:
    """Modelin bütün alanları doldurduğu kuralda boş alanlar her değerle eşleşir."""
    match = StyleMatch.model_validate(
        {"font": None, "size": 10.5, "bold": None, "italic": None, "color": None, "box": None}
    )

    assert match.model_dump(exclude_none=True) == {"size": 10.5}


@pytest.mark.parametrize(
    ("match", "expected"),
    [
        (StyleMatch(size=10, bold=False), True),
        (StyleMatch(size=10, bold=True), False),
        (StyleMatch(boxed=False), True),
        (StyleMatch(boxed=True), False),
        (StyleMatch(box="#d9ebff"), False),
        (StyleMatch(font="Sans"), False),
    ],
    ids=["same-fields", "one-differs", "unboxed", "boxed", "other-box", "other-font"],
)
def test_matches_compares_only_given_fields(match: StyleMatch, expected: bool) -> None:
    """Kural sadece dolu alanlarına bakar; boxed kutunun olup olmadığını sorar."""
    assert matches(BODY, match) is expected


def test_boxed_rule_on_boxed_text() -> None:
    """Kutudaki metin boxed: true kuralına uyar, boxed: false kuralına uymaz."""
    boxed = BODY.model_copy(update={"box": "#d9ebff"})

    assert matches(boxed, StyleMatch(boxed=True))
    assert not matches(boxed, StyleMatch(size=10, boxed=False))


def test_first_matching_rule_wins() -> None:
    """Bir stile birden çok kural uyarsa listede önce gelen kazanır."""
    profile = sample_profile(
        rules=[
            {"match": {"size": 10}, "block_type": "ALINTI"},
            {"match": {"size": 10, "bold": False}, "block_type": "METIN"},
        ]
    )

    rule = rule_for(BODY, profile)

    assert rule is not None and rule.block_type == "ALINTI"


def write_profile(directory: Path, name: str, text: str = PROFILE_YAML) -> None:
    """Klasöre profil dosyası yazar; varsayılan metindeki ad dosya adıyla değiştirilir."""
    content = text.replace("name: ornek_kitap", f"name: {name}")
    (directory / f"{name}.yaml").write_text(content, encoding="utf-8")


def test_load_profiles_reads_yaml_files_in_name_order(tmp_path: Path) -> None:
    """Profiller dosya adı sırasıyla okunur, YAML olmayan dosya atlanır."""
    write_profile(tmp_path, "ornek_kitap")
    write_profile(tmp_path, "a_seri")
    (tmp_path / "README.md").write_text("profil değil", encoding="utf-8")

    profiles = load_profiles(tmp_path)

    assert [profile.name for profile in profiles] == ["a_seri", "ornek_kitap"]
    assert profiles[1] == sample_profile()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (PROFILE_YAML.replace("name: ornek_kitap", "name: baska"), "does not match file"),
        ("rules: [", "Invalid profile kitap.yaml"),
        ("", "Invalid profile kitap.yaml"),
        (PROFILE_YAML.replace("size: 14", "size: 14.2"), "Invalid profile kitap.yaml"),
    ],
    ids=["other-name", "broken-yaml", "empty-file", "invalid-rule"],
)
def test_load_profiles_names_the_broken_file(tmp_path: Path, content: str, message: str) -> None:
    """Bozuk ya da adı tutmayan profil, dosya adıyla birlikte hata verir."""
    (tmp_path / "kitap.yaml").write_text(
        content.replace("name: ornek_kitap", "name: kitap"), encoding="utf-8"
    )

    with pytest.raises(ValueError, match=message):
        load_profiles(tmp_path)


def test_load_profiles_requires_the_directory(tmp_path: Path) -> None:
    """Profil klasörü yoksa okuma boş liste değil hata verir."""
    with pytest.raises(FileNotFoundError):
        load_profiles(tmp_path / "yok")
