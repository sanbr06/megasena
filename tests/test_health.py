def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_v1_readiness_checks_database_without_authentication(client):
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json == {
        "api_version": "v1",
        "data": {
            "status": "ready",
            "checks": {"database": "available"},
        },
    }


def test_v1_readiness_returns_structured_unavailable_error(app, client, monkeypatch):
    repository = app.extensions["result_repository"]
    monkeypatch.setattr(repository, "is_ready", lambda: False)

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json == {
        "api_version": "v1",
        "error": {
            "code": "service_unavailable",
            "message": "The service is not ready.",
            "details": [
                {"component": "database", "status": "unavailable"},
            ],
        },
    }
