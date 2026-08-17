const form = document.querySelector("#budget-form");
const status = document.querySelector("#status");
const results = document.querySelector("#results");

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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  results.hidden = true;
  status.textContent = "Calculando…";

  const budgetText = document.querySelector("#budget").value;
  const budgetCents = Math.round(Number(budgetText) * 100);
  const seed = Number(document.querySelector("#seed").value);
  const token = document.querySelector("#token").value;

  try {
    const response = await fetch("/api/v1/megasena/budget-plan", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({budget_cents: budgetCents, seed}),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message || payload.error || "Falha ao calcular o plano.");
    }

    const plan = payload.data.simple_plan;
    document.querySelector("#used-budget").textContent = formatMoney(plan.cost_cents);
    document.querySelector("#unspent-budget").textContent = formatMoney(plan.unspent_cents);
    document.querySelector("#games").textContent = plan.games;
    document.querySelector("#used-seed").textContent = seed;
    document.querySelector("#jackpot-probability").textContent =
      formatProbability(plan.jackpot_probability);
    document.querySelector("#any-prize-probability").textContent =
      formatOptionalProbability(plan.prize_risk?.any_prize_probability);
    document.querySelector("#multiple-prizes-probability").textContent =
      formatOptionalProbability(plan.prize_risk?.multiple_prizes_probability);

    const gameList = document.querySelector("#generated-games");
    gameList.replaceChildren();
    for (const game of plan.generated_games || []) {
      const item = document.createElement("li");
      item.className = "game-card";
      item.textContent = game.map((number) => String(number).padStart(2, "0")).join(" · ");
      gameList.append(item);
    }

    const hasGeneratedGames = plan.generated_games !== null;
    gameList.hidden = !hasGeneratedGames;
    document.querySelector("#generated-games-title").hidden = !hasGeneratedGames;
    const explanation = document.querySelector("#portfolio-explanation");
    if (hasGeneratedGames) {
      explanation.textContent = "As combinações foram distribuídas para limitar a sobreposição entre pares de jogos. Isso melhora a cobertura certificada de Quadra+, mas não prevê dezenas nem altera a chance de Sena para a mesma quantidade de combinações simples distintas.";
    } else if (plan.games === 0) {
      explanation.textContent = "O orçamento informado não comporta uma aposta simples de Mega-Sena nesta versão de preços.";
    } else {
      explanation.textContent = "O orçamento excede o limite de geração certificada desta versão. As métricas sem certificado não são apresentadas como se fossem uma carteira concreta.";
    }
    status.textContent = "Plano calculado com sucesso.";
    results.hidden = false;
  } catch (error) {
    status.textContent = error.message;
  }
});
