AUTH = {"Authorization": "Bearer test-token"}


def _portfolio(**overrides):
    payload = {
        "lottery": "diadesorte",
        "contest": 1100,
        "games": [{
            "numbers": [31, 2, 7, 11, 18, 23, 29],
            "extra_selection": {"lucky_month": "agosto"},
        }],
        "strategy": {
            "name": "uniform-random",
            "version": "1",
            "parameters": {"budget_cents": 250},
        },
        "seed": 17,
        "cost_snapshot": {
            "pricing_version": "caixa-2026-08-17",
            "simple_game_cost_cents": 250,
            "total_cost_cents": 250,
        },
    }
    payload.update(overrides)
    return payload


def test_saved_portfolio_round_trip_is_isolated_from_official_results(client, app):
    created = client.post("/api/v1/portfolios", json=_portfolio(), headers=AUTH)

    assert created.status_code == 201
    data = created.json["data"]
    assert data["id"] == 1
    assert data["status"] == "saved"
    assert data["lottery"] == "diadesorte"
    assert data["contest"] == 1100
    assert data["games"] == [{
        "numbers": [2, 7, 11, 18, 23, 29, 31],
        "extra_selection": {"lucky_month": "agosto"},
    }]
    assert data["strategy"] == _portfolio()["strategy"]
    assert data["cost_snapshot"] == _portfolio()["cost_snapshot"]
    assert data["created_at"]
    assert app.extensions["result_repository"].count_results("diadesorte") == 0

    fetched = client.get("/api/v1/portfolios/1", headers=AUTH)
    assert fetched.status_code == 200
    assert fetched.json["data"] == data


def test_saved_portfolio_requires_bearer_authentication(client):
    response = client.post("/api/v1/portfolios", json=_portfolio())

    assert response.status_code == 401
    assert response.json == {"error": "token_required"}


def test_saved_portfolio_validates_games_and_versioned_cost(client):
    payload = _portfolio(
        games=[{
            "numbers": [2, 2, 7, 11, 18, 23, 32],
            "extra_selection": {"lucky_month": "inexistente"},
        }],
        cost_snapshot={
            "pricing_version": "unverified",
            "simple_game_cost_cents": 200,
            "total_cost_cents": 200,
        },
    )
    response = client.post("/api/v1/portfolios", json=payload, headers=AUTH)

    assert response.status_code == 400
    details = response.json["error"]["details"]
    assert any(item["field"] == "games[0].numbers" for item in details)
    assert any(item["field"] == "games[0].extra_selection" for item in details)
    assert any(item["field"] == "cost_snapshot.pricing_version" for item in details)
    assert any(item["field"] == "cost_snapshot.simple_game_cost_cents" for item in details)


def test_saved_portfolio_not_found_is_structured(client):
    response = client.get("/api/v1/portfolios/999", headers=AUTH)

    assert response.status_code == 404
    assert response.json["error"]["code"] == "portfolio_not_found"


def test_saved_portfolio_malformed_collections_return_validation_error(client):
    response = client.post(
        "/api/v1/portfolios",
        json=_portfolio(lottery={"slug": "megasena"}, games=7),
        headers=AUTH,
    )

    assert response.status_code == 400
    details = response.json["error"]["details"]
    assert {"field": "lottery", "code": "unsupported_lottery"} in details
