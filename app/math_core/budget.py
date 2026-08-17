from dataclasses import asdict, dataclass
from math import comb

from app.lotteries import LOTTERIES
from app.math_core.exact_packing import (
    certify_megasena_quadraplus_optimum,
    generate_megasena_quadraplus_optimal_packing,
)
from app.math_core.prize_dependency import (
    prize_threshold_probability,
)

MEGASENA_PRICING_VERSION = "caixa-2026-08-17"
MEGASENA_PRICING_SOURCE = (
    "https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx"
)
MEGASENA_SIMPLE_GAME_COST_CENTS = 600
MEGASENA_MIN_MARKED_NUMBERS = 6
MEGASENA_MAX_MARKED_NUMBERS = 20
MEGASENA_TOTAL_OUTCOMES = comb(60, 6)


@dataclass(frozen=True)
class MegaSenaBetProfile:
    marked_numbers: int
    simple_equivalents: int
    cost_cents: int
    jackpot_probability: float
    quadra_plus_probability: float
    quadra_plus_disjoint_upper_bound: float
    quadra_plus_efficiency_vs_disjoint_bound: float


@dataclass(frozen=True)
class SimpleBudgetPlan:
    budget_cents: int
    simple_game_cost_cents: int
    games: int
    cost_cents: int
    unspent_cents: int
    jackpot_probability: float
    quadra_plus_disjoint_upper_bound: float
    certified_quadra_plus_probability: float | None
    globally_optimal_quadra_plus: bool
    max_pairwise_overlap: int | None
    generated_games: list[tuple[int, ...]] | None


@dataclass(frozen=True)
class BudgetPlannerResult:
    pricing_version: str
    pricing_source: str
    budget_cents: int
    simple_plan: SimpleBudgetPlan
    affordable_single_system_bets: list[MegaSenaBetProfile]


def _validate_marked_numbers(marked_numbers):
    marked_numbers = int(marked_numbers)

    if not (
        MEGASENA_MIN_MARKED_NUMBERS
        <= marked_numbers
        <= MEGASENA_MAX_MARKED_NUMBERS
    ):
        raise ValueError("invalid_marked_numbers")

    return marked_numbers


def megasena_system_bet_cost_cents(marked_numbers):
    marked_numbers = _validate_marked_numbers(marked_numbers)

    return (
        comb(marked_numbers, 6)
        * MEGASENA_SIMPLE_GAME_COST_CENTS
    )


def megasena_at_least_hits_probability(
    marked_numbers,
    threshold,
):
    marked_numbers = _validate_marked_numbers(marked_numbers)
    threshold = int(threshold)

    if threshold <= 0 or threshold > 6:
        raise ValueError("invalid_threshold")

    favorable = sum(
        comb(marked_numbers, hits)
        * comb(60 - marked_numbers, 6 - hits)
        for hits in range(threshold, 7)
        if hits <= marked_numbers
        and 0 <= 6 - hits <= 60 - marked_numbers
    )

    return favorable / MEGASENA_TOTAL_OUTCOMES


def profile_megasena_system_bet(marked_numbers):
    marked_numbers = _validate_marked_numbers(marked_numbers)

    simple_equivalents = comb(marked_numbers, 6)
    cost_cents = megasena_system_bet_cost_cents(
        marked_numbers
    )

    jackpot_probability = (
        simple_equivalents / MEGASENA_TOTAL_OUTCOMES
    )

    quadra_plus_probability = (
        megasena_at_least_hits_probability(
            marked_numbers,
            threshold=4,
        )
    )

    single_quadra_plus = prize_threshold_probability(
        LOTTERIES["megasena"],
        threshold=4,
    )

    disjoint_upper_bound = min(
        1.0,
        simple_equivalents * single_quadra_plus,
    )

    efficiency = (
        quadra_plus_probability / disjoint_upper_bound
        if disjoint_upper_bound
        else 0.0
    )

    return MegaSenaBetProfile(
        marked_numbers=marked_numbers,
        simple_equivalents=simple_equivalents,
        cost_cents=cost_cents,
        jackpot_probability=jackpot_probability,
        quadra_plus_probability=quadra_plus_probability,
        quadra_plus_disjoint_upper_bound=(
            disjoint_upper_bound
        ),
        quadra_plus_efficiency_vs_disjoint_bound=efficiency,
    )


def plan_megasena_budget(
    budget_cents,
    *,
    seed=42,
    certificate_game_limit=20,
):
    budget_cents = int(budget_cents)
    certificate_game_limit = int(certificate_game_limit)

    if budget_cents < 0:
        raise ValueError("budget_must_not_be_negative")
    if certificate_game_limit < 0:
        raise ValueError("certificate_limit_must_not_be_negative")

    config = LOTTERIES["megasena"]

    games = (
        budget_cents // MEGASENA_SIMPLE_GAME_COST_CENTS
    )
    cost_cents = (
        games * MEGASENA_SIMPLE_GAME_COST_CENTS
    )
    unspent_cents = budget_cents - cost_cents

    jackpot_probability = (
        games / MEGASENA_TOTAL_OUTCOMES
    )

    single_quadra_plus = prize_threshold_probability(
        config,
        threshold=4,
    )
    disjoint_upper_bound = min(
        1.0,
        games * single_quadra_plus,
    )

    generated_games = None
    certified_probability = None
    globally_optimal = False
    max_pairwise_overlap = None

    if 0 < games <= certificate_game_limit:
        generated_games = (
            generate_megasena_quadraplus_optimal_packing(
                config,
                games,
                seed=seed,
            )
        )

        certificate = (
            certify_megasena_quadraplus_optimum(
                config,
                generated_games,
            )
        )

        certified_probability = (
            certificate.achieved_probability
        )
        globally_optimal = certificate.is_global_optimum
        max_pairwise_overlap = (
            certificate.max_pairwise_overlap
        )

    simple_plan = SimpleBudgetPlan(
        budget_cents=budget_cents,
        simple_game_cost_cents=(
            MEGASENA_SIMPLE_GAME_COST_CENTS
        ),
        games=games,
        cost_cents=cost_cents,
        unspent_cents=unspent_cents,
        jackpot_probability=jackpot_probability,
        quadra_plus_disjoint_upper_bound=(
            disjoint_upper_bound
        ),
        certified_quadra_plus_probability=(
            certified_probability
        ),
        globally_optimal_quadra_plus=globally_optimal,
        max_pairwise_overlap=max_pairwise_overlap,
        generated_games=generated_games,
    )

    affordable = [
        profile_megasena_system_bet(marked_numbers)
        for marked_numbers in range(
            MEGASENA_MIN_MARKED_NUMBERS,
            MEGASENA_MAX_MARKED_NUMBERS + 1,
        )
        if megasena_system_bet_cost_cents(marked_numbers)
        <= budget_cents
    ]

    return BudgetPlannerResult(
        pricing_version=MEGASENA_PRICING_VERSION,
        pricing_source=MEGASENA_PRICING_SOURCE,
        budget_cents=budget_cents,
        simple_plan=simple_plan,
        affordable_single_system_bets=affordable,
    )


def budget_result_as_dict(result):
    return asdict(result)
