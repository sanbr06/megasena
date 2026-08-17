from dataclasses import dataclass
from itertools import combinations
from math import comb

from app.lotteries.base import LotteryConfig
from app.math_core.combinatorics import LotterySpace


def _comb_or_zero(n, k):
    if k < 0 or k > n:
        return 0
    return comb(n, k)


def prize_threshold_probability(
    config: LotteryConfig,
    threshold: int,
):
    threshold = int(threshold)

    if threshold <= 0 or threshold > config.quantity:
        raise ValueError("invalid_threshold")

    space = LotterySpace.from_config(config)

    return sum(
        space.exact_hits_probability(hits)
        for hits in range(threshold, config.quantity + 1)
    )


def pairwise_prize_intersection_probability(
    config: LotteryConfig,
    threshold: int,
    overlap: int,
):
    threshold = int(threshold)
    overlap = int(overlap)

    draw_size = config.quantity
    population_size = config.maximum - config.minimum + 1

    if threshold <= 0 or threshold > draw_size:
        raise ValueError("invalid_threshold")
    if overlap < 0 or overlap > draw_size:
        raise ValueError("invalid_overlap")

    shared_size = overlap
    left_only_size = draw_size - overlap
    right_only_size = draw_size - overlap
    outside_size = population_size - (2 * draw_size - overlap)

    favorable = 0

    for shared_hits in range(shared_size + 1):
        for left_hits in range(left_only_size + 1):
            for right_hits in range(right_only_size + 1):
                outside_hits = (
                    draw_size
                    - shared_hits
                    - left_hits
                    - right_hits
                )

                if outside_hits < 0:
                    continue

                if shared_hits + left_hits < threshold:
                    continue
                if shared_hits + right_hits < threshold:
                    continue

                favorable += (
                    _comb_or_zero(shared_size, shared_hits)
                    * _comb_or_zero(left_only_size, left_hits)
                    * _comb_or_zero(right_only_size, right_hits)
                    * _comb_or_zero(outside_size, outside_hits)
                )

    return favorable / comb(population_size, draw_size)


@dataclass(frozen=True)
class BonferroniMetrics:
    lottery: str
    threshold: int
    games: int
    single_ticket_probability: float
    first_order_sum: float
    pairwise_intersection_sum: float
    second_order_raw: float
    second_order_lower_bound: float
    average_pairwise_intersection: float
    maximum_pairwise_intersection: float


def analyze_prize_dependencies(
    config: LotteryConfig,
    games,
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

    threshold = int(threshold)
    single_probability = prize_threshold_probability(
        config,
        threshold,
    )

    intersection_probabilities = []

    for left, right in combinations(normalized, 2):
        overlap = len(set(left).intersection(right))
        intersection_probabilities.append(
            pairwise_prize_intersection_probability(
                config,
                threshold,
                overlap,
            )
        )

    first_order_sum = len(normalized) * single_probability
    pairwise_sum = sum(intersection_probabilities)
    second_order_raw = first_order_sum - pairwise_sum

    return BonferroniMetrics(
        lottery=config.slug,
        threshold=threshold,
        games=len(normalized),
        single_ticket_probability=single_probability,
        first_order_sum=first_order_sum,
        pairwise_intersection_sum=pairwise_sum,
        second_order_raw=second_order_raw,
        second_order_lower_bound=max(0.0, second_order_raw),
        average_pairwise_intersection=(
            pairwise_sum / len(intersection_probabilities)
            if intersection_probabilities
            else 0.0
        ),
        maximum_pairwise_intersection=max(
            intersection_probabilities,
            default=0.0,
        ),
    )
