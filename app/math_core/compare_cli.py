import argparse
import json
from dataclasses import asdict

from app.lotteries import LOTTERIES
from app.math_core.comparison import compare_strategies
from app.math_core.portfolio import generate_random_portfolio
from app.math_core.strategies import (
    generate_low_redundancy_portfolio,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compara baseline aleatório e carteira "
            "de baixa redundância"
        )
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
    parser.add_argument("--subset-size", type=int, default=4)
    parser.add_argument(
        "--candidate-pool-size",
        type=int,
        default=750,
    )
    parser.add_argument("--chunk-size", type=int, default=50_000)
    args = parser.parse_args()

    config = LOTTERIES[args.lottery]

    baseline = generate_random_portfolio(
        config,
        args.games,
        seed=args.seed,
    )

    challenger = generate_low_redundancy_portfolio(
        config,
        args.games,
        seed=args.seed,
        subset_size=args.subset_size,
        candidate_pool_size=args.candidate_pool_size,
    )

    result = compare_strategies(
        config,
        baseline,
        challenger,
        trials=args.trials,
        seed=args.seed,
        threshold=args.threshold,
        subset_size=args.subset_size,
        chunk_size=args.chunk_size,
    )

    output = asdict(result)
    output["interpretation"] = {
        "coverage_delta_positive_is_better": True,
        "overlap_delta_negative_is_better": True,
        "jackpot_probability_note": (
            "With the same number of unique simple games, "
            "jackpot probability is expected to be equal."
        ),
        "simulation_note": (
            "Monte Carlo differences are estimates under random "
            "draws and are not predictions of future results."
        ),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
