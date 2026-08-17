from dataclasses import dataclass

import numpy as np

from app.lotteries.base import LotteryConfig
from app.math_core.portfolio import generate_random_portfolio


@dataclass(frozen=True)
class ScenarioOptimizationResult:
    games: list[tuple[int, ...]]
    candidate_count: int
    training_scenarios: int
    threshold: int
    covered_training_scenarios: int
    training_coverage_ratio: float


def _draw_matrix(
    config: LotteryConfig,
    scenarios: int,
    seed: int,
):
    if scenarios <= 0:
        raise ValueError("scenarios_must_be_positive")

    rng = np.random.default_rng(seed)
    population_size = config.maximum - config.minimum + 1

    random_values = rng.random(
        (scenarios, population_size),
        dtype=np.float64,
    )
    draw_indexes = np.argpartition(
        random_values,
        config.quantity - 1,
        axis=1,
    )[:, : config.quantity]

    matrix = np.zeros(
        (scenarios, population_size),
        dtype=np.uint8,
    )
    rows = np.arange(scenarios)[:, None]
    matrix[rows, draw_indexes] = 1

    return matrix


def _candidate_matrix(config, candidates):
    matrix = np.zeros(
        (
            len(candidates),
            config.maximum - config.minimum + 1,
        ),
        dtype=np.uint8,
    )

    for row, game in enumerate(candidates):
        numbers = config.validate_numbers(game)
        indexes = np.asarray(numbers) - config.minimum
        matrix[row, indexes] = 1

    return matrix


def _mask_to_int(mask):
    packed = np.packbits(mask, bitorder="little")
    return int.from_bytes(packed.tobytes(), "little")


def _pairwise_overlap_penalty(candidate, selected):
    if not selected:
        return 0

    candidate_set = set(candidate)
    return sum(
        len(candidate_set.intersection(game)) ** 2
        for game in selected
    )


def optimize_scenario_coverage(
    config: LotteryConfig,
    game_count: int,
    *,
    candidate_count=1_000,
    training_scenarios=50_000,
    threshold=4,
    seed=42,
):
    game_count = int(game_count)
    candidate_count = int(candidate_count)
    training_scenarios = int(training_scenarios)
    threshold = int(threshold)

    if game_count <= 0:
        raise ValueError("game_count_must_be_positive")
    if candidate_count < game_count:
        raise ValueError("candidate_count_must_cover_game_count")
    if training_scenarios <= 0:
        raise ValueError("training_scenarios_must_be_positive")
    if threshold <= 0 or threshold > config.quantity:
        raise ValueError("invalid_threshold")

    candidates = generate_random_portfolio(
        config,
        candidate_count,
        seed=seed,
    )

    scenarios = _draw_matrix(
        config,
        training_scenarios,
        seed=seed + 1_000_003,
    )
    candidate_matrix = _candidate_matrix(config, candidates)

    hits = scenarios @ candidate_matrix.T
    coverage_bitsets = [
        _mask_to_int(hits[:, index] >= threshold)
        for index in range(candidate_count)
    ]

    selected_indexes = []
    selected_games = []
    remaining = set(range(candidate_count))
    covered = 0

    for _ in range(game_count):
        best_index = None
        best_score = None

        for index in remaining:
            new_coverage = (
                coverage_bitsets[index] & ~covered
            ).bit_count()

            overlap_penalty = _pairwise_overlap_penalty(
                candidates[index],
                selected_games,
            )

            score = (
                new_coverage,
                -overlap_penalty,
                tuple(-number for number in candidates[index]),
            )

            if best_score is None or score > best_score:
                best_score = score
                best_index = index

        selected_indexes.append(best_index)
        selected_games.append(candidates[best_index])
        covered |= coverage_bitsets[best_index]
        remaining.remove(best_index)

    covered_count = covered.bit_count()

    return ScenarioOptimizationResult(
        games=selected_games,
        candidate_count=candidate_count,
        training_scenarios=training_scenarios,
        threshold=threshold,
        covered_training_scenarios=covered_count,
        training_coverage_ratio=(
            covered_count / training_scenarios
        ),
    )
