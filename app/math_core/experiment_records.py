import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.math_core.comparison import StrategyComparison

EXPERIMENT_SCHEMA_VERSION = "strategy-comparison/v1"
SYNTHETIC_DATASET_VERSION = "uniform-lottery-draws/v1"


@dataclass(frozen=True)
class StrategyDescriptor:
    name: str
    version: str
    parameters: dict


@dataclass(frozen=True)
class DatasetDescriptor:
    name: str
    version: str
    range: dict


def _canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_strategy_experiment_record(
    comparison: StrategyComparison,
    *,
    seed: int,
    baseline: StrategyDescriptor,
    challenger: StrategyDescriptor,
    dataset: DatasetDescriptor | None = None,
    generated_at: datetime | None = None,
):
    """Build a versioned, self-describing record without persisting it."""
    if baseline.name != comparison.baseline_name:
        raise ValueError("baseline_name_mismatch")
    if challenger.name != comparison.challenger_name:
        raise ValueError("challenger_name_mismatch")

    dataset = dataset or DatasetDescriptor(
        name="synthetic_uniform_draws",
        version=SYNTHETIC_DATASET_VERSION,
        range={
            "start_trial": 0,
            "end_trial_exclusive": comparison.trials,
        },
    )
    reproducible_result = {
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "lottery": comparison.lottery,
        "seed": int(seed),
        "strategies": {
            "baseline": asdict(baseline),
            "challenger": asdict(challenger),
        },
        "dataset": asdict(dataset),
        "metrics": asdict(comparison),
    }
    experiment_id = hashlib.sha256(
        _canonical_json(reproducible_result).encode("utf-8")
    ).hexdigest()
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("generated_at_must_be_timezone_aware")

    return {
        "experiment_id": experiment_id,
        **reproducible_result,
        "execution": {
            "generated_at": timestamp.astimezone(UTC).isoformat(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        },
    }
