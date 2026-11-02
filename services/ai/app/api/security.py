"""İç uç noktaların token kontrolü.

Java her isteğe X-Internal-Token başlığını ekler (plan 13.5). Başlık yoksa ya da INTERNAL_TOKEN ile
aynı değilse istek 401 ile reddedilir. Karşılaştırma sabit sürede yapılır.
"""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.constants import INTERNAL_TOKEN_HEADER


async def require_internal_token(
    token: Annotated[str | None, Header(alias=INTERNAL_TOKEN_HEADER)] = None,
) -> None:
    """Başlıktaki token ayardakiyle aynı değilse isteği 401 ile reddeder."""
    expected = get_settings().api.internal_token.get_secret_value()
    if token is None or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
