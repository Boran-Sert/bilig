"""Claude modellerinin llm_pricing.yaml'daki token fiyatları ve çağrı maliyeti hesabı.

Anthropic yanıtta maliyet vermez, sadece token sayılarını verir; maliyet token sayılarıyla
fiyatların çarpımıdır. Fiyatlar milyon token başına dolardır ve sadece llm_pricing.yaml'da yazılır.
Bir modelin birden çok kademesi olabilir (Haiku 5.5'te 100.000 token üstü istem daha pahalıdır);
kademe istemin bütün giriş token'larıyla seçilir.
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, TypeAdapter

from app.constants import LLM_PRICING_PATH, TOKENS_PER_PRICE_UNIT


class PriceTier(BaseModel):
    """İstem uzunluğu sınırına kadar geçerli, milyon token başına dolar fiyatları."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    up_to_prompt_tokens: int | None = None
    input: Decimal
    cache_write: Decimal
    cache_read: Decimal
    output: Decimal


_PRICES = TypeAdapter(dict[str, list[PriceTier]])


def load_prices(path: Path) -> dict[str, list[PriceTier]]:
    """Model başına fiyat kademelerini okur."""
    return _PRICES.validate_python(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def get_prices() -> dict[str, list[PriceTier]]:
    """Fiyatları bir kez okuyup süreç boyunca aynı sözlüğü döner."""
    return load_prices(LLM_PRICING_PATH)


def calculate_cost(
    tiers: list[PriceTier],
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_write_tokens: int,
) -> Decimal:
    """Token sayılarını istem uzunluğuna uyan kademenin fiyatlarıyla dolara çevirir."""
    prompt_tokens = input_tokens + cache_read_tokens + cache_write_tokens
    tier = next(
        (
            tier
            for tier in tiers
            if tier.up_to_prompt_tokens is None or prompt_tokens <= tier.up_to_prompt_tokens
        ),
        None,
    )
    if tier is None:
        raise ValueError(f"No price tier for a prompt of {prompt_tokens} tokens")
    total = (
        input_tokens * tier.input
        + output_tokens * tier.output
        + cache_read_tokens * tier.cache_read
        + cache_write_tokens * tier.cache_write
    )
    return total / TOKENS_PER_PRICE_UNIT
