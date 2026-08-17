import pytest

from app.lotteries import LOTTERIES
from app.math_core import (
    LotterySpace,
    analyze_portfolio,
    generate_random_portfolio,
)


@pytest.mark.parametrize(
    ("lottery", "expected"),
    [
        ("megasena", 50_063_860),
        ("lotofacil", 3_268_760),
        ("quina", 24_040_016),
        ("diadesorte", 2_629_575),
    ],
)
def test_total_outcomes(lottery, expected):
    space = LotterySpace.from_config(LOTTERIES[lottery])
    assert space.total_outcomes == expected


def test_exact_hit_probabilities_sum_to_one():
    space = LotterySpace.from_config(LOTTERIES["megasena"])

    probability = sum(
        space.exact_hits_probability(hits)
        for hits in range(space.draw_size + 1)
    )

    assert probability == pytest.approx(1.0)


def test_duplicate_games_do_not_improve_jackpot_probability():
    config = LOTTERIES["megasena"]
    game = [1, 2, 3, 4, 5, 6]

    metrics = analyze_portfolio(
        config,
        [game, game],
        subset_size=4,
    )

    assert metrics.games == 2
    assert metrics.unique_games == 1
    assert metrics.duplicate_games == 1
    assert metrics.jackpot_probability == pytest.approx(
        1 / 50_063_860
    )


def test_subset_coverage_accounts_for_overlap():
    config = LOTTERIES["megasena"]

    metrics = analyze_portfolio(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 3, 4, 5, 7],
        ],
        subset_size=4,
    )

    assert metrics.covered_subsets == 25
    assert metrics.maximum_pairwise_overlap == 5


def test_random_portfolio_is_reproducible_and_unique():
    config = LOTTERIES["megasena"]

    first = generate_random_portfolio(config, 20, seed=42)
    second = generate_random_portfolio(config, 20, seed=42)

    assert set(first) == set(second)
    assert len(first) == 20
    assert len(set(first)) == 20


def test_less_redundant_portfolio_has_better_subset_coverage():
    config = LOTTERIES["megasena"]

    redundant = analyze_portfolio(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [1, 2, 3, 4, 5, 7],
            [1, 2, 3, 4, 5, 8],
        ],
        subset_size=4,
    )

    diversified = analyze_portfolio(
        config,
        [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
        ],
        subset_size=4,
    )

    assert diversified.covered_subsets > redundant.covered_subsets
    assert (
        diversified.average_pairwise_overlap
        < redundant.average_pairwise_overlap
    )
