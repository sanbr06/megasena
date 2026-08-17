def test_token_required(client):
    response = client.get("/api/stats/megasena")
    assert response.status_code == 401


def test_invalid_token(client):
    response = client.get(
        "/api/stats/megasena",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 403
