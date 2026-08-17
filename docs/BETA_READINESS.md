# MVP V2 — Beta readiness

Status: **candidate for closed/local beta review**.

Este documento é um gate técnico. Ele não autoriza lançamento público e não
transforma a aplicação em canal de aposta.

## Escopo validado

- Planejamento de carteira por orçamento, com combinações concretas e seed reproduzível.
- Comparação de jogos simples e apostas sistêmicas quando matematicamente aplicável.
- Mega-Sena, Lotofácil, Quina e Dia de Sorte.
- Explorador histórico descritivo.
- Laboratório walk-forward com baseline uniforme e conclusão explícita de evidência.
- Restrições experimentais de soma, paridade, repetição do concurso anterior e sobreposição máxima.
- Carteiras salvas separadas dos resultados oficiais.
- Conferência de carteira contra resultado oficial armazenado.
- Cópia/exportação e handoff somente para páginas oficiais da CAIXA.
- Avisos de jogo responsável, teto pessoal local e rascunhos legais identificados.
- Eventos locais de funil beta sem token, orçamento, dezenas ou carteira no payload.

## Gate automatizado

Antes de marcar um build para revisão:

```bash
python -m ruff check .
pytest -q
node --check app/static/app.js
python -m pip_audit -r requirements.txt
git diff --check
```

CI e Security no GitHub devem estar verdes no commit exato do candidato.

## Smoke test manual

1. Abrir `/` em desktop e viewport móvel.
2. Gerar uma carteira em cada modalidade.
3. Confirmar orçamento, saldo, concurso, seed e combinações.
4. Exercitar soma, paridade, repetição e sobreposição.
5. Salvar uma carteira associada a concurso e recarregar a lista.
6. Conferir carteira com e sem resultado oficial armazenado.
7. Copiar/exportar e abrir somente o handoff oficial da CAIXA.
8. Executar explorador histórico e walk-forward.
9. Confirmar navegação por teclado e foco visível.
10. Confirmar que o token não aparece em URL, localStorage ou telemetria.

## Claims que não podem regressar

- Não afirmar que IA ou filtros preveem dezenas.
- Não converter cobertura em chance de ganhar.
- Não confundir frequência histórica com probabilidade futura.
- Não tratar aposta como investimento.
- Não sugerir recuperação de perdas.
- Não inferir rateios quando os valores oficiais não estiverem disponíveis.
- Não afirmar que copiar/exportar/handoff registra aposta.

## Bloqueios para lançamento público

1. Revisão jurídica final de Termos de Uso e Privacidade/LGPD.
2. Autenticação por usuário; um Bearer token compartilhado não é arquitetura de beta público.
3. HTTPS, servidor WSGI de produção, configuração de segredos e operação/observabilidade.
4. Política de retenção/eliminação de dados de usuário para ambiente compartilhado.
5. Qualquer integração transacional com a CAIXA exige API/parceria/autorização oficial.
6. Revisão final de identidade, suporte e fluxo de incidentes antes de abrir para terceiros.

## Critério de saída do MVP V2

O MVP V2 pode ser chamado de **pronto para revisão de beta fechado/local** quando:

- testes locais passam;
- CI e Security passam no mesmo commit;
- não existe PR corretivo aberto;
- smoke test não encontra bloqueador;
- os bloqueios de lançamento público permanecem explicitamente fora do escopo.
