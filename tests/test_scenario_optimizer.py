import pytest

from app.lotteries import LOTTERIES
from app.math_core.scenario_optimizer import (
    optimize_scenario_coverage,
)


def test_scenario_optimizer_is_reproducible():
    config = LOTTERIES["megasena"]

    first = optimize_scenario_coverage(
        config,
        5,
        candidate_count=40,
        training_scenarios=2_000,
        threshold=3,
        seed=42,
    )
    second = optimize_scenario_coverage(
        config,
        5,
        candidate_count=40,
        training_scenarios=2_000,
        threshold=3,
        seed=42,
    )

    assert first.games == second.games
    assert (
        first.covered_training_scenarios
        == second.covered_training_scenarios
    )


def test_scenario_optimizer_returns_unique_valid_games():
    config = LOTTERIES["megasena"]

    result = optimize_scenario_coverage(
        config,
        8,
        candidate_count=80,
        training_scenarios=2_000,
        threshold=3,
        seed=7,
    )

    assert len(result.games) == 8
    assert len(set(result.games)) == 8

    for game in result.games:
        assert config.validate_numbers(game) == list(game)


def test_training_coverage_ratio_is_valid():
    config = LOTTERIES["megasena"]

    result = optimize_scenario_coverage(
        config,
        6,
        candidate_count=50,
        training_scenarios=1_500,
        threshold=3,
        seed=11,
    )

    assert 0 <= result.training_coverage_ratio <= 1
    assert (
        result.covered_training_scenarios
        <= result.training_scenarios
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"game_count": 0},
            "game_count_must_be_positive",
        ),
        (
            {
                "game_count": 10,
                "candidate_count": 5,
            },
            "candidate_count_must_cover_game_count",
        ),
        (
            {
                "game_count": 5,
                "training_scenarios": 0,
            },
            "training_scenarios_must_be_positive",
        ),
        (
            {
                "game_count": 5,
                "threshold": 7,
            },
            "invalid_threshold",
        ),
    ],
)
def test_invalid_parameters(kwargs, message):
    config = LOTTERIES["megasena"]

    with pytest.raises(ValueError, match=message):
        optimize_scenario_coverage(
            config,
            **kwargs,
        )
