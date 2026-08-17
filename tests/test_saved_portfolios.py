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


def test_saved_portfolio_check_waits_for_official_result(client):
    created = client.post("/api/v1/portfolios", json=_portfolio(), headers=AUTH)

    response = client.post(
        f"/api/v1/portfolios/{created.json['data']['id']}/check",
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.json["data"]["portfolio"]["status"] == "awaiting_result"
    assert response.json["data"]["check"] is None


def test_saved_portfolio_check_matches_numbers_and_lucky_month(client, app):
    payload = _portfolio(games=[
        {
            "numbers": [1, 2, 3, 4, 5, 6, 7],
            "extra_selection": {"lucky_month": "marco"},
        },
        {
            "numbers": [1, 2, 3, 8, 9, 10, 11],
            "extra_selection": {"lucky_month": "abril"},
        },
    ], cost_snapshot={
        "pricing_version": "caixa-2026-08-17",
        "simple_game_cost_cents": 250,
        "total_cost_cents": 500,
    })
    created = client.post("/api/v1/portfolios", json=payload, headers=AUTH)
    app.extensions["result_repository"].save_result(
        "diadesorte", 1100, "17/08/2026", [1, 2, 3, 4, 5, 6, 7],
        "caixa-loterias", metadata={"mes_sorte": "Março"},
    )

    response = client.post(
        f"/api/v1/portfolios/{created.json['data']['id']}/check",
        headers=AUTH,
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["portfolio"]["status"] == "checked"
    assert data["check"]["games"] == [
        {"game_number": 1, "number_hits": 7, "number_prize_tier": "7_acertos",
         "lucky_month_match": True},
        {"game_number": 2, "number_hits": 3, "number_prize_tier": None,
         "lucky_month_match": False},
    ]
    assert data["check"]["events"] == [{
        "type": "portfolio_game_match", "game_number": 1, "number_hits": 7,
        "number_prize_tier": "7_acertos", "lucky_month_match": True,
        "message": "Jogo 01: 7 acertos",
    }]
    assert data["check"]["payouts"] is None


def test_saved_portfolio_list_returns_most_recent_first(client):
    first = client.post("/api/v1/portfolios", json=_portfolio(), headers=AUTH)
    second = client.post(
        "/api/v1/portfolios",
        json=_portfolio(contest=1101),
        headers=AUTH,
    )

    response = client.get("/api/v1/portfolios", headers=AUTH)

    assert first.status_code == 201
    assert second.status_code == 201
    assert response.status_code == 200
    assert [item["id"] for item in response.json["data"]] == [2, 1]
    assert [item["contest"] for item in response.json["data"]] == [1101, 1100]


def test_saved_portfolio_list_requires_authentication(client):
    response = client.get("/api/v1/portfolios")

    assert response.status_code == 401
    assert response.json == {"error": "token_required"}
