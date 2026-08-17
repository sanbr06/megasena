import random
from dataclasses import dataclass
from math import comb

from app.lotteries.base import LotteryConfig

BACKTEST_VERSION = "walk-forward/v1"
FREQUENCY_STRATEGY_VERSION = "frequency-history/v1"
RANDOM_BASELINE_VERSION = "uniform-random/v1"


@dataclass(frozen=True)
class WalkForwardFold:
    contest: int
    training_start_contest: int
    training_end_contest: int
    training_draws: int
    challenger_game: tuple[int, ...]
    baseline_game: tuple[int, ...]
    challenger_hits: int
    baseline_hits: int


@dataclass(frozen=True)
class WalkForwardBacktest:
    version: str
    lottery: str
    seed: int
    threshold: int
    minimum_training_draws: int
    challenger_strategy: str
    baseline_strategy: str
    folds: tuple[WalkForwardFold, ...]
    challenger_observed_success_rate: float
    baseline_observed_success_rate: float
    observed_success_rate_difference: float
    challenger_mean_hits: float
    baseline_mean_hits: float
    challenger_observed_jackpot_rate: float
    baseline_observed_jackpot_rate: float
    challenger_only_successes: int
    baseline_only_successes: int
    paired_one_sided_p_value: float
    significance_level: float
    evidence_of_advantage: bool
    conclusion: str


def _normalize_draws(config, draws):
    normalized = []
    seen_contests = set()
    for draw in draws:
        try:
            contest = int(draw["contest"])
            numbers = tuple(config.validate_numbers(draw["numbers"]))
        except (KeyError, TypeError) as exc:
            raise ValueError("invalid_historical_draw") from exc
        if contest in seen_contests:
            raise ValueError("duplicate_contest")
        seen_contests.add(contest)
        normalized.append((contest, numbers))
    return sorted(normalized)


def _frequency_game(config, training_draws):
    counts = {number: 0 for number in range(config.minimum, config.maximum + 1)}
    for _, numbers in training_draws:
        for number in numbers:
            counts[number] += 1
    ranked = sorted(counts, key=lambda number: (-counts[number], number))
    return tuple(sorted(ranked[:config.quantity]))


def _one_sided_p_value(challenger_only, baseline_only):
    discordant = challenger_only + baseline_only
    if discordant == 0:
        return 1.0
    return sum(
        comb(discordant, successes)
        for successes in range(challenger_only, discordant + 1)
    ) / (2 ** discordant)


def walk_forward_frequency_backtest(
    config: LotteryConfig,
    draws,
    *,
    minimum_training_draws=20,
    threshold=4,
    seed=42,
    significance_level=0.05,
):
    """Evaluate a history-only frequency heuristic against random, fold by fold."""
    minimum_training_draws = int(minimum_training_draws)
    threshold = int(threshold)
    significance_level = float(significance_level)
    if minimum_training_draws <= 0:
        raise ValueError("minimum_training_draws_must_be_positive")
    if threshold <= 0 or threshold > config.quantity:
        raise ValueError("invalid_threshold")
    if not 0 < significance_level < 1:
        raise ValueError("invalid_significance_level")

    ordered = _normalize_draws(config, draws)
    if len(ordered) <= minimum_training_draws:
        raise ValueError("insufficient_historical_draws")

    rng = random.Random(seed)
    population = list(range(config.minimum, config.maximum + 1))
    folds = []
    for index in range(minimum_training_draws, len(ordered)):
        training = ordered[:index]
        contest, actual_numbers = ordered[index]
        challenger = _frequency_game(config, training)
        baseline = tuple(sorted(rng.sample(population, config.quantity)))
        actual = set(actual_numbers)
        folds.append(WalkForwardFold(
            contest=contest,
            training_start_contest=training[0][0],
            training_end_contest=training[-1][0],
            training_draws=len(training),
            challenger_game=challenger,
            baseline_game=baseline,
            challenger_hits=len(actual.intersection(challenger)),
            baseline_hits=len(actual.intersection(baseline)),
        ))

    challenger_successes = sum(fold.challenger_hits >= threshold for fold in folds)
    baseline_successes = sum(fold.baseline_hits >= threshold for fold in folds)
    challenger_only = sum(
        fold.challenger_hits >= threshold and fold.baseline_hits < threshold
        for fold in folds
    )
    baseline_only = sum(
        fold.baseline_hits >= threshold and fold.challenger_hits < threshold
        for fold in folds
    )
    p_value = _one_sided_p_value(challenger_only, baseline_only)
    fold_count = len(folds)
    challenger_rate = challenger_successes / fold_count
    baseline_rate = baseline_successes / fold_count
    evidence = challenger_only > baseline_only and p_value < significance_level

    return WalkForwardBacktest(
        version=BACKTEST_VERSION,
        lottery=config.slug,
        seed=int(seed),
        threshold=threshold,
        minimum_training_draws=minimum_training_draws,
        challenger_strategy=FREQUENCY_STRATEGY_VERSION,
        baseline_strategy=RANDOM_BASELINE_VERSION,
        folds=tuple(folds),
        challenger_observed_success_rate=challenger_rate,
        baseline_observed_success_rate=baseline_rate,
        observed_success_rate_difference=challenger_rate - baseline_rate,
        challenger_mean_hits=sum(fold.challenger_hits for fold in folds) / fold_count,
        baseline_mean_hits=sum(fold.baseline_hits for fold in folds) / fold_count,
        challenger_observed_jackpot_rate=(
            sum(fold.challenger_hits == config.quantity for fold in folds) / fold_count
        ),
        baseline_observed_jackpot_rate=(
            sum(fold.baseline_hits == config.quantity for fold in folds) / fold_count
        ),
        challenger_only_successes=challenger_only,
        baseline_only_successes=baseline_only,
        paired_one_sided_p_value=p_value,
        significance_level=significance_level,
        evidence_of_advantage=evidence,
        conclusion=(
            "evidence_of_historical_advantage"
            if evidence
            else "no_evidence_of_historical_advantage"
        ),
    )
