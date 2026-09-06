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

### O atestado trava por versão do core, não só por prazo

Todo mundo sabe que o atestado expira (7 dias). O que **não estava escrito em
lugar nenhum**: ele também é chaveado pela **versão do core**.

```
trials.harness_attestation.json  ->  "core_version": "3.0.0"
pyproject.toml                   ->  "predictor-core>=3.0.0,<4"
```

O intervalo permitido é toda a linha 3.x, mas o atestado vale para **uma versão
exata**. Um bump de minor — `3.1.0`, um Dependabot, um `uv lock --upgrade` —
invalida o atestado e **bloqueia todo registro de trial** até alguém rodar
`scripts/attest_harness.py` de novo.

O comportamento é fail-closed e está **correto**: um harness não aferido não
deve poder registrar hipótese. O problema é de expectativa — a falha aparece
como recusa de registro, não como "sua dependência subiu de versão". Descoberto
por acidente na auditoria de 2026-09-05, ao errar a versão do core.

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

## ⚠️ Rodar o backtest sem registrar trial sem querer

**Duas flags do `backtest_v3` registram trials de verdade no `trials.json` e
consomem o atestado de poder — sem confirmação, antes de qualquer resultado
aparecer.** Verificado no código (`v3/backtest_v3.py`, `register_trial` nas
linhas 1179 e 1210, ambas dentro de `run_threshold_grid`):

```
--fr-thresholds           -> desvia para run_threshold_grid  -> REGISTRA
--confidence-thresholds   -> desvia para run_threshold_grid  -> REGISTRA
```

O registro acontece **antes** de o WFA rodar (comentário no próprio código:
*"Registra TODAS as combinações antes de olhar qualquer resultado"*). Isso é
deliberado e correto — é o que impede escolher o vencedor depois de ver o
resultado. Mas significa que **uma grade 4×4 gasta 16 tentativas do denominador
do DSR** no instante em que você aperta enter.

Foi exatamente assim que as 16 trials `v3-grid-btcusdt-*` nasceram em
2026-09-04T02:32:31Z e ficaram só nesta máquina até a reconciliação de
2026-09-05.

**`--kelly-fractions` NÃO registra** (`run_kelly_sweep` não chama
`register_trial`) — mas é outra varredura, então trata-se de multiplicidade que
o registro não vê. Use com a mesma consciência.

O caminho simples **não registra nada**:

```powershell
.\.venv\Scripts\python.exe -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT
```

### A armadilha documental

`docs/RISK_MGMT_E_CALIBRACAO_2026-08-27.md` §"Como rodar" apresenta exatamente
o comando da grade:

```
--fr-thresholds 1.5 2.0 2.5 3.0 --confidence-thresholds 0.55 0.60 0.65 0.70
```

**sem dizer que ele registra 16 trials.** Aquele documento é um retrato datado,
e a convenção do projeto é não reescrever registro histórico — então o aviso
mora aqui. Quem seguir aquele doc ao pé da letra gasta 16 tentativas sem saber.

## O controle do H7/H9, quando for rodar

Nunca foi rodado (ver `docs/HYPOTHESES.md`, "Lacunas conhecidas"). Só roda nesta
máquina, porque depende do histórico de OI. **Os dois braços na mesma janela** —
rodar só o baseline num período diferente reintroduz o confundidor que o
controle existe para eliminar:

```powershell
cd C:\predictor\prod
.\.venv\Scripts\python.exe -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT 2>&1 | Tee-Object controle_A_baseline.log
.\.venv\Scripts\python.exe -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT --use-oi-volume-ratio 2>&1 | Tee-Object controle_B_oivol.log
```

Todo o resto no default (fee 10bps, slippage 5bps, horizonte 24h, `fr-window`
90) — idêntico ao que o H9 usou. **Nenhuma outra flag**, pelas razões da seção
acima.

Extrair o que importa:

```powershell
Select-String -Path controle_A_baseline.log,controle_B_oivol.log -Pattern "Folds:|PSR agregado|IC Spearman|Max Drawdown|Sharpe agregado"
git status --short GarimpoInvestimentos/trials.json   # tem que sair VAZIO
```

**Checagem de validade antes de interpretar:** o braço B precisa reproduzir
`Sharpe ≈ −1,0041 / PSR ≈ 0,1621`. Se não bater, o harness mudou e a comparação
está contaminada — investigue isso antes de ler qualquer coisa.

| Resultado | Leitura |
|---|---|
| A ≈ B ≈ −1,0 | a covariável é inocente; o −1,0041 vem do período/harness. O H9 mediu isso, não crowding, e o H7 devolveria o mesmo |
| A ≈ 0 e B ≈ −1,0 | acrescentar covariável exógena degrada de verdade; o H7 está condenado por razão mecânica |
| A pior que B | inesperado — a covariável estaria ajudando, e o desenho do teste precisa de revisão |

Nada disso reabre o H9: ele segue `CLOSED_NO_GO`. O braço B é diagnóstico, não
veredito.

## Estado local desta máquina em 2026-09-05

Registrado porque é a origem de uma cadeia de problemas reais, e some se
ninguém anotar.

**O `main` local estava `[ahead 7, behind 5]`** — 7 commits locais não enviados,
5 do remoto não incorporados. Os locais eram resoluções manuais de conflito:

```
75cea8c Merge branch 'main' ...
baad153 resolve trials.json conflict: merge H9 registration with local state
62cc323 resolve stash conflict: preserve H6 real verdict (n=84, RUIDO) ...
1804213 resolve trials.json conflict: merge H7/H8 upstream registration with local SL/TP grid results
```

Foram essas resoluções à mão — feitas porque o `safe_pull.ps1` não rodava — que
corromperam o encoding do registro científico.

**Arquivos não versionados presentes na raiz:**

| Arquivo | O que é |
|---|---|
| `h9_backtest_result.log` | evidência primária do veredito do H9 |
| `h7_backtest_result.log` | a tentativa abortada do H7 |
| `grid_thresholds_log.txt` | a varredura de 16 thresholds |
| `dxy_history.csv` | **a série do DXY existe aqui** — o H7 era executável |
| `check_predictions.py`, `dump_methods.py`, `test_covtype.py` | sondas avulsas, mesma natureza das de `scripts/forense/` |

`dxy_history.csv` merece destaque: enquanto o charter dizia "coleta não
iniciada", o dado do H7 já estava na máquina e o backtest já tinha sido tentado.

## Sincronizar extras: os três juntos, sempre

```powershell
uv sync --extra llm --extra excel --extra v3
```

Sincronizar só `llm+excel` **desinstala** numpy/hmmlearn/ccxt e quebra a família
V3. Os `.bat` de produção já fazem isso certo; o alerta vale para comando
digitado à mão.
