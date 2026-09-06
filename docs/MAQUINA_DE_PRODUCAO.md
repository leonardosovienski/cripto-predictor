# Mapa da máquina de produção — onde cada coisa vive

> **Por que este documento existe.** A informação abaixo estava espalhada por
> oito arquivos (`RUNBOOK_COLETA_H6_WINDOWS.md`, `OVERVIEW_E_ROADMAP`,
> `PANORAMA`, `EVIDENCE_REGISTRY`, `COLLECTION_ONLY_OBSERVATION`,
> `CRON_H6_PROMPT`, `RETROACTIVE_QUALITY`, `README`) e, em parte, **em lugar
> nenhum** — só em scripts de uma branch prestes a ser apagada. Consolidado em
> 2026-09-06.
>
> **Este documento é um mapa, não um runbook.** Ele diz *onde estão as coisas*.
> Para *como rodar a coleta*, veja `RUNBOOK_COLETA_H6_WINDOWS.md`.

O ponto que torna este mapa necessário: **o Feature Store é gitignored**
(`.gitignore`: `output/`, `logs/`). Nenhuma sessão de assistente, CI ou
container enxerga esses dados. Se um caminho não estiver escrito aqui, ele
existe apenas na cabeça de quem senta na máquina.

## Árvore

```
C:\predictor\
├── prod\                                    <- o repositório (git clone)
│   ├── GarimpoInvestimentos\
│   │   ├── trials.json                      <- registro VERSIONADO (26 trials)
│   │   ├── h6_status.json                   <- ponte producao -> git
│   │   ├── trials.harness_attestation.json
│   │   └── trials.phase1_harness_attestation.json
│   ├── scripts\
│   │   ├── safe_pull.ps1                    <- USE ISTO para dar pull (ver abaixo)
│   │   └── forense\                         <- sondas dos bancos (ver abaixo)
│   ├── run_sinal_diario.bat
│   ├── run_garimpo_fase1.bat
│   └── logs\                                <- GITIGNORED
│       └── garimpo_fase1_*.log              <- 5 historicos tem credencial (ver abaixo)
│
├── data\                                    <- DATA_DIR (configuravel)
│   ├── output\                              <- GITIGNORED
│   │   ├── feature_store.db                 <- O HISTORICO OFICIAL
│   │   └── feature_store_backup_antes_limpeza.db
│   ├── failed-runs\
│   │   ├── feature_store-before-first-valid-run-2026-08-09.db
│   │   ├── feature_store-partial-rebuild-2026-08-09.db
│   │   └── feature_store-pre-live-collector-2026-08-09.db
│   └── v3\
│       └── ETHUSDT\spot_1h.csv
│
└── (fora da arvore) C:\restore-tests\previsao-cripto-20260720
                                             <- teste de restore ja executado
```

## Tarefas agendadas (Windows Task Scheduler)

| Tarefa | O que faz | Registrada por |
|---|---|---|
| `GarimpoFase1` | coleta diária (H5 multi-juiz) | manual |
| `GarimpoV3Daily` | pipeline V3 | manual |
| `cripto-watchdog-coleta` | vigia se a coleta parou | manual |
| `cripto-attest-renew` | renova o atestado de poder (`--if-expiring-within 2`) | `scripts\register_task_attest_renew.ps1` |
| `cripto-backup-featurestore` | backup do Feature Store | `scripts\register_task_backup.ps1` |

Duas armadilhas já corrigidas nos scripts de registro, que causaram **falha
silenciosa** no passado: energia (`0x800710E0`) e `LogonType S4U`
(`0x80070005`). Os scripts `fix_task_*.ps1` existem para reaplicá-las.

Conferir se uma tarefa rodou:

```powershell
Get-ScheduledTaskInfo -TaskName cripto-attest-renew | Select-Object LastRunTime, LastTaskResult
```

`LastTaskResult` **0** = OK.

### Rotina obsoleta

Existe uma rotina agendada **fora da máquina** (na conta Claude, não no Windows)
chamada *"Watch H6 n>=30"*, disparando às segundas 12h UTC. Ela vigia uma
hipótese **fechada desde 2026-09-04**. Não faz mal, mas não faz sentido —
apagar quando conveniente. Fica aqui porque não está registrada em nenhum outro
lugar do repositório.

## Logs de resultado (gitignored, citados em `docs/HYPOTHESES.md`)

| Arquivo | Contém |
|---|---|
| `h9_backtest_result.log` | o run da H9 — é dele que sai o `Folds: 45 \| GO: 0 \| NO-GO: 1` |
| `h7_backtest_result.log` | a tentativa abortada da H7 (`transmat_ rows must sum to 1`) |
| `grid_thresholds_log.txt` | a varredura de 16 thresholds de 2026-09-04T02:32:31Z |

Estes três são a **evidência primária** de vereditos já registrados. O
`h9_backtest_result.log` em particular sustenta a ressalva do 1-de-45: 44 dos 45
folds saíram `INSUFFICIENT_DATA`. Se a máquina for reinstalada, eles se perdem e
os vereditos ficam sem lastro verificável.

## A pista aberta: o `n` da H6

**Única ressalva de proveniência ainda não resolvida no registro científico.**

`trials.json` registra a H6 (`h6-sinal-invertido-d7`) com `sharpe = 0.4766`,
carimbado explicitamente com **maturidade DESCONHECIDA**: o valor anterior vinha
com `n=6` (imaturo), e o `n` por trás do 0,4766 não está documentado em lugar
nenhum do repositório. A auditoria de 2026-09-05 não conseguiu recuperá-lo.

`C:\predictor\data\output\feature_store_backup_antes_limpeza.db` é um snapshot
**anterior a uma limpeza** e é o candidato mais provável a conter a resposta:

```powershell
cd C:\predictor\prod
python scripts\forense\check_backup.py
```

A saída traz `total predictions`, a quebra por fonte e o intervalo de `ts` — o
suficiente para datar o número e dizer sobre quantas observações ele foi
medido. Se aparecer, atualize a nota da trial e esta seção.

Isso **não reabre a H6**, que segue `CLOSED_NO_GO` pelo Spearman IC95
(rho −0,057 [−0,231; +0,129], n=84). O Sharpe sempre foi auxiliar, nunca
critério. O que está em jogo é a honestidade do registro, não o veredito.

## Incidente de credencial — não abrir em texto bruto

Cinco logs históricos em `logs\garimpo_fase1_*.log` contêm uma credencial
SerpAPI em texto claro. **Nunca entraram no Git** (a pasta é gitignored). As
chaves foram rotacionadas e isso foi confirmado pelo dono em 2026-08-19; a causa
(wrapper sem redação) está corrigida em
`GarimpoInvestimentos/security/redaction.py`.

Continua pendente, e é ação **externa** — não observável a partir deste
repositório: confirmar no painel do provedor que as chaves antigas foram
**revogadas**, não apenas que novas foram geradas. Registro canônico:
`docs/SECURITY_INCIDENT_SERPAPI.md`.

## Dar pull nesta máquina: use `safe_pull.ps1`

```powershell
cd C:\predictor\prod
.\scripts\safe_pull.ps1
```

Não faça `stash / pull / pop` à mão sobre o `trials.json`. Isso já corrompeu o
registro científico uma vez: uma resolução manual de conflito leu o arquivo como
cp850 e regravou em UTF-8, transformando os travessões das notas em mojibake.

O próprio `safe_pull.ps1` existia para evitar isso desde o PR #84 e **nunca
rodou** — era UTF-8 sem BOM com travessões dentro de strings, e o PowerShell 5.1
lê `.ps1` sem BOM como cp1252, onde o travessão vira uma aspa dupla que fecha a
string e quebra o parser. Corrigido em 2026-09-05 (ASCII puro + BOM), com teste
de regressão em `tests/test_registry_e_scripts_encoding.py`.

## O que roda AQUI e não roda em nenhum outro lugar

Registrado porque foi tentado e falhou num ambiente de auditoria:

- **Qualquer coisa que precise de histórico de Open Interest.** A REST da
  Binance serve só ~30 dias, e `data.binance.vision` está bloqueado pela
  política de rede dos ambientes remotos. O **controle `extra_features=()`**
  do H7/H9 depende disso e por isso segue não rodado (ver
  `docs/HYPOTHESES.md`, "Lacunas conhecidas e NÃO corrigidas").
- **Qualquer leitura do `n` real de uma hipótese.** Vem do `feature_store.db`.
  A única via pela qual esse número sai da máquina é
  `GarimpoInvestimentos/h6_status.json`, gerado pelo `quality_snapshot` e
  **commitado à mão**.

## Sincronizar extras: os três juntos, sempre

```powershell
uv sync --extra llm --extra excel --extra v3
```

Sincronizar só `llm+excel` **desinstala** numpy/hmmlearn/ccxt e quebra a família
V3. Os `.bat` de produção já fazem isso certo; o alerta vale para comando
digitado à mão.
