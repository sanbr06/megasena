import argparse
import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.math_core.budget import (
    budget_result_as_dict,
    plan_megasena_budget,
)


def _currency_to_cents(value):
    try:
        amount = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(
            "invalid_budget"
        ) from exc

    if amount < 0:
        raise argparse.ArgumentTypeError(
            "budget_must_not_be_negative"
        )

    return int(
        (amount * 100).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Planejador analítico de orçamento da Mega-Sena"
        )
    )
    parser.add_argument(
        "--budget",
        required=True,
        help="Orçamento em reais, por exemplo 120 ou 120,00",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    budget_cents = _currency_to_cents(args.budget)

    result = plan_megasena_budget(
        budget_cents,
        seed=args.seed,
    )

    output = budget_result_as_dict(result)

    output["interpretation"] = {
        "jackpot": (
            "O custo oficial das apostas com mais dezenas é "
            "proporcional ao número de combinações simples; "
            "por isso a chance de Sena por combinação comprada "
            "permanece a mesma."
        ),
        "quadra_plus": (
            "Apostas concentradas em mais dezenas reutilizam "
            "muitas combinações relacionadas. O campo "
            "quadra_plus_efficiency_vs_disjoint_bound mede a "
            "probabilidade de pelo menos uma Quadra+ em relação "
            "ao limite de combinações disjuntas."
        ),
        "scope": (
            "Esta versão mede probabilidade de pelo menos um "
            "prêmio 4+. Multiplicidade de prêmios, retorno "
            "financeiro esperado e valor dos rateios ainda não "
            "fazem parte do modelo."
        ),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
