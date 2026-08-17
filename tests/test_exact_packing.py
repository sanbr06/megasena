from itertools import combinations

import pytest

from app.lotteries import LOTTERIES
from app.math_core.exact_packing import (
    certify_megasena_quadraplus_optimum,
    generate_megasena_quadraplus_optimal_packing,
)
from app.math_core.prize_dependency import (
    pairwise_prize_intersection_probability,
    prize_threshold_probability,
)


def test_quadraplus_pair_intersection_boundary_is_exact():
    config = LOTTERIES["megasena"]

    assert pairwise_prize_intersection_probability(
        config,
        threshold=4,
        overlap=0,
    ) == 0
    assert pairwise_prize_intersection_probability(
        config,
        threshold=4,
        overlap=1,
    ) == 0
    assert pairwise_prize_intersection_probability(
        config,
        threshold=4,
        overlap=2,
    ) > 0


def test_generator_produces_20_pair_packed_games():
    config = LOTTERIES["megasena"]

    games = generate_megasena_quadraplus_optimal_packing(
        config,
        20,
        seed=42,
    )

    assert len(games) == 20
    assert len(set(games)) == 20

    for left, right in combinations(games, 2):
        assert len(set(left).intersection(right)) <= 1


def test_generated_portfolio_has_global_optimality_certificate():
    config = LOTTERIES["megasena"]

    games = generate_megasena_quadraplus_optimal_packing(
        config,
        20,
        seed=7,
    )

    certificate = certify_megasena_quadraplus_optimum(
        config,
        games,
    )

    single = prize_threshold_probability(config, 4)

    assert certificate.is_global_optimum is True
    assert certificate.optimality_gap == 0
    assert certificate.achieved_probability == pytest.approx(
        20 * single
    )
    assert certificate.global_upper_bound == pytest.approx(
        20 * single
    )


def test_generator_is_reproducible():
    config = LOTTERIES["megasena"]

    first = generate_megasena_quadraplus_optimal_packing(
        config,
        20,
        seed=123,
    )
    second = generate_megasena_quadraplus_optimal_packing(
        config,
        20,
        seed=123,
    )

    assert first == second


def test_non_packed_portfolio_is_not_certified():
    config = LOTTERIES["megasena"]

    certificate = certify_megasena_quadraplus_optimum(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 7, 8, 9, 10],
        ],
    )

    assert certificate.max_pairwise_overlap == 2
    assert certificate.is_global_optimum is False
    assert certificate.achieved_probability is None
    assert certificate.optimality_gap is None


def test_pair_packing_elementary_bound_is_enforced():
    config = LOTTERIES["megasena"]

    with pytest.raises(
        ValueError,
        match="game_count_exceeds_pair_packing_bound",
    ):
        generate_megasena_quadraplus_optimal_packing(
            config,
            119,
        )
