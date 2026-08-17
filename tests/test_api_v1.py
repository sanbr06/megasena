from math import comb

import pytest

ENDPOINT = "/api/v1/planners/megasena/budget"
AUTH = {"Authorization": "Bearer test-token"}


def test_budget_planner_v1_exposes_exact_analysis(client):
    response = client.post(
        ENDPOINT,
        headers=AUTH,
        json={"budget_cents": 4_200, "seed": 42},
    )

    assert response.status_code == 200
    assert response.json["api_version"] == "v1"
    assert response.json["lottery"] == "megasena"

    analysis = response.json["analysis"]
    assert analysis["simple_plan"]["games"] == 7
    assert analysis["simple_plan"]["jackpot_probability"] == pytest.approx(
        7 / comb(60, 6)
    )
    assert analysis["simple_plan"]["prize_risk"] is not None
    assert analysis["affordable_single_system_bets"][-1]["marked_numbers"] == 7


def test_budget_planner_v1_accepts_explicit_payout_scenario(client):
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
    assert response.json["analysis"]["simple_plan"]["payout_risk"] is not None


@pytest.mark.parametrize(
    ("payload", "code", "field"),
    [
        ({}, "invalid_type", "budget_cents"),
        ({"budget_cents": -1}, "value_out_of_range", "budget_cents"),
        ({"budget_cents": True}, "invalid_type", "budget_cents"),
        ({"budget_cents": 600, "seed": 1.5}, "invalid_type", "seed"),
        ({"budget_cents": 600, "extra": 1}, "unknown_fields", "extra"),
        (
            {"budget_cents": 600, "payout_scenario": {"sena_cents": 1}},
            "invalid_payout_scenario",
            "payout_scenario",
        ),
    ],
)
def test_budget_planner_v1_returns_structured_validation_errors(
    client,
    payload,
    code,
    field,
):
    response = client.post(ENDPOINT, headers=AUTH, json=payload)

    assert response.status_code == 400
    assert response.json == {
        "api_version": "v1",
        "error": {
            "code": code,
            "message": response.json["error"]["message"],
            "field": field,
        },
    }


def test_budget_planner_v1_rejects_non_json_body(client):
    response = client.post(ENDPOINT, headers=AUTH, data="budget_cents=600")

    assert response.status_code == 415
    assert response.json["error"]["code"] == "unsupported_media_type"


def test_budget_planner_v1_uses_structured_auth_errors(client):
    response = client.post(ENDPOINT, json={"budget_cents": 600})

    assert response.status_code == 401
    assert response.json == {
        "api_version": "v1",
        "error": {
            "code": "token_required",
            "message": "A bearer token is required.",
        },
    }
