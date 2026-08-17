import argparse
import json
from dataclasses import asdict

from app.lotteries import LOTTERIES
from app.math_core.comparison import compare_strategies
from app.math_core.pairwise_optimizer import (
    optimize_pairwise_prize_dependency,
)
from app.math_core.portfolio import generate_random_portfolio
from app.math_core.prize_dependency import (
    analyze_prize_dependencies,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Otimiza dependência exata de prêmio entre pares "
            "de jogos simples"
        )
    )
    parser.add_argument(
        "--lottery",
        choices=LOTTERIES.keys(),
        required=True,
    )
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--threshold", type=int, default=4)
    parser.add_argument("--candidates", type=int, default=1000)
    parser.add_argument("--restarts", type=int, default=20)
    parser.add_argument("--trials", type=int, default=500000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--chunk-size", type=int, default=25000)
    args = parser.parse_args()

    config = LOTTERIES[args.lottery]

    baseline = generate_random_portfolio(
        config,
        args.games,
        seed=args.seed + 2_000_003,
    )

    optimized = optimize_pairwise_prize_dependency(
        config,
        args.games,
        threshold=args.threshold,
        candidate_pool_size=args.candidates,
        restarts=args.restarts,
        seed=args.seed,
    )

    baseline_exact = analyze_prize_dependencies(
        config,
        baseline,
        args.threshold,
    )
    optimized_exact = analyze_prize_dependencies(
        config,
        optimized.games,
        args.threshold,
    )

    holdout = compare_strategies(
        config,
        baseline,
        optimized.games,
        trials=args.trials,
        seed=args.seed + 3_000_017,
        threshold=args.threshold,
        subset_size=min(4, config.quantity),
        chunk_size=args.chunk_size,
        baseline_name="random_baseline",
        challenger_name="exact_pairwise",
    )

    output = {
        "optimizer": asdict(optimized),
        "exact_dependency": {
            "baseline": asdict(baseline_exact),
            "optimized": asdict(optimized_exact),
            "delta": {
                "pairwise_intersection_sum": (
                    optimized_exact.pairwise_intersection_sum
                    - baseline_exact.pairwise_intersection_sum
                ),
                "second_order_lower_bound": (
                    optimized_exact.second_order_lower_bound
                    - baseline_exact.second_order_lower_bound
                ),
            },
        },
        "monte_carlo_holdout": asdict(holdout),
        "methodology": {
            "objective": (
                "minimize exact pairwise intersection probability "
                "for the selected prize threshold"
            ),
            "bonferroni_note": (
                "The second-order Bonferroni value is a rigorous "
                "lower bound for the probability of at least one "
                "winning ticket, not an exact union probability."
            ),
            "prediction_claim": False,
        },
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
