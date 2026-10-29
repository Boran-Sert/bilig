"""Model fiyatlarının okunmasını ve çağrı maliyeti hesabını test eder."""

from decimal import Decimal

from app.constants import LLM_PRICING_PATH, LLM_TASKS_PATH
from app.llm.pricing import PriceTier, calculate_cost, load_prices
from app.llm.tasks import load_task_configs

CHEAP = PriceTier(
    up_to_prompt_tokens=100,
    input=Decimal("1"),
    cache_write=Decimal("1.25"),
    cache_read=Decimal("0.1"),
    output=Decimal("5"),
)
EXPENSIVE = PriceTier(
    input=Decimal("2"),
    cache_write=Decimal("2.50"),
    cache_read=Decimal("0.10"),
    output=Decimal("10"),
)


def test_every_task_model_has_a_price() -> None:
    """llm_tasks.yaml'daki her modelin llm_pricing.yaml'da fiyatı vardır."""
    prices = load_prices(LLM_PRICING_PATH)

    models = {config.model for config in load_task_configs(LLM_TASKS_PATH).values()}

    assert models <= prices.keys()


def test_cost_adds_every_token_type() -> None:
    """Giriş, çıkış, önbellekten okuma ve önbelleğe yazma kendi fiyatıyla toplanır."""
    cost = calculate_cost(
        [EXPENSIVE],
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=2000,
        cache_write_tokens=400,
    )

    assert cost == Decimal("0.0082")


def test_tier_is_chosen_by_whole_prompt_length() -> None:
    """Önbellekli token'lar da istem uzunluğuna sayılır; sınır dahil alt kademede kalır."""
    at_limit = calculate_cost(
        [CHEAP, EXPENSIVE],
        input_tokens=50,
        output_tokens=0,
        cache_read_tokens=50,
        cache_write_tokens=0,
    )
    over_limit = calculate_cost(
        [CHEAP, EXPENSIVE],
        input_tokens=50,
        output_tokens=0,
        cache_read_tokens=50,
        cache_write_tokens=1,
    )

    assert at_limit == Decimal("0.000055")
    assert over_limit == Decimal("0.0001075")
