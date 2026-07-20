# Auditoria final local — previsao-cripto — 2026-07-20

> **Adendo operacional:** o risco local de backup/restore citado originalmente
> foi corrigido por `scripts/feature_store_backup.py`. Cinco testes novos passam;
> a suite completa agora registra **320 passed, 2 skipped**. Um roundtrip com o
> banco real confirmou `integrity_check=ok`, 6 tabelas e contagens identicas.
> Retencao/copia externa continuam decisoes humanas; SEC-1 permanece bloqueado.

## 1. Estado inicial

- Branch `main`, worktree inicialmente limpo.
- `HEAD=556f5ad`, um commit local posterior a `origin/main`, contendo a H6 já
  pré-registrada e autorizada. Foi tratado como estado científico existente.
- Vendor `predictor_core` em sincronia: agregado `dc7676a61c86f908`, 44 arquivos.
- Incidente SEC-1 já aberto e não encerrável localmente.

## 2. Incidente de segurança

`SECURITY_INCIDENT_STATUS=BLOCKED_PENDING_SECRET_ROTATION` permanece inalterado.
Os logs contaminados não foram abertos. Para os três arquivos destacados na
missão (13–15/07), a auditoria consultou somente existência, tamanho, timestamp,
SHA-256, ignore e tracking: todos existem, são ignorados e não rastreados.

Varredura estrutural dos arquivos rastreados, sem imprimir valores: zero arquivos
com atribuição aparente de `api_key`, header Bearer literal ou token estrutural
`sk`/`AIza` fora de documentação e testes. A suíte usa somente segredos sintéticos.

## 3. Bug encontrado e correção

Reprodução: `py -3.14 scripts/ci_check.py --fast` falhou na barreira de ASCII
porque `scripts/fix_task_power_watchdog.ps1` continha um travessão U+2014 (três
bytes UTF-8). Essa barreira existe porque PowerShell 5.1 pode interpretar `.ps1`
sem BOM como Windows-1252 e quebrar antes da execução.

Correção: substituição exclusiva do travessão por `--`. Nenhuma ação, parâmetro
ou tarefa do Scheduler foi alterada. A própria CI existente é o teste de regressão.

## 4. Point-in-time, trials e consenso

- A suíte vigente cobre vintage, `available_at`/`observed_at`, timestamps
  inválidos, store bitemporal, maturação, duplicação, truncamento, NaN/Inf,
  falhas de provedor e recuperação.
- H6 mantém trava de dado posterior a `registered_at`; nenhuma hipótese,
  limiar, modelo ou resultado histórico foi alterado nesta auditoria.
- `consensus_median`/`consensus_mean` permanecem sem call site no pipeline ativo.
  Com duas fontes, mediana e média são equivalentes e não oferecem robustez a um
  outlier. A documentação já alerta esse risco; nenhum comportamento foi mudado.

## 5. Testes e verificações

| Comando (cwd: repo) | Resultado | Duração |
|---|---:|---:|
| `py -3.14 -m pytest tests -q` | 315 passed, 2 skipped | 34,03 s |
| `py -3.14 scripts/ci_check.py --fast` (antes) | 1 falha ASCII | 1,13 s |
| mesmo comando (depois) | verde, 7 `.ps1` ASCII + parseados | 1,03 s |
| pytest ops/security/watchdog/trials | 58 passed | 8,97 s |
| pytest `tools/tests/test_operational_runner.py` | 24 passed | 14,80 s |
| `sync_core.py --target previsao-cripto --check` | 44 arquivos em sincronia | — |
| SQLite `PRAGMA integrity_check` read-only | `ok` | — |

Os dois skips da suíte são opcionais e não impediram a cobertura obrigatória.
Nenhuma credencial real ou rede foi usada nos testes.

## 6. Automação (somente leitura)

- `GarimpoFase1`: Ready, S4U, 22:00, resultado 0; coleta e backtest passam pelo
  `operational_runner` no `.bat`.
- `GarimpoV3Daily`: Ready, S4U, 21:30, resultado 0; executa `run_daily_v3.ps1`.
- `cripto-watchdog-coleta`: Ready, S4U, resultado 0; gatilhos 19:00 e 22:30.
- As três têm `StartWhenAvailable=True` e bloqueios de bateria desativados.
- `GarimpoInvestimentos-ColetaDiaria`: Disabled; não há duplicação ativa.

Nenhuma tarefa foi alterada.

## 7. Artefatos e concorrência

`events.jsonl`, `data/v3/events_v3.jsonl`, eventos/heartbeats/logs operacionais,
`.env` e `output/feature_store.db` permanecem ignorados e não foram commitados.
`trials.json` e seu atestado são científicos versionados; não foram modificados.
O banco estava íntegro e sua atividade/timestamp foi tratada como produção real.

## 8. Bloqueios e riscos residuais

- A rotação/revogação humana da SerpAPI, invalidação da chave antiga, teste da
  nova e registro da decisão de retenção dos cinco logs continuam obrigatórios.
- O fallback RSS tem cobertura menor por ativo; `input_degradado=1` pode continuar
  ocorrendo sem constituir regressão.
- Consenso com apenas duas fontes não é robusto contra outlier.
- O gap local de backup/restore do Feature Store foi fechado apos esta auditoria:
  `scripts/feature_store_backup.py` cria snapshot SQLite consistente, manifesta
  SHA-256, verifica integridade e restaura somente em raiz nova. Politica comum
  de retencao e copia externa permanece decisao humana no OP-4.

## 9. Veredito

**BLOQUEADO POR ROTAÇÃO DE CREDENCIAL.** O estado local de código, testes,
vendor, banco e automação é consistente após a correção; o único bloqueio do
veredito limpo exige evidência humana externa e não pode ser inferido.
