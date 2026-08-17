from flask import Blueprint, current_app, jsonify

from app.core.security import require_token
from app.providers.lottery_api import ProviderError

api = Blueprint("api", __name__)


def services():
    return (
        current_app.extensions["result_service"],
        current_app.extensions["lottery_service"],
    )


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


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
