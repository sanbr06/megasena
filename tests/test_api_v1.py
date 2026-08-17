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
