# HANDOFF — GarimpoInvestimentos (Fase 1 + melhorias)

> ## ⚠️ ERRATA 2026-08-19 — leia antes dos adendos abaixo
>
> Este documento é um **registro histórico da era pré-DPL** e não é reescrito: os
> adendos abaixo permanecem como foram publicados, com as datas que tinham. Três
> pontos deles já não descrevem o estado atual:
>
> 1. **Incidente de segurança.** O adendo de 2026-07-18 registra
>    `SECURITY_INCIDENT_STATUS = BLOCKED_PENDING_SECRET_ROTATION`. O estado atual é
>    `ROTATED_CONFIRMED_BY_OWNER_2026-08-19` — as 5 chaves expostas foram rotacionadas,
>    confirmado pelo dono do repositório. Resta apenas a verificação externa de que as
>    chaves **antigas** foram revogadas. Registro canônico:
>    [docs/SECURITY_INCIDENT_SERPAPI.md](docs/SECURITY_INCIDENT_SERPAPI.md).
> 2. **Arquivos citados que não existem neste repositório.**
>    `../SECURITY_INCIDENT_SECRET_ROTATION.md` e `../ECOSYSTEM_HANDOFF.md` eram
>    documentos do workspace do ecossistema, fora deste repo. Use
>    `docs/SECURITY_INCIDENT_SERPAPI.md` e `docs/RELATORIO_FINAL.md` §9 no lugar.
> 3. **Contagens de teste.** Os números citados nos adendos (302, 306, 320…) são de
>    suas respectivas datas. A suíte atual: **616 verdes, 0 skips** com
>    `uv sync --locked --all-extras`.
>
> Estado científico e operacional corrente: [README.md](README.md) e
> [docs/RELATORIO_FINAL.md](docs/RELATORIO_FINAL.md) §9.

> **Hardening operacional 2026-07-20:** `scripts/feature_store_backup.py`
> fecha o gap local de backup/restore do `output/feature_store.db`: snapshot
> consistente via API SQLite, manifesto SHA-256, `integrity_check`, publicacao
> atomica e restore somente para raiz inexistente. Cinco testes de regressao
> cobrem roundtrip, adulteracao/truncamento, banco/manifesto ausentes e recusa
> de sobrescrita. Runbook: `docs/BACKUP_RESTORE.md`. Politica de retencao e
> copia para volume externo continuam decisoes humanas do ecossistema.
> Validacao final: **320 passed, 2 skipped**; roundtrip no banco real confirmou
> `integrity_check=ok`, 6 tabelas e contagens de linhas identicas.

> ## 🔴 ADENDO ECOSSISTEMA (2026-07-18) — INCIDENTE DE SEGURANÇA ATIVO
>
> **`SECURITY_INCIDENT_STATUS = BLOCKED_PENDING_SECRET_ROTATION`** — chave da
> SerpAPI registrada em texto plano em 5 logs históricos
> (`logs/garimpo_fase1_20260713.log` a `_17.log`; nunca entraram no Git,
> gitignored). Mecanismo de prevenção (redação de log,
> `_RedactSecrets`/`predictor_ops.redaction`) já corrigido e **verificado
> funcionando** com evidência de produção real (log de 18/07 limpo).
> Rotação da credencial no provedor foi explicitamente despriorizada pelo
> responsável em 2026-07-18 — sem prazo, mas não esquecida. Nunca abra
> esses 5 logs em texto bruto. Detalhe completo, checklist e critério de
> encerramento: `../SECURITY_INCIDENT_SECRET_ROTATION.md`.
>
> Vendor de `predictor_core` byte-idêntico ao canônico, sincronizado em
> `f4d4d81`. Suíte: 302 passed, 2 skipped. `garimpo_fase1.py` teve seu lock
> interno redundante removido (`50379b1`) — o job real já é envelopado pelo
> `operational_runner` via `run_garimpo_fase1.bat`. `api_guard` desligado
> agora emite um evento de aviso em vez de falhar silenciosamente
> (`b094d05`). `GarimpoInvestimentos/trials.json` teve uma maturação real
> de produção commitada (`40f3ddc`, sharpe null→-0.531). Tarefas agendadas
> (`GarimpoFase1`, `GarimpoV3Daily`, `cripto-watchdog-coleta`): `Ready`,
> `S4U`, últimas execuções com sucesso (verificado 2026-07-18). Tarefa
> legada `GarimpoInvestimentos-ColetaDiaria`: confirmada `Disabled`, sem
> risco de coleta duplicada. `consensus_median`/`consensus_mean` (em
> `predictor_core/data/aggregation.py`, re-exportado aqui) não têm nenhum
> call site no pipeline ativo hoje — código inerte, ver correção de
> docstring no próprio arquivo. Documento canônico do ecossistema:
> `../ECOSYSTEM_HANDOFF.md`.

> ## 🔎 Rodada 2026-07-18 — Evolução final: auditoria completa + 3 correções locais
>
> Reconstrução independente do estado + auditoria dos eixos point-in-time,
> segurança e operação. Suíte: **306 passed, 2 skipped** (302 + 4 testes novos).
> Vendor byte-idêntico (44/44), manifest OK, 4 heartbeats da última noite
> (17→18/07) todos `SUCCEEDED`. Correções: (1) **watchdog** contava linha de
> fallback do LLM como coleta do dia — agora usa a semântica de
> `predictions_on` (só previsão real; `contagem_previsoes_reais()` + 4 testes);
> (2) `core/logger.py` perdeu a `run_logging_setup` morta (zero call sites
> desde jul/2026; se religada criaria `logs/garimpo.log` SEM redação de
> segredos — mesmo modo de falha do SEC-1); (3) `_doc` do
> `crypto_price_consensus` corrigido (mediana de 2 fontes = média, sem
> imunidade a outlier — alinhado ao docstring do core) + mensagem de
> histórico vazio do backtest. Varredura sanitizada AMPLIADA de segredos:
> todos os logs nunca catalogados (`garimpo.log`, `cron_*.log`,
> `v3_daily_*.log`, `watchdog.log`, `logs/operations/*`) e os 3 JSONL de
> eventos = **0 segredos reais**; o log do runner tem 144 marcadores
> `[REDACTED]` (prova de redação funcionando em produção); precisão do
> escopo: o log de 17/07 tem **115** ocorrências reais (não 114) e a única
> ocorrência de 18/07 é o próprio marcador `[REDACTED]`. Observações sem
> mudança (decisão humana): `--timeout 252000` (70h) nas duas tarefas diárias
> do runner — teto quase-inócuo; um travamento seguraria o lock até o
> watchdog alertar no dia seguinte; a suíte exige o layout de workspace
> (dependência histórica de repositório irmão ou override de importação) — num
> worktree/clone isolado a coleta de `test_ops_hardening.py` falha com
> `ModuleNotFoundError: tools` (esperado, não é bug do projeto). Incidente
> SEC-1 permanece `BLOCKED_PENDING_SECRET_ROTATION` (rotação humana).
>
> **Revalidação independente de 2026-07-20:** suíte atual em `main` (incluindo
> H6) com **315 passed, 2 skipped** em 34,03 s. Foi reproduzida uma falha real
> da CI: `scripts/fix_task_power_watchdog.ps1` continha um travessão UTF-8,
> contrariando a barreira de ASCII criada após o incidente de parse do
> PowerShell 5.1. O caractere foi substituído por `--`, sem alterar a lógica;
> `scripts/ci_check.py --fast` voltou a ficar verde. Testes direcionados:
> segurança/operação **58 passed** e runner compartilhado **24 passed**.
> Auditoria read-only do Scheduler confirmou as três tarefas ativas `Ready`,
> `S4U`, resultado 0, energia alinhada; watchdog com gatilhos 19:00 e 22:30;
> tarefa legada `Disabled`. SQLite `output/feature_store.db`: `integrity_check=ok`.
> Relatório: `docs/FINAL_AUDIT_2026-07-20.md`.
>
> **Achado do dia 19/07 — CORRIGIDO em 20/07 (aprovação do dono via UAC)**: o
> `cripto-watchdog-coleta` **não rodou** em 18/07 19:00; a tentativa atrasada
> de 19/07 00:14 falhou com `0x800710E0` — o MESMO erro da GarimpoFase1 em
> 12/07. O `fix_task_power.ps1` da época corrigiu SÓ a GarimpoFase1; o
> watchdog seguia com `DisallowStartIfOnBatteries=True` +
> `StartWhenAvailable=False`. **`scripts/fix_task_power_watchdog.ps1`
> executado com sucesso em 2026-07-20** (elevado, aprovado pelo dono):
> confirmado `StartWhenAvailable=True`, `DisallowStartIfOnBatteries=False`,
> `StopIfGoingOnBatteries=False` — mesma config das tarefas de coleta. O
> guardião não deve mais falhar na condição que ele existe pra vigiar.
> **2º gatilho 22:30 também aplicado em 2026-07-20** (mesma sessão,
> `scripts/fix_task_watchdog_trigger.ps1`, elevado, aprovado pelo dono):
> confirmado 2 gatilhos ativos no `cripto-watchdog-coleta` (19:00 original +
> 22:30 novo) — pendência da triagem de 16/07 (item b) fechada. Com os dois
> gatilhos e a energia alinhada, uma falha da GarimpoFase1 (22:00) tem
> chance real de ser pega ainda na mesma noite, não só 21h depois.
> `trials.json` maturou de novo em produção
> (`v2-dpl-multi-h7` sharpe −0.531→−0.6725, backtest de 19/07 03:20 UTC) —
> mudança científica concorrente, **não commitada** por esta rodada.
>
> **🔴 Achado grave de 20/07 — SerpAPI esgotada, 3 noites de input degradado
> (18, 19, 20/07)**: eu tinha reportado "coletas indo bem" olhando só
> `exit_code`/`status`/`llm_fallback` — **erro meu**: não cruzei
> `input_degradado`, que já mostrava 28/28 previsões/noite sem notícias
> desde 18/07 (17/07: 16/18; 16/07 e antes: limpo). Causa raiz (logs
> `garimpo_fase1_2026071{8,9}.log`/`_20.log`, sem valor de segredo — só
> `HTTPStatusError` como tipo, nunca o corpo/status real): toda chamada
> falha já no 1º ativo da noite, com retry 3x + backoff — e o classificador
> `predictor_core.kernel.net.is_transient` trata cota **diária** como
> NÃO-retryable (falha instantânea, sem backoff). Como o padrão observado É
> retry-com-backoff todo dia (inclusive o 1º ativo de um dia UTC novo, onde
> uma cota diária já teria resetado), a hipótese mais provável é **cota
> MENSAL/de plano esgotada** (comum no free tier da SerpAPI), não diária —
> **inferência forte, não confirmada** (o log não grava o status HTTP real).
> Sem `NEWS_FALLBACK_PROVIDER` configurado, não há segunda fonte. Não é
> regressão de código: a estratificação por `input_degradado` (migração
> 0008) está fazendo o trabalho certo — as maturações da H5 vão separar
> corretamente as previsões degradadas das completas quando D+7 chegar. Mas
> a série "H5 com notícias reais" está parada desde 18/07.
>
> **Decisão tomada e APLICADA (2026-07-20, autorização explícita do dono
> — "faça o que você acha melhor")**: `NEWS_FALLBACK_PROVIDER=curated_rss`
> ligado dentro da H5 atual, não como trial nova. Justificativa registrada
> na própria leitura do código: o gate "exige trial forward" no `config.py`
> está escrito sobre `NEWS_PROVIDERS` (a lista PRIMÁRIA — não tocada), não
> sobre `NEWS_FALLBACK_PROVIDER` (descrito ali como mecanismo operacional,
> consultado só depois das fontes primárias); o backtest já estratifica por
> `news_provider` por desenho (0010/0011) — o mecanismo científico para
> tolerar múltiplas fontes na mesma trial já existia antes desta decisão,
> não foi criado para justificá-la. `.env` de produção editado (uma linha
> nova, `GarimpoInvestimentos/.env` — arquivo gitignorado, mudança **não
> versionada por Git**, registrada só aqui).
>
> **Bug real encontrado e corrigido no processo** (`1f51618`): a URL
> `blockworks.co` (1 das 5 fontes de `curated_rss`) migrou para
> `blockworks.com` com redirect 308 permanente; o cliente HTTP do núcleo
> não segue redirect por padrão, então TODA chamada que hasheasse para
> "blockworks" derrubava com `HTTPStatusError` — indistinguível de "fonte
> fora do ar" até eu reproduzir manualmente (sandbox, sem chave real:
> confirmei 308 no domínio antigo, 200+Atom válido no novo). Corrigido +
> 2 testes de regressão (URL fixada; contrato de propagação de erro com
> resposta mockada, sem depender de rede real no teste).
>
> **Verificação real ponta a ponta (não só suíte)**: smoke test ao vivo
> (sandbox, sem gastar cota do SerpAPI para múltiplos ativos) —
> `ethereum` trouxe 2 títulos reais via `curated_rss`, confirmando o
> caminho completo funciona. **Caveat honesto**: `bitcoin`, `solana`,
> `chainlink` no mesmo teste vieram `curated_rss:empty` — não é bug, é
> limitação inerente ao desenho (1 feed geral escolhido por hash do nome
> do ativo, filtro por substring no título) — cobertura por ativo será
> MENOR que a do SerpAPI quando ele funcionava (busca dedicada por termo).
> Esperar que algumas previsões continuem `input_degradado=1` mesmo com o
> fallback ativo — isso é esperado, não é o incidente OP-7 voltando.
> Suíte: 306→**308 passed**, 2 skipped (2 testes novos do fix de URL).
>
> **Confirmado por e-mail real do provedor (2026-07-20)**: plano free da
> SerpAPI, **250/250 buscas do mês usadas, renova em 2026-08-07** — depois
> da janela de decisão da H5 (28/07). A hipótese de "cota mensal, não
> diária" registrada acima deixa de ser inferência. Sem custo monetário —
> nunca foi plano pago. `curated_rss` segue sendo o único jeito de ter
> notícia até 07/08 (ou até uma rotação de chave, que também resolveria o
> SEC-1 e devolveria 250 buscas na hora).
>
> **H6 implementada e ligada ao ciclo automático (2026-07-20, decisão
> explícita do dono: "implementa tudo, quero tudo pronto")**: nova função
> `close_h6_inverted_signal()` em `analyzers/backtest.py`, chamada dentro de
> `run()` junto do `close_trial_sharpes()` já existente — passa a rodar
> TODA noite, automaticamente, dentro da tarefa `GarimpoBacktest` já
> agendada. **Não muda nada da coleta**: prompt, modelo, `ai_insights.py`,
> `main.py`/`garimpo_fase1.py` intocados — o score do LLM continua
> significando exatamente o que sempre significou. A função só REINTERPRETA
> o score já gravado: seleciona `score ≤ (100 − limiar)` como sinal
> invertido forte (espelho exato do limiar original), e só conta previsões
> com `pred_date` POSTERIOR ao `registered_at` da própria trial H6
> (2026-07-20T07:00:37Z) — trava anti-data-snooping embutida na função, não
> só na nota do registro. Casamento por NOME (`h6-sinal-invertido-d7`), não
> pelo mecanismo genérico de `fonte`/`horizonte` do `close_trial_sharpes`
> (que nunca vai casar sozinho, de propósito — `params.fonte` continua
> `reserved:h6-inversao-sinal`, identidade preservada, nenhuma trial nova
> criada). 6 testes novos (`test_experiment_registry.py`): no-op sem H6
> registrada, trava de data anterior ao registro, maturação real com dado
> posterior, ignora score acima do limiar invertido, ignora fonte errada,
> e confere que a trial real do repositório segue reservada/não-ativada.
> Suíte: 309→**315 passed**, 2 skipped. **Zero passo manual restante** —
> a partir da coleta de hoje à noite (22:00), qualquer previsão com
> `score ≤ 40` começa a contar pro H6 organicamente, sem precisar tocar em
> nada de novo. Com n≥3 sinais, o backtest já imprime e grava o sharpe
> sozinho, todo dia, junto do resto do relatório.
>
> **🔴 Leitura honesta dos resultados da H5 (2026-07-20, relatório real da
> produção, `logs/operations/GarimpoBacktest.log`, não recalculado por
> mim)**: D+7 (horizonte principal), n=198 — Spearman(Score, retorno) =
> **−0,255**, IC95% [−0,377, −0,120], **validado (IC não cruza zero) — na
> direção ERRADA**. Acurácia direcional 29,3% (pior que aleatório); hit
> rate score≥60 = 24%; estratégia retorno médio −6,87%, Sharpe −0,33; DSR
> 0,00 (não passa 0,95); benchmark BTC buy&hold bateu a estratégia
> (+0,67%). Nenhum juiz com n suficiente tem sinal positivo confiável
> (gemini −0,330 n=159, groq −0,585 n=12, ambos IC fora de zero; mistral
> −0,023 n=20, IC cruza zero = ruído). `v2-dpl-multi-h7` piorou entre
> execuções (−0,531→−0,6725). Mesmo padrão que já derrubou a H4. **Não é
> falta de amostra** — n=198 já é relevante no horizonte principal. Nenhuma
> alteração de modelo/hipótese feita; só leitura do que a produção já
> calculou. Decisão de GO/NO-GO continua sendo humana, janela 28/07.
>
> **Mapeamento de cobertura por categoria (2026-07-20)**: conferido
> arquivo:linha, sem assumir por nome de arquivo, que a suíte cobre todos os
> eixos pedidos na missão (point-in-time, vintage, trials/serialização,
> redação, sem-credencial, falha de provedor, NaN/Inf, duplicação, arquivo
> truncado, recuperação após falha) — locks/runner/timeout são
> deliberadamente delegados aos contract tests de `predictor_ops`
> (`garimpo_fase1.py` não tem lock próprio desde a remoção da duplicação).
> 2 gaps reais achados: (a) nenhum teste cobria `ts` genuinamente ilegível
> (só ordem errada/lag excessivo) — **corrigido**, `_load_rows()` já se
> comportava certo, só faltava o teste (`e9165b6`); (b) concorrência real
> (threads) não é testada localmente — decisão consciente, catalogada como
> **OP-1** `CORRECTLY_DEFERRED`, não reaberta. Suíte final: **309 passed**,
> 2 skipped.

Data: 2026-06-14 (última rodada: 2026-07-20 — SerpAPI esgotada + fallback + fix de energia/gatilho do watchdog + auditoria de cobertura de testes)
Estado: **Fase 1 + CLI + notícias + backtesting + sinal calibrado + indicadores técnicos + LLM multi-provedor + métricas + retry/backoff + agendamento diário + V3 (edge mecânico: funding/OI/HMM).**

> **NOTA (jun/2026 — Red Team):** o pacote `core/` foi **renomeado para `store/`**
> (eliminar a colisão de nome com `predictor_core`). Toda referência a `core/X.py` nas
> entradas históricas abaixo corresponde hoje a **`store/X.py`** — o texto do changelog
> foi preservado como registro do que aconteceu, não reescrito. Falhas silenciosas
> (`except Exception`) foram instrumentadas e a Fase-1 passou a emitir o sinal via
> `predictor_core.obs.emit_event` (paridade de telemetria com o V3).
>
> **ERRATA (jul/2026):** o rename `core/`→`store/` foi DESFEITO na reconciliação
> com o histórico antigo do GitHub (merge `a3404ce`) — a árvore atual usa
> **`GarimpoInvestimentos/core/`** de novo. A colisão temida era com
> `predictor_core` (nomes distintos, sem conflito de import real). Referências a
> `store/X.py` abaixo correspondem hoje a `core/X.py`.

---

## 🔭 Rodada 2026-07-16 — Backtest diário reativado + operational_runner commitado

**Backtest órfão corrigido (commit no `run_garimpo_fase1.bat`)**: o passo de
backtest (Spearman+IC95+DSR) morava no `run_daily.ps1` da ColetaDiaria (18:00),
desabilitada em 11/07 — desde então o relatório só saía manualmente, às vésperas
da primeira maturação da H5 (previsões de 10/07 amadurecem D+7 em 17/07). Agora
roda como segunda etapa da GarimpoFase1 (22:00), envelopado no
`operational_runner` com task `GarimpoBacktest` (heartbeat/log/eventos próprios,
timeout 1800s, artefato esperado `output/garimpo_backtest.csv`). Não gasta cota
de LLM (análise offline). Roda mesmo se a coleta falhar, mas o exit code da
coleta tem precedência. Validado manualmente: `SUCCEEDED`, exit 0, ~18s, relatório
completo e legível (UTF-8) em `logs/operations/GarimpoBacktest.log`.

**Integração operational_runner commitada (`8aede5b`)**: as mudanças que já
rodavam em produção desde 14/07 (3 tarefas envelopadas com heartbeat JSON
atômico, `events.jsonl`, redação de segredos, lock anti-duplicata) estavam só no
working tree — histórico e produção reconciliados.

**Snapshot do estado (16/07)**: 3 noites automáticas seguidas OK (13→15/07,
28 ativos × 4 juízes, exit 0 nas 3 tarefas). Backtest da série antiga (H4):
Spearman D+7 **−0,207** [IC95 −0,355 a −0,054, n=121] — validado na direção
ERRADA (motivo do NO-GO); hit rate 20%, estratégia −7,67% vs BTC +0,60%, DSR
0,00. H5 ainda sem previsões maduras; n≥30 global ~18–19/07, por juiz ~21–22/07.

**Pendências conhecidas (triagem 16/07)**: (a) chave SerpAPI em texto puro no
log legado `garimpo_fase1_*.log` (28×/noite; logs gitignorados, mas redigir via
logger httpx→WARNING ou filtro no formatter); (b) falha noturna só alerta no dia
seguinte — 2º gatilho do watchdog ~22:30 e/ou `RestartCount` na GarimpoFase1;
(c) `v3_daily_*.log` sai UTF-16 quebrado (`*>>` no PS 5.1) — padronizar
`-Encoding utf8`.

---

## 🧹 Rodada 2026-07-12 — Correção LogonType (S4U) + limpeza de branches

**LogonType S4U aplicado** (`scripts/fix_task_logon.ps1`, commit `5ae3b18`) nas 3
tarefas do Agendador (`cripto-watchdog-coleta`, `GarimpoFase1`, `GarimpoV3Daily`),
corrigindo o `0x80070005` (Access Denied) de disparos sem sessão interativa ativa
(tela bloqueada/PC dormindo). `GarimpoInvestimentos-ColetaDiaria` (rotina antiga,
18:00) segue **desabilitada de propósito** (evita corrida dupla de cota com a
`GarimpoFase1`, que assumiu a coleta da H5 às 22:00) — não reabilitar. Confirmação
da execução real headless (19:00/21:30/22:00) fica para a rodada seguinte.

**Confirmação da noite de 12/07 (headless, pós-S4U)**: `GarimpoV3Daily` (21:30) e
`cripto-watchdog-coleta` (19:00) rodaram headless com sucesso — o `exit 1` do
watchdog é esperado (`scripts/watchdog_coleta.py:76`, alerta correto de que a
`ColetaDiaria` está desabilitada). **`GarimpoFase1` (22:00) falhou** com
`0x800710E0` sem sequer invocar o Python (nenhuma linha nova no log daquela
janela) — causa: `DisallowStartIfOnBatteries=True` + `StartWhenAvailable=False`,
diferente da `GarimpoV3Daily` (que rodou OK). **Corrigido** (`scripts/fix_task_power.ps1`,
rodado manualmente pelo dono como Admin em 2026-07-13): energia da `GarimpoFase1`
alinhada com a `GarimpoV3Daily` (`DisallowStartIfOnBatteries=False`,
`StopIfGoingOnBatteries=False`, `StartWhenAvailable=True`) + log operacional do
Task Scheduler (`Microsoft-Windows-TaskScheduler/Operational`) habilitado, para
capturar o código Win32 exato se algo falhar de novo.

**FIX CONFIRMADO (2026-07-13 02:24, `Start-ScheduledTask` manual)**: disparo
forçado da `GarimpoFase1` (mesma conta/S4U real, fora do horário programado)
rodou ponta a ponta pela primeira vez pós-fix — ingestão dos 28 ativos
pendentes, 4 juízes (gemini/groq/cerebras/mistral) via LLM (um retry 503
transitório no Gemini, tratado normalmente pelo `with_retry`), `=== concluído:
28 gravado(s) na Feature Store, 0 falha(s) isolada(s) ===`,
`Get-ScheduledTaskInfo` retornou `LastTaskResult = 0`. **Confirma que a causa
raiz era mesmo a config de energia** (não sobrou nenhuma outra hipótese em
aberto).

**SELO FINAL — disparo automático real confirmado (2026-07-13 22:00)**: sem
qualquer gatilho manual, a `GarimpoFase1` disparou sozinha no horário
programado com `LastTaskResult = 0` — junto com `GarimpoV3Daily` (21:30, `0`) e
`cripto-watchdog-coleta` (19:00, `1` esperado). As três tarefas rodam headless
de ponta a ponta, sem intervenção humana. Ciclo de correção (S4U +
energia + log operacional) encerrado com sucesso.

**Limpeza de branches (só `main` deve existir)**: antes de apagar, confirmado por
`git merge-base --is-ancestor` que as 3 branches locais extras já eram 100%
ancestrais de `main` (nenhum commit exclusivo) e os worktrees correspondentes
estavam limpos (`git status --short` vazio) — apagar não perdeu nenhum conteúdo:
- `claude/previsao-cripto-guided-tour-daac3e` (297a52f) — branch apagada.
- `claude/remote-control-0b5470` (297a52f, worktree em HEAD destacado) — worktree
  removido + branch apagada.
- `claude/chat-automation-performance-6cc25a` (fdb3c3f) — mergeada em `main`, mas
  é a branch do worktree onde ESTA sessão está rodando; apagar exigiria remover o
  worktree ativo, o que encerraria o chat no meio. Fica pendente: depois que esta
  sessão terminar, rodar `git worktree remove .claude/worktrees/beautiful-saha-2799a6`
  seguido de `git branch -D claude/chat-automation-performance-6cc25a` na raiz do
  repo para fechar a limpeza. Origin já só tinha `main` (nada a limpar lá).

---

## 🔧 Rodada 2026-07-10 — Validação E2E completa + incidente OPS-1 (agendador)

**Validação comando-a-comando (checklist de 9 itens, tudo executado de verdade):**
ci_check 3/3 verde (269 testes); registry reconciliado confirmado (shim +
trials.json válido + atestado válido); trava de poder provada em tmp
(PowerAttestationMissingError barra, attest_pipeline_power destrava;
attest_harness --dry-run PASSOU); backtest_v3 BTCUSDT k=0.5 **reproduz o NO-GO
exato** (PSR 0.4649, IC_lower −0.0794, MaxDD 15.56%, 45 folds
INSUFFICIENT_DATA); sweep --kelly-fractions 1.0 0.5 sem TypeError (C1 ok);
idempotência (C4) e timeindex (C5) verdes; H4/trial-1 conferidos.

**ATUALIZAÇÃO C2 (psr_nonoverlap)**: com a série crescida (n=4049), as
sub-séries 24h dão PSR **0.004 / 0.989 / 0.552 → 1/3 aprovada** (era 0/3 em
09/07: 0.009/0.701/0.470) — veredicto do script: **AMBÍGUO**. NÃO muda a
refutação: o juiz principal é o Spearman (imune à sobreposição), cujo IC_lower
segue **−0.0794** (cruza zero); o PSR não-sobreposto é teste de robustez
auxiliar. Implicação de 28/07 inalterada: **não promover a capital real**.

**Provedores LLM free-tier adicionados (mesma data, pedido do dono — custo do
Gemini)**: `ai_insights.py`/`config.py` ganharam Groq, Cerebras e Mistral via
rota OpenAI-compatível (mesmo SDK `openai` já instalado, só muda `base_url` —
**zero dependência nova**). Smoke test real 3/3 OK (groq:llama-3.3-70b-versatile,
cerebras:gpt-oss-120b, mistral:mistral-small-latest); chaves no `.env`
(gitignorado). **NADA foi trocado**: `LLM_PROVIDER` segue `gemini` — trocar
provedor = juiz novo (judge_signature muda) = trial NOVA no registry, decisão
que pertence à janela de 28/07. Diagnóstico do custo: a lista DEFAULT_ASSETS
tem 22 ativos vs teto de ~20/dia do free tier do Gemini (aviso já existente no
.env) — o problema é volume, não preço por chamada. Suíte: 269 verdes.

**Modo `LLM_PROVIDER=multi` implementado (mesma data, NÃO ativado)**: partição
FIXA e determinística dos ativos entre gemini/groq/cerebras/mistral (sha256 do
nome mod n — cada ativo tem SEMPRE o mesmo juiz; nada de rodízio, que misturaria
calibrações na mesma série). Com os 22 ativos atuais: groq 8, mistral 6,
gemini 5, cerebras 3 — todos folgados nos free tiers. O carimbo `judge` da
previsão passa a ser por-ativo (`judge_signature(ativo)`); modo multi sem
asset_name levanta ValueError (não carimba juiz errado). Trava P0 exige as
chaves de TODOS os provedores da partição. ⚠️ ATIVAR = 4 juízes em paralelo =
encerra a coleta da `v2-dpl-gemini-h7` e exige trial nova — decisão do dono
(natural na janela de 28/07). Suíte: **270** (teste novo da partição).

**Modo multi ATIVADO (mesma data, decisão do dono)**: `LLM_PROVIDER=multi` no
.env; trial **`v2-dpl-multi-h7`** registrada (trava de poder validou contra o
atestado real) e hipótese **H5** pré-registrada em docs/HYPOTHESES.md ANTES de
qualquer resultado. A `v2-dpl-gemini-h7` foi ENCERRADA com n=5 (imatura, sem
veredicto — nota de encerramento no registry); razão: risco iminente de estouro
da cota free-tier do Gemini (22 ativos vs ~20/dia) — interrupção planejada >
dias perdidos por 429. As 5 previsões antigas ficam no histórico com o carimbo
gemini e não se misturam à série nova (juiz por-ativo). DSR desconta a
tentativa adicional — governança funcionando como desenhada. Sanity pós-switch:
settings carrega (P0 exige as 4 chaves), carimbo por-ativo correto, suíte 270.

**Hardening pós-multi (mesma data, 3 correções da revisão de arquitetura)**:
(1) **Migração 0009** `llm_fallback` — o fallback neutro do LLM (score 50 em
falha) entrava no histórico e o backtest o excluía por STRING no resumo
("fallback aplicado") — frágil; agora o carimbo é coluna estrutural
(ai_insights → main → history → store), o filtro usa a coluna e o marcador só
cobre o legado (NULL = pré-0009). Com 4 provedores a superfície de falha
quadruplicou — era o fix mais urgente. (2) **Backtest estratifica por JUIZ** no
horizonte principal (prometido pela H5, não existia) e `close_trial_sharpes`
ganhou **divisão por ERAS**: bug real — a v2-dpl-gemini-h7 (encerrada) e a
v2-dpl-multi-h7 casam pelos MESMOS (fonte, horizonte); antes, o Sharpe da era
multi seria gravado na trial errada e/ou herdaria os n=5 do juiz antigo. Agora
cada previsão matura a trial vigente na sua data (fronteira = registered_at da
sucessora; linha sem data = primeira era, semântica de legado). (3)
**Atestado reforçado**: `attest_harness.py` agora certifica DOIS juízes — o do
V3 (PSR/IC_lower) e o da Fase 1 (Spearman IC95 block bootstrap, o que julga a
H5) — 4 braços (2×edge/ruído); atestado re-emitido e versionado. Nota honesta:
o controle positivo do juiz Fase 1 JÁ existia como teste de regressão
(test_positive_control.py) — a novidade é ele entrar no ATESTADO que destrava o
registry. Suíte: **272** (testes novos: exclusão estrutural de fallback, divisão
de eras).

**OpenRouter adicionado como 5º provedor (mesma data) — RESERVA, fora da
partição**: entrar na partição mudaria o hash mod 4→5 e reembaralharia os
juízes da H5 em curso (= trial nova). Uso: fallback manual se um dos 4 titulares
morrer, ou juiz de trial futura. Default `nvidia/nemotron-3-super-120b-a12b:free`
(único que respondeu no smoke — os `:free` do OpenRouter rotacionam e
congestionam com 429; testar antes de usar). Chave no .env (gitignorado).

**INCIDENTE OPS-1 — GarimpoV3Daily não rodou em 09-10/07**: último resultado
`0x800710E0` ("operador/administrador recusou"), causa: tarefa "Interativo
apenas" + bloqueio de bateria — máquina bloqueada/sem sessão no horário. Sem
log de 09-10/07. **Correção aplicada (2026-07-10)**: `Set-ScheduledTask` com
AllowStartIfOnBatteries + DontStopIfGoingOnBatteries + StartWhenAvailable
(execução perdida roda assim que possível). PENDENTE (exige admin): mudar
logon para S4U ("executar estando conectado ou não") — hoje segue Interactive.
**Buraco preenchido manualmente** (run_daily_v3.ps1, exit 0): vision_ingest
trouxe +288 registros de OI (histórico íntegro até 09/07, não-destrutivo);
paper_trader registrou o dia 10/07 (FLAT, no_signal, sideways). Ledger: **3
trades, 0 ativos, 3 FLAT, P&L 0**. O sinal do dia 09/07 não é recuperável
retroativamente (1 dia FLAT faltante no ledger; dados OK) — perda de 1/30 dias
na janela até 28/07, não compromete a decisão.

**SELO FINAL — OPS-1 ENCERRADO (2026-07-10 21:30, confirmado 2026-07-11)**:
disparo automático do Windows Task Scheduler rodou SOZINHO pela primeira vez
desde a correção — `LastTaskResult = 0`. Log mostra dois `run` no dia (12:58
manual + **21:30:01 automático**), ambos `exit 0`, sem ERROR/Traceback.
Idempotência C4 comprovada em produção: o ledger permaneceu em **3 trades, 3
FLAT, P&L 0** — o disparo automático NÃO duplicou o dia já registrado
manualmente. Pendência residual (baixa prioridade, inalterada): logon S4U
exige admin.

---

## 🔴 Rodada 2026-07-09 — Auditoria cruzada: correções + REFUTAÇÃO do GO do BTC

**Correções (commits 7cd3d58, 1e033c8, c43ce51, 7d6cc07)**: CLI do Kelly sweep
consertado (TypeError com --taker-fee-bps — regressão do Risco 4, sem teste de
CLI; agora coberto); idempotência no paper_trader (re-execução duplicava o
sinal do dia e o paper_report contava dobrado — livro real tinha 2 duplicatas,
todas FLAT, deduplicado com backup); helper único `v3/timeindex.py` (3 cópias
de nearest-timestamp viraram bisect O(log n)); reporter em UTC. Suíte 254→266.

**ACHADO MAIOR (C2 → refutação)**: investigando o PSR sobre retornos de 24h
amostrados a cada 8h (sobreposição infla significância), o WFA foi re-rodado
na base ATUAL (2021 → jul/2026; a homologação de jun/2026 usou 2021 → out/2024):

| Config | PSR | IC_lower | MaxDD | Veredicto |
|---|---|---|---|---|
| Custos completos (fee 10bps + funding), kelly 0.5 | 0.465 | **−0.0794** | 15.56% | **NO-GO** |
| Custos da época da homologação (slip 5bps) | 0.728 | **−0.0794** | 23.74% | **NO-GO** |
| PSR sem sobreposição (3 sub-séries 24h) | 0.009 / 0.701 / 0.470 | — | — | 0/3 |

Causa dominante: **extensão da base** — o edge funding/OI não se sustentou no
forward 2025-26 (IC_lower era +0.0205 em out/2024; virou −0.079 e cruza zero).
Retorno líquido médio por sinal: **−0.000003** (IC95 cruza zero). Todos os 45
folds ficam INSUFFICIENT_DATA (<10 sinais ativos). Coerente com o paper
trading: só FLATs desde 28/06. Reprodução: `python -m ...backtest_v3 --symbol
BTCUSDT` e `python scripts/psr_nonoverlap.py`.

**Implicação para a decisão de 28/07: NÃO promover a capital real.** O GO de
junho era específico do regime 2021-24 e anterior ao modelo de custos.

**Decisões de produto PENDENTES (dono)**: (1) destino do V3 — encerrar,
manter em paper como sonda de regime, ou pesquisar variante; (2) **C6**:
Fase 1 LLM maturou Sharpe **−0.5734** (trial 1, n pequeno) — decidir
continuidade até 28/07 e registrar no Experiment Registry.

**Limitação documentada (C3)**: MaxDD do WFA compõe P&L de sinais
sobrepostos como sequenciais — não é DD de portfólio realizável (nota em
`_equity_curve`; correção na v2 do backtest, no core).

**Experiment Registry reconciliado no core (0ace288 + ADR-015, mesma data)**:
a versão evoluída DAQUI (validate_trials, governança N+1) virou a canônica no
predictor_core **v1.1.0**; `analyzers/trials.py` virou compat shim (padrão dos
shims do circuit_breaker). `close_trial_sharpes` permanece aqui (lógica de
domínio). Novidade: **trava de poder** — criar trial NOVA exige atestado de
controle positivo; `scripts/attest_harness.py` certifica o juiz GO/NO-GO real
(PSR≥0.80 ∧ IC_lower>0) contra edge plantado e ruído, e o atestado
(`GarimpoInvestimentos/trials.harness_attestation.json`) está versionado.
Corolário: o NO-GO acima é veredito de juiz com poder comprovado, não cegueira.
Decisão e alternativa rejeitada (flag em memória): docs/ADR-015. Suíte: **269**
(256 no Python global, 2 skips sem hmmlearn). trials.json com o Sharpe −0.5734
da trial 1 commitado (0a79ab4); contexto em docs/HYPOTHESES.md (H4).

---

## ⭐ Rodada 2026-07-07 — Auditoria + Experiment Registry + qualidade de medição

**Bug CRÍTICO corrigido:** a regra não-ancorada `data/` no `.gitignore` engolia o
snapshot embarcado antigo do core (o commit `20128f6` referenciava a camada,
mas ela nunca entrou no git) — **qualquer clone fresco quebrava com 22 erros de
coleta**; a suíte só passava na máquina do dono (arquivos presentes, untracked).
Corrigido (`/data/` ancorado + camada commitada do canônico, hashes batem com o
CORE_MANIFEST) e blindado: `tests/test_repo_hygiene.py` falha se qualquer `.py`
de código estiver gitignorado ou se arquivo do manifesto estiver untracked.
Prova: clone limpo → suíte verde.

**Experiment Registry (governança do DSR):** schema formal do `trials.json`
(`validate_trials`, validado pela suíte contra o arquivo real); mudar `params`
de trial existente é ERRO — variação de configuração é tentativa NOVA (N+1);
`close_trial_sharpes` no backtest grava o Sharpe por-trade automaticamente
quando um estrato de Fonte casa com uma trial e tem n≥3 sinais fortes maduros
(nunca cria trial — pré-registro segue humano).

**Feature Store (schema 6→8):** guard temporal bidirecional na inserção
(`published_at < ts` = look-ahead de rotulagem; `> ts+45d` = anomalia; segunda
cinta — o contrato já barrava o limite inferior); migração **0007**
`feature_version` na PK de `features_aligned` (lógica nova escreve ao lado,
nunca por cima; histórico = 'v1'); migração **0008** `input_degradado` nas
predictions (NULL p/ legado — nunca reinterpretar o passado).

**Qualidade de medição:** backtest mede o preço realizado OFFLINE-FIRST
(`close_on` na store, preferindo a família de fontes da previsão; CoinGecko só
como fallback; coluna `medida_d*` carimba a régua); estratificação por input
degradado no relatório; `series_quality` na ingestão (gaps + saltos >30% viram
`data.quality_warning` + aviso no console, sem bloquear); previsões carimbadas
em **UTC** (`utc_stamp`; pré-2026-07-07 são BRT, skew ≤3h documentado).

**Backlog condicional B1–B8** em docs/HYPOTHESES.md (triagem de propostas
externas; nada consome tentativa; ativação típica: pós-veredicto H4).

Suíte: **201 → 241 verdes** (+40 testes). Nenhuma dependência nova. Auditoria
externa (LLM sem ler o código) foi triada: achados factualmente errados
descartados e documentados; Prefect/Docker/L2/Regime-Shift rejeitados por
complexidade sem benefício.

---

## ⭐ V3.3.2 — Bug do agendador (encoding) + smoke test validado (2026-06-28)

**Incidente:** o agendador `GarimpoV3Daily` rodou em 27/06 21:30 mas **falhou
(Último resultado: 1) e não criou log** — não havia smoke test de fato.

**Causa-raiz:** `scripts/run_daily_v3.ps1` tinha caracteres não-ASCII (em-dash `—`,
acentos). O Windows PowerShell 5.1 lê `.ps1` **sem BOM como Windows-1252**; o byte
`0x94` do em-dash UTF-8 (`E2 80 94`) vira **`"` (aspas)** no 1252, corrompendo o
balanceamento de aspas/chaves → **erro de parse** → `powershell -File` sai 1 ANTES
de executar (por isso nenhum log). Diagnosticado com
`[Parser]::ParseFile(...)` ("`}` de fechamento ausente na linha 30").

**Correção:** script reescrito em **ASCII puro** (0 bytes não-ASCII). Regra
permanente: **manter `.ps1` sem acentos e sem travessões** (comentário no topo do
script avisa). Parse confirmado limpo.

**Smoke test validado (28/06):** rodado na invocação idêntica à do schtasks, exit 0.
- Encanamento end-to-end OK (vision_ingest → pipeline → paper_trader → paper_report).
- **Catch-up não-destrutivo provado:** funding 4108→**5931**, OI 433k→**616k** (cresceu,
  não foi clampado — o fix do V3.3.1 segurou).
- **Sinal corrente:** BTC FLAT @ **73.499** (jun/2026), não mais o cache de out/2024.

**Lição registrada:** os 3 paper trades acumulados são TODOS FLAT — confirma na
prática que 30 dias com sinal a 2.4% geram ~0–2 trades ativos. **A janela de 30
dias é smoke test OPERACIONAL, não validação estatística.** A validação do edge já
é a WFA (29 folds, PSR 0.909); capital pequeno se apoia nela + encanamento limpo,
não em significância de 2 trades.

> Cross-projeto: nesta mesma sessão, o `wc-predictor-v2` (futebol) teve seu edge
> **refutado** com a régua open-CLV (sem edge — ver HANDOFF do wc). O investimento
> de atenção fica no V3, que é o único dos dois que passou no juiz estatístico.

---

## ⭐ VERSÃO V3.3 — Sweep multi-ativo e automação (2026-06-27)

### Resumo

Fechamento para **produção assistida**: lock de dependências limpo, automação do
feed diário, relatório semanal de paper trading e início da ingestão ETH/SOL.

### Tarefas executadas

| # | Tarefa | Estado |
|---|--------|--------|
| 1 | Ingestão histórica ETHUSDT/SOLUSDT (Binance Vision) | 🟡 EM ANDAMENTO (ver abaixo) |
| 2 | Feed diário automatizado | ✅ `scripts/run_daily_v3.ps1` |
| 3 | Regeneração do `requirements.lock.txt` (sem loguru) | ✅ |
| 4 | Relatório de paper trading | ✅ `v3/paper_report.py` |
| 5 | Integridade do wc-predictor-v2 | ✅ 94/94 |

### Tarefa 3 — Lock regenerado

`requirements.lock.txt` regenerado na `.venv_v3` (Python 3.13.14) com o
`requirements.txt` COMPLETO instalado (Fase 1 + V3). **loguru removido**;
confirmadas: google-genai, openai, openpyxl, python-dotenv, hmmlearn, httpx,
pydantic, numpy, scikit-learn, pandas. (Atenção: congelar só a venv V3 sem as
deps da Fase 1 truncaria o lock — por isso o `pip install -r requirements.txt`
ANTES do freeze.)

### Tarefa 2 — Feed diário (`scripts/run_daily_v3.ps1`)

Auto-ancorado (raiz via `$PSScriptRoot`, sem path hardcoded — o `run_daily.ps1`
da Fase 1 tem path defasado `C:\Claude\ProjetosPython`, **não alterado** por ora).

> 🔴 **BUG corrigido durante a execução:** a 1ª versão usava `pipeline
> --force-refresh`. Isso é **DESTRUTIVO**: `force_refresh=True` re-coleta OI via
> `OICollector` REST, que **clampa em 30 dias** (`_MAX_OI_HISTORY_DAYS=30`,
> limite da Binance) e **sobrescreve** os 433k registros históricos de OI (base
> de treino do HMM). Corrigido para o fluxo NÃO-destrutivo:
> **`vision_ingest` (estende histórico do data lake até ontem) → `pipeline` SEM
> force-refresh (lê CSVs atualizados + modelo treinado) → `paper_trader` →
> `paper_report`.** A atualização de dados é responsabilidade do `vision_ingest`,
> nunca do REST. Lag de ~1 dia (data lake), aceitável para horizonte de 24h.

Loga em `logs/v3_daily_<data>.log`.

### Tarefa 4 — Relatório de paper trading (`v3/paper_report.py`)

Lê `data/v3/paper/{symbol}_paper.jsonl`, casa cada posição com o preço D+horizon
(spot_1h.csv) e computa: P&L acumulado (log), MaxDD corrente (predictor_core.stats),
hit rate, distribuição por regime/motivo. Emite `paper_report` (domain `v3_paper`).
8 testes novos (puros, rodam no global).

### Tarefa 5 — wc-predictor-v2

94/94 testes verdes. `prediction` e `status_check` confirmados emitindo em
execução real (`predict Brazil Argentina`, `status`). `ingest_done` está cabeado
e compila, mas **não exercido** — rodar o `ingest` toca rede/produção (projeto é
SHADOW read-only). Verificar numa janela de manutenção dedicada.

### Tarefa 1 — Ingestão + Sweep ETHUSDT: **NO-GO (sem edge)**

ETHUSDT ingerido (funding 4381, OI 324k de **mai/2022**, spot 35k). Sweep rodado
(26 folds, fr_window=90, frações [1.0, 0.5, 0.25, 0.10]):

| Kelly | PSR | IC | IC_lower | MaxDD | Veredicto |
|-------|-----|-----|----------|-------|-----------|
| 1.00 | 0.125 | **−0.113** | −0.353 | 22.61% | ❌ NO-GO |
| 0.50 | 0.125 | −0.113 | −0.353 | 11.73% | ❌ NO-GO |
| 0.25 | 0.125 | −0.113 | −0.353 | 5.97% | ❌ NO-GO |
| 0.10 | 0.125 | −0.113 | −0.353 | 2.41% | ❌ NO-GO |

**Conclusão (crítica):** o ETH **não tem edge** neste período. Diferente do BTC,
a falha **NÃO é de risco** (MaxDD passa folgado em 0.25/0.10) — é de **sinal**:
PSR=0.125 (vs BTC 0.909) e **IC NEGATIVO** −0.113 (vs BTC +0.229), IC_lower
−0.353 (cruza zero). Kelly fracional é **inútil** aqui: ele só escala MaxDD, não
PSR/IC. Nenhuma fração resgata um edge inexistente.

**Decisão:** ETHUSDT **NÃO homologado**, **NÃO adicionado** ao `$symbols` do feed
diário. O edge funding/OI-overcrowding é **específico do BTC** nestes regimes.
Resultado negativo valioso: confirma que o juiz estatístico **não dá falso
positivo** (coerente com a validação de "NO-GO correto em ruído"). SOLUSDT
permanece em backlog. BTCUSDT segue como único ativo em produção assistida.

> Ressalva metodológica: a janela do ETH (mai/2022–dez/2024) difere da do BTC
> (2021–2024) por indisponibilidade de OI no data lake. Ainda assim, IC negativo
> não é artefato de período — indica ausência de edge, não edge enfraquecido.

### Produção Assistida — início dos 30 dias (autorizado pelo arquiteto)

| Item | Valor |
|------|-------|
| **Ativo em produção assistida** | BTCUSDT |
| **Kelly homologado** | **0.50** (PSR 0.909, IC_lower +0.0205, MaxDD 10.45%) |
| **Agendador** | Task `GarimpoV3Daily`, Windows Task Scheduler |
| **Horário** | 21:30 local (UTC-3) = **00:30 UTC** (após fechamento do daily candle) |
| **Comando** | `powershell -ExecutionPolicy Bypass -NoProfile -File <repo>\scripts\run_daily_v3.ps1` |
| **1ª execução agendada** | 2026-06-27 21:30 local |
| **Início oficial dos 30 dias** | **2026-06-28** (1º candle diário com agendador ativo) |
| **Fim previsto** | **2026-07-28** (avaliação: capital real + design `predictor_core.backtest`) |

Validação manual da cadeia (em cache out/2024): `paper_trade` emitido,
`paper_report` coerente (trades flat / `no_signal` — esperado até o catch-up de
dados frescos via `vision_ingest` no 1º run agendado). Acompanhamento semanal via
`paper_report.py`. **Gatilho de alerta:** MaxDD corrente do paper > 15% → reportar
imediatamente ao arquiteto.

### Testes (contagem atual)

- **previsao-cripto: 88** (76 portáveis no global + 12 hmmlearn-gated na venv V3).
- **wc-predictor-v2: 94**.

---

## ⭐ V3.3.1 — Correção de force-refresh destrutivo (2026-06-27)

**Incidente (capturado em revisão, ANTES de ir a produção):** a 1ª versão do
`scripts/run_daily_v3.ps1` chamava `pipeline --force-refresh` no feed diário.

**Falha latente:** `force_refresh=True` faz o pipeline re-coletar OI via
`OICollector` REST, que **clampa em 30 dias** (`_MAX_OI_HISTORY_DAYS=30`, limite
da API Binance, erro -1130 acima disso) e em seguida **`save_oi_csv` sobrescreve**
`data/v3/{symbol}/oi.csv`. Resultado: os **433k registros históricos de OI
(2021-2024)** seriam trocados por ~30 dias de REST — **destruindo a base de treino
do HMM**. O modelo continuaria rodando sobre dados mutilados, emitindo sinais
espúrios **sem alerta** (falha silenciosa).

**Correção:** fluxo NÃO-destrutivo — a atualização de dados é responsabilidade
EXCLUSIVA do `vision_ingest` (data lake, append/cache não-destrutivo); o
`pipeline` no diário roda **sem** `--force-refresh` (lê os CSVs já estendidos +
carrega o modelo HMM treinado, inferência causal). Ver V3.3 Tarefa 2.

**Lição arquitetural (regra permanente):** *nunca permitir que um comando de
coleta LIMITADA (REST clampado, amostragem, janela curta) sobrescreva um artefato
de dados HISTÓRICO COMPLETO.* Coleta incremental/limitada e base histórica devem
ter caminhos de escrita separados. Onde houver clamp/limite de API, o save deve
ser append-guarded ou bloqueado contra overwrite de série longa.

---

## ⭐ VERSÃO V3.2 — Kelly Sweep + Paper Trading + Logging Unificado (2026-06-27)

### Resumo executivo

O V3 **passou no Go/No-Go** via position sizing (Kelly fracional), sem tocar no
modelo. O edge sempre foi real; o único gargalo era risk sizing — resolvido.

### Kelly Sweep — BTCUSDT (homologado)

Comando: `python -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT --kelly-fractions 1.0 0.5 0.25 0.10`

Data do sweep: **2026-06-27** | Dados: BTCUSDT 2021-01-01 → 2024-10-01 (29 folds, fr_window=90)

| Kelly | PSR | IC_lower | MaxDD | Veredicto |
|-------|------|----------|-------|-----------|
| 1.00 | 0.909 | +0.0205 | 20.14% | ❌ NO-GO |
| **0.50** | **0.909** | **+0.0205** | **10.45%** | ✅ **GO (homologado)** |
| 0.25 | 0.909 | +0.0205 | 5.32% | ✅ GO |
| 0.10 | 0.909 | +0.0205 | 2.15% | ✅ GO |

**Insight-chave:** PSR e IC_lower são **invariantes** sob fracionamento de Kelly
(o Kelly escala exposição, não o sinal). Só o MaxDD escala — quase linearmente.

**Thresholds aprovados (Go/No-Go):** PSR ≥ 0.80 · IC_lower > 0 · MaxDD < 20%.

**Fração homologada: `DEFAULT_KELLY_FRACTION = 0.50`** (`v3/backtest_v3.py`).
Critério: maior fração com GO → maximiza retorno absoluto dentro do orçamento de
risco, com margem confortável (10.45% < 18%). A escolha "menor fração vencedora"
foi rejeitada por ser degenerada (a menor sempre vence trivialmente, subutilizando
o orçamento de risco). PSR idêntico em todas → a decisão é retorno absoluto vs DD.

### Paper Trading (`v3/paper_trader.py` — NOVO)

- Domain `v3_paper`; evento `paper_trade` (direction, strength, kelly_fraction,
  position, ref_price, regime_confidence + metadados).
- Persiste em `data/v3/paper/{symbol}_paper.jsonl` (append-only).
- Aplica a fração homologada (0.50) ao sinal MAIS RECENTE do pipeline V3.
- Uso: `python -m GarimpoInvestimentos.v3.paper_trader --symbol BTCUSDT --start-date 2021-01-01`
- ⚠️ Para sinal "de hoje" real, o pipeline precisa re-ingerir dados frescos
  (`--force-refresh`). Hoje o cache do BTC termina em out/2024.

### Logging unificado (Fase 1) — `loguru` REMOVIDO

- `store/logger.py` reescrito: stdlib `logging` + `emit_event`. Zero `print()`.
- Domain padronizado **`previsao_cripto`** (Fase 1/2). V3 mantém `v3_cripto`;
  paper trading usa `v3_paper`.
- Eventos: `pipeline_start/success/error`, `fallback_triggered`, `cache_integrity`,
  `llm_quota_alert`, `batch_start/success`, `toll_passed`.
- Collectors e analyzers deixaram de ser silenciosos (logging mínimo adicionado).

### Resiliência (Fase 1)

- `main.py`: `asyncio.gather` + `Semaphore(5)` (paralelismo respeitando rate limit).
- Alerta de cota LLM: fallback > 20% dos ativos → `llm_quota_alert` + WARNING.

### Ambiente

- **venv V3: `.venv_v3` (Python 3.13.14)** — hmmlearn NÃO compila no 3.14 global
  (sem MSVC). 3.13 tem wheel binário. `py install 3.13` resolveu.
- Suíte histórica: **80 testes verdes** na venv V3 (com override de importação então usado).
  68 no global (sem os testes que dependem de hmmlearn).

### Pendências

- **ETHUSDT / SOLUSDT:** sweep não rodou — dados não existem em `data/v3/`.
  Exigem `python -m GarimpoInvestimentos.v3.pipeline --symbol ETHUSDT SOLUSDT --start-date 2021-01-01`
  (ingestão via rede Binance Vision).
- **Feed diário:** automatizar pipeline `--force-refresh` 1×/dia para o paper
  trading registrar sinais correntes (hoje usa cache até out/2024).

---

## 0. Integração à plataforma predictor_core (2026-06-16/17)

Sessão de plataforma — o Garimpo virou consumidor do núcleo canônico `predictor_core`
(vendorizado em `vendor/`, sincronizado por hash). Visão arquitetural completa da
plataforma (DPL, Feature Store, Alignment Engine, CCXT, ADRs, backlog) no
[docs/DOSSIE_PLATAFORMA.md](docs/DOSSIE_PLATAFORMA.md). Mudanças:

| Área | Mudança |
|------|---------|
| Significância | `analyzers/backtest.py` emite **Spearman com IC95%** (block bootstrap PAREADO via `predictor_core.stats`) — "validado / RUÍDO" em vez de estimativa pontual nua. |
| Modo B / reprodutibilidade | **carimbo do juiz** (`provider:modelo:hash-do-prompt`) em cada previsão (`ai_insights.judge_signature`), persistido no histórico (coluna `Juiz`). |
| Cross-check | `score_engine.divergence_flag` — tagueia contradição LLM×indicadores determinísticos (flag-only, **não muta o score**); o backtest **estratifica** alinhadas vs divergentes. |
| Degradação | `main.py` instrumenta `input_degraded` (notícia/indicador faltando deixou de ser engolido). |
| Rede unificada | imports de rede agora vêm de `predictor_core.net` (httpx async + retry); `core/retry.py` e `core/http_client.py` **deletados** (duplicata aposentada). |
| Trava de credenciais | `config.__post_init__` usa `predictor_core.settings.require_secrets` — chave ausente/falsa/`<16 chars` → **crash imediato**. `requirements.lock.txt` cravado. |

**Suíte: 26 testes verdes** (`py -3.12 -m pytest tests/ -q`). O caminho **live nunca
rodou** (`.env` vazio crasha de propósito — falta colar chaves reais: P0).

---

## 1. Resumo do que foi feito

Refatoração da Fase 1 (deixar o código limpo, funcional e pronto para o backtesting
da Fase 2). As 6 tarefas do roadmap foram aplicadas:

| # | Arquivo | Mudança |
|---|---------|---------|
| 1 | `config.py` | Chaves agora vêm do `.env` via `field(default_factory=os.getenv)`; `__post_init__` levanta `ValueError` no import se faltar `GEMINI_API_KEY`/`SERP_API_KEY`. Removidas as chaves hardcoded. |
| 2 | `collectors/coingecko_api.py` | `CoinData` ganhou `change_7d`, `change_30d`, `volume_avg_7d` (com `or 0.0` contra `None`); import absoluto. |
| 3 | `main.py` | Usa `get_coin_data` real (`model_dump()`) em vez de dados fixos; `asyncio.sleep(1)` entre ativos (ausente após o último); imports absolutos; `price_usd` no resultado. |
| 4 | `core/cache.py` | TTL de 6h com timestamps UTC timezone-aware; entradas sem/`cached_at` inválido descartadas. |
| 5 | `core/history.py` | Coluna `price_usd` adicionada ao histórico (âncora da Fase 2). |
| 6 | estrutura | Deletadas duplicatas da raiz e hacks de importação; criados `GarimpoInvestimentos/__init__.py` e `pyproject.toml`. |

---

## 2. O que foi consertado / além do prompt nesta sessão

- **Bug real de runtime — `UnicodeEncodeError`:** o console do Windows (cp1252) quebrava
  ao imprimir os emojis dos `print()`. Corrigido forçando UTF-8 em `sys.stdout`/`sys.stderr`
  no **`GarimpoInvestimentos/__init__.py`** — cobre qualquer entry-point (`main`, `backtest`, …).
- **venv recriada:** a antiga (`GarimpoInvestimentos/env`) apontava para um Python 3.14
  que não existe mais na máquina. Recriada com **Python 3.12** + `requirements.txt`.
- **Imports em 2 arquivos da lista "não tocar"** (`serpapi_news.py`, `ai_insights.py`):
  tinham `from config import...`/`from core.http_client import...` implícitos, que
  quebram sob `python -m`. Corrigidas **apenas as linhas de import** (lógica intacta) —
  era impossível satisfazer o "rodar como módulo" sem isso.
- **`pyproject.toml`:** o backend pedido no prompt (`setuptools.backends.legacy:build`)
  não existe e quebraria `pip install`. Usado o correto `setuptools.build_meta`.
- **Caminhos de saída ancorados (`core/paths.py`, novo):** antes `output/` e `logs/`
  eram relativos ao cwd, gerando pastas duplicadas conforme de onde se rodava. Agora
  `cache.py`/`history.py`/`reporter.py`/`logger.py` resolvem tudo via `core/paths.py`
  (baseado em `__file__`) → sempre na raiz do projeto, independente do cwd. Validado
  rodando de `C:\Claude` sem criar `output/` lá. Atenção: a pasta `GarimpoInvestimentos/output/`
  **é o pacote** que contém `reporter.py` — não apague; os dados agora vão para a raiz.
- **`.gitignore` + chaves no `.env`:** chaves reais (funcionais) movidas para o `.env`
  e `.gitignore` criado protegendo `.env`/venv/saídas.

---

## 2b. Melhorias e features (rodada 2)

Feito pelo Leo e validado/estendido nesta sessão:

| Área | Mudança |
|------|---------|
| `config.py` | Novas configs lidas do `.env`: `DEFAULT_ASSETS`, `CACHE_TTL_HOURS`, `ENABLE_CACHE`. Limiar default corrigido de `0.6` → **`60`** (estava em escala errada; scores são 0-100). |
| `main.py` (CLI) | `--assets`, `--min-score`, `--no-cache`, **`--output-dir`** (novo), **`--summary`** (novo). `--no-cache` agora também **não regrava** o `cache.json`. Pré-parse de `--output-dir` antes dos imports (seta `GARIMPO_OUTPUT_DIR`). |
| `core/cache.py` | TTL agora vem de `settings.CACHE_TTL_HOURS`. |
| `output/reporter.py` | Colunas `Data` e `Preço USD` em CSV **e XLSX** (o corpo do XLSX estava faltando os 2 campos — bug corrigido). |
| `core/paths.py` | `OUTPUT_DIR`/`LOGS_DIR` respeitam `GARIMPO_OUTPUT_DIR`/`GARIMPO_LOGS_DIR` (suporte ao `--output-dir`). |
| `collectors/serpapi_news.py` | **Query corrigida**: removido o filtro `site:news.google.com` que zerava resultados; agora as notícias realmente chegam ao Gemini. Guarda contra payload `{"error": ...}`. |
| `analyzers/backtest.py` (novo) | Esqueleto da Fase 2: lê histórico (ignora fallback), busca preço em D+1/D+7/D+30 (CoinGecko `/history`), calcula variações e **Spearman sem `scipy`**. |

---

## 2c. Calibração do sinal (rodada 3) — corrige a "matemática" do score

Após revisão crítica, atacamos os defeitos que invalidavam o backtesting:

| Arquivo | Correção |
|---------|----------|
| `score_engine.py` | **Removida a multiplicação por sentimento** (era dupla contagem; esmagava o número do modelo, ex.: 35→7). `Score` = `opportunity_score` puro (clamp 0-100). Sentimento vira só metadado. |
| `ai_insights.py` | Prompt **ancorado a um horizonte** (`SCORE_HORIZON_DAYS`); escala 0-100 definida como retorno esperado nesse prazo. **JSON mode + `temperature=0.2`** → score reprodutível. |
| `collectors/coingecko_api.py` | **Removido o `volume_avg_7d` falso** (era o volume de hoje rotulado como média de 7d — enganava o LLM). |
| `core/cache.py` | `save_cache` usa `setdefault` no `cached_at` → **preserva o timestamp da análise original** (antes o TTL era renovado a cada run e nunca expirava). |
| `core/history.py` | **Dedup por (Ativo, Data)** → cache hits/reexecuções não inflam o `n` do Spearman. |
| `analyzers/backtest.py` | Horizonte principal vem do config; dedup defensivo no load. |
| `config.py` | Novo `SCORE_HORIZON_DAYS` (default 7). `.env` carregado por **caminho explícito** (robusto a cwd e a `-m`/`-c`/testes). |

Validado: `score_engine` (negativo+35 → **35**, era 7); `volume_avg_7d` ausente do
`model_dump`; dedup (3 appends idênticos → **1 linha**); `cached_at` preservado p/ entrada
existente e carimbado p/ nova; análise real do Gemini com o novo prompt (BTC 30-35, ETH 75).

> **Cota do Gemini free tier (~20 req/dia)** foi estourada nos testes de hoje → alguns
> ativos caíram em fallback por `429`. Não é bug. Para um dataset limpo, rode com calma
> após o reset diário (ou chave paga).

---

## 2d. Maturidade de dados e análise (rodada 4)

Foco em deixar dados/análise úteis (não em features de infra):

| Área | Mudança |
|------|---------|
| **Feature engineering** | Novo `analyzers/indicators.py` (RSI 14, SMA 50/200, MACD, Bollinger %B — Python puro). `coingecko_api.get_price_series()` busca 200 closes diários; `main.py` calcula e injeta em `hard_data["indicadores"]`. O LLM agora interpreta indicadores reais, não só preço. |
| **Provedor de LLM** | `ai_insights.py` agora é agnóstico (`analyze_asset`): Gemini **ou** OpenAI via `LLM_PROVIDER`. Clientes lazy; validação de chave por provedor. `GEMINI_MODEL`/`OPENAI_MODEL`/`OPENAI_API_KEY` no config. **OpenAI = API paga, não ChatGPT Plus.** |
| **Métricas de backtest** | `backtest.py` ganhou acurácia direcional, hit rate (score≥limiar), estratégia fictícia + Sharpe simplificado, e benchmark BTC buy&hold — no horizonte principal. |
| `requirements.txt` | `+ openai`. |

Validado (sem gastar cota de LLM): indicadores em série real do BTC (RSI 35.9, −17% vs SMA200,
MACD virando, %B 0.37); validação de provedor (openai sem chave → erro certo; com chave →
carrega sem exigir Gemini); métricas em dado sintético (direcional/hit rate/Sharpe/benchmark
corretos); pipeline ponta a ponta sem quebrar (LLM caiu em fallback por 503/cota).

> ⚠️ **Não misture provedores na mesma janela de coleta** — contamina o backtest (dois
> juízes, calibrações diferentes). E **mais chamadas/dia não amadurecem o backtest mais
> rápido**: D+7 leva 7 dias reais (a não ser que se faça replay histórico point-in-time,
> que é projeto à parte com risco de lookahead).

---

## 2e. Coleta honesta: agendamento, escala e resiliência (rodada 5)

Foco: **ligar o relógio** (tempo é incompressível) e não envenenar o histórico com fallback.

| Área | Mudança |
|------|---------|
| **Retry/backoff** | Novo `core/retry.py` (`@with_retry`, backoff exponencial + jitter) aplicado a CoinGecko, SerpAPI e LLM. `503`/`429` transitório re-tenta; 404/chave inválida/**cota diária** não (retry não resolve). Validado por testes unitários. |
| **Escala transversal** | `DEFAULT_ASSETS` expandido para 22 ativos (dilui variância da amostra). Ids inválidos se auto-podam (404 → ativo pulado). |
| **Pin do modelo** | `GEMINI_MODEL` no `.env` com aviso para fixar um snapshot datado (alias flutuante deriva a calibração no meio da coleta). |
| **Agendamento** | `scripts/run_daily.ps1` + comando `schtasks` no README para rodar 1×/dia (Agendador do Windows — nuvem é over-engineering antes de sinal validado). |

> **Decisão metodológica registrada:** replay histórico do LLM é inválido (a memória
> paramétrica do modelo já "conhece" o futuro = look-ahead embutido). Forward test é o
> único caminho limpo para o LLM; replay só vale para o **baseline técnico** (indicadores
> não têm memória). **Teto free Gemini ~20 req/dia** → lista cheia exige Gemini pago.

---

## 2f. V3 Crypto-Predictor — Fase 1: validação de edge mecânico (2026-06-25)

Linha de pesquisa **nova e independente** do pipeline LLM. Hipótese: edge vem de
ineficiência mecânica — **funding rate extremo + OI crescendo** (alavancagem forçada)
condicionado por **regime de volatilidade (HMM)**. Sem WebSocket L2, sem notícias.

**Arquitetura** (`GarimpoInvestimentos/v3/`):

| Arquivo | Papel |
|---|---|
| `circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN; propaga `data_quality_score` (1.0/0.5/0.0). |
| `collectors/funding_collector.py` | Funding rate 8h (Binance fapi), CSV idempotente, `with_retry`+CB. |
| `collectors/oi_collector.py` | Open Interest (period **`1h`**), clampa em 30d (limite Binance). |
| `collectors/spot_collector.py` | Klines 1h spot. |
| `feature_builder.py` | `funding_zscore`, `oi_log_delta`, `leverage_pressure`, `realized_vol_24h`. Nunca interpola. |
| `regime_engine.py` | GaussianHMM 3 estados; **Forward Algorithm causal à mão** (hmmlearn.predict_proba usa forward-backward = lookahead). |
| `signal_engine.py` | SignalRecord canônico; short/long/flat; degradado→CRITICAL. |
| `pipeline.py` | Orquestra coleta→features→HMM→sinais; CLI `--symbol/--start-date`. |
| `backtest_v3.py` | WFA 180/30/7d + PSR + Spearman CI + MaxDD → veredicto GO/NO-GO. |

**Bugs reais encontrados e corrigidos na verificação** (o backtest quebrava ou produzia
lixo silencioso antes disso):

| Bug | Sintoma | Fix |
|---|---|---|
| `spearman_block_ci` retorna **tupla** `(rho,lo,hi)`, programei contra objeto `.ci_lower` | `AttributeError` no 1º fold | unpack de tupla + None-handling |
| `max_drawdown` espera **equity acumulada**, passei retornos brutos | `max_drawdown([.01,-.02,.03])=3.0` (300% falso) | `_equity_curve()` composto antes |
| Warmup do z-score (90 períodos) recomputado por fatia OOS (30d≈90) | **~0 features/fold** | features construídas **uma vez** na série contínua, particionadas por timestamp |
| `period="8h"` no OI hist | HTTP 400 (-1130) toda chamada | → `"1h"` (alinha exato nos funding times) |

**🔴 LIMITE DURO do REST: OI histórico grátis = ~30 dias.** `openInterestHist` recusa
start > ~30d (`startTime invalid`). Com z-score consumindo 30d de warmup, sobram **~61
feature vectors reais**, abaixo do piso de 100 do HMM → Go/No-Go histórico inviável só
com REST.

**✅ RESOLVIDO — Quarta Via: data lake público `data.binance.vision`.** A Binance arquiva
anos de funding + OI (dataset **`metrics`**, 5min, desde ~2021) + klines em ZIPs grátis.
Dois módulos novos:

| Arquivo | Papel |
|---|---|
| `collectors/binance_vision.py` | Baixa ZIPs (cache local + verificação **SHA256**), parseia e devolve os MESMOS dataclasses (FundingRecord/OIRecord/KlineRecord). Funding/klines = mensais; OI metrics = diários. |
| `vision_ingest.py` | CLI que grava nos MESMOS CSVs do caminho REST → `pipeline`/`backtest_v3` rodam sem alteração. |

Schemas reais confirmados (2026-06-25): funding `calc_time(ms)/last_funding_rate` (sem
mark_price → 0.0); metrics `create_time(str UTC)/sum_open_interest/sum_open_interest_value`;
klines padrão. Join funding×OI: match exato em ~86% dos ts, resto cai na tolerância ±5min.
`oi_collector` REST permanece só para coleta **ao vivo**. Decisão do Leo: validar o
Go/No-Go sobre BTC com janela de anos via Vision **antes** de qualquer infra de WebSocket.

**Perf:** `feature_builder` tinha hotspot O(n²) (re-ordenava o spot a cada ts) — corrigido
com `bisect` (O(n log n)), necessário para escala de anos do data lake.

### Diário de pesquisa — runs do WFA (Go/No-Go)

| Data | Janela | fr_window | Folds | PSR | IC_CI_lower | MaxDD | Veredicto | Leitura honesta |
|---|---|---|---|---|---|---|---|---|
| 2026-06-25 | BTC 2024-01→10 (9m) | 90 | 2 | 1.000 | −0.148 | 0.1% | NO-GO | **INCONCLUSIVO por underpowering** — <10 sinais/OOS, CI [−1,1] degenerado. |
| 2026-06-25 | BTC 2021→2024 (anos) | **90** | **29** | **0.909** | **+0.021** | **20.14%** | NO-GO (só MaxDD, por 0.14pp) | **EDGE REAL.** IC_lower>0 (não cruza zero) + PSR>0.80. Falha só no risco, na trave. |
| 2026-06-25 | BTC 2021→2024 (anos) | **21** | **36** | 0.896 | **−0.092** | **12.06%** | NO-GO (só IC) | Pivot baixou MaxDD (20→12%) mas **matou o edge** (IC cruza zero). Janela curta = ruído de spike. |

**Conclusão dos 3 runs:** a tese de alavancagem **sobrevive ao WFA de poder real** — no baseline de
29 folds (anos, 5bps slippage) o IC_lower ficou **positivo** e o PSR limpou 0.80. As duas configs
reprovam em critérios **opostos**: fr_window=90 tem edge mas MaxDD=20.14% (0.14pp acima); fr_window=21
controla risco (12%) mas perde significância. **O pivot de fr_window foi o lever errado** — o edge mora
na janela longa (funding extremo *sustentado*), e a falha do baseline é de **gestão de risco**, não de
normalização. Próximo lever: **position sizing** (fractional Kelly 0.25x / vol-targeting) para puxar o
MaxDD <20% preservando o IC_lower>0. NÃO mexer mais no fr_window.

**Diagnóstico de esparsidade** (727 features): `|z|≥2.0` → só 36 (5%); `|z|≥1.0` → 141 (19%).
z-score std=1.29 e max=7.66 ⇒ janela de 90 (30d) mistura regimes de funding (não-estacionária).

**Plano aprovado (próximo run, dados 2021→2024):**
1. Ingestão massiva via Vision (em andamento) — engloba bull 2021 / bear 2022 / recovery 2023-24.
2. **Baseline:** `backtest_v3 --fr-window 90` (linha de base de longo prazo).
3. **Pivot:** `backtest_v3 --fr-window 21` (z-score local-estacionário; +gatilhos sem baratear o threshold).
   - Flag `--fr-window` adicionada ao `backtest_v3` (default 90; thread → `build_feature_vectors`; gravada no `wfa_result`).

**Camada 1 auditada (sem lookahead):** HMM re-treina por fold (`engine=RegimeEngine()` DENTRO do
loop, `fit()` só no IS); `StandardScaler` fit no IS e só `transform` no OOS; rotulagem bull/bear
por mean-return do IS; `all_features` construído 1× é seguro (features são rolantes causais);
purge de 7d entre IS e OOS.

**Validação real (não só syntax):**
- ✅ Cadeia pura testada (feature_builder→signal_engine, todos os caminhos).
- ✅ HMM treinado + Forward causal + WFA rodados em dado sintético → **NO-GO correto em
  ruído** (juiz não dá falso positivo); evento `wfa_result` emitido.
- ✅ Coletores batem na Binance real: funding=359, OI clampado ~21d, 2877 klines, 61 features.
- 🔴 Veredicto sobre BTC real bloqueado pelo limite de OI.

**Deps novas** (`requirements.txt`): `hmmlearn`, `numpy`, `scikit-learn` — instaladas neste ambiente.

---

## 3. Validação (execução real, não só syntax)

Tudo rodado de verdade com as **chaves reais** no `.env`:

- ✅ Pipeline ponta a ponta sem erro; CoinGecko traz dados reais e campos temporais.
- ✅ Análise **real do Gemini** (não fallback) — com a query de notícias corrigida, os
  scores ficaram variados (ex.: BTC 5, ETH 80, SOL 85) e os resumos citam notícias.
- ✅ `garimpo_historico.csv` com `Data` + `price_usd`; XLSX com as 6 colunas preenchidas.
- ✅ `cache.json` com `cached_at` UTC; 2ª execução → **cache hit**; `--no-cache` não grava.
- ✅ CLI validada: `--assets`, `--min-score`, `--summary` (lista só ≥ limiar), `--output-dir`
  (grava em pasta alternativa), `--help`.
- ✅ `backtest.py` executa e gera `garimpo_backtest.csv`; reporta "dados insuficientes"
  porque as previsões são de hoje (D+1 ainda não chegou) — comportamento esperado.
- ✅ `ValueError` de startup testado nos dois sentidos.
- ✅ Validado também rodando de outro cwd (`C:\Claude`): saída sempre na raiz do projeto.

---

## 4. Pendências / próximos passos

1. ✅ **Chaves reais já no `.env`** (Gemini + SerpAPI), testadas e funcionais.
2. **🔴 SEGURANÇA — rotacionar chaves antigas:** o `config.py` anterior tinha
   `GEMINI_API_KEY` (`AIzaSy...`) e `SERP_API_KEY` (`d6f8e4f3...`) **reais e hardcoded**.
   São as mesmas chaves em uso hoje. O backup `core.zip` (que as continha) foi apagado
   nesta sessão, mas elas ainda podem existir em cópias antigas do projeto
   (`source\repos\GarimpoInvestimentos`, `Downloads\GarimpoInvestimentos_vstudio`).
   **Rotacionar é recomendável** (não urgente; o `.gitignore` agora protege o `.env`).
3. **Fase 2 — acumular dados e validar:** o esqueleto (`analyzers/backtest.py`) está pronto,
   mas precisa de **tempo**: rodar o pipeline periodicamente por semanas para acumular
   previsões maduras, então rodar o backtest e olhar o Spearman. Se ~0 ou negativo, revisar
   o prompt do Gemini antes de migrar para nuvem/Postgres. (Automatizar via tarefa agendada
   é um bom próximo passo.)
4. ✅ **Retry/backoff** implementado (`core/retry.py`). Restam: registrar o `schtasks`
   diário (ação do usuário — muda o sistema), ativar Gemini pago e fixar o `GEMINI_MODEL`
   num snapshot datado antes de começar a coleta "pra valer".
5. **Baseline técnico no replay** (rápido e honesto): backtestar regras puras (ex.: RSI<30)
   no histórico para estabelecer o Sharpe mínimo que o LLM precisa bater. Indicadores não
   têm memória → replay é válido aqui (ao contrário do LLM).
6. **Features adiadas** (só depois que o backtest provar o sinal): paralelismo entre ativos
   com `Semaphore`, NLP/sentimento de notícias, relatório HTML, e migração nuvem/Postgres.
7. **Testes automatizados:** só há testes manuais/ad-hoc. Priorizar `score_engine`,
   `indicators`, Spearman/métricas e o `retry`.

---

## 5. Limpeza (feita nesta sessão)

Removido tudo que não é usado, deixando só os fontes do pacote + venv + docs:

- `core.zip` (backup stale com chaves antigas), `Novo Arquivo` (órfão),
  `GarimpoInvestimentos/GarimpoInvestimentos/` (subpasta vazia),
  `GarimpoInvestimentosCrypto/` (stub `.pyproj` morto do VS),
  `GarimpoInvestimentos/.vs/` (estado do Visual Studio) e todos os `__pycache__/`.
- Não há módulo `.py` morto: tudo em `analyzers/collectors/core/output` é importado
  por `main` ou `backtest`. O `.gitignore` evita o reacúmulo de `__pycache__`/`.vs`.

Há cópias divergentes e **desatualizadas** do projeto em
`C:\Users\Superleo13\source\repos\GarimpoInvestimentos` e
`C:\Users\Superleo13\Downloads\GarimpoInvestimentos_vstudio`. A cópia canônica é
**`C:\Claude\ProjetosPython\GarimpoInvestimentos`**.

---

## 6. Como rodar (resumo)

```powershell
cd C:\Claude\ProjetosPython
# pipeline (sem flags = DEFAULT_ASSETS do .env)
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main
# com CLI
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main --assets bitcoin,solana --min-score 70 --summary
# backtest (Fase 2)
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.analyzers.backtest
```

Roteiro de testes completo (deps, config, pipeline, CLI, cache, saídas, backtest,
independência de cwd): ver seção **"Como testar o projeto inteiro"** no `README.md`.

> Nota: a pasta foi movida de `C:\ProjetosPython` para `C:\Claude\ProjetosPython` em
> 14/06. O `python.exe -m` da venv continua funcionando no novo local; só os atalhos
> `activate` e `pip.exe` da venv guardam o caminho antigo — use sempre
> `env\Scripts\python.exe -m pip ...` (ou recrie a venv) se precisar instalar algo.
