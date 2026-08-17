import random
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from math import comb

from app.lotteries.base import LotteryConfig
from app.math_core.combinatorics import LotterySpace


@dataclass(frozen=True)
class PortfolioMetrics:
    lottery: str
    games: int
    unique_games: int
    duplicate_games: int
    total_outcomes: int
    jackpot_probability: float
    average_pairwise_overlap: float
    maximum_pairwise_overlap: int
    subset_size: int
    covered_subsets: int
    total_subsets: int
    subset_coverage_ratio: float


def _normalize_game(config: LotteryConfig, game):
    return tuple(config.validate_numbers(game))


def generate_random_portfolio(
    config: LotteryConfig,
    game_count: int,
    seed: int | None = None,
):
    game_count = int(game_count)
    if game_count <= 0:
        raise ValueError("game_count_must_be_positive")

    space = LotterySpace.from_config(config)
    if game_count > space.total_outcomes:
        raise ValueError("game_count_exceeds_outcome_space")

    rng = random.Random(seed)
    population = list(range(config.minimum, config.maximum + 1))
    games = set()

    while len(games) < game_count:
        game = tuple(sorted(rng.sample(population, config.quantity)))
        games.add(game)

    return list(games)


def generate_sum_constrained_portfolio(
    config: LotteryConfig,
    game_count: int,
    *,
    minimum_sum: int,
    maximum_sum: int,
    minimum_odd_count: int = 0,
    maximum_odd_count: int | None = None,
    minimum_repeat_count: int = 0,
    maximum_repeat_count: int | None = None,
    reference_numbers=None,
    maximum_pairwise_overlap: int | None = None,
    seed: int | None = None,
):
    """Sample unique games uniformly from combinations satisfying the constraints."""
    game_count = int(game_count)
    if game_count <= 0:
        raise ValueError("game_count_must_be_positive")
    if minimum_sum > maximum_sum:
        raise ValueError("sum_range_is_reversed")
    if maximum_odd_count is None:
        maximum_odd_count = config.quantity
    if minimum_odd_count > maximum_odd_count:
        raise ValueError("odd_count_range_is_reversed")
    if maximum_repeat_count is None:
        maximum_repeat_count = config.quantity
    if minimum_repeat_count > maximum_repeat_count:
        raise ValueError("repeat_count_range_is_reversed")
    reference_set = frozenset(reference_numbers or ())
    if (minimum_repeat_count > 0 or maximum_repeat_count < config.quantity) and not reference_set:
        raise ValueError("repeat_reference_required")
    if maximum_pairwise_overlap is not None:
        maximum_pairwise_overlap = int(maximum_pairwise_overlap)
        if not 0 <= maximum_pairwise_overlap < config.quantity:
            raise ValueError("invalid_maximum_pairwise_overlap")

    @lru_cache(maxsize=None)
    def completion_count(
        next_number,
        remaining,
        remaining_min,
        remaining_max,
        remaining_odd_min,
        remaining_odd_max,
        remaining_repeat_min,
        remaining_repeat_max,
    ):
        if remaining == 0:
            return int(
                remaining_min <= 0 <= remaining_max
                and remaining_odd_min <= 0 <= remaining_odd_max
                and remaining_repeat_min <= 0 <= remaining_repeat_max
            )
        last_start = config.maximum - remaining + 1
        return sum(
            completion_count(
                number + 1,
                remaining - 1,
                remaining_min - number,
                remaining_max - number,
                remaining_odd_min - (number % 2),
                remaining_odd_max - (number % 2),
                remaining_repeat_min - int(number in reference_set),
                remaining_repeat_max - int(number in reference_set),
            )
            for number in range(next_number, last_start + 1)
        )

    eligible = completion_count(
        config.minimum,
        config.quantity,
        minimum_sum,
        maximum_sum,
        minimum_odd_count,
        maximum_odd_count,
        minimum_repeat_count,
        maximum_repeat_count,
    )
    if game_count > eligible:
        raise ValueError("game_count_exceeds_constrained_space")

    rng = random.Random(seed)
    games = set()
    attempts = 0
    max_attempts = min(100_000, max(10_000, game_count * 100))
    while len(games) < game_count:
        attempts += 1
        if attempts > max_attempts:
            raise ValueError("overlap_constraint_unsatisfied")
        game = []
        next_number = config.minimum
        remaining_min = minimum_sum
        remaining_max = maximum_sum
        remaining_odd_min = minimum_odd_count
        remaining_odd_max = maximum_odd_count
        remaining_repeat_min = minimum_repeat_count
        remaining_repeat_max = maximum_repeat_count
        for remaining in range(config.quantity, 0, -1):
            choices = []
            total_weight = 0
            last_start = config.maximum - remaining + 1
            for number in range(next_number, last_start + 1):
                weight = completion_count(
                    number + 1,
                    remaining - 1,
                    remaining_min - number,
                    remaining_max - number,
                    remaining_odd_min - (number % 2),
                    remaining_odd_max - (number % 2),
                    remaining_repeat_min - int(number in reference_set),
                    remaining_repeat_max - int(number in reference_set),
                )
                if weight:
                    choices.append((number, weight))
                    total_weight += weight
            ticket = rng.randrange(total_weight)
            for number, weight in choices:
                if ticket < weight:
                    game.append(number)
                    next_number = number + 1
                    remaining_min -= number
                    remaining_max -= number
                    remaining_odd_min -= number % 2
                    remaining_odd_max -= number % 2
                    remaining_repeat_min -= int(number in reference_set)
                    remaining_repeat_max -= int(number in reference_set)
                    break
                ticket -= weight
        candidate = tuple(game)
        if (
            maximum_pairwise_overlap is not None
            and any(
                len(set(candidate).intersection(existing)) > maximum_pairwise_overlap
                for existing in games
            )
        ):
            continue
        games.add(candidate)

    return list(games)


def analyze_portfolio(
    config: LotteryConfig,
    games,
    subset_size: int = 4,
):
    games = list(games)
    if not games:
        raise ValueError("portfolio_must_not_be_empty")

    subset_size = int(subset_size)
    if subset_size <= 0 or subset_size > config.quantity:
        raise ValueError("invalid_subset_size")

    normalized = [_normalize_game(config, game) for game in games]
    unique = list(dict.fromkeys(normalized))

    overlaps = [
        len(set(left).intersection(right))
        for left, right in combinations(unique, 2)
    ]

    average_overlap = (
        sum(overlaps) / len(overlaps)
        if overlaps
        else 0.0
    )
    maximum_overlap = max(overlaps, default=0)

    covered = {
        subset
        for game in unique
        for subset in combinations(game, subset_size)
    }

    space = LotterySpace.from_config(config)
    total_subsets = comb(space.population_size, subset_size)

    return PortfolioMetrics(
        lottery=config.slug,
        games=len(normalized),
        unique_games=len(unique),
        duplicate_games=len(normalized) - len(unique),
        total_outcomes=space.total_outcomes,
        jackpot_probability=space.jackpot_probability(len(unique)),
        average_pairwise_overlap=average_overlap,
        maximum_pairwise_overlap=maximum_overlap,
        subset_size=subset_size,
        covered_subsets=len(covered),
        total_subsets=total_subsets,
        subset_coverage_ratio=len(covered) / total_subsets,
    )
