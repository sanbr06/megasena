import pytest

from app.lotteries import LOTTERIES
from app.math_core.walk_forward import walk_forward_frequency_backtest


def _draws(count, numbers=None):
    numbers = numbers or [1, 2, 3, 4, 5, 6]
    return [
        {"contest": contest, "numbers": numbers}
        for contest in range(1, count + 1)
    ]


def test_walk_forward_uses_only_prior_contests_and_is_reproducible():
    config = LOTTERIES["megasena"]
    draws = _draws(8)

    first = walk_forward_frequency_backtest(
        config, draws, minimum_training_draws=3, seed=17
    )
    second = walk_forward_frequency_backtest(
        config, list(reversed(draws)), minimum_training_draws=3, seed=17
    )

    assert first == second
    assert [fold.contest for fold in first.folds] == [4, 5, 6, 7, 8]
    assert all(fold.training_end_contest < fold.contest for fold in first.folds)
    assert first.baseline_strategy == "uniform-random/v1"


def test_future_draw_change_cannot_change_earlier_fold_predictions():
    config = LOTTERIES["megasena"]
    original = _draws(7)
    changed = _draws(7)
    changed[-1] = {"contest": 7, "numbers": [10, 11, 12, 13, 14, 15]}

    before = walk_forward_frequency_backtest(
        config, original, minimum_training_draws=3, seed=9
    )
    after = walk_forward_frequency_backtest(
        config, changed, minimum_training_draws=3, seed=9
    )

    assert before.folds[:-1] == after.folds[:-1]
    assert before.folds[-1].challenger_game == after.folds[-1].challenger_game
    assert before.folds[-1].baseline_game == after.folds[-1].baseline_game


def test_backtest_reports_evidence_only_with_exact_paired_support():
    result = walk_forward_frequency_backtest(
        LOTTERIES["megasena"],
        _draws(30),
        minimum_training_draws=5,
        threshold=4,
        seed=42,
    )

    assert result.evidence_of_advantage is True
    assert result.conclusion == "evidence_of_historical_advantage"
    assert result.paired_one_sided_p_value < result.significance_level
    assert result.challenger_observed_jackpot_rate == 1.0
    assert result.baseline_observed_jackpot_rate == 0.0


def test_backtest_rejects_insufficient_or_ambiguous_history():
    config = LOTTERIES["megasena"]
    with pytest.raises(ValueError, match="insufficient_historical_draws"):
        walk_forward_frequency_backtest(config, _draws(3), minimum_training_draws=3)

    duplicate = _draws(4) + [{"contest": 4, "numbers": [7, 8, 9, 10, 11, 12]}]
    with pytest.raises(ValueError, match="duplicate_contest"):
        walk_forward_frequency_backtest(config, duplicate, minimum_training_draws=3)
