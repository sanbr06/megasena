const form = document.querySelector("#budget-form");
const status = document.querySelector("#status");
const results = document.querySelector("#results");
const lotteryNames = {
  megasena: "Mega-Sena",
  lotofacil: "Lotofácil",
  quina: "Quina",
  diadesorte: "Dia de Sorte",
};
const caixaLotteryPages = {
  megasena: "https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx",
  lotofacil: "https://loterias.caixa.gov.br/Paginas/Lotofacil.aspx",
  quina: "https://loterias.caixa.gov.br/Paginas/Quina.aspx",
  diadesorte: "https://loterias.caixa.gov.br/Paginas/default.aspx",
};

const betaFunnelEventName = "megasena:beta-funnel";
const emitBetaFunnelEvent = (event, lottery) => {
  document.dispatchEvent(new CustomEvent(betaFunnelEventName, {
    detail: {
      schema_version: "beta-funnel/v1",
      event,
      lottery,
    },
  }));
};

let portablePortfolio = null;
const budgetCeilingInput = document.querySelector("#budget-ceiling");
const budgetWarning = document.querySelector("#budget-warning");
const budgetCeilingStorageKey = "megasena.personalBudgetCeiling";

let storedBudgetCeiling = null;
try {
  storedBudgetCeiling = localStorage.getItem(budgetCeilingStorageKey);
} catch (error) {
  // The ceiling remains session-only when browser storage is unavailable.
}
if (storedBudgetCeiling !== null) {
  budgetCeilingInput.value = storedBudgetCeiling;
}

const validateBudgetCeiling = () => {
  const budget = Number(document.querySelector("#budget").value);
  const ceilingText = budgetCeilingInput.value;
  const ceiling = Number(ceilingText);
  const exceeded = ceilingText !== "" && Number.isFinite(ceiling) && budget > ceiling;
  budgetWarning.hidden = !exceeded;
  budgetWarning.textContent = exceeded
    ? `O valor solicitado excede seu teto pessoal de ${formatMoney(Math.round(ceiling * 100))}. Reduza o orçamento ou ajuste conscientemente o teto.`
    : "";
  return !exceeded;
};

budgetCeilingInput.addEventListener("change", () => {
  try {
    if (budgetCeilingInput.value === "") {
      localStorage.removeItem(budgetCeilingStorageKey);
    } else if (budgetCeilingInput.checkValidity()) {
      localStorage.setItem(budgetCeilingStorageKey, budgetCeilingInput.value);
    }
  } catch (error) {
    // Keep enforcing the entered value for this session even without persistence.
  }
  validateBudgetCeiling();
});
document.querySelector("#budget").addEventListener("input", validateBudgetCeiling);

const formatMoney = (cents) => new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
}).format(cents / 100);

const formatProbability = (value) => new Intl.NumberFormat("pt-BR", {
  style: "percent",
  maximumFractionDigits: 8,
}).format(value);

const formatOptionalProbability = (value) => (
  value === null || value === undefined
    ? "Não certificado para esta carteira"
    : formatProbability(value)
);

const appendComparisonRow = (body, values) => {
  const row = document.createElement("tr");
  for (const value of values) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(cell);
  }
  body.append(row);
};

const gameText = (game, index) => {
  const numbers = game.numbers.map((number) => String(number).padStart(2, "0")).join(" ");
  const luckyMonth = game.extraSelection?.lucky_month;
  return `Jogo ${String(index + 1).padStart(2, "0")}: ${numbers}${luckyMonth ? ` | Mês de Sorte: ${luckyMonth}` : ""}`;
};

const portfolioText = (portfolio) => [
  `${portfolio.lotteryName}${portfolio.contestNumber === null ? "" : ` | Concurso ${portfolio.contestNumber}`}`,
  `Seed: ${portfolio.seed}`,
  `Versão de preços: ${portfolio.pricingVersion}`,
  `Custo: ${formatMoney(portfolio.costCents)}`,
  "Carteira analítica; não comprova registro de aposta.",
  "",
  ...portfolio.games.map(gameText),
].join("\n");

const csvCell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;

const portfolioCsv = (portfolio) => {
  const rows = [
    ["modalidade", portfolio.lotteryName],
    ["concurso", portfolio.contestNumber],
    ["seed", portfolio.seed],
    ["versao_precos", portfolio.pricingVersion],
    ["custo_centavos", portfolio.costCents],
    ["aviso", "Carteira analítica; não comprova registro de aposta."],
    [],
    ["jogo", "dezenas", "mes_de_sorte"],
    ...portfolio.games.map((game, index) => [
      index + 1,
      game.numbers.map((number) => String(number).padStart(2, "0")).join(" "),
      game.extraSelection?.lucky_month || "",
    ]),
  ];
  return rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
};

const downloadPortfolio = (contents, extension, mimeType) => {
  const blob = new Blob([contents], {type: `${mimeType};charset=utf-8`});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `carteira-${portablePortfolio.lottery}-${portablePortfolio.seed}.${extension}`;
  link.click();
  URL.revokeObjectURL(link.href);
};

const renderTrendChart = (container, draws) => {
  container.replaceChildren();
  if (draws.length === 0) return;

  const namespace = "http://www.w3.org/2000/svg";
  const width = 720;
  const height = 210;
  const padding = {left: 20, right: 20, top: 30, bottom: 20};
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const svg = document.createElementNS(namespace, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");

  for (const fraction of [0, 0.5, 1]) {
    const line = document.createElementNS(namespace, "line");
    const y = padding.top + (plotHeight * fraction);
    line.setAttribute("x1", padding.left);
    line.setAttribute("x2", width - padding.right);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("class", "trend-grid");
    svg.append(line);
  }

  const series = [
    {label: "Soma", key: "sum", className: "trend-sum"},
    {label: "Ímpares", key: "odd_count", className: "trend-odd"},
    {label: "Repetidas", key: "repeated_from_previous", className: "trend-repeated"},
  ];
  series.forEach((definition, seriesIndex) => {
    const values = draws.map((draw) => draw[definition.key]).filter((value) => value !== null);
    if (values.length === 0) return;
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const span = maximum - minimum;
    const points = draws.flatMap((draw, index) => {
      const value = draw[definition.key];
      if (value === null) return [];
      const x = draws.length === 1
        ? width / 2
        : padding.left + ((index / (draws.length - 1)) * plotWidth);
      const normalized = span === 0 ? 0.5 : (value - minimum) / span;
      return [`${x},${padding.top + ((1 - normalized) * plotHeight)}`];
    });
    const polyline = document.createElementNS(namespace, "polyline");
    polyline.setAttribute("points", points.join(" "));
    polyline.setAttribute("class", `trend-line ${definition.className}`);
    svg.append(polyline);

    const label = document.createElementNS(namespace, "text");
    label.setAttribute("x", padding.left + (seriesIndex * 120));
    label.setAttribute("y", 16);
    label.setAttribute("class", `trend-label ${definition.className}`);
    label.textContent = `${definition.label} (${minimum}–${maximum})`;
    svg.append(label);
  });
  container.append(svg);
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  results.hidden = true;
  if (!validateBudgetCeiling()) {
    status.textContent = "Plano não gerado: o orçamento está acima do teto pessoal configurado.";
    budgetWarning.focus();
    return;
  }
  status.textContent = "Calculando…";

  const budgetText = document.querySelector("#budget").value;
  const lottery = document.querySelector("#lottery").value;
  const budgetCents = Math.round(Number(budgetText) * 100);
  const seed = Number(document.querySelector("#seed").value);
  const contestText = document.querySelector("#contest-number").value;
  const token = document.querySelector("#token").value;
  const requestBody = {budget_cents: budgetCents, seed};
  if (contestText !== "") {
    requestBody.contest_number = Number(contestText);
  }
  const allowedSumMin = document.querySelector("#allowed-sum-min").value;
  const allowedSumMax = document.querySelector("#allowed-sum-max").value;
  const allowedOddMin = document.querySelector("#allowed-odd-min").value;
  const allowedOddMax = document.querySelector("#allowed-odd-max").value;
  const allowedMaxOverlap = document.querySelector("#allowed-max-overlap").value;
  if (allowedSumMin !== "") requestBody.allowed_sum_min = Number(allowedSumMin);
  if (allowedSumMax !== "") requestBody.allowed_sum_max = Number(allowedSumMax);
  if (allowedOddMin !== "") requestBody.allowed_odd_min = Number(allowedOddMin);
  if (allowedOddMax !== "") requestBody.allowed_odd_max = Number(allowedOddMax);
  if (allowedMaxOverlap !== "") {
    requestBody.allowed_max_overlap = Number(allowedMaxOverlap);
  }
  const hasGenerationConstraint = [
    allowedSumMin, allowedSumMax, allowedOddMin, allowedOddMax, allowedMaxOverlap,
  ].some((value) => value !== "");

  try {
    const endpoint = lottery === "megasena" && !hasGenerationConstraint
      ? "/api/v1/megasena/budget-plan"
      : `/api/v1/lotteries/${lottery}/simple-budget-plan`;
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message || payload.error || "Falha ao calcular o plano.");
    }

    const isMegaSena = lottery === "megasena" && !hasGenerationConstraint;
    const plan = isMegaSena ? payload.data.simple_plan : payload.data;
    const context = payload.data.generation_context;
    document.querySelector("#portfolio-context").textContent = context.contest_number === null
      ? `${lotteryNames[lottery]} · carteira analítica sem vínculo com concurso específico`
      : `${lotteryNames[lottery]} · concurso ${context.contest_number}`;
    document.querySelector("#used-budget").textContent = formatMoney(plan.cost_cents);
    document.querySelector("#unspent-budget").textContent = formatMoney(plan.unspent_cents);
    document.querySelector("#games").textContent = plan.games;
    document.querySelector("#used-seed").textContent = context.seed;
    document.querySelector("#jackpot-probability").textContent =
      formatProbability(plan.jackpot_probability);
    document.querySelector("#any-prize-probability").textContent = isMegaSena
      ? formatOptionalProbability(plan.prize_risk?.any_prize_probability)
      : "Não calculada para esta modalidade";
    document.querySelector("#multiple-prizes-probability").textContent = isMegaSena
      ? formatOptionalProbability(plan.prize_risk?.multiple_prizes_probability)
      : "Não calculada para esta modalidade";

    const comparisonBody = document.querySelector("#structure-comparison");
    comparisonBody.replaceChildren();
    if (isMegaSena) appendComparisonRow(comparisonBody, [
      "Jogos simples diversificados",
      String(plan.games),
      formatMoney(plan.cost_cents),
      formatMoney(plan.unspent_cents),
      formatProbability(plan.jackpot_probability),
      formatOptionalProbability(plan.prize_risk?.any_prize_probability),
      formatOptionalProbability(plan.prize_risk?.multiple_prizes_probability),
    ]);
    for (const system of payload.data.affordable_single_system_bets || []) {
      appendComparisonRow(comparisonBody, [
        `Aposta sistêmica · ${system.marked_numbers} dezenas`,
        String(system.simple_equivalents),
        formatMoney(system.cost_cents),
        formatMoney(payload.data.budget_cents - system.cost_cents),
        formatProbability(system.jackpot_probability),
        formatOptionalProbability(system.prize_risk?.any_prize_probability),
        formatOptionalProbability(system.prize_risk?.multiple_prizes_probability),
      ]);
    }
    const comparisonEmpty = document.querySelector("#comparison-empty");
    const hasSystemBet = payload.data.affordable_single_system_bets?.length > 0;
    comparisonEmpty.hidden = hasSystemBet;
    comparisonEmpty.textContent = hasSystemBet
      ? ""
      : "Nenhuma aposta sistêmica cabe no orçamento informado.";
    document.querySelector("#system-comparison").hidden = !isMegaSena;

    const gameList = document.querySelector("#generated-games");
    gameList.replaceChildren();
    const normalizedGames = [];
    for (const generatedGame of plan.generated_games || []) {
      const numbers = Array.isArray(generatedGame) ? generatedGame : generatedGame.numbers;
      normalizedGames.push({
        numbers,
        extraSelection: Array.isArray(generatedGame) ? null : generatedGame.extra_selection,
      });
      const item = document.createElement("li");
      item.className = "game-card";
      item.textContent = numbers.map((number) => String(number).padStart(2, "0")).join(" · ");
      const luckyMonth = generatedGame.extra_selection?.lucky_month;
      if (luckyMonth) {
        const extra = document.createElement("span");
        extra.textContent = `Mês de Sorte: ${luckyMonth}`;
        item.append(extra);
      }
      gameList.append(item);
    }

    const hasGeneratedGames = plan.generated_games !== null;
    gameList.hidden = !hasGeneratedGames;
    document.querySelector("#generated-games-title").hidden = !hasGeneratedGames;
    portablePortfolio = normalizedGames.length === 0 ? null : {
      lottery,
      lotteryName: lotteryNames[lottery],
      contestNumber: context.contest_number,
      seed: context.seed,
      pricingVersion: plan.pricing_version,
      simpleGameCostCents: plan.simple_game_cost_cents,
      costCents: plan.cost_cents,
      generationConstraints: plan.generation_constraints || {},
      games: normalizedGames,
    };
    document.querySelector("#portfolio-actions").hidden = portablePortfolio === null;
    document.querySelector("#portfolio-action-status").textContent = "";
    document.querySelector("#caixa-handoff").href = caixaLotteryPages[lottery];
    const explanation = document.querySelector("#portfolio-explanation");
    if (plan.games === 0) {
      explanation.textContent = `O orçamento informado não comporta uma aposta simples de ${lotteryNames[lottery]} nesta versão de preços.`;
    } else if (hasGeneratedGames && isMegaSena) {
      explanation.textContent = "As combinações foram distribuídas para limitar a sobreposição entre pares de jogos. Isso melhora a cobertura certificada de Quadra+, mas não prevê dezenas nem altera a chance de Sena para a mesma quantidade de combinações simples distintas.";
    } else if (hasGeneratedGames) {
      explanation.textContent = "As combinações foram geradas de forma uniforme e reproduzível pelo seed informado. Elas não preveem resultados nem melhoram a probabilidade de uma combinação individual.";
    } else {
      explanation.textContent = "O orçamento excede o limite de geração certificada desta versão. As métricas sem certificado não são apresentadas como se fossem uma carteira concreta.";
    }
    const constraintDisclaimer = document.querySelector("#constraint-disclaimer");
    constraintDisclaimer.hidden = !plan.constraint_disclaimer;
    constraintDisclaimer.textContent = plan.constraint_disclaimer || "";
    status.textContent = "Plano calculado com sucesso.";
    results.hidden = false;
    emitBetaFunnelEvent("portfolio_generated", lottery);
  } catch (error) {
    status.textContent = error.message;
  }
});

const apiToken = () => document.querySelector("#token").value;

const savedPortfolioRequest = (portfolio) => ({
  lottery: portfolio.lottery,
  contest: portfolio.contestNumber,
  games: portfolio.games.map((game) => ({
    numbers: game.numbers,
    extra_selection: game.extraSelection,
  })),
  strategy: {
    name: "portfolio-planner",
    version: "v2.6-ui",
    parameters: portfolio.generationConstraints,
  },
  seed: portfolio.seed,
  cost_snapshot: {
    pricing_version: portfolio.pricingVersion,
    simple_game_cost_cents: portfolio.simpleGameCostCents,
    total_cost_cents: portfolio.costCents,
  },
});

const renderSavedPortfolioCheck = (portfolioId, data) => {
  const section = document.querySelector("#saved-portfolio-check");
  const context = document.querySelector("#saved-portfolio-check-context");
  const events = document.querySelector("#saved-portfolio-events");
  events.replaceChildren();
  section.hidden = false;

  if (data.check === null) {
    context.textContent = `Carteira #${portfolioId}: ${data.message}`;
    return;
  }

  context.textContent =
    `Carteira #${portfolioId}: resultado conferido. Rateios não são inferidos.`;
  if ((data.check.events || []).length === 0) {
    const item = document.createElement("li");
    item.textContent = "Nenhum evento de faixa foi identificado para esta carteira.";
    events.append(item);
    return;
  }
  for (const checkEvent of data.check.events) {
    const item = document.createElement("li");
    item.textContent = checkEvent.message;
    events.append(item);
  }
};

const checkSavedPortfolio = async (portfolioId, lottery) => {
  const savedStatus = document.querySelector("#saved-portfolios-status");
  savedStatus.textContent = `Conferindo carteira #${portfolioId}…`;
  try {
    const response = await fetch(`/api/v1/portfolios/${portfolioId}/check`, {
      method: "POST",
      headers: {"Authorization": `Bearer ${apiToken()}`},
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(
        payload.error?.message || payload.error || "Falha ao conferir a carteira.",
      );
    }
    renderSavedPortfolioCheck(portfolioId, payload.data);
    savedStatus.textContent = "Conferência concluída.";
    emitBetaFunnelEvent("portfolio_result_checked", lottery);
    await loadSavedPortfolios();
  } catch (error) {
    savedStatus.textContent = error.message;
  }
};

const renderSavedPortfolios = (portfolios) => {
  const body = document.querySelector("#saved-portfolios-body");
  body.replaceChildren();

  for (const portfolio of portfolios) {
    const row = document.createElement("tr");
    const values = [
      String(portfolio.id),
      lotteryNames[portfolio.lottery] || portfolio.lottery,
      String(portfolio.contest),
      String(portfolio.games.length),
      formatMoney(portfolio.cost_snapshot.total_cost_cents),
      portfolio.status,
      portfolio.created_at,
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    const actionCell = document.createElement("td");
    const checkButton = document.createElement("button");
    checkButton.type = "button";
    checkButton.textContent = "Conferir";
    checkButton.addEventListener("click", () => {
      checkSavedPortfolio(portfolio.id, portfolio.lottery);
    });
    actionCell.append(checkButton);
    row.append(actionCell);
    body.append(row);
  }
};

const loadSavedPortfolios = async () => {
  const savedStatus = document.querySelector("#saved-portfolios-status");
  savedStatus.textContent = "Carregando carteiras…";
  try {
    const response = await fetch("/api/v1/portfolios", {
      headers: {"Authorization": `Bearer ${apiToken()}`},
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(
        payload.error?.message || payload.error || "Falha ao carregar as carteiras.",
      );
    }
    renderSavedPortfolios(payload.data);
    savedStatus.textContent = payload.data.length === 0
      ? "Nenhuma carteira salva nesta instalação."
      : `${payload.data.length} carteira(s) carregada(s).`;
  } catch (error) {
    savedStatus.textContent = error.message;
  }
};

document.querySelector("#copy-games").addEventListener("click", async () => {
  if (portablePortfolio === null) return;
  const actionStatus = document.querySelector("#portfolio-action-status");
  try {
    await navigator.clipboard.writeText(portfolioText(portablePortfolio));
    actionStatus.textContent = "Jogos e metadados copiados.";
    emitBetaFunnelEvent("portfolio_copied", portablePortfolio.lottery);
  } catch (error) {
    actionStatus.textContent = "Não foi possível copiar automaticamente; use uma exportação.";
  }
});

document.querySelector("#export-txt").addEventListener("click", () => {
  if (portablePortfolio === null) return;
  downloadPortfolio(portfolioText(portablePortfolio), "txt", "text/plain");
  document.querySelector("#portfolio-action-status").textContent = "Arquivo TXT preparado.";
  emitBetaFunnelEvent("portfolio_exported_txt", portablePortfolio.lottery);
});

document.querySelector("#export-csv").addEventListener("click", () => {
  if (portablePortfolio === null) return;
  downloadPortfolio(portfolioCsv(portablePortfolio), "csv", "text/csv");
  document.querySelector("#portfolio-action-status").textContent = "Arquivo CSV preparado.";
  emitBetaFunnelEvent("portfolio_exported_csv", portablePortfolio.lottery);
});

document.querySelector("#save-portfolio").addEventListener("click", async () => {
  if (portablePortfolio === null) return;
  const actionStatus = document.querySelector("#portfolio-action-status");
  if (portablePortfolio.contestNumber === null) {
    actionStatus.textContent =
      "Informe o concurso e gere novamente a carteira antes de salvá-la para acompanhamento.";
    return;
  }

  actionStatus.textContent = "Salvando carteira…";
  try {
    const response = await fetch("/api/v1/portfolios", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiToken()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(savedPortfolioRequest(portablePortfolio)),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(
        payload.error?.message || payload.error || "Falha ao salvar a carteira.",
      );
    }
    actionStatus.textContent =
      `Carteira #${payload.data.id} salva para o concurso ${payload.data.contest}.`;
    emitBetaFunnelEvent("portfolio_saved", portablePortfolio.lottery);
    await loadSavedPortfolios();
  } catch (error) {
    actionStatus.textContent = error.message;
  }
});

document.querySelector("#refresh-saved-portfolios").addEventListener(
  "click",
  loadSavedPortfolios,
);

document.querySelector("#caixa-handoff").addEventListener("click", () => {
  if (portablePortfolio === null) return;
  emitBetaFunnelEvent("official_handoff_opened", portablePortfolio.lottery);
});

const historyForm = document.querySelector("#history-form");
const historyStatus = document.querySelector("#history-status");
const historyResults = document.querySelector("#history-results");

historyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  historyResults.hidden = true;
  historyStatus.textContent = "Carregando histórico…";

  const lottery = document.querySelector("#history-lottery").value;
  const token = document.querySelector("#token").value;
  const parameters = new URLSearchParams();
  for (const [field, elementId] of [
    ["contest_from", "#contest-from"],
    ["contest_to", "#contest-to"],
    ["date_from", "#date-from"],
    ["date_to", "#date-to"],
  ]) {
    const value = document.querySelector(elementId).value;
    if (value !== "") parameters.set(field, value);
  }

  try {
    const query = parameters.toString();
    const endpoint = `/api/v1/lotteries/${lottery}/history-explorer${query ? `?${query}` : ""}`;
    const response = await fetch(endpoint, {
      headers: {"Authorization": `Bearer ${token}`},
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message || payload.error || "Falha ao carregar o histórico.");
    }

    const data = payload.data;
    document.querySelector("#history-context").textContent =
      `${lotteryNames[lottery]} · ${data.draw_count} concurso(s) no recorte`;
    document.querySelector("#history-disclaimer").textContent = data.disclaimer;

    const maximumFrequency = Math.max(0, ...data.number_metrics.map((item) => item.frequency));
    const heatmap = document.querySelector("#frequency-heatmap");
    const metricsBody = document.querySelector("#number-metrics");
    heatmap.replaceChildren();
    metricsBody.replaceChildren();
    for (const metric of data.number_metrics) {
      const intensity = maximumFrequency === 0 ? 0 : metric.frequency / maximumFrequency;
      const cell = document.createElement("span");
      cell.className = "heatmap-cell";
      cell.style.setProperty("--intensity", intensity);
      cell.textContent = String(metric.number).padStart(2, "0");
      cell.title = `Dezena ${metric.number}: ${metric.frequency} ocorrência(s)`;
      heatmap.append(cell);

      appendComparisonRow(metricsBody, [
        String(metric.number).padStart(2, "0"),
        String(metric.frequency),
        metric.draws_since_last_seen === null
          ? "Sem ocorrência no recorte"
          : String(metric.draws_since_last_seen),
      ]);
    }
    renderTrendChart(document.querySelector("#draw-trends"), data.draws);
    const drawMetricsBody = document.querySelector("#draw-metrics");
    drawMetricsBody.replaceChildren();
    for (const draw of data.draws) {
      const bands = draw.band_counts
        .map((band) => `${band.start}–${band.end}: ${band.count}`)
        .join("; ");
      appendComparisonRow(drawMetricsBody, [
        String(draw.contest),
        draw.draw_date || "Data indisponível",
        String(draw.sum),
        String(draw.odd_count),
        String(draw.even_count),
        draw.repeated_from_previous === null
          ? "Sem concurso anterior no recorte"
          : String(draw.repeated_from_previous),
        bands,
      ]);
    }
    historyStatus.textContent = "Histórico carregado.";
    historyResults.hidden = false;
    emitBetaFunnelEvent("history_explored", lottery);
  } catch (error) {
    historyStatus.textContent = error.message;
  }
});

const backtestForm = document.querySelector("#backtest-form");
const backtestStatus = document.querySelector("#backtest-status");
const backtestResults = document.querySelector("#backtest-results");

backtestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  backtestResults.hidden = true;
  backtestStatus.textContent = "Executando backtest sem dados futuros…";

  const lottery = document.querySelector("#backtest-lottery").value;
  const token = document.querySelector("#token").value;
  const requestBody = {
    minimum_training_draws: Number(document.querySelector("#minimum-training-draws").value),
    threshold: Number(document.querySelector("#backtest-threshold").value),
    seed: Number(document.querySelector("#backtest-seed").value),
    significance_level: 0.05,
  };

  try {
    const response = await fetch(`/api/v1/lotteries/${lottery}/walk-forward-backtest`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message || payload.error || "Falha ao executar o backtest.");
    }

    const data = payload.data;
    document.querySelector("#evidence-statement").textContent = data.evidence_statement;
    document.querySelector("#backtest-context").textContent =
      `${lotteryNames[lottery]} · concursos ${data.dataset.contest_from}–${data.dataset.contest_to}`;
    document.querySelector("#backtest-folds").textContent = String(data.folds.length);
    document.querySelector("#challenger-rate").textContent =
      formatProbability(data.challenger_observed_success_rate);
    document.querySelector("#baseline-rate").textContent =
      formatProbability(data.baseline_observed_success_rate);
    document.querySelector("#rate-difference").textContent =
      formatProbability(data.observed_success_rate_difference);
    document.querySelector("#paired-p-value").textContent =
      new Intl.NumberFormat("pt-BR", {maximumFractionDigits: 6}).format(
        data.paired_one_sided_p_value,
      );
    document.querySelector("#backtest-strategies").textContent =
      `Regra avaliada: ${data.challenger_strategy}. Baseline obrigatório: ${data.baseline_strategy}. Seed: ${data.seed}. Limiar: ${data.threshold} acertos.`;
    document.querySelector("#backtest-disclaimer").textContent = data.disclaimer;
    backtestStatus.textContent = "Backtest concluído.";
    backtestResults.hidden = false;
    emitBetaFunnelEvent("walk_forward_completed", lottery);
  } catch (error) {
    backtestStatus.textContent = error.message;
  }
});
