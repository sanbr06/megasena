from functools import wraps

from flask import current_app, jsonify, request


def require_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("API_TOKEN", "")
        if not expected:
            return fn(*args, **kwargs)

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "token_required"}), 401

        token = header.removeprefix("Bearer ").strip()
        if token != expected:
            return jsonify({"error": "invalid_token"}), 403

        return fn(*args, **kwargs)

    return wrapper
