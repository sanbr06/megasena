import argparse
import json
from dataclasses import asdict

from app.lotteries import LOTTERIES
from app.math_core.portfolio import (
    analyze_portfolio,
    generate_random_portfolio,
)


def main():
    parser = argparse.ArgumentParser(
        description="Mathematical Core - análise combinatória de carteiras"
    )
    parser.add_argument(
        "--lottery",
        choices=LOTTERIES.keys(),
        required=True,
    )
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--subset-size", type=int, default=4)
    args = parser.parse_args()

    config = LOTTERIES[args.lottery]
    games = generate_random_portfolio(
        config,
        args.games,
        seed=args.seed,
    )

    metrics = analyze_portfolio(
        config,
        games,
        subset_size=args.subset_size,
    )

    output = asdict(metrics)
    output["jackpot_odds_one_in"] = (
        1 / metrics.jackpot_probability
        if metrics.jackpot_probability
        else None
    )

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
