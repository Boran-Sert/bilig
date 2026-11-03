"""Kaynak profilini (A4) kendi ürettiğimiz küçük PDF ve örnek profille test eder.

Örnek PDF'te kalın büyük başlık, gövde, gri kutudaki bilgi ve italik alıntı satırı vardır.
Örnek profil bu dört stili BASLIK, METIN, BILGI ve ALINTI yapar; stil sayımının her çalışmada
aynı çıkması, profilin eşleşmesi ve eşleşmemesi, dosyadan okuma ve profil adının yazılması sınanır.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

from app.ingest import profile
from app.schemas.profile import Profile
from app.storage import LocalFileStorage, source_key
from tests.pdf_factory import Box, Text, make_pdf

SAMPLE_PROFILE = """
description: Sınama için üretilmiş örnek profil
styles:
  - style: {font: LiberationSans-Bold, size: 18, bold: true}
    block_type: BASLIK
  - style: {font: LiberationSans, size: 10}
    block_type: METIN
  - style: {font: LiberationSans, size: 10, box_color: "#DCDCDC"}
    block_type: BILGI
  - style: {font: LiberationSans-Italic, size: 10, italic: true}
    block_type: ALINTI
"""
OTHER_PROFILE = """
styles:
  - style: {font: Palatino, size: 11}
    block_type: METIN
"""
SAMPLE_PDF = make_pdf(
    [
        [
            Text("**Roman**", 56, 80, 18),
            Text("Roman, olay örgüsü içinde kişileri anlatan uzun bir yazı türüdür.", 56, 110, 10),
            Box(50, 145, 348, 172),
            Text("Bilgi: Roman Batı'dan gelmiştir.", 60, 160, 10),
            Text("*Alıntı olarak yazılmış bir cümle.*", 56, 200, 10),
        ]
    ]
)


@pytest.fixture
def profile_dir(tmp_path: Path) -> Path:
    """Örnek ve başka bir profil dosyası içeren klasör."""
    directory = tmp_path / "profiles"
    directory.mkdir()
    (directory / "ornek-seri.yaml").write_text(SAMPLE_PROFILE, encoding="utf-8")
    (directory / "baska-seri.yaml").write_text(OTHER_PROFILE, encoding="utf-8")
    return directory


def test_sample_profile_turns_heading_box_and_italic_into_block_types(profile_dir: Path) -> None:
    """Örnek profil başlığı, bilgi kutusunu ve italiği doğru türe çevirir."""
    sample = next(p for p in profile.load_profiles(profile_dir) if p.name == "ornek-seri")
    lines = profile.read_styled_lines(SAMPLE_PDF)

    classified = profile.apply_profile(sample, lines)

    assert [(line.text[:5], line.block_type) for line in classified] == [
        ("Roman", "BASLIK"),
        ("Roman", "METIN"),
        ("Bilgi", "BILGI"),
        ("Alınt", "ALINTI"),
    ]


def test_style_counts_are_identical_on_every_run() -> None:
    """Aynı PDF'in stil sayımı her çalışmada aynı sırayla çıkar."""
    first = profile.count_styles(profile.read_styled_lines(SAMPLE_PDF))
    second = profile.count_styles(profile.read_styled_lines(SAMPLE_PDF))

    assert first == second
    assert len(first) == 4
    assert first[0].chars >= first[-1].chars
    assert {count.style.box_color for count in first} == {None, "#dcdcdc"}


def test_matching_finds_registered_profile_by_style_trace(profile_dir: Path) -> None:
    """Stil izi kayıtlı profille örtüşünce profil bulunur."""
    counts = profile.count_styles(profile.read_styled_lines(SAMPLE_PDF))

    match = profile.match_profile(counts, profile.load_profiles(profile_dir))

    assert match.profile_name == "ornek-seri"
    assert match.share == 1.0


def test_no_profile_matches_unknown_style_trace() -> None:
    """Stilleri örtüşmeyen profil eşleşmez."""
    counts = profile.count_styles(profile.read_styled_lines(SAMPLE_PDF))
    other = Profile.model_validate(
        {
            "name": "baska",
            "styles": [{"style": {"font": "Palatino", "size": 11}, "block_type": "METIN"}],
        }
    )

    match = profile.match_profile(counts, [other])

    assert match.profile_name is None


def test_profile_covering_too_little_of_document_does_not_match() -> None:
    """Belgenin harflerini yeterince kapsamayan profil eşleşmez."""
    counts = profile.count_styles(profile.read_styled_lines(SAMPLE_PDF))
    heading_only = Profile.model_validate(
        {
            "name": "baslik",
            "styles": [
                {
                    "style": {"font": "LiberationSans-Bold", "size": 18, "bold": True},
                    "block_type": "BASLIK",
                }
            ],
        }
    )

    assert profile.match_profile(counts, [heading_only]).profile_name is None


def test_profile_file_name_is_profile_name(profile_dir: Path) -> None:
    """Profil adı dosya adıdır ve profiller ada göre sıralı gelir."""
    names = [loaded.name for loaded in profile.load_profiles(profile_dir)]

    assert names == ["baska-seri", "ornek-seri"]


def test_invalid_profile_file_is_reported(tmp_path: Path) -> None:
    """Biçimi bozuk profil dosyası dosya adıyla hata verir."""
    (tmp_path / "bozuk.yaml").write_text("styles: []\n", encoding="utf-8")

    with pytest.raises(profile.ProfileError, match="bozuk.yaml"):
        profile.load_profiles(tmp_path)


class FakeConnection:
    """execute çağrılarını kaydeden sahte bağlantı."""

    def __init__(self) -> None:
        """Boş çağrı listesiyle başlar."""
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, query: str, params: dict[str, Any]) -> None:
        """Sorguyu ve parametreleri kaydeder."""
        self.calls.append((query, params))


@pytest.mark.asyncio
async def test_run_profile_step_writes_profile_name(profile_dir: Path, tmp_path: Path) -> None:
    """Eşleşen profilin adı kaynağa yazılır."""
    storage = LocalFileStorage(tmp_path / "storage")
    storage.write(source_key(7), SAMPLE_PDF)
    connection = FakeConnection()

    @asynccontextmanager
    async def connect() -> AsyncIterator[FakeConnection]:
        yield connection

    match = await profile.run_profile_step(7, connect, storage, profile.load_profiles(profile_dir))

    assert match.profile_name == "ornek-seri"
    assert connection.calls[0][1] == {"source_id": 7, "profile_name": "ornek-seri"}


@pytest.mark.asyncio
async def test_run_profile_step_clears_name_when_nothing_matches(tmp_path: Path) -> None:
    """Eşleşme yoksa profil adı boşaltılır."""
    storage = LocalFileStorage(tmp_path / "storage")
    storage.write(source_key(8), SAMPLE_PDF)
    connection = FakeConnection()

    @asynccontextmanager
    async def connect() -> AsyncIterator[FakeConnection]:
        yield connection

    match = await profile.run_profile_step(8, connect, storage, [])

    assert match.profile_name is None
    assert connection.calls[0][1] == {"source_id": 8, "profile_name": None}
