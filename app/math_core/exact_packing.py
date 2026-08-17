import random
from dataclasses import dataclass
from itertools import combinations
from math import comb

from app.lotteries.base import LotteryConfig
from app.math_core.prize_dependency import (
    pairwise_prize_intersection_probability,
    prize_threshold_probability,
)


@dataclass(frozen=True)
class GlobalOptimalityCertificate:
    lottery: str
    threshold: int
    games: int
    max_pairwise_overlap: int
    pairwise_prize_events_disjoint: bool
    single_ticket_probability: float
    global_upper_bound: float
    achieved_probability: float | None
    optimality_gap: float | None
    is_global_optimum: bool


def _validate_mega_quadraplus(config: LotteryConfig):
    if (
        config.slug != "megasena"
        or config.minimum != 1
        or config.maximum != 60
        or config.quantity != 6
    ):
        raise ValueError(
            "exact_packing_currently_supports_megasena_only"
        )


def _ticket_pairs(game):
    return frozenset(combinations(game, 2))


def _max_pairwise_overlap(games):
    if len(games) < 2:
        return 0

    return max(
        len(set(left).intersection(right))
        for left, right in combinations(games, 2)
    )


def certify_disjoint_prize_optimum(
    config: LotteryConfig,
    games,
    *,
    threshold: int,
):
    normalized = [
        tuple(config.validate_numbers(game))
        for game in games
    ]

    if not normalized:
        raise ValueError("portfolio_must_not_be_empty")

    if len(set(normalized)) != len(normalized):
        raise ValueError("portfolio_must_contain_unique_games")

    max_overlap = _max_pairwise_overlap(normalized)
    threshold = int(threshold)

    single_probability = prize_threshold_probability(
        config,
        threshold=threshold,
    )
    disjoint = all(
        pairwise_prize_intersection_probability(
            config,
            threshold,
            len(set(left).intersection(right)),
        ) == 0
        for left, right in combinations(normalized, 2)
    )
    upper_bound = min(
        1.0,
        len(normalized) * single_probability,
    )

    achieved = upper_bound if disjoint else None
    gap = 0.0 if disjoint else None

    return GlobalOptimalityCertificate(
        lottery=config.slug,
        threshold=threshold,
        games=len(normalized),
        max_pairwise_overlap=max_overlap,
        pairwise_prize_events_disjoint=disjoint,
        single_ticket_probability=single_probability,
        global_upper_bound=upper_bound,
        achieved_probability=achieved,
        optimality_gap=gap,
        is_global_optimum=disjoint,
    )


def certify_megasena_quadraplus_optimum(
    config: LotteryConfig,
    games,
):
    _validate_mega_quadraplus(config)
    return certify_disjoint_prize_optimum(
        config,
        games,
        threshold=4,
    )


def generate_megasena_quadraplus_optimal_packing(
    config: LotteryConfig,
    game_count: int,
    *,
    seed=42,
    max_attempts_per_game=200_000,
):
    _validate_mega_quadraplus(config)

    game_count = int(game_count)
    max_attempts_per_game = int(max_attempts_per_game)

    if game_count <= 0:
        raise ValueError("game_count_must_be_positive")
    if max_attempts_per_game <= 0:
        raise ValueError("max_attempts_must_be_positive")

    # Every 6-number ticket consumes C(6,2)=15 unique number-pairs.
    # If no number-pair is reused, two tickets can share at most
    # one number. C(60,2)/C(6,2)=118 is therefore an elementary
    # packing upper bound. It is a bound, not an existence claim.
    packing_upper_bound = comb(60, 2) // comb(6, 2)

    if game_count > packing_upper_bound:
        raise ValueError("game_count_exceeds_pair_packing_bound")

    rng = random.Random(seed)
    population = list(range(1, 61))

    selected = []
    used_pairs = set()

    while len(selected) < game_count:
        chosen = None

        for _ in range(max_attempts_per_game):
            candidate = tuple(
                sorted(rng.sample(population, 6))
            )
            candidate_pairs = _ticket_pairs(candidate)

            if candidate_pairs.isdisjoint(used_pairs):
                chosen = candidate
                used_pairs.update(candidate_pairs)
                break

        if chosen is None:
            raise RuntimeError(
                "unable_to_extend_pair_packing_with_current_seed"
            )

        selected.append(chosen)

    certificate = certify_megasena_quadraplus_optimum(
        config,
        selected,
    )

    if not certificate.is_global_optimum:
        raise RuntimeError("generated_portfolio_failed_certificate")

    return selected
