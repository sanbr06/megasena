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
