from dataclasses import asdict, dataclass
from math import comb

from app.lotteries import LOTTERIES
from app.lotteries.catalog import lottery_product_catalog
from app.math_core.portfolio import (
    generate_random_portfolio,
    generate_sum_constrained_portfolio,
)

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
    generation_constraints: dict[str, int] | None
    constraint_disclaimer: str | None


def plan_simple_lottery_budget(
    lottery,
    budget_cents,
    *,
    seed=42,
    allowed_sum_min=None,
    allowed_sum_max=None,
    allowed_odd_min=None,
    allowed_odd_max=None,
    allowed_repeat_min=None,
    allowed_repeat_max=None,
    reference_numbers=None,
    allowed_max_overlap=None,
):
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

    constraints = None
    disclaimer = None
    if any(value is not None for value in (
        allowed_sum_min, allowed_sum_max, allowed_odd_min, allowed_odd_max,
        allowed_repeat_min, allowed_repeat_max, allowed_max_overlap,
    )):
        natural_min = sum(range(config.minimum, config.minimum + config.quantity))
        natural_max = sum(range(config.maximum - config.quantity + 1, config.maximum + 1))
        minimum_sum = natural_min if allowed_sum_min is None else int(allowed_sum_min)
        maximum_sum = natural_max if allowed_sum_max is None else int(allowed_sum_max)
        minimum_odd = 0 if allowed_odd_min is None else int(allowed_odd_min)
        maximum_odd = config.quantity if allowed_odd_max is None else int(allowed_odd_max)
        minimum_repeat = 0 if allowed_repeat_min is None else int(allowed_repeat_min)
        maximum_repeat = (
            config.quantity if allowed_repeat_max is None else int(allowed_repeat_max)
        )
        maximum_overlap = (
            None if allowed_max_overlap is None else int(allowed_max_overlap)
        )
        constraints = {}
        if allowed_sum_min is not None or allowed_sum_max is not None:
            constraints.update({
                "allowed_sum_min": minimum_sum,
                "allowed_sum_max": maximum_sum,
            })
        if allowed_odd_min is not None or allowed_odd_max is not None:
            constraints.update({
                "allowed_odd_min": minimum_odd,
                "allowed_odd_max": maximum_odd,
            })
        if allowed_repeat_min is not None or allowed_repeat_max is not None:
            constraints.update({
                "allowed_repeat_min": minimum_repeat,
                "allowed_repeat_max": maximum_repeat,
            })
        if allowed_max_overlap is not None:
            constraints["allowed_max_overlap"] = maximum_overlap
        disclaimer = (
            "A aplicação dessas restrições de composição não prevê resultados nem aumenta "
            "a probabilidade futura."
        )
        number_games = sorted(generate_sum_constrained_portfolio(
            config,
            games,
            minimum_sum=minimum_sum,
            maximum_sum=maximum_sum,
            minimum_odd_count=minimum_odd,
            maximum_odd_count=maximum_odd,
            minimum_repeat_count=minimum_repeat,
            maximum_repeat_count=maximum_repeat,
            reference_numbers=reference_numbers,
            maximum_pairwise_overlap=maximum_overlap,
            seed=seed,
        )) if games else []
    else:
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
        generation_constraints=constraints,
        constraint_disclaimer=disclaimer,
    )


def simple_budget_plan_as_dict(plan):
    return asdict(plan)
