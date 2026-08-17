from datetime import UTC, datetime, timedelta

import pytest

from app.lotteries import LOTTERIES
from app.math_core.comparison import compare_strategies
from app.math_core.experiment_records import (
    EXPERIMENT_SCHEMA_VERSION,
    SYNTHETIC_DATASET_VERSION,
    StrategyDescriptor,
    build_strategy_experiment_record,
)


def _comparison():
    return compare_strategies(
        LOTTERIES["megasena"],
        [[1, 2, 3, 4, 5, 6]],
        [[7, 8, 9, 10, 11, 12]],
        trials=100,
        seed=17,
        threshold=3,
        chunk_size=50,
    )


def _descriptors():
    return (
        StrategyDescriptor("random_baseline", "random-portfolio/v1", {"games": 1}),
        StrategyDescriptor("low_redundancy", "low-redundancy/v1", {"games": 1}),
    )


def test_experiment_record_captures_reproducibility_metadata():
    baseline, challenger = _descriptors()
    record = build_strategy_experiment_record(
        _comparison(),
        seed=17,
        baseline=baseline,
        challenger=challenger,
        generated_at=datetime(2026, 8, 17, tzinfo=UTC),
    )

    assert record["schema_version"] == EXPERIMENT_SCHEMA_VERSION
    assert len(record["experiment_id"]) == 64
    assert record["seed"] == 17
    assert record["strategies"]["baseline"]["version"] == "random-portfolio/v1"
    assert record["dataset"] == {
        "name": "synthetic_uniform_draws",
        "version": SYNTHETIC_DATASET_VERSION,
        "range": {"start_trial": 0, "end_trial_exclusive": 100},
    }
    assert record["metrics"]["delta"]["jackpot_probability"] == pytest.approx(0)
    assert record["execution"]["generated_at"] == "2026-08-17T00:00:00+00:00"
    assert record["execution"]["python_version"]


def test_experiment_identity_excludes_execution_time():
    baseline, challenger = _descriptors()
    first = build_strategy_experiment_record(
        _comparison(),
        seed=17,
        baseline=baseline,
        challenger=challenger,
        generated_at=datetime(2026, 8, 17, tzinfo=UTC),
    )
    second = build_strategy_experiment_record(
        _comparison(),
        seed=17,
        baseline=baseline,
        challenger=challenger,
        generated_at=datetime(2026, 8, 18, tzinfo=UTC),
    )

    assert first["experiment_id"] == second["experiment_id"]
    assert first["execution"] != second["execution"]


def test_experiment_record_rejects_ambiguous_metadata():
    _, challenger = _descriptors()

    with pytest.raises(ValueError, match="baseline_name_mismatch"):
        build_strategy_experiment_record(
            _comparison(),
            seed=17,
            baseline=StrategyDescriptor("other", "v1", {}),
            challenger=challenger,
        )

    baseline, challenger = _descriptors()
    with pytest.raises(ValueError, match="generated_at_must_be_timezone_aware"):
        build_strategy_experiment_record(
            _comparison(),
            seed=17,
            baseline=baseline,
            challenger=challenger,
            generated_at=datetime(2026, 8, 17) + timedelta(0),
        )
