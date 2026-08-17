import random
from itertools import combinations

from app.lotteries.base import LotteryConfig
from app.math_core.combinatorics import LotterySpace


def _candidate_subsets(game, subset_size):
    return set(combinations(game, subset_size))


def _overlap_score(candidate, selected):
    if not selected:
        return 0, 0

    overlaps = [
        len(set(candidate).intersection(game))
        for game in selected
    ]
    return max(overlaps), sum(value * value for value in overlaps)


def generate_low_redundancy_portfolio(
    config: LotteryConfig,
    game_count: int,
    seed: int | None = None,
    subset_size: int = 4,
    candidate_pool_size: int = 750,
):
    game_count = int(game_count)
    subset_size = int(subset_size)
    candidate_pool_size = int(candidate_pool_size)

    if game_count <= 0:
        raise ValueError("game_count_must_be_positive")
    if subset_size <= 0 or subset_size > config.quantity:
        raise ValueError("invalid_subset_size")
    if candidate_pool_size <= 0:
        raise ValueError("candidate_pool_size_must_be_positive")

    space = LotterySpace.from_config(config)
    if game_count > space.total_outcomes:
        raise ValueError("game_count_exceeds_outcome_space")

    rng = random.Random(seed)
    population = list(range(config.minimum, config.maximum + 1))

    selected = []
    selected_set = set()
    covered_subsets = set()

    while len(selected) < game_count:
        candidates = set()

        attempts = 0
        max_attempts = candidate_pool_size * 20

        while (
            len(candidates) < candidate_pool_size
            and attempts < max_attempts
        ):
            candidate = tuple(
                sorted(rng.sample(population, config.quantity))
            )
            attempts += 1

            if candidate not in selected_set:
                candidates.add(candidate)

        if not candidates:
            raise RuntimeError("unable_to_generate_candidate")

        best_candidate = None
        best_score = None

        for candidate in candidates:
            subsets = _candidate_subsets(candidate, subset_size)
            subset_gain = len(subsets - covered_subsets)
            max_overlap, squared_overlap = _overlap_score(
                candidate,
                selected,
            )

            # Lexicographic objective:
            # 1. maximize new combinatorial coverage;
            # 2. minimize worst pairwise overlap;
            # 3. minimize concentrated overlap across the portfolio;
            # 4. deterministic numeric tie-break.
            score = (
                subset_gain,
                -max_overlap,
                -squared_overlap,
                tuple(-number for number in candidate),
            )

            if best_score is None or score > best_score:
                best_score = score
                best_candidate = candidate

        selected.append(best_candidate)
        selected_set.add(best_candidate)
        covered_subsets.update(
            _candidate_subsets(best_candidate, subset_size)
        )

    return selected
