import random
from dataclasses import dataclass
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
