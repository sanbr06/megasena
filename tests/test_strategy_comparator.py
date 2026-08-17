import pytest

from app.lotteries import LOTTERIES
from app.math_core.comparison import compare_strategies
from app.math_core.portfolio import (
    analyze_portfolio,
    generate_random_portfolio,
)
from app.math_core.strategies import (
    generate_low_redundancy_portfolio,
)


def test_low_redundancy_generator_is_reproducible():
    config = LOTTERIES["megasena"]

    first = generate_low_redundancy_portfolio(
        config,
        8,
        seed=42,
        candidate_pool_size=150,
    )
    second = generate_low_redundancy_portfolio(
        config,
        8,
        seed=42,
        candidate_pool_size=150,
    )

    assert first == second
    assert len(first) == 8
    assert len(set(first)) == 8


def test_low_redundancy_portfolio_improves_structural_coverage():
    config = LOTTERIES["megasena"]

    random_games = generate_random_portfolio(
        config,
        20,
        seed=42,
    )
    optimized_games = generate_low_redundancy_portfolio(
        config,
        20,
        seed=42,
        subset_size=4,
        candidate_pool_size=500,
    )

    random_metrics = analyze_portfolio(
        config,
        random_games,
        subset_size=4,
    )
    optimized_metrics = analyze_portfolio(
        config,
        optimized_games,
        subset_size=4,
    )

    assert (
        optimized_metrics.covered_subsets
        >= random_metrics.covered_subsets
    )
    assert (
        optimized_metrics.average_pairwise_overlap
        <= random_metrics.average_pairwise_overlap
    )


def test_same_number_of_unique_games_has_same_jackpot_probability():
    config = LOTTERIES["megasena"]

    baseline = [
        [1, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 7],
    ]
    challenger = [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11, 12],
    ]

    result = compare_strategies(
        config,
        baseline,
        challenger,
        trials=5_000,
        seed=42,
        threshold=3,
        chunk_size=1_000,
    )

    assert result.delta["jackpot_probability"] == pytest.approx(0.0)


def test_comparator_reports_structural_improvement():
    config = LOTTERIES["megasena"]

    baseline = [
        [1, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 7],
        [1, 2, 3, 4, 5, 8],
    ]
    challenger = [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11, 12],
        [13, 14, 15, 16, 17, 18],
    ]

    result = compare_strategies(
        config,
        baseline,
        challenger,
        trials=8_000,
        seed=7,
        threshold=3,
        chunk_size=2_000,
    )

    assert result.delta["subset_coverage_ratio"] > 0
    assert result.delta["average_pairwise_overlap"] < 0


def test_invalid_threshold_is_rejected():
    config = LOTTERIES["megasena"]

    with pytest.raises(ValueError, match="invalid_threshold"):
        compare_strategies(
            config,
            [[1, 2, 3, 4, 5, 6]],
            [[7, 8, 9, 10, 11, 12]],
            threshold=7,
        )
