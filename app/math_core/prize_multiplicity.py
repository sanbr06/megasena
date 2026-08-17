from dataclasses import asdict, dataclass
from math import comb, sqrt

from app.lotteries import LOTTERIES
from app.math_core.budget import (
    MEGASENA_SIMPLE_GAME_COST_CENTS,
    MEGASENA_TOTAL_OUTCOMES,
    megasena_system_bet_cost_cents,
)
from app.math_core.combinatorics import LotterySpace
from app.math_core.exact_packing import (
    certify_megasena_quadraplus_optimum,
    generate_megasena_quadraplus_optimal_packing,
)

MEGASENA_PRIZE_RULES_VERSION = "caixa-2026-08-17"
MEGASENA_PRIZE_RULES_SOURCE = (
    "https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx"
)


def _comb_or_zero(n, k):
    if k < 0 or k > n:
        return 0
    return comb(n, k)


@dataclass(frozen=True)
class PrizeCounts:
    sena: int
    quina: int
    quadra: int

    @property
    def total(self):
        return self.sena + self.quina + self.quadra


@dataclass(frozen=True)
class SystemPrizeState:
    hits_among_marked: int
    probability: float
    prizes: PrizeCounts


@dataclass(frozen=True)
class PrizeRiskProfile:
    structure: str
    simple_equivalents: int
    cost_cents: int
    any_prize_probability: float
    multiple_prizes_probability: float
    expected_sena_tickets: float
    expected_quina_tickets: float
    expected_quadra_tickets: float
    expected_prize_tickets: float
    conditional_expected_prize_tickets: float
    concentration_ratio: float
    globally_optimal_any_4plus: bool | None
    max_pairwise_overlap: int | None


@dataclass(frozen=True)
class PayoutScenario:
    sena_cents: int
    quina_cents: int
    quadra_cents: int

    def __post_init__(self):
        if min(
            self.sena_cents,
            self.quina_cents,
            self.quadra_cents,
        ) < 0:
            raise ValueError("payouts_must_not_be_negative")


@dataclass(frozen=True)
class PayoutRisk:
    expected_gross_payout_cents: float
    expected_net_result_cents: float
    expected_return_ratio: float
    expected_roi: float
    payout_variance_cents_squared: float
    payout_stddev_cents: float
    probability_positive_payout: float
    maximum_gross_payout_cents: int


@dataclass(frozen=True)
class StructureComparison:
    marked_numbers: int
    simple_equivalents: int
    system: PrizeRiskProfile
    diversified: PrizeRiskProfile
    delta_any_prize_probability: float
    delta_multiple_prizes_probability: float
    delta_expected_prize_tickets: float
    payout_system: PayoutRisk | None
    payout_diversified: PayoutRisk | None
    delta_expected_gross_payout_cents: float | None
    delta_payout_variance_cents_squared: float | None


def megasena_system_prize_counts(
    marked_numbers,
    hits_among_marked,
):
    marked_numbers = int(marked_numbers)
    hits_among_marked = int(hits_among_marked)

    if not 6 <= marked_numbers <= 20:
        raise ValueError("invalid_marked_numbers")
    if not 0 <= hits_among_marked <= 6:
        raise ValueError("invalid_hits_among_marked")

    non_hits_among_marked = (
        marked_numbers - hits_among_marked
    )

    return PrizeCounts(
        sena=(
            _comb_or_zero(hits_among_marked, 6)
            * _comb_or_zero(non_hits_among_marked, 0)
        ),
        quina=(
            _comb_or_zero(hits_among_marked, 5)
            * _comb_or_zero(non_hits_among_marked, 1)
        ),
        quadra=(
            _comb_or_zero(hits_among_marked, 4)
            * _comb_or_zero(non_hits_among_marked, 2)
        ),
    )


def megasena_system_prize_states(marked_numbers):
    marked_numbers = int(marked_numbers)

    if not 6 <= marked_numbers <= 20:
        raise ValueError("invalid_marked_numbers")

    states = []

    for hits in range(7):
        probability = (
            _comb_or_zero(marked_numbers, hits)
            * _comb_or_zero(
                60 - marked_numbers,
                6 - hits,
            )
            / MEGASENA_TOTAL_OUTCOMES
        )

        states.append(
            SystemPrizeState(
                hits_among_marked=hits,
                probability=probability,
                prizes=megasena_system_prize_counts(
                    marked_numbers,
                    hits,
                ),
            )
        )

    return states


def _expected_simple_prize_counts(simple_equivalents):
    config = LOTTERIES["megasena"]
    space = LotterySpace.from_config(config)

    return {
        "sena": (
            simple_equivalents
            * space.exact_hits_probability(6)
        ),
        "quina": (
            simple_equivalents
            * space.exact_hits_probability(5)
        ),
        "quadra": (
            simple_equivalents
            * space.exact_hits_probability(4)
        ),
    }


def profile_megasena_system_risk(marked_numbers):
    marked_numbers = int(marked_numbers)
    states = megasena_system_prize_states(marked_numbers)

    simple_equivalents = comb(marked_numbers, 6)
    expected = _expected_simple_prize_counts(
        simple_equivalents
    )

    any_prize_probability = sum(
        state.probability
        for state in states
        if state.prizes.total > 0
    )
    multiple_prizes_probability = sum(
        state.probability
        for state in states
        if state.prizes.total > 1
    )

    expected_prize_tickets = sum(expected.values())

    conditional_expected = (
        expected_prize_tickets / any_prize_probability
        if any_prize_probability
        else 0.0
    )

    return PrizeRiskProfile(
        structure=f"system_{marked_numbers}_numbers",
        simple_equivalents=simple_equivalents,
        cost_cents=megasena_system_bet_cost_cents(
            marked_numbers
        ),
        any_prize_probability=any_prize_probability,
        multiple_prizes_probability=(
            multiple_prizes_probability
        ),
        expected_sena_tickets=expected["sena"],
        expected_quina_tickets=expected["quina"],
        expected_quadra_tickets=expected["quadra"],
        expected_prize_tickets=expected_prize_tickets,
        conditional_expected_prize_tickets=(
            conditional_expected
        ),
        concentration_ratio=conditional_expected,
        globally_optimal_any_4plus=None,
        max_pairwise_overlap=None,
    )


def profile_certified_diversified_simples(
    simple_games,
    *,
    seed=42,
):
    simple_games = int(simple_games)

    if simple_games <= 0:
        raise ValueError("simple_games_must_be_positive")

    config = LOTTERIES["megasena"]

    games = generate_megasena_quadraplus_optimal_packing(
        config,
        simple_games,
        seed=seed,
    )
    certificate = certify_megasena_quadraplus_optimum(
        config,
        games,
    )

    if not certificate.is_global_optimum:
        raise RuntimeError("portfolio_not_globally_optimal")

    expected = _expected_simple_prize_counts(simple_games)
    expected_prize_tickets = sum(expected.values())

    # The certificate proves the 4+ events are disjoint.
    any_prize_probability = expected_prize_tickets

    return PrizeRiskProfile(
        structure="certified_diversified_simples",
        simple_equivalents=simple_games,
        cost_cents=(
            simple_games
            * MEGASENA_SIMPLE_GAME_COST_CENTS
        ),
        any_prize_probability=any_prize_probability,
        multiple_prizes_probability=0.0,
        expected_sena_tickets=expected["sena"],
        expected_quina_tickets=expected["quina"],
        expected_quadra_tickets=expected["quadra"],
        expected_prize_tickets=expected_prize_tickets,
        conditional_expected_prize_tickets=1.0,
        concentration_ratio=1.0,
        globally_optimal_any_4plus=True,
        max_pairwise_overlap=(
            certificate.max_pairwise_overlap
        ),
    )


def payout_risk_for_system(
    marked_numbers,
    scenario: PayoutScenario,
):
    cost_cents = megasena_system_bet_cost_cents(
        marked_numbers
    )
    states = megasena_system_prize_states(marked_numbers)

    payouts = []

    for state in states:
        gross = (
            state.prizes.sena * scenario.sena_cents
            + state.prizes.quina * scenario.quina_cents
            + state.prizes.quadra * scenario.quadra_cents
        )
        payouts.append((state.probability, gross))

    expected = sum(
        probability * gross
        for probability, gross in payouts
    )
    expected_square = sum(
        probability * (gross**2)
        for probability, gross in payouts
    )
    variance = max(0.0, expected_square - expected**2)

    return PayoutRisk(
        expected_gross_payout_cents=expected,
        expected_net_result_cents=expected - cost_cents,
        expected_return_ratio=(
            expected / cost_cents if cost_cents else 0.0
        ),
        expected_roi=(
            (expected - cost_cents) / cost_cents
            if cost_cents
            else 0.0
        ),
        payout_variance_cents_squared=variance,
        payout_stddev_cents=sqrt(variance),
        probability_positive_payout=sum(
            probability
            for probability, gross in payouts
            if gross > 0
        ),
        maximum_gross_payout_cents=max(
            gross for _, gross in payouts
        ),
    )


def payout_risk_for_certified_simples(
    simple_games,
    scenario: PayoutScenario,
):
    simple_games = int(simple_games)

    if simple_games <= 0:
        raise ValueError("simple_games_must_be_positive")

    config = LOTTERIES["megasena"]
    space = LotterySpace.from_config(config)

    tier_states = [
        (
            simple_games * space.exact_hits_probability(6),
            scenario.sena_cents,
        ),
        (
            simple_games * space.exact_hits_probability(5),
            scenario.quina_cents,
        ),
        (
            simple_games * space.exact_hits_probability(4),
            scenario.quadra_cents,
        ),
    ]

    expected = sum(
        probability * payout
        for probability, payout in tier_states
    )
    expected_square = sum(
        probability * (payout**2)
        for probability, payout in tier_states
    )
    variance = max(0.0, expected_square - expected**2)

    cost_cents = (
        simple_games * MEGASENA_SIMPLE_GAME_COST_CENTS
    )

    return PayoutRisk(
        expected_gross_payout_cents=expected,
        expected_net_result_cents=expected - cost_cents,
        expected_return_ratio=expected / cost_cents,
        expected_roi=(expected - cost_cents) / cost_cents,
        payout_variance_cents_squared=variance,
        payout_stddev_cents=sqrt(variance),
        probability_positive_payout=sum(
            probability
            for probability, payout in tier_states
            if payout > 0
        ),
        maximum_gross_payout_cents=max(
            scenario.sena_cents,
            scenario.quina_cents,
            scenario.quadra_cents,
        ),
    )


def compare_system_to_diversified(
    marked_numbers,
    *,
    seed=42,
    payout_scenario=None,
    max_certified_simple_games=50,
):
    marked_numbers = int(marked_numbers)
    simple_equivalents = comb(marked_numbers, 6)

    if simple_equivalents > max_certified_simple_games:
        raise ValueError(
            "system_too_large_for_current_certified_comparison"
        )

    system = profile_megasena_system_risk(
        marked_numbers
    )
    diversified = profile_certified_diversified_simples(
        simple_equivalents,
        seed=seed,
    )

    payout_system = None
    payout_diversified = None
    expected_delta = None
    variance_delta = None

    if payout_scenario is not None:
        payout_system = payout_risk_for_system(
            marked_numbers,
            payout_scenario,
        )
        payout_diversified = (
            payout_risk_for_certified_simples(
                simple_equivalents,
                payout_scenario,
            )
        )
        expected_delta = (
            payout_system.expected_gross_payout_cents
            - payout_diversified.expected_gross_payout_cents
        )
        variance_delta = (
            payout_system.payout_variance_cents_squared
            - payout_diversified.payout_variance_cents_squared
        )

    return StructureComparison(
        marked_numbers=marked_numbers,
        simple_equivalents=simple_equivalents,
        system=system,
        diversified=diversified,
        delta_any_prize_probability=(
            system.any_prize_probability
            - diversified.any_prize_probability
        ),
        delta_multiple_prizes_probability=(
            system.multiple_prizes_probability
            - diversified.multiple_prizes_probability
        ),
        delta_expected_prize_tickets=(
            system.expected_prize_tickets
            - diversified.expected_prize_tickets
        ),
        payout_system=payout_system,
        payout_diversified=payout_diversified,
        delta_expected_gross_payout_cents=expected_delta,
        delta_payout_variance_cents_squared=variance_delta,
    )


def structure_comparison_as_dict(comparison):
    return asdict(comparison)
