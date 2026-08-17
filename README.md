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

A interface web mínima em `/` permite gerar carteiras concretas de Mega-Sena,
Lotofácil, Quina e Dia de Sorte. Ela mostra custo, saldo, seed reproduzível e
probabilidade exata do prêmio principal; no Dia de Sorte, o Mês de Sorte é
exibido separadamente das dezenas. Para Mega-Sena, também compara jogos simples
diversificados com as apostas sistêmicas que cabem no mesmo orçamento, sem
recomendar uma estrutura como superior. Um número de concurso opcional identifica
o contexto da carteira, mas não altera sua geração. O token informado fica
somente no formulário e não é armazenado.

Use `Authorization: Bearer <API_TOKEN>` quando `API_TOKEN` estiver configurado.

Carteiras simples reproduzíveis das quatro modalidades estão disponíveis em
`POST /api/v1/lotteries/<modalidade>/simple-budget-plan`, com `budget_cents` e
`seed` no corpo JSON. A resposta usa o snapshot de preços versionado, informa
custo, saldo e probabilidade exata do prêmio principal, e devolve as
combinações concretas. No Dia de Sorte, `lucky_month` aparece em
`extra_selection`, separado das sete dezenas. A geração é limitada a 1.000
jogos por requisição para manter o endpoint local previsível.

O planner comparativo da Mega-Sena também devolve combinações concretas para
até 1.000 jogos. Acima de 20 jogos elas são uniformes e reproduzíveis pelo seed,
mas não recebem o certificado de Quadra+ nem perfis de risco que dependem dele.

O explorador histórico descritivo está disponível em
`GET /api/v1/lotteries/<modalidade>/history-explorer`. Ele aceita os filtros
`contest_from`, `contest_to`, `date_from` e `date_to` (datas ISO `AAAA-MM-DD`) e
retorna frequência/recência por dezena, soma, paridade, repetição em relação ao
concurso anterior dentro do recorte e contagem por faixas de dez dezenas. Essas
métricas descrevem os resultados oficiais armazenados; não predizem sorteios.
A interface em `/` expõe os filtros de concurso e data, uma visualização de
intensidade da frequência e uma tabela acessível equivalente com frequência e
recência por dezena. Ela também apresenta tendências descritivas de soma,
paridade e repetição em SVG, acompanhadas por uma tabela com os valores exatos e
a distribuição das dezenas por faixa.

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

A saída é um registro de experimento `strategy-comparison/v1`. Ela inclui um
identificador determinístico, versões e parâmetros das estratégias, seed,
versão e intervalo dos sorteios sintéticos, métricas e versão do runtime. O
timestamp de execução não participa do identificador, portanto duas execuções
com as mesmas entradas e resultados podem ser reconhecidas como equivalentes.

Com a mesma quantidade de jogos simples únicos, a probabilidade matemática
de Sena permanece igual. O objetivo da estratégia de baixa redundância é
melhorar a estrutura da carteira e a cobertura de faixas inferiores, não
prever o sorteio.

## Scenario Coverage Optimizer

A cobertura de subconjuntos de 4 dezenas fica quase saturada rapidamente em
carteiras pequenas. Por isso, o próximo otimizador trabalha diretamente com
o objetivo operacional: cobrir o maior número possível de sorteios
simulados que resultariam em um limiar de prêmio.

O algoritmo usa um problema de `maximum coverage`:

1. gera um conjunto de jogos candidatos;
2. gera cenários de treino independentes;
3. representa a cobertura de cada jogo por bitsets;
4. seleciona jogos de forma greedy pelo maior ganho marginal;
5. mede o resultado em um conjunto Monte Carlo holdout separado.

Exemplo:

```bash
python -m app.math_core.scenario_cli   --lottery megasena   --games 20   --candidates 1000   --training-scenarios 50000   --holdout-trials 500000   --threshold 4   --seed 42
```

O holdout é obrigatório para evitar que uma carteira pareça melhor apenas
porque foi otimizada sobre os mesmos cenários usados na avaliação.

## Exact Pairwise Prize Dependency

Experimentos com cenários aleatórios não produziram ganho consistente de
`quadra+` fora da amostra. Por isso, o próximo objetivo deixa de aprender
sobre amostras simuladas e passa a usar uma quantidade combinatória exata.

Para dois jogos simples, a probabilidade de ambos atingirem um limiar de
acertos depende apenas da quantidade de dezenas compartilhadas entre eles.
Essa interseção é calculada exatamente.

Para uma carteira, usamos a expansão de Bonferroni de segunda ordem:

`S1 - S2`

onde `S1` é a soma das probabilidades individuais e `S2` é a soma das
interseções entre pares. Esse valor é um limite inferior rigoroso para a
probabilidade de pelo menos um jogo atingir o limiar.

O otimizador procura reduzir `S2`, isto é, reduzir redundância de prêmio
matematicamente mensurável, em vez de otimizar ruído de cenários aleatórios.

Exemplo:

```bash
python -m app.math_core.pairwise_cli   --lottery megasena   --games 20   --threshold 4   --candidates 1000   --restarts 20   --trials 500000   --seed 42
```

O Monte Carlo continua sendo usado como validação independente; a função
objetivo do otimizador é combinatória e exata.

## Provably Optimal Mega-Sena Packing

O experimento exato mostrou que carteiras de 20 jogos podem atingir o limite
superior global de probabilidade de `Quadra+`.

A condição pode ser expressa de forma mais simples: dois jogos de 6 dezenas
só podem fazer `4+` simultaneamente no mesmo sorteio se compartilharem pelo
menos duas dezenas.

Logo, se cada par de jogos da carteira compartilhar no máximo uma dezena,
os eventos de `Quadra+` são disjuntos e:

`P(pelo menos uma Quadra+) = quantidade_de_jogos * P(Quadra+ de um jogo)`

Esse valor é o limite superior universal da união das probabilidades.
Portanto a carteira vem acompanhada de um certificado de ótimo global, sem
Monte Carlo e sem solver.

O gerador implementa isso como um problema de packing de pares: cada jogo
usa 15 pares de dezenas e nenhum par pode ser reutilizado em outro jogo.

Exemplo:

```bash
python -m app.math_core.packing_cli --games 20 --seed 42
```

O certificado vale para a probabilidade de pelo menos uma `Quadra+`. Ele
não altera a probabilidade da Sena para a mesma quantidade de jogos simples
únicos.

## Budget Portfolio Planner

O núcleo matemático agora possui uma camada de orçamento para Mega-Sena.

A versão de preços `caixa-2026-08-17` usa a tabela oficial da CAIXA:
aposta simples de 6 dezenas por R$ 6,00 e apostas de 6 a 20 dezenas.
O custo de uma aposta com `m` dezenas é:

`C(m, 6) * R$ 6,00`

O planner separa duas dimensões que costumam ser confundidas:

- **Sena:** comprar a mesma quantidade de combinações simples produz a mesma
  probabilidade de Sena, independentemente de elas estarem agrupadas em uma
  aposta com mais dezenas ou em jogos simples distintos.
- **Pelo menos uma Quadra+:** agrupar combinações em uma aposta maior cria
  forte sobreposição entre os jogos componentes. Jogos simples bem
  distribuídos podem cobrir mais resultados distintos de `4+`.

Para até 20 jogos simples, o planner usa o gerador de pair-packing e retorna
um certificado de ótimo global para a probabilidade de pelo menos uma
Quadra+.

O resultado também inclui `prize_risk`: probabilidade de qualquer prêmio,
probabilidade de prêmios múltiplos e quantidades esperadas de bilhetes
premiados por faixa. Essas métricas são exatas para apostas sistêmicas e para
carteiras simples com certificado de eventos `4+` disjuntos. Carteiras fora
do limite de certificação não recebem um perfil de risco presumido.

Exemplo:

```bash
python -m app.math_core.budget_cli --budget 120
```

A saída inclui orçamento usado, saldo não utilizado, quantidade de jogos,
probabilidade de Sena, probabilidade certificada de Quadra+ e perfis das
apostas únicas com mais dezenas que cabem no mesmo orçamento.

Por padrão, o planner não presume rateios. Quando recebe um cenário explícito
de pagamentos por faixa, ele também retorna valor esperado, resultado líquido,
ROI e variância para cada aposta sistêmica acessível e para a carteira simples
certificada. Os valores do cenário são hipóteses analíticas, não previsões de
rateios reais.

## Prize Multiplicity and Risk

O Portfolio Planner também separa **probabilidade de ganhar**, **quantidade de
prêmios** e **valor esperado**.

Em apostas com mais de 6 dezenas, um único sorteio pode gerar várias
combinações simples premiadas. Para uma aposta com `m` dezenas que acerta
`h` das 6 dezenas sorteadas, a quantidade de prêmios de uma faixa `r` é:

`C(h, r) * C(m - h, 6 - r)`

para `r = 4, 5, 6`.

Isso reproduz a tabela oficial de multiplicidade da CAIXA. Por exemplo, uma
aposta de 7 dezenas que contém as 6 dezenas sorteadas recebe 1 Sena e 6
Quinas; se contém 5 dezenas sorteadas, recebe 2 Quinas e 5 Quadras.

O engine calcula exatamente:

- probabilidade de pelo menos um prêmio;
- probabilidade de múltiplos prêmios no mesmo sorteio;
- quantidade esperada de Quadras, Quinas e Senas;
- concentração de prêmios;
- valor esperado e variância sob um cenário explícito de rateios.

Com a mesma quantidade de combinações simples e os mesmos valores pagos por
combinação vencedora, o valor esperado bruto é igual por linearidade da
esperança. O que muda entre uma aposta concentrada e jogos diversificados é
a distribuição do risco: cobertura, multiplicidade e variância.

Exemplo estrutural:

```bash
python -m app.math_core.risk_cli --marked-numbers 7
```

Exemplo com um cenário de rateios informado pelo analista:

```bash
python -m app.math_core.risk_cli \
  --marked-numbers 7 \
  --sena-payout 5000000 \
  --quina-payout 50000 \
  --quadra-payout 1000
```

Os valores informados são cenários de análise e não previsões de rateio.

## Analytical API v1

O catálogo protegido `GET /api/v1/lotteries` expõe as quatro modalidades do
produto, seus intervalos, tamanho do sorteio e o snapshot de preço simples
`caixa-2026-08-17`. Em Dia de Sorte, `extra_selection` mantém o "Mês de
Sorte" explícito e separado das sete dezenas; as demais modalidades retornam
esse campo como nulo. O catálogo descreve regras de geração e não atribui
vantagem preditiva a nenhuma modalidade ou seleção.

O planner de orçamento da Mega-Sena está disponível em
`POST /api/v1/megasena/budget-plan`, com o mesmo bearer token das demais
rotas protegidas. Valores monetários são inteiros em centavos.

```json
{
  "budget_cents": 12000,
  "seed": 42,
  "certificate_game_limit": 20
}
```

Um cenário opcional de pagamentos pode ser informado em `payout_scenario`
com `sena_cents`, `quina_cents` e `quadra_cents`. Esses valores são hipóteses
analíticas, não previsões de rateios. A resposta separa probabilidade de Sena,
probabilidade de qualquer prêmio, multiplicidade, valor esperado e variância.

Respostas bem-sucedidas usam o envelope `{"api_version": "v1", "data": ...}`.
Erros de entrada retornam HTTP 400 com `error.code`, `error.message` e uma lista
`error.details` de campos inválidos. Campos desconhecidos são rejeitados para
evitar que erros de digitação alterem silenciosamente a análise.

`GET /health` é uma verificação pública de processo (liveness). A verificação
pública `GET /api/v1/ready` confirma também o acesso ao banco local e usa o
envelope v1; enquanto o banco estiver indisponível, responde HTTP 503 com o
código estruturado `service_unavailable`.

## Strict Walk-Forward Backtesting

O módulo `app.math_core.walk_forward` avalia a heurística histórica de frequência
sem vazamento de dados futuros. Para cada concurso de teste, o jogo da heurística
é construído somente com concursos de número menor. Um jogo aleatório
uniforme, reproduzível por seed, é sempre avaliada nos mesmos concursos.

O relatório mantém separadas as taxas históricas observadas do limiar escolhido,
a média de acertos e a taxa observada de prêmio máximo. Uma alegação de vantagem
histórica só é emitida quando o teste pareado binomial exato, calculado sobre os
resultados discordantes, produz valor-p menor que o nível configurado. Caso
contrário, o resultado declara `no_evidence_of_historical_advantage`.

Esse backtest mede desempenho histórico fora da amostra. Ele não prevê sorteios
futuros e não altera a probabilidade matemática de uma combinação individual.

## Exact Certificates for Supported Lotteries

O certificado de eventos de prêmio disjuntos também pode ser aplicado às
configurações de Lotofácil, Quina e Dia de Sorte. Para uma carteira e um limiar
de acertos informados pelo analista, o cálculo combinatório exato verifica se
dois jogos podem premiar no mesmo sorteio. Se todas as interseções forem nulas,
a probabilidade da carteira é a soma das probabilidades individuais e atinge o
limite superior universal da união.

Essa generalização não presume faixas de prêmio, preços ou pagamentos das
outras loterias: o limiar é uma entrada analítica explícita. O certificado mede
probabilidade de atingir esse limiar, não valor esperado nem probabilidade de
qualquer faixa oficial não modelada.
