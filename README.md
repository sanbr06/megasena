# MegaSena Intelligence

Aplicação Python para coleta, armazenamento, análise estatística e geração de jogos para Mega-Sena, Lotofácil, Quina e Dia de Sorte.

> Loterias são eventos aleatórios. O sistema não prevê resultados nem aumenta matematicamente a probabilidade de um jogo individual. O componente inteligente organiza dados históricos, calcula métricas e gera combinações conforme regras explícitas.

## Arquitetura

- Flask: API HTTP.
- SQLite: persistência local por padrão.
- Repository pattern: isolamento da persistência.
- Serviços: regras de negócio.
- Intelligence: features, pesos e geração estatística.
- Docker: execução reproduzível.
- GitHub Actions: testes, lint e build.

## Execução

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

API: `/health`, `/api/results/<lottery>`, `/api/results/update/<lottery>`, `/api/generate/<lottery>`, `/api/stats/<lottery>`, `/api/train/<lottery>`.

Use `Authorization: Bearer <API_TOKEN>` quando `API_TOKEN` estiver configurado.

## Docker

```bash
docker compose up --build
```

## Testes

```bash
pytest -q
```

## Segurança

- Segredos somente em `.env`/Secrets.
- Nunca colocar tokens na URL.
- `.env` não é versionado.
- Produção deve usar HTTPS e PostgreSQL.
- Debug deve ficar desligado em produção.

## Roadmap

1. Migrar e validar o legado.
2. Aumentar cobertura de testes.
3. PostgreSQL.
4. Observabilidade.
5. CI/CD.
6. Cloud.
7. Kubernetes somente se houver necessidade operacional.

## Backfill histórico

Carrega concursos históricos da CAIXA de forma idempotente:

```bash
python -m app.cli backfill --lottery megasena --start 1 --end 10
python -m app.cli backfill --lottery all --start 1
```

Concursos já existentes no banco são ignorados. O intervalo sem `--end`
usa o concurso mais recente informado pela CAIXA para cada modalidade.

## Mathematical Core

O núcleo matemático mede a estrutura de uma carteira de jogos sem alegar
previsão de sorteios.

Métricas iniciais:

- espaço combinatório total;
- probabilidade exata do prêmio máximo por quantidade de jogos únicos;
- distribuição exata de acertos para um jogo;
- duplicidade e sobreposição entre jogos;
- cobertura de subconjuntos;
- baseline aleatório reproduzível por seed.

Exemplo:

```bash
python -m app.math_core.cli   --lottery megasena   --games 20   --seed 42   --subset-size 4
```

Esse núcleo será a base para Monte Carlo, backtesting e otimização de
carteiras por orçamento.

## Monte Carlo Engine

O Monte Carlo Engine avalia carteiras em sorteios aleatórios simulados.
Ele mede a distribuição do melhor número de acertos da carteira e calcula
intervalos de confiança para probabilidades estimadas.

Exemplo:

```bash
python -m app.math_core.monte_carlo_cli   --lottery megasena   --games 20   --trials 100000   --threshold 4   --seed 42
```

A simulação é reproduzível por seed, executada em chunks para controlar
memória e validada nos testes contra probabilidades combinatórias exatas.

O resultado é uma estimativa de comportamento da carteira sob sorteios
aleatórios, não uma previsão de resultados futuros.

## Strategy Comparator

O comparador coloca estratégias diferentes sob as mesmas condições de
avaliação.

A primeira estratégia experimental é `low_redundancy`: uma heurística
greedy que procura aumentar cobertura de subconjuntos e reduzir
sobreposição entre jogos.

Exemplo:

```bash
python -m app.math_core.compare_cli   --lottery megasena   --games 20   --trials 100000   --threshold 4   --seed 42
```

O relatório compara:

- cobertura combinatória;
- sobreposição média e máxima;
- probabilidade exata do prêmio máximo;
- distribuição Monte Carlo;
- probabilidade simulada de atingir um limiar de acertos.

Com a mesma quantidade de jogos simples únicos, a probabilidade matemática
de Sena permanece igual. O objetivo da estratégia de baixa redundância é
melhorar a estrutura da carteira e a cobertura de faixas inferiores, não
prever o sorteio.
