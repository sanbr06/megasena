import argparse
import json
from dataclasses import asdict

from app.lotteries import LOTTERIES
from app.math_core.exact_packing import (
    certify_megasena_quadraplus_optimum,
    generate_megasena_quadraplus_optimal_packing,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Gera uma carteira Mega-Sena com certificado "
            "matemático de ótimo global para Quadra+"
        )
    )
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    config = LOTTERIES["megasena"]

    games = generate_megasena_quadraplus_optimal_packing(
        config,
        args.games,
        seed=args.seed,
    )

    certificate = certify_megasena_quadraplus_optimum(
        config,
        games,
    )

    output = {
        "lottery": "megasena",
        "strategy": "provably_optimal_quadraplus_packing",
        "games": games,
        "certificate": asdict(certificate),
        "proof_summary": (
            "Every pair of tickets shares at most one number. "
            "Two Mega-Sena tickets can both score 4+ in the same "
            "draw only if they share at least two numbers. "
            "Therefore their 4+ winning events are disjoint and "
            "the union reaches the universal sum-probability "
            "upper bound."
        ),
        "jackpot_note": (
            "The jackpot probability remains determined only by "
            "the number of unique simple tickets."
        ),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
