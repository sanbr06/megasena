def test_home_exposes_minimal_budget_planner(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b'id="budget-form"' in response.data
    assert b'id="lottery"' in response.data
    assert b'value="diadesorte"' in response.data
    assert b'id="seed"' in response.data
    assert b'id="contest-number"' in response.data
    assert b'id="generated-games"' in response.data
    assert b'id="structure-comparison"' in response.data
    assert b"Simples diversificados" in response.data
    assert b"n\xc3\xa3o influencia as combina\xc3\xa7\xc3\xb5es geradas" in response.data
    assert b'/api/v1/megasena/budget-plan' not in response.data
    assert b"n\xc3\xa3o prev\xc3\xaa" in response.data


def test_web_assets_are_available(client):
    script = client.get("/static/app.js")
    manifest = client.get("/static/manifest.webmanifest")

    assert script.status_code == 200
    assert b'/api/v1/megasena/budget-plan' in script.data
    assert b'/api/v1/lotteries/${lottery}/simple-budget-plan' in script.data
    assert b"M\xc3\xaas de Sorte:" in script.data
    assert b"Not certified" not in script.data
    assert b"N\xc3\xa3o certificado" in script.data
    assert b"plan.generated_games" in script.data
    assert b"plan.unspent_cents" in script.data
    assert b"affordable_single_system_bets" in script.data
    assert b"system.simple_equivalents" in script.data
    assert b"payload.data.budget_cents - system.cost_cents" in script.data
    assert b"seed" in script.data
    assert b"generation_context" in script.data
    assert b"contest_number" in script.data
    assert manifest.status_code == 200
    assert manifest.json["start_url"] == "/"
    assert manifest.json["display"] == "standalone"
