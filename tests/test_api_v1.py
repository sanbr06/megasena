from math import comb

import pytest

AUTH = {"Authorization": "Bearer test-token"}


def test_lottery_catalog_exposes_versioned_product_rules(client):
    response = client.get("/api/v1/lotteries", headers=AUTH)

    assert response.status_code == 200
    assert response.json["api_version"] == "v1"
    lotteries = {
        lottery["slug"]: lottery
        for lottery in response.json["data"]["lotteries"]
    }

    assert set(lotteries) == {"megasena", "lotofacil", "quina", "diadesorte"}
    assert lotteries["megasena"] == {
        "slug": "megasena",
        "name": "Mega-Sena",
        "minimum_number": 1,
        "maximum_number": 60,
        "draw_size": 6,
        "simple_game_cost_cents": 600,
        "pricing_version": "caixa-2026-08-17",
        "extra_selection": None,
    }
    assert lotteries["lotofacil"]["simple_game_cost_cents"] == 350
    assert lotteries["quina"]["simple_game_cost_cents"] == 300

    lucky_month = lotteries["diadesorte"]["extra_selection"]
    assert lotteries["diadesorte"]["simple_game_cost_cents"] == 250
    assert lucky_month["key"] == "lucky_month"
    assert lucky_month["label"] == "Mês de Sorte"
    assert lucky_month["quantity"] == 1
    assert len(lucky_month["options"]) == 12
    assert lucky_month["options"][0] == "janeiro"
    assert lucky_month["options"][-1] == "dezembro"


def test_lottery_catalog_preserves_bearer_authentication(client):
    response = client.get("/api/v1/lotteries")

    assert response.status_code == 401
    assert response.json == {"error": "token_required"}


def test_budget_plan_exposes_exact_analytics(client):
    response = client.post(
        "/api/v1/megasena/budget-plan",
        json={"budget_cents": 4_200, "seed": 42},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.json["api_version"] == "v1"
    data = response.json["data"]
    assert data["budget_cents"] == 4_200
    assert data["generation_context"] == {
        "lottery": "megasena",
        "contest_number": None,
        "seed": 42,
    }
    assert data["simple_plan"]["games"] == 7
    assert data["simple_plan"]["jackpot_probability"] == pytest.approx(
        7 / comb(60, 6)
    )
    assert data["simple_plan"]["prize_risk"]["multiple_prizes_probability"] == 0
    assert data["affordable_single_system_bets"][-1]["marked_numbers"] == 7
    assert (
        data["affordable_single_system_bets"][-1]["prize_risk"]
        ["multiple_prizes_probability"]
        > 0
    )


def test_budget_plan_preserves_explicit_contest_context(client):
    response = client.post(
        "/api/v1/megasena/budget-plan",
        json={"budget_cents": 600, "seed": 17, "contest_number": 3000},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.json["data"]["generation_context"] == {
        "lottery": "megasena",
        "contest_number": 3000,
        "seed": 17,
    }


def test_budget_plan_accepts_explicit_payout_scenario(client):
    response = client.post(
        "/api/v1/megasena/budget-plan",
        json={
            "budget_cents": 600,
            "payout_scenario": {
                "sena_cents": 500_000_000,
                "quina_cents": 5_000_000,
                "quadra_cents": 100_000,
            },
        },
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.json["data"]["simple_plan"]["payout_risk"] is not None


@pytest.mark.parametrize(
    ("body", "field", "code"),
    [
        ({}, "budget_cents", "required"),
        ({"budget_cents": True}, "budget_cents", "must_be_integer"),
        ({"budget_cents": -1}, "budget_cents", "must_be_at_least"),
        (
            {"budget_cents": 600, "contest_number": 0},
            "contest_number",
            "must_be_at_least",
        ),
        ({"budget_cents": 600, "extra": 1}, "extra", "unknown_field"),
        (
            {"budget_cents": 600, "payout_scenario": {}},
            "payout_scenario.quadra_cents",
            "required",
        ),
    ],
)
def test_budget_plan_returns_structured_validation_errors(
    client,
    body,
    field,
    code,
):
    response = client.post(
        "/api/v1/megasena/budget-plan",
        json=body,
        headers=AUTH,
    )

    assert response.status_code == 400
    assert response.json["api_version"] == "v1"
    assert response.json["error"]["code"] == "validation_error"
    assert {"field": field, "code": code}.items() <= response.json["error"][
        "details"
    ][0].items()


def test_budget_plan_requires_existing_bearer_authentication(client):
    response = client.post(
        "/api/v1/megasena/budget-plan",
        json={"budget_cents": 600},
    )

    assert response.status_code == 401
    assert response.json == {"error": "token_required"}


@pytest.mark.parametrize(
    ("lottery", "budget", "cost", "quantity", "maximum"),
    [
        ("megasena", 1_300, 600, 6, 60),
        ("lotofacil", 800, 350, 15, 25),
        ("quina", 700, 300, 5, 80),
        ("diadesorte", 600, 250, 7, 31),
    ],
)
def test_simple_budget_plan_generates_supported_lottery_portfolios(
    client,
    lottery,
    budget,
    cost,
    quantity,
    maximum,
):
    response = client.post(
        f"/api/v1/lotteries/{lottery}/simple-budget-plan",
        json={"budget_cents": budget, "seed": 17},
        headers=AUTH,
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["lottery"] == lottery
    assert data["pricing_version"] == "caixa-2026-08-17"
    assert data["games"] == 2
    assert data["cost_cents"] == 2 * cost
    assert data["unspent_cents"] == budget - 2 * cost
    assert data["jackpot_probability"] == pytest.approx(
        2 / data["total_distinct_combinations"]
    )
    assert len(data["generated_games"]) == 2
    assert all(
        len(game["numbers"]) == quantity
        and len(set(game["numbers"])) == quantity
        and all(1 <= number <= maximum for number in game["numbers"])
        for game in data["generated_games"]
    )


def test_dia_de_sorte_models_lucky_month_separately_and_reproducibly(client):
    url = "/api/v1/lotteries/diadesorte/simple-budget-plan"
    first = client.post(
        url,
        json={"budget_cents": 500, "seed": 9},
        headers=AUTH,
    )
    second = client.post(
        url,
        json={"budget_cents": 500, "seed": 9},
        headers=AUTH,
    )

    assert first.json == second.json
    games = first.json["data"]["generated_games"]
    assert games[0]["extra_selection"] == {"lucky_month": "outubro"}
    assert games[1]["extra_selection"] == {"lucky_month": "novembro"}
    assert all(len(game["numbers"]) == 7 for game in games)


def test_simple_budget_plan_preserves_contest_context(client):
    response = client.post(
        "/api/v1/lotteries/quina/simple-budget-plan",
        json={"budget_cents": 600, "seed": 17, "contest_number": 7000},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.json["data"]["generation_context"] == {
        "lottery": "quina",
        "contest_number": 7000,
        "seed": 17,
    }


def test_simple_budget_plan_applies_reproducible_sum_constraint(client):
    url = "/api/v1/lotteries/megasena/simple-budget-plan"
    body = {
        "budget_cents": 1_800,
        "seed": 73,
        "allowed_sum_min": 100,
        "allowed_sum_max": 110,
    }

    first = client.post(url, json=body, headers=AUTH)
    second = client.post(url, json=body, headers=AUTH)

    assert first.status_code == 200
    assert first.json == second.json
    data = first.json["data"]
    assert data["generation_constraints"] == {
        "allowed_sum_min": 100,
        "allowed_sum_max": 110,
    }
    assert all(
        100 <= sum(game["numbers"]) <= 110
        for game in data["generated_games"]
    )
    assert "não prevê resultados" in data["constraint_disclaimer"]


@pytest.mark.parametrize(
    ("body", "field", "code"),
    [
        ({"budget_cents": 600, "allowed_sum_min": 20, "allowed_sum_max": 10},
         "allowed_sum_min", "range_is_reversed"),
        ({"budget_cents": 1_200, "allowed_sum_min": 21, "allowed_sum_max": 21},
         "budget_cents", "exceeds_constrained_combination_space"),
    ],
)
def test_simple_budget_plan_validates_sum_constraint(client, body, field, code):
    response = client.post(
        "/api/v1/lotteries/megasena/simple-budget-plan",
        json=body,
        headers=AUTH,
    )

    assert response.status_code == 400
    assert {"field": field, "code": code} in response.json["error"]["details"]


def test_simple_budget_plan_returns_structured_domain_errors(client):
    unknown = client.post(
        "/api/v1/lotteries/inexistente/simple-budget-plan",
        json={"budget_cents": 600},
        headers=AUTH,
    )
    too_large = client.post(
        "/api/v1/lotteries/quina/simple-budget-plan",
        json={"budget_cents": 300_300},
        headers=AUTH,
    )

    assert unknown.status_code == 404
    assert unknown.json["error"]["code"] == "lottery_not_found"
    assert too_large.status_code == 400
    assert too_large.json["error"]["details"] == [{
        "field": "budget_cents",
        "code": "generation_limit_exceeded",
        "maximum_generated_games": 1_000,
    }]


def test_megasena_budget_plan_returns_concrete_uncertified_portfolio(client):
    response = client.post(
        "/api/v1/megasena/budget-plan",
        json={"budget_cents": 12_600, "seed": 17},
        headers=AUTH,
    )

    assert response.status_code == 200
    plan = response.json["data"]["simple_plan"]
    assert plan["games"] == 21
    assert len(plan["generated_games"]) == 21
    assert plan["certified_quadra_plus_probability"] is None
    assert plan["prize_risk"] is None


def test_megasena_budget_plan_rejects_more_than_generation_limit(client):
    response = client.post(
        "/api/v1/megasena/budget-plan",
        json={"budget_cents": 600_600},
        headers=AUTH,
    )

    assert response.status_code == 400
    assert response.json["error"]["details"] == [{
        "field": "budget_cents",
        "code": "generation_limit_exceeded",
        "maximum_generated_games": 1_000,
    }]


def test_history_explorer_filters_and_returns_descriptive_metrics(app, client):
    repository = app.extensions["result_repository"]
    repository.save_result(
        "megasena", 100, "01/01/2026", [1, 2, 3, 4, 5, 6], "caixa"
    )
    repository.save_result(
        "megasena", 101, "08/01/2026", [1, 2, 10, 11, 20, 60], "caixa"
    )
    repository.save_result(
        "megasena", 102, "15/01/2026", [7, 8, 9, 10, 11, 12], "caixa"
    )

    response = client.get(
        "/api/v1/lotteries/megasena/history-explorer"
        "?contest_from=100&contest_to=101&date_from=2026-01-01",
        headers=AUTH,
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["draw_count"] == 2
    assert data["filters"] == {
        "contest_from": 100,
        "contest_to": 101,
        "date_from": "2026-01-01",
        "date_to": None,
    }
    assert data["draws"][0]["repeated_from_previous"] is None
    assert data["draws"][1] == {
        "contest": 101,
        "draw_date": "2026-01-08",
        "numbers": [1, 2, 10, 11, 20, 60],
        "odd_count": 2,
        "even_count": 4,
        "sum": 104,
        "repeated_from_previous": 2,
        "band_counts": [
            {"start": 1, "end": 10, "count": 3},
            {"start": 11, "end": 20, "count": 2},
            {"start": 21, "end": 30, "count": 0},
            {"start": 31, "end": 40, "count": 0},
            {"start": 41, "end": 50, "count": 0},
            {"start": 51, "end": 60, "count": 1},
        ],
    }
    metrics = {item["number"]: item for item in data["number_metrics"]}
    assert metrics[1] == {"number": 1, "frequency": 2, "draws_since_last_seen": 0}
    assert metrics[3] == {"number": 3, "frequency": 1, "draws_since_last_seen": 1}
    assert metrics[59] == {
        "number": 59,
        "frequency": 0,
        "draws_since_last_seen": None,
    }
    assert "não são previsão" in data["disclaimer"]


@pytest.mark.parametrize(
    ("query", "field", "code"),
    [
        ("contest_from=x", "contest_from", "must_be_integer"),
        ("date_from=01/01/2026", "date_from", "must_be_iso_date"),
        (
            "contest_from=20&contest_to=10",
            "contest_from",
            "range_is_reversed",
        ),
        ("unexpected=1", "unexpected", "unknown_field"),
    ],
)
def test_history_explorer_returns_structured_filter_errors(client, query, field, code):
    response = client.get(
        f"/api/v1/lotteries/megasena/history-explorer?{query}",
        headers=AUTH,
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_error"
    assert {"field": field, "code": code} in response.json["error"]["details"]


def test_walk_forward_api_uses_stored_history_and_mandatory_random_baseline(
    app,
    client,
):
    repository = app.extensions["result_repository"]
    for contest in range(1, 7):
        repository.save_result(
            "megasena",
            contest,
            f"{contest:02d}/01/2026",
            [1, 2, 3, 4, 5, 6],
            "caixa",
        )

    response = client.post(
        "/api/v1/lotteries/megasena/walk-forward-backtest",
        json={
            "minimum_training_draws": 2,
            "threshold": 6,
            "seed": 17,
            "significance_level": 0.05,
        },
        headers=AUTH,
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["version"] == "walk-forward/v1"
    assert data["challenger_strategy"] == "frequency-history/v1"
    assert data["baseline_strategy"] == "uniform-random/v1"
    assert data["dataset"] == {
        "kind": "stored_official_results",
        "draw_count": 6,
        "contest_from": 1,
        "contest_to": 6,
    }
    assert [fold["contest"] for fold in data["folds"]] == [3, 4, 5, 6]
    assert all(
        fold["training_end_contest"] < fold["contest"]
        for fold in data["folds"]
    )
    assert data["evidence_of_advantage"] is False
    assert data["evidence_statement"] == "SEM EVIDÊNCIA DE VANTAGEM"
    assert "não prevê sorteios futuros" in data["disclaimer"]


@pytest.mark.parametrize(
    ("body", "field", "code"),
    [
        ({"minimum_training_draws": 0}, "minimum_training_draws", "must_be_at_least"),
        ({"threshold": 7}, "threshold", "must_be_at_most"),
        ({"significance_level": 1}, "significance_level", "must_be_less_than"),
        ({"significance_level": float("inf")}, "significance_level", "must_be_finite"),
        ({"seed": True}, "seed", "must_be_integer"),
        ({"unexpected": 1}, "unexpected", "unknown_field"),
    ],
)
def test_walk_forward_api_returns_structured_validation_errors(
    client,
    body,
    field,
    code,
):
    response = client.post(
        "/api/v1/lotteries/megasena/walk-forward-backtest",
        json=body,
        headers=AUTH,
    )

    assert response.status_code == 400
    assert {"field": field, "code": code}.items() <= response.json["error"][
        "details"
    ][0].items()


def test_walk_forward_api_reports_insufficient_stored_history(client):
    response = client.post(
        "/api/v1/lotteries/quina/walk-forward-backtest",
        json={"minimum_training_draws": 3},
        headers=AUTH,
    )

    assert response.status_code == 400
    assert response.json["error"]["details"] == [{
        "field": "minimum_training_draws",
        "code": "insufficient_historical_draws",
        "available_draws": 0,
    }]


def test_history_explorer_preserves_auth_and_lottery_domain(client):
    unauthenticated = client.get(
        "/api/v1/lotteries/megasena/history-explorer"
    )
    unknown = client.get(
        "/api/v1/lotteries/inexistente/history-explorer",
        headers=AUTH,
    )

    assert unauthenticated.status_code == 401
    assert unknown.status_code == 404
    assert unknown.json["error"]["code"] == "lottery_not_found"
