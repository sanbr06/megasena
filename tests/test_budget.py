from math import comb

import pytest

from app.math_core.budget import (
    MEGASENA_SIMPLE_GAME_COST_CENTS,
    MEGASENA_TOTAL_OUTCOMES,
    megasena_at_least_hits_probability,
    megasena_system_bet_cost_cents,
    plan_megasena_budget,
    profile_megasena_system_bet,
)
from app.math_core.prize_multiplicity import PayoutScenario


@pytest.mark.parametrize(
    ("marked_numbers", "expected_cents"),
    [
        (6, 600),
        (7, 4_200),
        (8, 16_800),
        (9, 50_400),
        (10, 126_000),
        (11, 277_200),
        (12, 554_400),
        (13, 1_029_600),
        (14, 1_801_800),
        (15, 3_003_000),
        (16, 4_804_800),
        (17, 7_425_600),
        (18, 11_138_400),
        (19, 16_279_200),
        (20, 23_256_000),
    ],
)
def test_official_megasena_price_snapshot(
    marked_numbers,
    expected_cents,
):
    assert (
        megasena_system_bet_cost_cents(marked_numbers)
        == expected_cents
    )


def test_system_cost_is_simple_equivalent_count_times_base():
    for marked_numbers in range(6, 21):
        assert megasena_system_bet_cost_cents(
            marked_numbers
        ) == (
            comb(marked_numbers, 6)
            * MEGASENA_SIMPLE_GAME_COST_CENTS
        )


def test_seven_number_bet_has_same_jackpot_as_seven_simples():
    profile = profile_megasena_system_bet(7)

    assert profile.simple_equivalents == 7
    assert profile.jackpot_probability == pytest.approx(
        7 / comb(60, 6)
    )


def test_system_bet_quadraplus_probability_is_exact_hypergeometric():
    probability = megasena_at_least_hits_probability(
        7,
        threshold=4,
    )

    expected = sum(
        comb(7, hits) * comb(53, 6 - hits)
        for hits in range(4, 7)
    ) / comb(60, 6)

    assert probability == pytest.approx(expected)


def test_concentrated_seven_number_bet_has_lower_any_prize_coverage():
    profile = profile_megasena_system_bet(7)

    assert (
        profile.quadra_plus_probability
        < profile.quadra_plus_disjoint_upper_bound
    )
    assert (
        0
        < profile.quadra_plus_efficiency_vs_disjoint_bound
        < 1
    )


def test_120_reais_produces_20_game_global_optimum_certificate():
    result = plan_megasena_budget(
        12_000,
        seed=42,
    )

    plan = result.simple_plan

    assert plan.games == 20
    assert plan.cost_cents == 12_000
    assert plan.unspent_cents == 0
    assert plan.globally_optimal_quadra_plus is True
    assert plan.max_pairwise_overlap <= 1
    assert (
        plan.certified_quadra_plus_probability
        == pytest.approx(
            plan.quadra_plus_disjoint_upper_bound
        )
    )
    assert plan.prize_risk is not None
    assert plan.prize_risk.any_prize_probability == pytest.approx(
        plan.certified_quadra_plus_probability
    )
    assert plan.prize_risk.multiple_prizes_probability == 0.0
    assert plan.prize_risk.expected_prize_tickets == pytest.approx(
        plan.prize_risk.any_prize_probability
    )


def test_100_reais_uses_96_and_leaves_4():
    result = plan_megasena_budget(
        10_000,
        seed=42,
    )

    assert result.simple_plan.games == 16
    assert result.simple_plan.cost_cents == 9_600
    assert result.simple_plan.unspent_cents == 400


def test_simple_plan_stops_after_covering_every_distinct_combination():
    excess_cents = 1_200
    budget_cents = (
        MEGASENA_TOTAL_OUTCOMES * MEGASENA_SIMPLE_GAME_COST_CENTS
        + excess_cents
    )

    result = plan_megasena_budget(budget_cents)

    assert result.simple_plan.games == MEGASENA_TOTAL_OUTCOMES
    assert result.simple_plan.jackpot_probability == 1.0
    assert result.simple_plan.cost_cents == budget_cents - excess_cents
    assert result.simple_plan.unspent_cents == excess_cents


def test_affordable_system_bets_for_120_reais():
    result = plan_megasena_budget(12_000)

    assert [
        bet.marked_numbers
        for bet in result.affordable_single_system_bets
    ] == [6, 7]

    seven = result.affordable_single_system_bets[1]
    assert seven.prize_risk.simple_equivalents == 7
    assert (
        seven.prize_risk.any_prize_probability
        == pytest.approx(seven.quadra_plus_probability)
    )
    assert seven.prize_risk.multiple_prizes_probability > 0


def test_uncertified_simple_plan_does_not_claim_exact_risk_profile():
    result = plan_megasena_budget(
        12_600,
        certificate_game_limit=20,
    )

    assert result.simple_plan.games == 21
    assert result.simple_plan.globally_optimal_quadra_plus is False
    assert result.simple_plan.prize_risk is None


def test_budget_planner_integrates_explicit_payout_risk():
    scenario = PayoutScenario(
        sena_cents=500_000_000,
        quina_cents=5_000_000,
        quadra_cents=100_000,
    )

    result = plan_megasena_budget(
        4_200,
        seed=42,
        payout_scenario=scenario,
    )

    simple_risk = result.simple_plan.payout_risk
    system_risk = result.affordable_single_system_bets[-1].payout_risk

    assert simple_risk is not None
    assert system_risk is not None
    assert (
        simple_risk.expected_gross_payout_cents
        == pytest.approx(system_risk.expected_gross_payout_cents)
    )
    assert (
        simple_risk.payout_variance_cents_squared
        < system_risk.payout_variance_cents_squared
    )


def test_budget_planner_does_not_assume_a_payout_scenario():
    result = plan_megasena_budget(4_200)

    assert result.simple_plan.payout_risk is None
    assert all(
        bet.payout_risk is None
        for bet in result.affordable_single_system_bets
    )
