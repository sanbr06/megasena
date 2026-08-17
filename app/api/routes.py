from flask import Blueprint, current_app, jsonify, request

from app.core.security import require_token
from app.math_core.budget import budget_result_as_dict, plan_megasena_budget
from app.math_core.prize_multiplicity import PayoutScenario
from app.providers.caixa import ProviderError

api = Blueprint("api", __name__)


def services():
    return (
        current_app.extensions["result_service"],
        current_app.extensions["lottery_service"],
    )


def validation_error(code, message, *, field=None):
    error = {"code": code, "message": message}
    if field is not None:
        error["field"] = field
    return jsonify({"error": error}), 400


def integer_field(data, field, *, required=False, default=None):
    if field not in data:
        if required:
            raise ValueError(field)
        return default

    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(field)
    return value


def payout_scenario_from_request(data):
    if "payout_scenario" not in data:
        return None

    payout = data["payout_scenario"]
    if not isinstance(payout, dict):
        raise ValueError("payout_scenario")

    allowed = {"sena_cents", "quina_cents", "quadra_cents"}
    if set(payout) != allowed:
        raise ValueError("payout_scenario")

    return PayoutScenario(**{
        field: integer_field(payout, field, required=True)
        for field in allowed
    })


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.post("/api/v1/analytics/megasena/budget-plan")
@require_token
def megasena_budget_plan_v1():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return validation_error(
            "invalid_json_object",
            "Request body must be a JSON object.",
        )

    allowed = {"budget_cents", "seed", "payout_scenario"}
    unknown = sorted(set(data) - allowed)
    if unknown:
        return validation_error(
            "unknown_field",
            f"Unknown request field: {unknown[0]}.",
            field=unknown[0],
        )

    try:
        budget_cents = integer_field(
            data,
            "budget_cents",
            required=True,
        )
        seed = integer_field(data, "seed", default=42)
        payout_scenario = payout_scenario_from_request(data)
        result = plan_megasena_budget(
            budget_cents,
            seed=seed,
            payout_scenario=payout_scenario,
        )
    except TypeError as exc:
        field = str(exc)
        return validation_error(
            "invalid_integer",
            f"Field '{field}' must be an integer.",
            field=field,
        )
    except ValueError as exc:
        field = str(exc)
        if field == "budget_cents":
            return validation_error(
                "missing_field",
                "Field 'budget_cents' is required.",
                field=field,
            )
        if field == "payout_scenario":
            return validation_error(
                "invalid_payout_scenario",
                "Payout scenario must contain sena_cents, quina_cents, and quadra_cents.",
                field=field,
            )
        if field == "budget_must_not_be_negative":
            return validation_error(
                field,
                "Field 'budget_cents' must not be negative.",
                field="budget_cents",
            )
        if field == "payouts_must_not_be_negative":
            return validation_error(
                field,
                "Payout scenario values must not be negative.",
                field="payout_scenario",
            )
        raise

    return jsonify({
        "api_version": "v1",
        "lottery": "megasena",
        "result": budget_result_as_dict(result),
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
