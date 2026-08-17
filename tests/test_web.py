def test_home_exposes_minimal_budget_planner(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b'id="budget-form"' in response.data
    assert b'/api/v1/megasena/budget-plan' not in response.data
    assert b"n\xc3\xa3o prev\xc3\xaa" in response.data


def test_web_assets_are_available(client):
    script = client.get("/static/app.js")
    manifest = client.get("/static/manifest.webmanifest")

    assert script.status_code == 200
    assert b'/api/v1/megasena/budget-plan' in script.data
    assert b"Not certified" not in script.data
    assert b"N\xc3\xa3o certificado" in script.data
    assert manifest.status_code == 200
    assert manifest.json["start_url"] == "/"
    assert manifest.json["display"] == "standalone"
