import argparse
import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.math_core.prize_multiplicity import (
    MEGASENA_PRIZE_RULES_SOURCE,
    MEGASENA_PRIZE_RULES_VERSION,
    PayoutScenario,
    compare_system_to_diversified,
    structure_comparison_as_dict,
)


def _reais_to_cents(value):
    try:
        amount = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(
            "invalid_money_value"
        ) from exc

    if amount < 0:
        raise argparse.ArgumentTypeError(
            "money_must_not_be_negative"
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
            "Compara concentração de uma aposta Mega-Sena "
            "com jogos simples certificados equivalentes"
        )
    )
    parser.add_argument(
        "--marked-numbers",
        type=int,
        default=7,
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sena-payout")
    parser.add_argument("--quina-payout")
    parser.add_argument("--quadra-payout")
    args = parser.parse_args()

    payout_values = [
        args.sena_payout,
        args.quina_payout,
        args.quadra_payout,
    ]

    if any(value is not None for value in payout_values):
        if not all(value is not None for value in payout_values):
            parser.error(
                "informe sena, quina e quadra juntos"
            )

        scenario = PayoutScenario(
            sena_cents=_reais_to_cents(
                args.sena_payout
            ),
            quina_cents=_reais_to_cents(
                args.quina_payout
            ),
            quadra_cents=_reais_to_cents(
                args.quadra_payout
            ),
        )
    else:
        scenario = None

    comparison = compare_system_to_diversified(
        args.marked_numbers,
        seed=args.seed,
        payout_scenario=scenario,
    )

    output = structure_comparison_as_dict(comparison)
    output["rules"] = {
        "version": MEGASENA_PRIZE_RULES_VERSION,
        "source": MEGASENA_PRIZE_RULES_SOURCE,
    }
    output["interpretation"] = {
        "expected_value": (
            "Com a mesma quantidade de combinações simples e "
            "um mesmo valor de prêmio por aposta vencedora, o "
            "valor esperado bruto é igual por linearidade da "
            "esperança. A estrutura altera principalmente a "
            "probabilidade de pelo menos um prêmio, a "
            "multiplicidade e a variância do pagamento."
        ),
        "payout_scenario": (
            "Valores de prêmio informados na CLI são um cenário "
            "de análise; não são uma previsão de rateio."
        ),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
