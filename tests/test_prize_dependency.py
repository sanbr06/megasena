import pytest

from app.lotteries import LOTTERIES
from app.math_core.pairwise_optimizer import (
    optimize_pairwise_prize_dependency,
)
from app.math_core.prize_dependency import (
    analyze_prize_dependencies,
    pairwise_prize_intersection_probability,
    prize_threshold_probability,
)


def test_identical_ticket_intersection_equals_single_probability():
    config = LOTTERIES["megasena"]

    single = prize_threshold_probability(config, 4)
    joint = pairwise_prize_intersection_probability(
        config,
        4,
        overlap=config.quantity,
    )

    assert joint == pytest.approx(single)


def test_pairwise_prize_intersection_increases_with_overlap():
    config = LOTTERIES["megasena"]

    probabilities = [
        pairwise_prize_intersection_probability(
            config,
            4,
            overlap,
        )
        for overlap in range(config.quantity + 1)
    ]

    assert probabilities == sorted(probabilities)


def test_bonferroni_lower_bound_is_not_above_first_order_sum():
    config = LOTTERIES["megasena"]

    metrics = analyze_prize_dependencies(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ],
        threshold=4,
    )

    assert (
        0
        <= metrics.second_order_lower_bound
        <= metrics.first_order_sum
    )


def test_redundant_portfolio_has_more_pairwise_prize_dependency():
    config = LOTTERIES["megasena"]

    redundant = analyze_prize_dependencies(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 3, 4, 5, 7],
            [1, 2, 3, 4, 5, 8],
        ],
        threshold=4,
    )

    diversified = analyze_prize_dependencies(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ],
        threshold=4,
    )

    assert (
        diversified.pairwise_intersection_sum
        < redundant.pairwise_intersection_sum
    )
    assert (
        diversified.second_order_lower_bound
        > redundant.second_order_lower_bound
    )


def test_pairwise_optimizer_is_reproducible_and_unique():
    config = LOTTERIES["megasena"]

    first = optimize_pairwise_prize_dependency(
        config,
        8,
        threshold=4,
        candidate_pool_size=100,
        restarts=5,
        seed=42,
    )
    second = optimize_pairwise_prize_dependency(
        config,
        8,
        threshold=4,
        candidate_pool_size=100,
        restarts=5,
        seed=42,
    )

    assert first.games == second.games
    assert len(first.games) == 8
    assert len(set(first.games)) == 8
