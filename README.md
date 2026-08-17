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
