from math import comb

import pytest

from app.math_core.prize_multiplicity import (
    PayoutScenario,
    compare_system_to_diversified,
    megasena_system_prize_counts,
    megasena_system_prize_states,
    payout_risk_for_certified_simples,
    payout_risk_for_system,
    profile_megasena_system_risk,
)


def test_official_7_number_multiplicity_when_sena_hits():
    prizes = megasena_system_prize_counts(7, 6)

    assert prizes.sena == 1
    assert prizes.quina == 6
    assert prizes.quadra == 0


def test_official_7_number_multiplicity_when_quina_hits():
    prizes = megasena_system_prize_counts(7, 5)

    assert prizes.sena == 0
    assert prizes.quina == 2
    assert prizes.quadra == 5


def test_official_7_number_multiplicity_when_quadra_hits():
    prizes = megasena_system_prize_counts(7, 4)

    assert prizes.sena == 0
    assert prizes.quina == 0
    assert prizes.quadra == 3


def test_official_8_number_multiplicity_when_sena_hits():
    prizes = megasena_system_prize_counts(8, 6)

    assert prizes.sena == 1
    assert prizes.quina == 12
    assert prizes.quadra == 15


def test_system_state_probabilities_sum_to_one():
    states = megasena_system_prize_states(8)

    assert sum(
        state.probability for state in states
    ) == pytest.approx(1.0)


def test_expected_prize_ticket_count_scales_with_simple_equivalents():
    six = profile_megasena_system_risk(6)
    seven = profile_megasena_system_risk(7)

    assert seven.simple_equivalents == 7
    assert (
        seven.expected_prize_tickets
        == pytest.approx(
            7 * six.expected_prize_tickets
        )
    )


def test_system_concentrates_prizes_vs_certified_simples():
    comparison = compare_system_to_diversified(
        7,
        seed=42,
    )

    assert comparison.simple_equivalents == 7

    assert (
        comparison.system.any_prize_probability
        < comparison.diversified.any_prize_probability
    )
    assert (
        comparison.system.multiple_prizes_probability
        > comparison.diversified.multiple_prizes_probability
    )
    assert comparison.delta_expected_prize_tickets == pytest.approx(
        0.0,
        abs=1e-15,
    )


def test_fixed_payout_scenario_has_equal_expected_value():
    scenario = PayoutScenario(
        sena_cents=500_000_000,
        quina_cents=5_000_000,
        quadra_cents=100_000,
    )

    system = payout_risk_for_system(7, scenario)
    diversified = payout_risk_for_certified_simples(
        7,
        scenario,
    )

    assert (
        system.expected_gross_payout_cents
        == pytest.approx(
            diversified.expected_gross_payout_cents
        )
    )


def test_concentrated_system_has_higher_payout_variance():
    scenario = PayoutScenario(
        sena_cents=500_000_000,
        quina_cents=5_000_000,
        quadra_cents=100_000,
    )

    comparison = compare_system_to_diversified(
        7,
        seed=42,
        payout_scenario=scenario,
    )

    assert (
        comparison.delta_payout_variance_cents_squared
        > 0
    )


def test_8_number_system_can_compare_to_28_certified_simples():
    comparison = compare_system_to_diversified(
        8,
        seed=42,
    )

    assert comparison.simple_equivalents == comb(8, 6)
    assert comparison.simple_equivalents == 28
    assert (
        comparison.diversified.globally_optimal_any_4plus
        is True
    )


def test_9_number_system_exceeds_current_certified_comparison_limit():
    with pytest.raises(
        ValueError,
        match=(
            "system_too_large_for_current_certified_comparison"
        ),
    ):
        compare_system_to_diversified(9)


def test_zero_value_tier_is_not_a_positive_payout():
    scenario = PayoutScenario(
        sena_cents=1,
        quina_cents=0,
        quadra_cents=0,
    )

    risk = payout_risk_for_certified_simples(7, scenario)

    assert risk.probability_positive_payout == pytest.approx(
        7 / comb(60, 6)
    )
