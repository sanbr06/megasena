from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from app.core.security import require_token, require_token_v1
from app.math_core.budget import (
    budget_result_as_dict,
    plan_megasena_budget,
)
from app.math_core.prize_multiplicity import PayoutScenario
from app.providers.caixa import ProviderError

api = Blueprint("api", __name__)


def services():
    return (
        current_app.extensions["result_service"],
        current_app.extensions["lottery_service"],
    )


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


def _v1_error(code, message, *, status=400, field=None):
    error = {"code": code, "message": message}
    if field is not None:
        error["field"] = field
    return jsonify({"api_version": "v1", "error": error}), status


def _required_nonnegative_integer(payload, field):
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(field)
    if value < 0:
        raise ArithmeticError(field)
    return value


def _parse_payout_scenario(payload):
    raw = payload.get("payout_scenario")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError("payout_scenario")

    expected_fields = {"sena_cents", "quina_cents", "quadra_cents"}
    if set(raw) != expected_fields:
        raise KeyError("payout_scenario")

    return PayoutScenario(**{
        field: _required_nonnegative_integer(raw, field)
        for field in expected_fields
    })


@api.post("/api/v1/planners/megasena/budget")
@require_token_v1
def v1_megasena_budget():
    if not request.is_json:
        return _v1_error(
            "unsupported_media_type",
            "Content-Type must be application/json.",
            status=415,
        )

    try:
        payload = request.get_json()
    except BadRequest:
        return _v1_error("invalid_json", "The request body is not valid JSON.")

    if not isinstance(payload, dict):
        return _v1_error("invalid_request", "The request body must be a JSON object.")

    allowed_fields = {"budget_cents", "seed", "payout_scenario"}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        return _v1_error(
            "unknown_fields",
            "The request contains unsupported fields.",
            field=unknown_fields[0],
        )

    try:
        budget_cents = _required_nonnegative_integer(payload, "budget_cents")
        seed = payload.get("seed", 42)
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed")
        payout_scenario = _parse_payout_scenario(payload)
    except KeyError:
        return _v1_error(
            "invalid_payout_scenario",
            "payout_scenario must contain exactly sena_cents, quina_cents, and quadra_cents.",
            field="payout_scenario",
        )
    except TypeError as exc:
        return _v1_error(
            "invalid_type",
            "The field must be a JSON object.",
            field=str(exc),
        )
    except ArithmeticError as exc:
        return _v1_error(
            "value_out_of_range",
            "The field must not be negative.",
            field=str(exc),
        )
    except ValueError as exc:
        return _v1_error(
            "invalid_type",
            "The field must be an integer.",
            field=str(exc),
        )

    result = plan_megasena_budget(
        budget_cents,
        seed=seed,
        payout_scenario=payout_scenario,
    )

    return jsonify({
        "api_version": "v1",
        "lottery": "megasena",
        "analysis": budget_result_as_dict(result),
        "disclaimer": (
            "Lottery draws are random. This analysis does not predict numbers "
            "or improve jackpot odds through number selection."
        ),
    })


@api.get("/api/results/<lottery>")
@require_token
def results(lottery):
    result_service, _ = services()
    try:
        return jsonify({"lottery": lottery, "results": result_service.history(lottery)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api.post("/api/results/update/<lottery>")
@require_token
def update_results(lottery):
    result_service, _ = services()
    try:
        data = result_service.update_from_api(lottery)
        return jsonify({
            "status": "updated",
            "lottery": lottery,
            "contest": data.get("concurso"),
            "date": data.get("data"),
            "numbers": data.get("dezenas"),
            "next_contest": data.get("proximoConcurso"),
            "mes_sorte": data.get("mesSorte"),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except ProviderError:
        current_app.logger.exception("Lottery provider request failed")
        return jsonify({"error": "external_api_error"}), 502


@api.get("/api/generate/<lottery>")
@require_token
def generate(lottery):
    _, lottery_service = services()
    try:
        return jsonify({
            "lottery": lottery,
            "numbers": lottery_service.generate(lottery),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api.get("/api/stats/<lottery>")
@require_token
def stats(lottery):
    _, lottery_service = services()
    try:
        return jsonify(lottery_service.stats(lottery))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api.post("/api/train/<lottery>")
@require_token
def train(lottery):
    _, lottery_service = services()
    try:
        return jsonify(lottery_service.train(lottery))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
