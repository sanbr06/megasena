from math import comb

import pytest

AUTH = {"Authorization": "Bearer test-token"}


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
