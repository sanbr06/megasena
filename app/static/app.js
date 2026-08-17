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
  const token = document.querySelector("#token").value;

  try {
    const response = await fetch("/api/v1/megasena/budget-plan", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({budget_cents: budgetCents}),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error?.message || payload.error || "Falha ao calcular o plano.");
    }

    const plan = payload.data.simple_plan;
    document.querySelector("#used-budget").textContent = formatMoney(plan.cost_cents);
    document.querySelector("#games").textContent = plan.games;
    document.querySelector("#jackpot-probability").textContent =
      formatProbability(plan.jackpot_probability);
    document.querySelector("#any-prize-probability").textContent =
      formatOptionalProbability(plan.prize_risk?.any_prize_probability);
    document.querySelector("#multiple-prizes-probability").textContent =
      formatOptionalProbability(plan.prize_risk?.multiple_prizes_probability);
    status.textContent = "Plano calculado com sucesso.";
    results.hidden = false;
  } catch (error) {
    status.textContent = error.message;
  }
});
