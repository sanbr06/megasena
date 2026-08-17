from dataclasses import asdict
from datetime import date
from math import isfinite

from flask import Blueprint, current_app, jsonify, request

from app.core.security import require_token
from app.lotteries import LOTTERIES
from app.lotteries.catalog import (
    lottery_product_catalog,
    lottery_product_catalog_as_dict,
)
from app.math_core.budget import (
    MEGASENA_SIMPLE_GAME_COST_CENTS,
    budget_result_as_dict,
    plan_megasena_budget,
)
from app.math_core.prize_multiplicity import PayoutScenario
from app.math_core.simple_budget import (
    MAX_GENERATED_GAMES,
    plan_simple_lottery_budget,
    simple_budget_plan_as_dict,
)
from app.math_core.walk_forward import walk_forward_frequency_backtest
from app.services.historical_explorer import explore_history
from app.services.portfolio_matching import match_portfolio

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

_REQUEST_FIELDS = {
    "budget_cents",
    "seed",
    "contest_number",
    "certificate_game_limit",
    "payout_scenario",
}
_PAYOUT_FIELDS = {"sena_cents", "quina_cents", "quadra_cents"}


@api_v1.get("/lotteries")
@require_token
def lotteries():
    return jsonify({
        "api_version": "v1",
        "data": {
            "lotteries": lottery_product_catalog_as_dict(),
        },
    })


@api_v1.get("/ready")
def readiness():
    repository = current_app.extensions["result_repository"]
    if not repository.is_ready():
        return jsonify({
            "api_version": "v1",
            "error": {
                "code": "service_unavailable",
                "message": "The service is not ready.",
                "details": [
                    {"component": "database", "status": "unavailable"},
                ],
            },
        }), 503

    return jsonify({
        "api_version": "v1",
        "data": {
            "status": "ready",
            "checks": {"database": "available"},
        },
    })


def _validation_error(details):
    return jsonify({
        "api_version": "v1",
        "error": {
            "code": "validation_error",
            "message": "Request validation failed.",
            "details": details,
        },
    }), 400


def _integer_field(payload, field, *, default=None, minimum=None, maximum=None):
    value = payload.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int):
        return None, {"field": field, "code": "must_be_integer"}
    if minimum is not None and value < minimum:
        return None, {
            "field": field,
            "code": "must_be_at_least",
            "minimum": minimum,
        }
    if maximum is not None and value > maximum:
        return None, {
            "field": field,
            "code": "must_be_at_most",
            "maximum": maximum,
        }
    return value, None


def _query_integer(field, *, minimum=None):
    raw = request.args.get(field)
    if raw is None:
        return None, None
    try:
        value = int(raw)
    except ValueError:
        return None, {"field": field, "code": "must_be_integer"}
    if minimum is not None and value < minimum:
        return None, {"field": field, "code": "must_be_at_least", "minimum": minimum}
    return value, None


def _query_date(field):
    raw = request.args.get(field)
    if raw is None:
        return None, None
    try:
        return date.fromisoformat(raw), None
    except ValueError:
        return None, {"field": field, "code": "must_be_iso_date"}


def _number_field(payload, field, *, default=None, exclusive_minimum=None,
                  exclusive_maximum=None):
    value = payload.get(field, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, {"field": field, "code": "must_be_number"}
    if not isfinite(value):
        return None, {"field": field, "code": "must_be_finite"}
    if exclusive_minimum is not None and value <= exclusive_minimum:
        return None, {
            "field": field,
            "code": "must_be_greater_than",
            "minimum": exclusive_minimum,
        }
    if exclusive_maximum is not None and value >= exclusive_maximum:
        return None, {
            "field": field,
            "code": "must_be_less_than",
            "maximum": exclusive_maximum,
        }
    return float(value), None


def _validate_saved_games(games, product):
    if not isinstance(games, list) or not games:
        return [{"field": "games", "code": "must_be_non_empty_array"}]
    if len(games) > MAX_GENERATED_GAMES:
        return [{
            "field": "games",
            "code": "must_have_at_most",
            "maximum": MAX_GENERATED_GAMES,
        }]

    details = []
    seen_games = set()
    for index, game in enumerate(games):
        field = f"games[{index}]"
        if not isinstance(game, dict):
            details.append({"field": field, "code": "must_be_object"})
            continue
        allowed = {"numbers", "extra_selection"}
        for key in sorted(set(game) - allowed):
            details.append({"field": f"{field}.{key}", "code": "unknown_field"})
        numbers = game.get("numbers")
        if (
            not isinstance(numbers, list)
            or len(numbers) != product.draw_size
            or any(isinstance(number, bool) or not isinstance(number, int) for number in numbers)
        ):
            details.append({
                "field": f"{field}.numbers",
                "code": "invalid_combination",
                "required_numbers": product.draw_size,
            })
        elif (
            len(set(numbers)) != len(numbers)
            or any(
                number < product.minimum_number or number > product.maximum_number
                for number in numbers
            )
        ):
            details.append({
                "field": f"{field}.numbers",
                "code": "numbers_must_be_unique_and_in_range",
                "minimum": product.minimum_number,
                "maximum": product.maximum_number,
            })
        else:
            extra = game.get("extra_selection")
            extra_value = (
                extra.get(product.extra_selection.key)
                if product.extra_selection is not None and isinstance(extra, dict)
                else None
            )
            game_key = (tuple(sorted(numbers)), extra_value)
            if game_key in seen_games:
                details.append({"field": f"{field}.numbers", "code": "duplicate_game"})
            seen_games.add(game_key)

        extra = game.get("extra_selection")
        if product.extra_selection is None:
            if extra is not None:
                details.append({"field": f"{field}.extra_selection", "code": "not_supported"})
        elif (
            not isinstance(extra, dict)
            or set(extra) != {product.extra_selection.key}
            or extra[product.extra_selection.key] not in product.extra_selection.options
        ):
            details.append({
                "field": f"{field}.extra_selection",
                "code": "invalid_extra_selection",
            })
    return details


def _parse_payout_scenario(payload):
    raw = payload.get("payout_scenario")
    if raw is None:
        return None, []
    if not isinstance(raw, dict):
        return None, [{"field": "payout_scenario", "code": "must_be_object"}]

    details = [
        {
            "field": f"payout_scenario.{field}",
            "code": "unknown_field",
        }
        for field in sorted(set(raw) - _PAYOUT_FIELDS)
    ]
    values = {}
    for field in sorted(_PAYOUT_FIELDS):
        if field not in raw:
            details.append({
                "field": f"payout_scenario.{field}",
                "code": "required",
            })
            continue
        value, error = _integer_field(raw, field, minimum=0)
        if error:
            error["field"] = f"payout_scenario.{field}"
            details.append(error)
        else:
            values[field] = value

    if details:
        return None, details
    return PayoutScenario(**values), []


@api_v1.post("/megasena/budget-plan")
@require_token
def megasena_budget_plan():
    if not request.is_json:
        return _validation_error([
            {"field": "body", "code": "json_required"},
        ])

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _validation_error([
            {"field": "body", "code": "must_be_object"},
        ])

    details = [
        {"field": field, "code": "unknown_field"}
        for field in sorted(set(payload) - _REQUEST_FIELDS)
    ]
    if "budget_cents" not in payload:
        details.append({"field": "budget_cents", "code": "required"})

    budget_cents, error = _integer_field(payload, "budget_cents", minimum=0)
    if error and "budget_cents" in payload:
        details.append(error)
    seed, error = _integer_field(payload, "seed", default=42)
    if error:
        details.append(error)
    contest_number = None
    if "contest_number" in payload:
        contest_number, error = _integer_field(
            payload,
            "contest_number",
            minimum=1,
        )
        if error:
            details.append(error)
    certificate_limit, error = _integer_field(
        payload,
        "certificate_game_limit",
        default=20,
        minimum=0,
        maximum=20,
    )
    if error:
        details.append(error)
    payout_scenario, payout_errors = _parse_payout_scenario(payload)
    details.extend(payout_errors)

    if details:
        return _validation_error(details)

    if (
        budget_cents // MEGASENA_SIMPLE_GAME_COST_CENTS
        > MAX_GENERATED_GAMES
    ):
        return _validation_error([{
            "field": "budget_cents",
            "code": "generation_limit_exceeded",
            "maximum_generated_games": MAX_GENERATED_GAMES,
        }])

    result = plan_megasena_budget(
        budget_cents,
        seed=seed,
        certificate_game_limit=certificate_limit,
        payout_scenario=payout_scenario,
    )
    data = budget_result_as_dict(result)
    data["generation_context"] = {
        "lottery": "megasena",
        "contest_number": contest_number,
        "seed": seed,
    }
    return jsonify({
        "api_version": "v1",
        "data": data,
    })


@api_v1.post("/lotteries/<lottery>/simple-budget-plan")
@require_token
def simple_lottery_budget_plan(lottery):
    if not request.is_json:
        return _validation_error([
            {"field": "body", "code": "json_required"},
        ])

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _validation_error([
            {"field": "body", "code": "must_be_object"},
        ])

    details = [
        {"field": field, "code": "unknown_field"}
        for field in sorted(
            set(payload) - {
                "budget_cents", "seed", "contest_number",
                "allowed_sum_min", "allowed_sum_max",
                "allowed_odd_min", "allowed_odd_max",
                "allowed_repeat_min", "allowed_repeat_max",
                "allowed_max_overlap",
            }
        )
    ]
    if "budget_cents" not in payload:
        details.append({"field": "budget_cents", "code": "required"})
    budget_cents, error = _integer_field(
        payload,
        "budget_cents",
        minimum=0,
    )
    if error and "budget_cents" in payload:
        details.append(error)
    seed, error = _integer_field(payload, "seed", default=42)
    if error:
        details.append(error)
    contest_number = None
    if "contest_number" in payload:
        contest_number, error = _integer_field(
            payload,
            "contest_number",
            minimum=1,
        )
        if error:
            details.append(error)
    sum_fields = {}
    for field in ("allowed_sum_min", "allowed_sum_max"):
        if field in payload:
            sum_fields[field], error = _integer_field(payload, field, minimum=0)
            if error:
                details.append(error)
    if (
        "allowed_sum_min" in sum_fields
        and "allowed_sum_max" in sum_fields
        and sum_fields["allowed_sum_min"] > sum_fields["allowed_sum_max"]
    ):
        details.append({"field": "allowed_sum_min", "code": "range_is_reversed"})
    odd_fields = {}
    for field in ("allowed_odd_min", "allowed_odd_max"):
        if field in payload:
            odd_fields[field], error = _integer_field(
                payload, field, minimum=0, maximum=LOTTERIES.get(lottery).quantity
                if lottery in LOTTERIES else None,
            )
            if error:
                details.append(error)
    if (
        "allowed_odd_min" in odd_fields
        and "allowed_odd_max" in odd_fields
        and odd_fields["allowed_odd_min"] > odd_fields["allowed_odd_max"]
    ):
        details.append({"field": "allowed_odd_min", "code": "range_is_reversed"})
    repeat_fields = {}
    for field in ("allowed_repeat_min", "allowed_repeat_max"):
        if field in payload:
            repeat_fields[field], error = _integer_field(
                payload,
                field,
                minimum=0,
                maximum=LOTTERIES.get(lottery).quantity if lottery in LOTTERIES else None,
            )
            if error:
                details.append(error)
    if (
        "allowed_repeat_min" in repeat_fields
        and "allowed_repeat_max" in repeat_fields
        and repeat_fields["allowed_repeat_min"] > repeat_fields["allowed_repeat_max"]
    ):
        details.append({"field": "allowed_repeat_min", "code": "range_is_reversed"})
    if repeat_fields and contest_number is None:
        details.append({
            "field": "contest_number",
            "code": "required_for_repeat_constraint",
        })

    overlap_fields = {}
    if "allowed_max_overlap" in payload:
        overlap_fields["allowed_max_overlap"], error = _integer_field(
            payload,
            "allowed_max_overlap",
            minimum=0,
            maximum=(
                LOTTERIES[lottery].quantity - 1
                if lottery in LOTTERIES
                else None
            ),
        )
        if error:
            details.append(error)
    if details:
        return _validation_error(details)

    reference_numbers = None
    if repeat_fields:
        repository = current_app.extensions["result_repository"]
        previous_result = repository.get_result(lottery, contest_number - 1)
        if previous_result is None:
            return _validation_error([{
                "field": "contest_number",
                "code": "previous_official_result_not_available",
                "previous_contest": contest_number - 1,
            }])
        reference_numbers = previous_result["numbers"]

    try:
        plan = plan_simple_lottery_budget(
            lottery,
            budget_cents,
            seed=seed,
            **sum_fields,
            **odd_fields,
            **repeat_fields,
            reference_numbers=reference_numbers,
            **overlap_fields,
        )
    except ValueError as exc:
        if str(exc) == "unknown_lottery":
            return jsonify({
                "api_version": "v1",
                "error": {
                    "code": "lottery_not_found",
                    "message": "Lottery is not supported.",
                    "details": [{"field": "lottery", "value": lottery}],
                },
            }), 404
        if str(exc) == "generation_limit_exceeded":
            return _validation_error([{
                "field": "budget_cents",
                "code": "generation_limit_exceeded",
                "maximum_generated_games": MAX_GENERATED_GAMES,
            }])
        if str(exc) == "game_count_exceeds_constrained_space":
            return _validation_error([{
                "field": "budget_cents",
                "code": "exceeds_constrained_combination_space",
            }])
        if str(exc) == "sum_range_is_reversed":
            return _validation_error([{
                "field": "allowed_sum_min",
                "code": "range_is_reversed",
            }])
        if str(exc) == "overlap_constraint_unsatisfied":
            return _validation_error([{
                "field": "allowed_max_overlap",
                "code": "constraint_could_not_fill_portfolio",
            }])
        raise

    data = simple_budget_plan_as_dict(plan)
    data["generation_context"] = {
        "lottery": lottery,
        "contest_number": contest_number,
        "seed": seed,
    }
    return jsonify({
        "api_version": "v1",
        "data": data,
    })


@api_v1.get("/lotteries/<lottery>/history-explorer")
@require_token
def historical_explorer(lottery):
    if lottery not in LOTTERIES:
        return jsonify({
            "api_version": "v1",
            "error": {
                "code": "lottery_not_found",
                "message": "Lottery is not supported.",
                "details": [{"field": "lottery", "value": lottery}],
            },
        }), 404

    allowed_fields = {"contest_from", "contest_to", "date_from", "date_to"}
    details = [
        {"field": field, "code": "unknown_field"}
        for field in sorted(set(request.args) - allowed_fields)
    ]
    filters = {}
    for field in ("contest_from", "contest_to"):
        filters[field], error = _query_integer(field, minimum=1)
        if error:
            details.append(error)
    for field in ("date_from", "date_to"):
        filters[field], error = _query_date(field)
        if error:
            details.append(error)
    if (
        filters["contest_from"] is not None
        and filters["contest_to"] is not None
        and filters["contest_from"] > filters["contest_to"]
    ):
        details.append({"field": "contest_from", "code": "range_is_reversed"})
    if (
        filters["date_from"] is not None
        and filters["date_to"] is not None
        and filters["date_from"] > filters["date_to"]
    ):
        details.append({"field": "date_from", "code": "range_is_reversed"})
    if details:
        return _validation_error(details)

    repository = current_app.extensions["result_repository"]
    data = explore_history(repository.list_results(lottery), lottery, **filters)
    return jsonify({"api_version": "v1", "data": data})


@api_v1.post("/lotteries/<lottery>/walk-forward-backtest")
@require_token
def walk_forward_backtest(lottery):
    if lottery not in LOTTERIES:
        return jsonify({
            "api_version": "v1",
            "error": {
                "code": "lottery_not_found",
                "message": "Lottery is not supported.",
                "details": [{"field": "lottery", "value": lottery}],
            },
        }), 404
    if not request.is_json:
        return _validation_error([{"field": "body", "code": "json_required"}])

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _validation_error([{"field": "body", "code": "must_be_object"}])

    allowed_fields = {
        "minimum_training_draws", "threshold", "seed", "significance_level",
    }
    details = [
        {"field": field, "code": "unknown_field"}
        for field in sorted(set(payload) - allowed_fields)
    ]
    minimum_training_draws, error = _integer_field(
        payload, "minimum_training_draws", default=20, minimum=1,
    )
    if error:
        details.append(error)
    threshold, error = _integer_field(
        payload,
        "threshold",
        default=LOTTERIES[lottery].quantity,
        minimum=1,
        maximum=LOTTERIES[lottery].quantity,
    )
    if error:
        details.append(error)
    seed, error = _integer_field(payload, "seed", default=42)
    if error:
        details.append(error)
    significance_level, error = _number_field(
        payload,
        "significance_level",
        default=0.05,
        exclusive_minimum=0,
        exclusive_maximum=1,
    )
    if error:
        details.append(error)
    if details:
        return _validation_error(details)

    repository = current_app.extensions["result_repository"]
    draws = repository.list_results(lottery)
    try:
        result = walk_forward_frequency_backtest(
            LOTTERIES[lottery],
            draws,
            minimum_training_draws=minimum_training_draws,
            threshold=threshold,
            seed=seed,
            significance_level=significance_level,
        )
    except ValueError as exc:
        if str(exc) == "insufficient_historical_draws":
            return _validation_error([{
                "field": "minimum_training_draws",
                "code": "insufficient_historical_draws",
                "available_draws": len(draws),
            }])
        raise

    data = asdict(result)
    contests = [draw["contest"] for draw in draws]
    data["dataset"] = {
        "kind": "stored_official_results",
        "draw_count": len(draws),
        "contest_from": min(contests),
        "contest_to": max(contests),
    }
    data["analysis_scope"] = (
        "number_hits_only_excludes_lucky_month"
        if lottery == "diadesorte"
        else "number_hits"
    )
    data["evidence_statement"] = (
        "EVIDÊNCIA HISTÓRICA DE VANTAGEM"
        if result.evidence_of_advantage
        else "SEM EVIDÊNCIA DE VANTAGEM"
    )
    data["disclaimer"] = (
        "Desempenho histórico fora da amostra não prevê sorteios futuros nem altera "
        "a probabilidade matemática de uma combinação individual."
    )
    return jsonify({"api_version": "v1", "data": data})


@api_v1.get("/portfolios")
@require_token
def list_portfolios():
    repository = current_app.extensions["portfolio_repository"]
    return jsonify({
        "api_version": "v1",
        "data": repository.list_recent(),
    })


@api_v1.post("/portfolios")
@require_token
def save_portfolio():
    if not request.is_json:
        return _validation_error([{"field": "body", "code": "json_required"}])
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _validation_error([{"field": "body", "code": "must_be_object"}])

    allowed = {"lottery", "contest", "games", "strategy", "seed", "cost_snapshot"}
    required = allowed
    details = [
        {"field": field, "code": "unknown_field"}
        for field in sorted(set(payload) - allowed)
    ]
    details.extend(
        {"field": field, "code": "required"}
        for field in sorted(required - set(payload))
    )

    products = {product.slug: product for product in lottery_product_catalog()}
    lottery = payload.get("lottery")
    product = products.get(lottery) if isinstance(lottery, str) else None
    if "lottery" in payload and product is None:
        details.append({"field": "lottery", "code": "unsupported_lottery"})

    contest = seed = None
    if "contest" in payload:
        contest, error = _integer_field(payload, "contest", minimum=1)
        if error:
            details.append(error)
    if "seed" in payload:
        seed, error = _integer_field(payload, "seed")
        if error:
            details.append(error)

    games = payload.get("games")
    if product is not None and "games" in payload:
        details.extend(_validate_saved_games(games, product))

    strategy = payload.get("strategy")
    if "strategy" in payload:
        if not isinstance(strategy, dict):
            details.append({"field": "strategy", "code": "must_be_object"})
        else:
            for field in sorted(set(strategy) - {"name", "version", "parameters"}):
                details.append({"field": f"strategy.{field}", "code": "unknown_field"})
            for field in ("name", "version"):
                if not isinstance(strategy.get(field), str) or not strategy[field].strip():
                    details.append({
                        "field": f"strategy.{field}",
                        "code": "must_be_non_empty_string",
                    })
            if not isinstance(strategy.get("parameters"), dict):
                details.append({"field": "strategy.parameters", "code": "must_be_object"})

    cost_snapshot = payload.get("cost_snapshot")
    if "cost_snapshot" in payload:
        if not isinstance(cost_snapshot, dict):
            details.append({"field": "cost_snapshot", "code": "must_be_object"})
        else:
            cost_fields = {
                "pricing_version", "simple_game_cost_cents", "total_cost_cents",
            }
            for field in sorted(set(cost_snapshot) - cost_fields):
                details.append({"field": f"cost_snapshot.{field}", "code": "unknown_field"})
            if product is not None:
                game_count = len(games) if isinstance(games, list) else 0
                expected = {
                    "pricing_version": product.pricing_version,
                    "simple_game_cost_cents": product.simple_game_cost_cents,
                    "total_cost_cents": product.simple_game_cost_cents * game_count,
                }
                for field, expected_value in expected.items():
                    if cost_snapshot.get(field) != expected_value:
                        details.append({
                            "field": f"cost_snapshot.{field}",
                            "code": "must_match_pricing_snapshot",
                            "expected": expected_value,
                        })

    if details:
        return _validation_error(details)

    normalized = {
        "lottery": lottery,
        "contest": contest,
        "games": [
            {
                "numbers": sorted(game["numbers"]),
                "extra_selection": game.get("extra_selection"),
            }
            for game in games
        ],
        "strategy": {
            "name": strategy["name"].strip(),
            "version": strategy["version"].strip(),
            "parameters": strategy["parameters"],
        },
        "seed": seed,
        "cost_snapshot": cost_snapshot,
    }
    repository = current_app.extensions["portfolio_repository"]
    return jsonify({
        "api_version": "v1",
        "data": repository.save(normalized),
    }), 201


@api_v1.get("/portfolios/<int:portfolio_id>")
@require_token
def get_portfolio(portfolio_id):
    repository = current_app.extensions["portfolio_repository"]
    portfolio = repository.get(portfolio_id)
    if portfolio is None:
        return jsonify({
            "api_version": "v1",
            "error": {
                "code": "portfolio_not_found",
                "message": "Saved portfolio was not found.",
                "details": [{"field": "portfolio_id", "value": portfolio_id}],
            },
        }), 404
    return jsonify({"api_version": "v1", "data": portfolio})


@api_v1.post("/portfolios/<int:portfolio_id>/check")
@require_token
def check_portfolio(portfolio_id):
    portfolio_repository = current_app.extensions["portfolio_repository"]
    portfolio = portfolio_repository.get(portfolio_id)
    if portfolio is None:
        return jsonify({
            "api_version": "v1",
            "error": {
                "code": "portfolio_not_found",
                "message": "Saved portfolio was not found.",
                "details": [{"field": "portfolio_id", "value": portfolio_id}],
            },
        }), 404

    result_repository = current_app.extensions["result_repository"]
    official_result = result_repository.get_result(
        portfolio["lottery"], portfolio["contest"]
    )
    if official_result is None:
        portfolio = portfolio_repository.update_status(portfolio_id, "awaiting_result")
        return jsonify({
            "api_version": "v1",
            "data": {
                "portfolio": portfolio,
                "check": None,
                "message": "Official result is not available in local storage yet.",
            },
        })

    checked_portfolio = portfolio_repository.update_status(portfolio_id, "checked")
    return jsonify({
        "api_version": "v1",
        "data": {
            "portfolio": checked_portfolio,
            "check": match_portfolio(checked_portfolio, official_result),
        },
    })
