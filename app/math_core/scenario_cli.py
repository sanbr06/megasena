import argparse
import json
from dataclasses import asdict

from app.lotteries import LOTTERIES
from app.math_core.comparison import compare_strategies
from app.math_core.portfolio import generate_random_portfolio
from app.math_core.scenario_optimizer import (
    optimize_scenario_coverage,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Otimização greedy por cobertura de cenários "
            "com validação Monte Carlo holdout"
        )
    )
    parser.add_argument(
        "--lottery",
        choices=LOTTERIES.keys(),
        required=True,
    )
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument(
        "--candidates",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--training-scenarios",
        type=int,
        default=50000,
    )
    parser.add_argument(
        "--holdout-trials",
        type=int,
        default=500000,
    )
    parser.add_argument("--threshold", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=25000,
    )
    args = parser.parse_args()

    config = LOTTERIES[args.lottery]

    baseline = generate_random_portfolio(
        config,
        args.games,
        seed=args.seed + 2_000_003,
    )

    optimized = optimize_scenario_coverage(
        config,
        args.games,
        candidate_count=args.candidates,
        training_scenarios=args.training_scenarios,
        threshold=args.threshold,
        seed=args.seed,
    )

    comparison = compare_strategies(
        config,
        baseline,
        optimized.games,
        trials=args.holdout_trials,
        seed=args.seed + 3_000_017,
        threshold=args.threshold,
        subset_size=min(4, config.quantity),
        chunk_size=args.chunk_size,
        baseline_name="random_baseline",
        challenger_name="scenario_coverage",
    )

    output = {
        "optimizer": asdict(optimized),
        "holdout": asdict(comparison),
        "methodology": {
            "training_and_holdout_are_independent": True,
            "objective": (
                f"maximize unique simulated draws with "
                f"{args.threshold}+ hits"
            ),
            "note": (
                "The training scenarios are used only to select "
                "the portfolio. Reported performance is evaluated "
                "on independent Monte Carlo draws."
            ),
        },
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
