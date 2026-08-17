from math import comb

import pytest

AUTH = {"Authorization": "Bearer test-token"}
ENDPOINT = "/api/v1/analytics/megasena/budget-plan"


def test_budget_plan_v1_exposes_certified_analytics(client):
    response = client.post(
        ENDPOINT,
        headers=AUTH,
        json={"budget_cents": 12_000, "seed": 42},
    )

    assert response.status_code == 200
    body = response.json
    assert body["api_version"] == "v1"
    assert body["lottery"] == "megasena"

    result = body["result"]
    assert result["budget_cents"] == 12_000
    assert result["simple_plan"]["games"] == 20
    assert result["simple_plan"]["globally_optimal_quadra_plus"] is True
    assert result["simple_plan"]["jackpot_probability"] == pytest.approx(
        20 / comb(60, 6)
    )
    assert result["simple_plan"]["prize_risk"]["multiple_prizes_probability"] == 0
    assert result["affordable_single_system_bets"][1]["prize_risk"][
        "multiple_prizes_probability"
    ] > 0


def test_budget_plan_v1_accepts_explicit_payout_scenario(client):
    response = client.post(
        ENDPOINT,
        headers=AUTH,
        json={
            "budget_cents": 4_200,
            "payout_scenario": {
                "sena_cents": 500_000_000,
                "quina_cents": 5_000_000,
                "quadra_cents": 100_000,
            },
        },
    )

    assert response.status_code == 200
    risk = response.json["result"]["simple_plan"]["payout_risk"]
    assert risk["expected_gross_payout_cents"] > 0
    assert risk["payout_variance_cents_squared"] > 0


@pytest.mark.parametrize(
    ("payload", "code", "field"),
    [
        ({}, "missing_field", "budget_cents"),
        ({"budget_cents": "12000"}, "invalid_integer", "budget_cents"),
        ({"budget_cents": True}, "invalid_integer", "budget_cents"),
        ({"budget_cents": -1}, "budget_must_not_be_negative", "budget_cents"),
        ({"budget_cents": 600, "extra": 1}, "unknown_field", "extra"),
        (
            {"budget_cents": 600, "payout_scenario": []},
            "invalid_payout_scenario",
            "payout_scenario",
        ),
        (
            {"budget_cents": 600, "payout_scenario": {"sena_cents": 1}},
            "invalid_payout_scenario",
            "payout_scenario",
        ),
    ],
)
def test_budget_plan_v1_returns_structured_validation_errors(
    client,
    payload,
    code,
    field,
):
    response = client.post(ENDPOINT, headers=AUTH, json=payload)

    assert response.status_code == 400
    assert response.json["error"]["code"] == code
    assert response.json["error"]["field"] == field
    assert response.json["error"]["message"]


def test_budget_plan_v1_rejects_non_object_json(client):
    response = client.post(ENDPOINT, headers=AUTH, json=[])

    assert response.status_code == 400
    assert response.json == {
        "error": {
            "code": "invalid_json_object",
            "message": "Request body must be a JSON object.",
        }
    }


def test_budget_plan_v1_uses_existing_authentication(client):
    response = client.post(ENDPOINT, json={"budget_cents": 600})

    assert response.status_code == 401
    assert response.json == {"error": "token_required"}
