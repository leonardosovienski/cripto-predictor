# Runbook — a coleta da H6 na máquina Windows

> **Para quem é.** Para a pessoa sentada na máquina de coleta. Tudo aqui roda
> **lá** e em nenhum outro lugar: o `feature_store.db` é gitignored e vive fora do
> repositório (§10.2 do `OVERVIEW_E_ROADMAP_2026-08-21.md`), então nenhuma sessão
> de assistente, nenhum CI e nenhum container consegue executar a coleta por você.
> O que eles conseguem é garantir que, quando o `n` subir, ele seja visível e o
> veredito seja lido corretamente — e isso já está pronto.
>
> **Este documento não autoriza nada.** Nenhum gate deste ecossistema autoriza
> capital, alavancagem ou decisão direta de trading por LLM.

Os comandos estão em blocos `powershell` prontos para colar. Todos assumem que
você está na raiz do repositório, salvo indicação em contrário.

---

## Bloco A — uma vez só (destravar)

### A.1 Conferir a validade do atestado

O atestado de poder vale 7 dias. **Vencido, o Experiment Registry recusa
registrar qualquer trial nova.** Veja onde os dois estão:

```powershell
Get-Content GarimpoInvestimentos\trials.harness_attestation.json | ConvertFrom-Json |
    Select-Object evaluate, metric, edge_verdict, passed_at, expires_at
Get-Content GarimpoInvestimentos\trials.phase1_harness_attestation.json | ConvertFrom-Json |
    Select-Object evaluate, metric, edge_verdict, passed_at, expires_at
```

Estado em 2026-08-21: ambos emitidos `10:44Z`, expirando **`2026-08-28T10:44Z`**.

### A.2 Registrar a renovação diária (item 0.2 — é isto que resolve o prazo)

Um run manual **hoje não grava nada**, e isso é correto: o job carrega
`--if-expiring-within 2`, então só regrava quando faltam menos de 2 dias. O que
destrava o item 0.1 de forma permanente é o agendamento, não um run avulso.

Num **PowerShell elevado** (Executar como Administrador):

```powershell
.\scripts\register_task_attest_renew.ps1
```

O script é idempotente (atualiza em vez de duplicar) e já aplica as duas
configurações que causaram falha silenciosa no passado — energia
(`0x800710E0`) e `LogonType S4U` (`0x80070005`). Ver §10.3 do roadmap.

Teste sem esperar as 21:00:

```powershell
Start-ScheduledTask -TaskName cripto-attest-renew
Get-ScheduledTaskInfo -TaskName cripto-attest-renew | Select-Object LastRunTime, LastTaskResult
```

`LastTaskResult` **0** = OK. Com o vencimento ainda longe, o job roda e **não
grava** — comportamento esperado, não falha. A saída deve terminar com
`"run_status": "SUCCEEDED"`.

> **Se você vir `"run_status": "FAILED"` com `LastTaskResult` 0**, o repositório
> está antes do commit que corrigiu o `exit_statuses` em `jobs.py`. Até
> 2026-08-21 **todo** job desta suíte reportava `FAILED` ao sair com 0 — inclusive
> o `phase1` — porque o dicionário passado substituía o default do `predictor_ops`
> em vez de completá-lo. Atualize o repositório; não é falha da tarefa.

### A.3 Colar o prompt do cron (item 0.3 — prazo seg 2026-08-24 12:00 UTC)

O texto pronto está em [`CRON_H6_PROMPT.md`](CRON_H6_PROMPT.md), no bloco "O
prompt". Cole na rotina **"Watch H6 n>=30 (cripto-predictor)"**, substituindo o
texto inteiro. A convenção declarada naquele arquivo é: **a UI manda**; se você
editar lá, atualize a cópia no mesmo dia.

A ordem entre A.3 e o bloco B não é crítica. Se o cron disparar antes de o
`h6_status.json` existir, ele cai no fallback e conclui em silêncio.

---

## Bloco B — todo dia (a coleta)

### B.1 Rodar o ciclo

As tarefas do Agendador já fazem isso (`GarimpoFase1`, 22:00). Para rodar à mão,
**use os `.bat`** — nunca monte um comando próprio com log em arquivo:

```powershell
.\run_garimpo_fase1.bat    # jobs phase1 + jobs backtest
```

```powershell
.\run_sinal_diario.bat     # ingestão dos 10 fixos + --discover 15 + análise
```

Os dois rodam `uv sync --extra llm --extra excel --extra v3` — os **três** extras
juntos. Sincronizar só `llm+excel` desinstala numpy/scipy/hmmlearn/ccxt e quebra a
família V3 na execução seguinte (auditoria de 2026-08-19).

**Por que não improvisar um handler de log:** o `_RedactSecrets` do `phase1.py`
força `httpx`/`httpcore` para `WARNING`, porque em `INFO` eles logam a URL
completa — com a chave SerpAPI no query string. O log correto sai em
`LOGS_DIR\garimpo_fase1_AAAAMMDD.log`.

### B.2 Publicar o estado da H6

```powershell
uv run python -m GarimpoInvestimentos.quality_snapshot
```

Ele imprime o painel e termina com **uma de três linhas**, que decidem o que
fazer a seguir:

| O que ele imprime | Significa | O que fazer |
|---|---|---|
| `(estado da H6 MUDOU -> h6_status.json atualizado; commite-o...)` | o `n` ou o veredito mudou | **vá para B.3 e commite** |
| `(estado da H6 inalterado — h6_status.json não foi tocado)` | rotina | nada |
| `*** h6_status.json NÃO foi tocado: esta execução viu MENOS previsões maduras...` | **incidente** | **pare e investigue** — ver B.4 |

### B.3 Commitar — o passo que falta sempre

Este é o único caminho pelo qual o `n` sai da máquina de coleta. Sem ele, o cron
semanal e qualquer acompanhamento externo continuam vendo o estado antigo.

```powershell
git add GarimpoInvestimentos\h6_status.json
git commit -m "Publica o estado da H6 (n=<N>)"
git push -u origin <branch>
```

Se a `main` for protegida, faça pelo fluxo de PR normal do repositório — o que
importa é o arquivo chegar à `main`, não o caminho.

**Registro do histórico:** até 2026-08-21 o `h6_status.json` **nunca foi
commitado** — verificado com `git log --all -- GarimpoInvestimentos/h6_status.json`,
que volta vazio. O arquivo não é gitignored (`git check-ignore` sai com 1); ele
existe para ser commitado. A ponte do PR #40 ainda não transportou nada.

Confira que o arquivo tem os dez campos e que o `n` bate com o painel:

```powershell
Get-Content GarimpoInvestimentos\h6_status.json | ConvertFrom-Json |
    Select-Object trial, observed_at, n, gate, gate_atingido, veredito
```

`rho`, `ic_lower`, `ic_upper` e `veredito` vêm **`null` enquanto `n < 30`**. Isso
é a trava funcionando, não dado faltando: `h6_spearman_verdict` devolve `None` de
propósito abaixo do gate, para não expor correlação prematura como se fosse sinal.

### B.4 Se aparecer a recusa por regressão

Previsões são append-only (migração `_0016`), então o `n` elegível **não diminui
por evolução legítima do dado**. Uma queda indica execução degradada: banco vazio
ou apontado para o lugar errado, ou falha de coleta de preço (que depende de
rede). Nesses casos o painel calcula `n=0` sem levantar exceção nenhuma — e a
trava `_h6_regride()` é o que impede um `n=31 / validado` publicado de ser
sobrescrito por `n=0 / veredito=null`.

Antes de qualquer coisa, confirme para onde o banco está apontando:

```powershell
uv run python -c "from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB; print(FEATURE_STORE_DB)"
```

Reset deliberado (só depois de entender a causa): apague o `h6_status.json` e
rode o painel de novo.

---

## Bloco C — vigiar a continuidade

Interrupção de coleta é o modo de falha que **já matou a H4** (encerrada com
n=5). Um gap de dias não só atrasa: muda a composição da amostra.

```powershell
Get-ScheduledTask -TaskName GarimpoFase1, GarimpoV3Daily, cripto-watchdog-coleta, cripto-attest-renew |
    Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult, NextRunTime
```

```powershell
Get-ChildItem (uv run python -c "from GarimpoInvestimentos.core.paths import LOGS_DIR; print(LOGS_DIR)") |
    Sort-Object LastWriteTime -Descending | Select-Object -First 7 Name, LastWriteTime
```

Um dia sem arquivo de log é um dia sem coleta.

**Se a coleta "não rodou e não deixou rastro", comece pelo histórico do
Agendador, não pelo log da aplicação** — os dois modos de falha conhecidos
(`0x800710E0`, `0x80070005`) barram antes do Python ser invocado:

```powershell
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational -MaxEvents 40 |
    Where-Object { $_.Message -match 'Garimpo|cripto-' } |
    Select-Object TimeCreated, Id, Message | Format-List
```

Correções já escritas: `scripts\fix_task_power.ps1`,
`scripts\fix_task_power_watchdog.ps1`, `scripts\fix_task_logon.ps1`.

---

## Bloco D — sanidade (quando mexer no repositório)

```powershell
uv run python -m scripts.freeze_h6_definition --check
```

**Hash divergente é bloqueante até investigação humana.**

```powershell
uv sync --locked --extra test
uv build
uv run pytest -q
```

---

## O que NÃO fazer

Do checklist de invariantes (§8 do roadmap):

- **Não toque no gate `n>=30`.** O critério pré-registrado diz *"n ≥ 30 antes de
  calcular veredito"*; ele **não** diz *"pare em 30"*. Mudar o 30 agora, depois
  de o poder ter sido medido, seria ajuste post-hoc — exatamente o que o
  pré-registro existe para impedir.
- **Não escreva em `trials.json`** por automação. Ele é o denominador do DSR;
  inflá-lo em silêncio corrompe todos os vereditos, passados e futuros.
- **Não edite** `charters/`, `docs/HYPOTHESES.md` nem o `h6_status.json` à mão.
- **Não pare a coleta em n=30.** Em `n=30` o poder é de **14,7%** para um efeito
  real de rho=0,2: um "RUÍDO" ali é **ausência de evidência**, não evidência de
  ausência. O **mesmo** critério, sem nenhuma alteração, chega a 80% de poder por
  volta de **n≈250**. Registre a leitura qualificada pelo poder e **continue
  coletando**.

Na taxa observada da H5 (~24 previsões elegíveis/dia), n=30 chega em ~1,5 dia e
n≈250 em ~10 dias de coleta ininterrupta, mais os 7 dias de maturação do D+7 para
as últimas previsões.
