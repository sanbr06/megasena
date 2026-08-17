import pytest

from app.lotteries import LOTTERIES
from app.math_core.combinatorics import LotterySpace
from app.math_core.simulation import simulate_portfolio


def test_simulation_is_reproducible():
    config = LOTTERIES["megasena"]
    games = [[1, 2, 3, 4, 5, 6]]

    first = simulate_portfolio(
        config,
        games,
        trials=5_000,
        seed=123,
        chunk_size=1_000,
    )
    second = simulate_portfolio(
        config,
        games,
        trials=5_000,
        seed=123,
        chunk_size=1_000,
    )

    assert first.max_hit_counts == second.max_hit_counts


def test_simulation_accounts_for_every_trial():
    config = LOTTERIES["megasena"]

    result = simulate_portfolio(
        config,
        [[1, 2, 3, 4, 5, 6]],
        trials=7_500,
        seed=42,
        chunk_size=2_000,
    )

    assert sum(result.max_hit_counts.values()) == 7_500
    assert sum(result.max_hit_probabilities.values()) == pytest.approx(1.0)


def test_single_game_mean_hits_matches_exact_expectation():
    config = LOTTERIES["megasena"]

    result = simulate_portfolio(
        config,
        [[1, 2, 3, 4, 5, 6]],
        trials=40_000,
        seed=7,
        chunk_size=10_000,
    )

    expected_mean = config.quantity**2 / (
        config.maximum - config.minimum + 1
    )

    assert result.mean_best_hits == pytest.approx(
        expected_mean,
        abs=0.025,
    )


def test_single_game_common_hit_probability_matches_exact_math():
    config = LOTTERIES["megasena"]
    space = LotterySpace.from_config(config)

    result = simulate_portfolio(
        config,
        [[1, 2, 3, 4, 5, 6]],
        trials=50_000,
        seed=99,
        chunk_size=10_000,
    )

    simulated = result.max_hit_probabilities[1]
    exact = space.exact_hits_probability(1)

    assert simulated == pytest.approx(exact, abs=0.01)


def test_probability_at_least_is_monotonic():
    config = LOTTERIES["megasena"]

    result = simulate_portfolio(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
        ],
        trials=10_000,
        seed=11,
        chunk_size=2_500,
    )

    assert (
        result.probability_at_least(3)
        >= result.probability_at_least(4)
        >= result.probability_at_least(5)
        >= result.probability_at_least(6)
    )


def test_confidence_interval_contains_estimate():
    config = LOTTERIES["megasena"]

    result = simulate_portfolio(
        config,
        [[1, 2, 3, 4, 5, 6]],
        trials=10_000,
        seed=15,
        chunk_size=2_500,
    )

    estimate = result.probability_at_least(2)
    interval = result.confidence_interval_at_least(2)

    assert interval.lower <= estimate <= interval.upper
    assert 0 <= interval.lower <= interval.upper <= 1
