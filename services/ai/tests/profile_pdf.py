"""Profil testlerinin ortak örnek profili.

Örnek profil, testlerde üretilen sayfanın stillerini (kalın 14 puan başlık, mavi bilgi kutusu,
10 puan gövde, mavi 8 puan sayfa numarası) BASLIK, BILGI, METIN ve IGNORE'a eşler.
"""

import yaml

from app.schemas.profile import SourceProfile, TextStyle

PROFILE_YAML = """
name: ornek_kitap
description: Testte üretilen PDF'in profili.
rules:
  - match: {size: 8, color: "#0000ff"}
    block_type: IGNORE
  - match: {size: 14, bold: true}
    block_type: BASLIK
  - match: {box: "#d9ebff"}
    block_type: BILGI
  - match: {size: 10, boxed: false}
    block_type: METIN
"""


def charis(
    variant: str = "", size: float = 10, color: str = "#000000", box: str | None = None
) -> TextStyle:
    """Örnek PDF'teki CharisSIL fontunun bir stilini kurar."""
    return TextStyle(
        font=f"CharisSIL{variant}",
        size=size,
        bold=variant == "-Bold",
        italic=variant == "-Italic",
        color=color,
        box=box,
    )


def sample_profile(**changes: object) -> SourceProfile:
    """Örnek profili okur; verilen alanlar değiştirilir."""
    return SourceProfile.model_validate({**yaml.safe_load(PROFILE_YAML), **changes})
