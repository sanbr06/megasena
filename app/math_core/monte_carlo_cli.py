import argparse
import json
from dataclasses import asdict

from app.lotteries import LOTTERIES
from app.math_core.portfolio import (
    analyze_portfolio,
    generate_random_portfolio,
)
from app.math_core.simulation import simulate_portfolio


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo Engine - avaliação de carteiras"
    )
    parser.add_argument(
        "--lottery",
        choices=LOTTERIES.keys(),
        required=True,
    )
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--trials", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threshold", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=50_000)
    args = parser.parse_args()

    config = LOTTERIES[args.lottery]

    games = generate_random_portfolio(
        config,
        args.games,
        seed=args.seed,
    )

    portfolio = analyze_portfolio(
        config,
        games,
        subset_size=min(4, config.quantity),
    )

    simulation = simulate_portfolio(
        config,
        games,
        trials=args.trials,
        seed=args.seed,
        chunk_size=args.chunk_size,
    )

    interval = simulation.confidence_interval_at_least(
        args.threshold
    )

    output = {
        "lottery": args.lottery,
        "strategy": "random_baseline",
        "seed": args.seed,
        "portfolio": asdict(portfolio),
        "simulation": {
            "trials": simulation.trials,
            "max_hit_counts": simulation.max_hit_counts,
            "max_hit_probabilities": (
                simulation.max_hit_probabilities
            ),
            "mean_best_hits": simulation.mean_best_hits,
            "threshold": args.threshold,
            "probability_at_least_threshold": (
                simulation.probability_at_least(args.threshold)
            ),
            "confidence_interval_95": asdict(interval),
        },
        "disclaimer": (
            "Monte Carlo estimates portfolio behavior under random "
            "draws; it does not predict future lottery results."
        ),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
