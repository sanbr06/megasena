import random
from dataclasses import dataclass

from app.lotteries.base import LotteryConfig
from app.math_core.portfolio import generate_random_portfolio
from app.math_core.prize_dependency import (
    analyze_prize_dependencies,
    pairwise_prize_intersection_probability,
)


@dataclass(frozen=True)
class PairwiseOptimizationResult:
    games: list[tuple[int, ...]]
    threshold: int
    candidate_pool_size: int
    restarts: int
    pairwise_intersection_sum: float
    second_order_lower_bound: float


def _intersection_cost(
    config,
    threshold,
    left,
    right,
    cache,
):
    overlap = len(set(left).intersection(right))

    if overlap not in cache:
        cache[overlap] = (
            pairwise_prize_intersection_probability(
                config,
                threshold,
                overlap,
            )
        )

    return cache[overlap]


def _greedy_from_start(
    config,
    candidates,
    game_count,
    threshold,
    start_index,
):
    selected = [candidates[start_index]]
    selected_indexes = {start_index}
    cache = {}

    while len(selected) < game_count:
        best_index = None
        best_score = None

        for index, candidate in enumerate(candidates):
            if index in selected_indexes:
                continue

            incremental_cost = sum(
                _intersection_cost(
                    config,
                    threshold,
                    candidate,
                    chosen,
                    cache,
                )
                for chosen in selected
            )

            maximum_overlap = max(
                len(set(candidate).intersection(chosen))
                for chosen in selected
            )

            score = (
                incremental_cost,
                maximum_overlap,
                candidate,
            )

            if best_score is None or score < best_score:
                best_score = score
                best_index = index

        selected.append(candidates[best_index])
        selected_indexes.add(best_index)

    return selected


def optimize_pairwise_prize_dependency(
    config: LotteryConfig,
    game_count: int,
    *,
    threshold=4,
    candidate_pool_size=1_000,
    restarts=20,
    seed=42,
):
    game_count = int(game_count)
    threshold = int(threshold)
    candidate_pool_size = int(candidate_pool_size)
    restarts = int(restarts)

    if game_count <= 0:
        raise ValueError("game_count_must_be_positive")
    if candidate_pool_size < game_count:
        raise ValueError("candidate_pool_must_cover_game_count")
    if restarts <= 0:
        raise ValueError("restarts_must_be_positive")
    if threshold <= 0 or threshold > config.quantity:
        raise ValueError("invalid_threshold")

    candidates = sorted(
        generate_random_portfolio(
            config,
            candidate_pool_size,
            seed=seed,
        )
    )

    rng = random.Random(seed + 9_000_001)
    start_indexes = list(range(candidate_pool_size))
    rng.shuffle(start_indexes)
    start_indexes = start_indexes[: min(restarts, candidate_pool_size)]

    best_games = None
    best_metrics = None

    for start_index in start_indexes:
        games = _greedy_from_start(
            config,
            candidates,
            game_count,
            threshold,
            start_index,
        )
        metrics = analyze_prize_dependencies(
            config,
            games,
            threshold,
        )

        score = (
            metrics.pairwise_intersection_sum,
            -metrics.second_order_lower_bound,
            games,
        )

        if best_metrics is None:
            best_games = games
            best_metrics = metrics
            best_score = score
            continue

        if score < best_score:
            best_games = games
            best_metrics = metrics
            best_score = score

    return PairwiseOptimizationResult(
        games=best_games,
        threshold=threshold,
        candidate_pool_size=candidate_pool_size,
        restarts=len(start_indexes),
        pairwise_intersection_sum=(
            best_metrics.pairwise_intersection_sum
        ),
        second_order_lower_bound=(
            best_metrics.second_order_lower_bound
        ),
    )
