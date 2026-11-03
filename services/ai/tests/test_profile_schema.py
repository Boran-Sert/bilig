"""Profil modellerinin (A4) kurallarını sınar: tekrar eden stil ve boyut yuvarlama."""

import pytest
from pydantic import ValidationError

from app.schemas.profile import Profile, StyleKey


def test_profile_rejects_repeated_style() -> None:
    """Aynı stil profilde iki kez yazılamaz."""
    rule = {"style": {"font": "A", "size": 10}, "block_type": "METIN"}

    with pytest.raises(ValidationError, match="repeats"):
        Profile.model_validate({"name": "x", "styles": [rule, rule]})


def test_style_size_is_rounded_to_half_points() -> None:
    """Boyut 0,5 adımına yuvarlanır."""
    assert StyleKey(font="A", size=10.26) == StyleKey(font="A", size=10.5)
