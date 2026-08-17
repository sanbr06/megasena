import hmac
from functools import wraps

from flask import current_app, jsonify, request


def require_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("API_TOKEN", "")
        if not expected:
            return jsonify({"error": "auth_not_configured"}), 503

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "token_required"}), 401

        token = header.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, expected):
            return jsonify({"error": "invalid_token"}), 403

        return fn(*args, **kwargs)

    return wrapper


def require_token_v1(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("API_TOKEN", "")
        if not expected:
            return _v1_auth_error(
                "auth_not_configured",
                "API authentication is not configured.",
                503,
            )

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return _v1_auth_error(
                "token_required",
                "A bearer token is required.",
                401,
            )

        token = header.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, expected):
            return _v1_auth_error(
                "invalid_token",
                "The bearer token is invalid.",
                403,
            )

        return fn(*args, **kwargs)

    return wrapper


def _v1_auth_error(code, message, status):
    return jsonify({
        "api_version": "v1",
        "error": {
            "code": code,
            "message": message,
        },
    }), status
