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
