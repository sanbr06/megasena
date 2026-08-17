const form = document.querySelector("#budget-form");
const status = document.querySelector("#status");
const results = document.querySelector("#results");
const lotteryNames = {
  megasena: "Mega-Sena",
  lotofacil: "Lotofácil",
  quina: "Quina",
  diadesorte: "Dia de Sorte",
};

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

  try {
    const endpoint = lottery === "megasena"
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

    const isMegaSena = lottery === "megasena";
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
    for (const generatedGame of plan.generated_games || []) {
      const numbers = Array.isArray(generatedGame) ? generatedGame : generatedGame.numbers;
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
    status.textContent = "Plano calculado com sucesso.";
    results.hidden = false;
  } catch (error) {
    status.textContent = error.message;
  }
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
  } catch (error) {
    historyStatus.textContent = error.message;
  }
});
