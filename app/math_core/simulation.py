from dataclasses import dataclass
from math import sqrt

import numpy as np

from app.lotteries.base import LotteryConfig


@dataclass(frozen=True)
class ConfidenceInterval:
    lower: float
    upper: float
    confidence: float = 0.95


@dataclass(frozen=True)
class SimulationResult:
    lottery: str
    trials: int
    seed: int
    games: int
    max_hit_counts: dict[int, int]

    @property
    def max_hit_probabilities(self):
        return {
            hits: count / self.trials
            for hits, count in self.max_hit_counts.items()
        }

    @property
    def mean_best_hits(self):
        return (
            sum(
                hits * count
                for hits, count in self.max_hit_counts.items()
            )
            / self.trials
        )

    def probability_at_least(self, hits):
        hits = int(hits)
        successes = sum(
            count
            for hit_count, count in self.max_hit_counts.items()
            if hit_count >= hits
        )
        return successes / self.trials

    def confidence_interval_at_least(self, hits, z=1.959963984540054):
        hits = int(hits)
        successes = sum(
            count
            for hit_count, count in self.max_hit_counts.items()
            if hit_count >= hits
        )
        return _wilson_interval(successes, self.trials, z=z)


def _wilson_interval(successes, trials, z=1.959963984540054):
    if trials <= 0:
        raise ValueError("trials_must_be_positive")

    proportion = successes / trials
    z2 = z * z
    denominator = 1 + z2 / trials

    center = (
        proportion + z2 / (2 * trials)
    ) / denominator

    margin = (
        z
        * sqrt(
            (proportion * (1 - proportion) / trials)
            + (z2 / (4 * trials * trials))
        )
        / denominator
    )

    return ConfidenceInterval(
        lower=max(0.0, center - margin),
        upper=min(1.0, center + margin),
    )


def _game_matrix(config: LotteryConfig, games):
    games = list(games)
    if not games:
        raise ValueError("portfolio_must_not_be_empty")

    matrix = np.zeros(
        (len(games), config.maximum - config.minimum + 1),
        dtype=np.uint8,
    )

    for row, game in enumerate(games):
        numbers = config.validate_numbers(game)
        indexes = np.asarray(numbers) - config.minimum
        matrix[row, indexes] = 1

    return matrix


def simulate_portfolio(
    config: LotteryConfig,
    games,
    trials=100_000,
    seed=42,
    chunk_size=50_000,
):
    trials = int(trials)
    chunk_size = int(chunk_size)

    if trials <= 0:
        raise ValueError("trials_must_be_positive")
    if chunk_size <= 0:
        raise ValueError("chunk_size_must_be_positive")

    game_matrix = _game_matrix(config, games)
    rng = np.random.default_rng(seed)

    population_size = config.maximum - config.minimum + 1
    counts = np.zeros(config.quantity + 1, dtype=np.int64)

    completed = 0
    while completed < trials:
        current = min(chunk_size, trials - completed)

        random_values = rng.random(
            (current, population_size),
            dtype=np.float64,
        )

        draw_indexes = np.argpartition(
            random_values,
            config.quantity - 1,
            axis=1,
        )[:, : config.quantity]

        draw_matrix = np.zeros(
            (current, population_size),
            dtype=np.uint8,
        )
        rows = np.arange(current)[:, None]
        draw_matrix[rows, draw_indexes] = 1

        hits = draw_matrix @ game_matrix.T
        best_hits = hits.max(axis=1)

        counts += np.bincount(
            best_hits,
            minlength=config.quantity + 1,
        )[: config.quantity + 1]

        completed += current

    return SimulationResult(
        lottery=config.slug,
        trials=trials,
        seed=int(seed),
        games=game_matrix.shape[0],
        max_hit_counts={
            hits: int(count)
            for hits, count in enumerate(counts)
        },
    )
