from dataclasses import asdict, dataclass

from app.lotteries.base import LotteryConfig
from app.math_core.portfolio import analyze_portfolio
from app.math_core.simulation import simulate_portfolio


@dataclass(frozen=True)
class StrategyComparison:
    lottery: str
    trials: int
    threshold: int
    baseline_name: str
    challenger_name: str
    baseline: dict
    challenger: dict
    delta: dict


def _strategy_snapshot(
    config,
    games,
    trials,
    seed,
    threshold,
    subset_size,
    chunk_size,
):
    portfolio = analyze_portfolio(
        config,
        games,
        subset_size=subset_size,
    )
    simulation = simulate_portfolio(
        config,
        games,
        trials=trials,
        seed=seed,
        chunk_size=chunk_size,
    )

    return {
        "portfolio": asdict(portfolio),
        "simulation": {
            "probability_at_least_threshold": (
                simulation.probability_at_least(threshold)
            ),
            "mean_best_hits": simulation.mean_best_hits,
            "max_hit_counts": simulation.max_hit_counts,
            "confidence_interval_95": asdict(
                simulation.confidence_interval_at_least(
                    threshold
                )
            ),
        },
    }


def compare_strategies(
    config: LotteryConfig,
    baseline_games,
    challenger_games,
    *,
    trials=100_000,
    seed=42,
    threshold=4,
    subset_size=4,
    chunk_size=50_000,
    baseline_name="random_baseline",
    challenger_name="low_redundancy",
):
    trials = int(trials)
    threshold = int(threshold)
    subset_size = int(subset_size)

    if threshold <= 0 or threshold > config.quantity:
        raise ValueError("invalid_threshold")

    baseline = _strategy_snapshot(
        config,
        baseline_games,
        trials,
        seed,
        threshold,
        subset_size,
        chunk_size,
    )
    challenger = _strategy_snapshot(
        config,
        challenger_games,
        trials,
        seed,
        threshold,
        subset_size,
        chunk_size,
    )

    baseline_portfolio = baseline["portfolio"]
    challenger_portfolio = challenger["portfolio"]
    baseline_simulation = baseline["simulation"]
    challenger_simulation = challenger["simulation"]

    return StrategyComparison(
        lottery=config.slug,
        trials=trials,
        threshold=threshold,
        baseline_name=baseline_name,
        challenger_name=challenger_name,
        baseline=baseline,
        challenger=challenger,
        delta={
            "subset_coverage_ratio": (
                challenger_portfolio["subset_coverage_ratio"]
                - baseline_portfolio["subset_coverage_ratio"]
            ),
            "average_pairwise_overlap": (
                challenger_portfolio["average_pairwise_overlap"]
                - baseline_portfolio["average_pairwise_overlap"]
            ),
            "maximum_pairwise_overlap": (
                challenger_portfolio["maximum_pairwise_overlap"]
                - baseline_portfolio["maximum_pairwise_overlap"]
            ),
            "jackpot_probability": (
                challenger_portfolio["jackpot_probability"]
                - baseline_portfolio["jackpot_probability"]
            ),
            "probability_at_least_threshold": (
                challenger_simulation[
                    "probability_at_least_threshold"
                ]
                - baseline_simulation[
                    "probability_at_least_threshold"
                ]
            ),
            "mean_best_hits": (
                challenger_simulation["mean_best_hits"]
                - baseline_simulation["mean_best_hits"]
            ),
        },
    )
