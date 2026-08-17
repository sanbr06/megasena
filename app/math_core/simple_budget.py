from dataclasses import asdict, dataclass
from math import comb

from app.lotteries import LOTTERIES
from app.lotteries.catalog import lottery_product_catalog
from app.math_core.portfolio import generate_random_portfolio

MAX_GENERATED_GAMES = 1_000


@dataclass(frozen=True)
class GeneratedSimpleGame:
    numbers: tuple[int, ...]
    extra_selection: dict[str, str] | None


@dataclass(frozen=True)
class SimpleLotteryBudgetPlan:
    lottery: str
    pricing_version: str
    budget_cents: int
    simple_game_cost_cents: int
    games: int
    cost_cents: int
    unspent_cents: int
    total_distinct_combinations: int
    jackpot_probability: float
    seed: int
    generated_games: list[GeneratedSimpleGame]


def plan_simple_lottery_budget(lottery, budget_cents, *, seed=42):
    products = {
        product.slug: product
        for product in lottery_product_catalog()
    }
    if lottery not in products:
        raise ValueError("unknown_lottery")

    budget_cents = int(budget_cents)
    seed = int(seed)
    if budget_cents < 0:
        raise ValueError("budget_must_not_be_negative")

    product = products[lottery]
    config = LOTTERIES[lottery]
    total_combinations = comb(
        config.maximum - config.minimum + 1,
        config.quantity,
    )
    games = min(
        budget_cents // product.simple_game_cost_cents,
        total_combinations,
    )
    if games > MAX_GENERATED_GAMES:
        raise ValueError("generation_limit_exceeded")

    number_games = (
        sorted(generate_random_portfolio(config, games, seed=seed))
        if games
        else []
    )
    generated_games = []
    for index, numbers in enumerate(number_games):
        extra_selection = None
        if product.extra_selection is not None:
            options = product.extra_selection.options
            extra_selection = {
                product.extra_selection.key: options[(seed + index) % len(options)]
            }
        generated_games.append(GeneratedSimpleGame(
            numbers=tuple(numbers),
            extra_selection=extra_selection,
        ))

    cost_cents = games * product.simple_game_cost_cents
    return SimpleLotteryBudgetPlan(
        lottery=lottery,
        pricing_version=product.pricing_version,
        budget_cents=budget_cents,
        simple_game_cost_cents=product.simple_game_cost_cents,
        games=games,
        cost_cents=cost_cents,
        unspent_cents=budget_cents - cost_cents,
        total_distinct_combinations=total_combinations,
        jackpot_probability=games / total_combinations,
        seed=seed,
        generated_games=generated_games,
    )


def simple_budget_plan_as_dict(plan):
    return asdict(plan)
