def test_home_exposes_minimal_budget_planner(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b'id="budget-form"' in response.data
    assert b'id="lottery"' in response.data
    assert b'value="diadesorte"' in response.data
    assert b'id="seed"' in response.data
    assert b'id="budget-ceiling"' in response.data
    assert b'id="budget-warning"' in response.data
    assert b'id="contest-number"' in response.data
    assert b'id="generated-games"' in response.data
    assert b'id="portfolio-actions"' in response.data
    assert b'id="copy-games"' in response.data
    assert b'id="export-txt"' in response.data
    assert b'id="export-csv"' in response.data
    assert b'id="caixa-handoff"' in response.data
    assert "não registra uma aposta".encode() in response.data
    assert b'id="structure-comparison"' in response.data
    assert b'id="history-form"' in response.data
    assert b'id="history-lottery"' in response.data
    assert b'id="frequency-heatmap"' in response.data
    assert b'id="number-metrics"' in response.data
    assert b'id="draw-trends"' in response.data
    assert b'id="draw-metrics"' in response.data
    assert b'id="backtest-form"' in response.data
    assert b'id="evidence-statement"' in response.data
    assert "baseline uniforme".encode() in response.data
    assert "não usa dados futuros".encode() in response.data
    assert "Cada série usa sua própria".encode() in response.data
    assert "Padrões".encode() in response.data
    assert b"Simples diversificados" in response.data
    assert b"n\xc3\xa3o influencia as combina\xc3\xa7\xc3\xb5es geradas" in response.data
    assert b'/api/v1/megasena/budget-plan' not in response.data
    assert b"n\xc3\xa3o prev\xc3\xaa" in response.data
    assert "18+ · Aposta não é investimento.".encode() in response.data
    assert "Não tente recuperar perdas.".encode() in response.data
    assert "rascunho sujeito a revisão jurídica".encode() in response.data
    assert "somente em memória".encode() in response.data


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
    assert b"portfolioText" in script.data
    assert b"portfolioCsv" in script.data
    assert b"navigator.clipboard.writeText" in script.data
    assert b"URL.createObjectURL" in script.data
    assert b"caixaLotteryPages[lottery]" in script.data
    assert "não comprova registro de aposta".encode() in script.data
    assert b'/history-explorer' in script.data
    assert b'new URLSearchParams()' in script.data
    assert b'draws_since_last_seen' in script.data
    assert b'maximumFrequency === 0' in script.data
    assert b'renderTrendChart' in script.data
    assert b'draw.repeated_from_previous' in script.data
    assert b'draw.band_counts' in script.data
    assert b'/walk-forward-backtest' in script.data
    assert b'data.evidence_statement' in script.data
    assert b'data.challenger_observed_success_rate' in script.data
    assert b'data.baseline_observed_success_rate' in script.data
    assert b'data.paired_one_sided_p_value' in script.data
    assert b'megasena.personalBudgetCeiling' in script.data
    assert b'localStorage.setItem' in script.data
    assert b'localStorage.removeItem' in script.data
    assert b'if (!validateBudgetCeiling())' in script.data
    assert "Plano não gerado".encode() in script.data
    assert manifest.status_code == 200
    assert manifest.json["start_url"] == "/"
    assert manifest.json["display"] == "standalone"


def test_web_javascript_exposes_privacy_preserving_beta_funnel_hooks(client):
    script = client.get("/static/app.js")

    assert script.status_code == 200
    assert b"megasena:beta-funnel" in script.data
    assert b"beta-funnel/v1" in script.data
    for event in (
        b"portfolio_generated",
        b"portfolio_copied",
        b"portfolio_exported_txt",
        b"portfolio_exported_csv",
        b"official_handoff_opened",
        b"history_explored",
        b"walk_forward_completed",
    ):
        assert event in script.data

    hook_source = script.data.split(
        b"const emitBetaFunnelEvent", maxsplit=1
    )[1].split(b"let portablePortfolio", maxsplit=1)[0]
    assert b"token" not in hook_source
    assert b"budget" not in hook_source
    assert b"numbers" not in hook_source
