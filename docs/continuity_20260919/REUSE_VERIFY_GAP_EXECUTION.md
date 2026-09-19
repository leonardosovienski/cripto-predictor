# CRIPTO PREDICTOR — REUSE → VERIFY → GAP — EXECUÇÃO NÍVEL 2/3

Data da execução: 2026-09-19  
Escopo: reutilizar e verificar o PR122 e o laço `profit-recovery/v1`, sem adicionar nova tese, feature, modelo, limiar econômico, LLM, HMM, notícia ou order book.  
Autorização de capital: **NÃO**.

## Resultado executivo

- **LEVEL_2_VERDICT: INCONCLUSIVE**
- **ROUND_A_BTC_VERDICT: INCONCLUSIVE**
- **ROUND_B_ETH_SOL_VERDICT: INCONCLUSIVE**
- **OPERATIONAL_VERDICT: RESEARCH_ONLY**
- **PAPER_TRADING_READINESS: NOT_READY**
- **MICROCAPITAL_READINESS: NOT_READY**
- **RESERVED_FINAL: RESERVED_FINAL_INSUFFICIENT**
- **NOVA COMPLEXIDADE: NÃO AUTORIZADA**

Não há prova de edge incremental do PR122. No BTC, o único episódio independente da validação ficou praticamente no zero líquido no custo-base. No ETH, houve média líquida positiva, mas com apenas três episódios, intervalo de confiança atravessando zero e desempenho inferior ao buy-and-hold no mesmo coorte. No SOL, o resultado líquido foi positivo inclusive no stress, mas com apenas cinco episódios, limite inferior negativo e resultado exatamente igual ao momentum de 1 dia. Isso é evidência insuficiente, não edge lucrativo provado.

## 1. Integridade, preservação e congelamento

O `BASELINE_V1` foi materializado antes das rodadas no artefato `BASELINE_V1.json`. A lógica econômica congelada permaneceu a do PR122, commit-base `1b2bee85f552667ed74a17e5da3526b62541d2d2`. A implementação anterior a esta extensão de mensuração era `854854b6e7de41a95383aa881eccb4a4360d98a6`.

A extensão de mensuração validada foi congelada apenas localmente no commit `a458bb6688f0b682a7d1008aa3f29321904eaae7`, branch `profit-recovery-20260919`. O worktree ficou limpo e nenhuma branch remota contém esse commit.

Alterações desta execução limitaram-se a:

1. integridade e leitura imutável de datasets reconstruídos;
2. classificação explícita da procedência;
3. campos de resultado 1h, 4h, 1d, 3d e 7d;
4. agrupamento de sinais em episódios independentes;
5. métricas econômicas, cenários de custo e comparação de baselines;
6. artefatos e testes.

Não foram alterados detector, features, limiares, direção, horizonte decisório, regra de transição ou autorização de capital. Os dois relatórios anteriores foram preservados byte a byte:

| Relatório | SHA-256 confirmado |
|---|---|
| `AUDITORIA_ECONOMICA_SEQUENCIAL_20260919.md` | `6637DE6FD4AB36F166FFD42D57E935492DE7550FEF1EC37EBF9645538CEB9E64` |
| `PROFIT_RECOVERY_EXECUTION.md` | `098ADC49CF38C389C87A706F80B68ABB15BFC7A6A4D3E02C979108DC273F7724` |

Nenhum push, merge, deploy, agendamento, envio de alerta ou operação financeira foi realizado.

## 2. Protocolo congelado

- Janela uniforme: 200 candles diários contíguos por ativo.
- Split cronológico predeclarado: 60% desenvolvimento, 20% validação, 20% reservado.
- Horizonte econômico principal: fechamento em 3 dias após o sinal.
- Independência: sinais do mesmo ativo e direção dentro de 7 dias pertencem ao mesmo episódio; somente o primeiro conta no `effective_independent_count`.
- Custos round-trip, todos **ASSUMED**: otimista 10 bps, base 35 bps, conservador 70 bps e stress 105 bps.
- Exposição comparável: todas as regras foram medidas nos mesmos timestamps candidatos do PR122; regra flat não paga custo, regra ativa paga o mesmo custo do cenário.
- Baselines: flat, buy-and-hold, momentum 1d/7d/30d, breakout 20d, tendência SMA50 e mean reversion 1d.
- Critério positivo: amostra efetiva mínima de 20 episódios, limite inferior de 95% líquido acima de zero, limite inferior incremental acima do melhor baseline e expectativa líquida positiva no stress.
- O catálogo oracle permaneceu diagnóstico e não entrou em treino, seleção, tuning ou decisão.

### Limite da comparação

As estratégias simples foram comparadas no coorte de timestamps candidatos do PR122, assegurando custo e exposição comparáveis. Isso não equivale a um backtest contínuo e independente de cada estratégia no mercado inteiro. A comparação responde “qual direção teria sido melhor quando o PR122 sinalizou?”, não “qual estratégia integral maximiza retorno no universo”.

## 3. Classificação dos dados

| Ativo | Origem | Linhas usadas | Cobertura aproximada | Classificação |
|---|---|---:|---|---|
| BTC | `feature_store.db`, leitura SQLite imutável | 200 | 2026-02-21 a 2026-09-08 UTC | `RECONSTRUCTED_HISTORICAL` |
| ETH | Binance REST restaurado, `ETHUSDT.json.gz` | 200 de 2.167 | 2026-02-19 a 2026-09-06 UTC | `RECONSTRUCTED_HISTORICAL` |
| SOL | Binance REST restaurado, `SOLUSDT.json.gz` | 200 de 2.167 | 2026-02-19 a 2026-09-06 UTC | `RECONSTRUCTED_HISTORICAL` |

ETH e SOL têm zero dias internos ausentes e zero duplicatas segundo os metadados restaurados. Ainda assim, os arquivos foram finalizados em 07/09/2026, depois dos eventos. BTC também não possui vintage imutável que prove o conteúdo efetivamente disponível em cada instante. Portanto nenhum input recebeu rótulo `TRUE_PIT`.

O histórico BTC inteiro já havia sido observado no replay anterior, e o contexto de agosto/setembro influenciou a criação do PR122. Reservar tardiamente 20% desse mesmo arquivo e chamá-lo de teste final seria falso. O bloco foi separado e suas métricas não foram computadas. Por consistência conservadora, os blocos finais de ETH e SOL também ficaram sem avaliação final: são históricos pré-existentes, não observações novas coletadas após o congelamento.

## 4. Ledger causal V2 e horizontes

Cada candidato agora contém:

- timestamp candidato, primeiro tempo observável/acionável, classe, direção e features disponíveis em `t`;
- preço no sinal, retorno anterior, custos estimados, decisão e razão;
- resultados futuros 1d, 3d e 7d, MFE, MAE e máximo caminho adverso;
- campos 1h e 4h explicitamente nulos com `NOT_AVAILABLE_DAILY_DATA_FREQUENCY`;
- `episode_id`, `independent_event` e regra de agrupamento;
- rótulo de evidência, disponibilidade do outcome, resultado paper e permissão de capital.

Os outcomes futuros são anexados somente como campos de avaliação. O forecast expansivo continua aceitando apenas outcomes maturados antes do candidato corrente. Os campos intradiários não foram interpolados nem inventados.

## 5. Round A — BTC

### Contagem

| Coorte | Sinais | Episódios independentes |
|---|---:|---:|
| Desenvolvimento | 9 | 4 |
| Validação | 1 | 1 |
| Reservado, não avaliado | 1 | não calculado |

### Validação, PR122

| Cenário | Gross médio | Custo médio | Net médio | Hit rate | MaxDD sequencial | Incremental vs melhor baseline |
|---|---:|---:|---:|---:|---:|---:|
| 10 bps | 0,3484% | 0,1000% | 0,2484% | 100,0% | 0,0000% | 0,0000% vs buy-and-hold |
| 35 bps | 0,3484% | 0,3500% | -0,0016% | 0,0% | 0,0016% | -0,0016% vs breakout/flat |
| 70 bps | 0,3484% | 0,7000% | -0,3516% | 0,0% | 0,3516% | -0,3516% vs breakout/flat |
| 105 bps | 0,3484% | 1,0500% | -0,7016% | 0,0% | 0,7016% | -0,7016% vs breakout/flat |

Com `n=1`, Sharpe, Sortino e intervalo de confiança não são estimáveis. O único episódio não cobre o custo-base. Resultado: **INCONCLUSIVE**.

## 6. Round B — ETH e SOL, configuração fixa

### ETH

| Coorte | Sinais | Episódios independentes |
|---|---:|---:|
| Desenvolvimento | 10 | 5 |
| Validação | 6 | 3 |
| Reservado, não avaliado | 1 | não calculado |

Na validação a 35 bps, PR122 teve gross médio de 0,7002%, custo de 0,3500%, net de 0,3502%, hit rate de 33,33%, profit factor 1,292 e MaxDD sequencial de 2,990%. O IC95 da expectativa líquida foi de -4,0759% a 4,7762%. Buy-and-hold no mesmo coorte teve net médio de 0,5254%; o incremental pareado do PR122 foi -0,1752%, com limite inferior -0,5186%.

No stress de 105 bps, a expectativa líquida do PR122 caiu para -0,3498%. Resultado: **INCONCLUSIVE**.

### SOL

| Coorte | Sinais | Episódios independentes |
|---|---:|---:|
| Desenvolvimento | 13 | 6 |
| Validação | 8 | 5 |
| Reservado, não avaliado | 2 | não calculado |

Na validação a 35 bps, PR122 teve gross médio de 2,1576%, custo de 0,3500%, net de 1,8076%, hit rate de 80,0%, profit factor 6,146 e MaxDD sequencial de 1,756%. O IC95 da expectativa líquida foi de -0,8127% a 4,4279%.

O melhor baseline foi momentum 1d, com os mesmos retornos: incremental do PR122 exatamente 0,0000%. Mesmo no stress de 105 bps, o net médio permaneceu 1,1076%, mas o limite inferior de 95% foi -1,5127%. Com `n=5` e nenhuma vantagem incremental, o resultado é **INCONCLUSIVE**, não positivo.

## 7. Leitura causal e econômica

1. O PR122 não demonstrou vantagem própria sobre regras simples. No SOL, ele reproduziu momentum 1d; no ETH, perdeu para buy-and-hold; no BTC, a evidência é uma única observação.
2. A aparente força do SOL é frágil a dependência e tamanho amostral. Cinco episódios não satisfazem o mínimo congelado de 20, e o intervalo atravessa zero.
3. Custos mudam a conclusão: BTC passa de levemente positivo no otimista para negativo no base; ETH fica negativo no stress.
4. Nenhum resultado representa fill executável. Não há bid/ask, profundidade, slippage observado, latência observada, funding realizado ou confirmação de entrega.
5. Passing tests e replay causal provam engenharia e disciplina temporal; não provam lucro.

## 8. Gaps formalmente demonstrados

| Gap | Evidência | Menor incremento seguinte |
|---|---|---|
| `NO_TRUE_PIT_RESERVED_FINAL` | todos os inputs já existiam antes deste freeze | coletar observações novas, append-only, após `BASELINE_V1` |
| `NO_OBSERVED_EXECUTION_COSTS_OR_QUOTES` | somente OHLCV diário | registrar bid/ask/depth em tempo de evento e acknowledgements de paper fills |
| `NO_INTRADAY_OUTCOMES` | frequência diária torna 1h/4h indisponíveis | coletar dados horários prospectivamente; não rebatizar backfill como PIT |
| `NO_AUTOMATIC_DELIVERY_EVIDENCE` | status atual não observa heartbeat, scan, criação ou recebimento | registrar acknowledgement de entrega no trial prospectivo |
| `EFFECTIVE_N_TOO_SMALL` | validação BTC/ETH/SOL com n efetivo 1/3/5 | acumular pelo menos 20 episódios por avaliação e 60 no trial final congelado |

Esses gaps autorizam somente instrumentação mínima e coleta prospectiva. Não provam necessidade de LLM, HMM, notícias, order book como feature, nova família de sinais ou tuning de limiares.

## 9. Estado operacional

O status observado anteriormente e preservado em `RADAR_STATUS_20260919.json` é:

- schedule configurado: falso;
- scheduler enabled: `NOT_VERIFIED`;
- heartbeat observado: falso;
- live scan observado: falso;
- fresh data observado: falso;
- alerta criado observado: falso;
- entrega observada: falso;
- blind time mensurável: falso.

Assim, o sistema permanece **RESEARCH_ONLY** e **NOT_READY** tanto para paper trading realista quanto para microcapital. O `REALISTIC_PAPER_V2` existe como engenharia, mas não possui quotes históricos/contemporâneos suficientes para execução válida.

## 10. Validação de engenharia

- Primeira tentativa da suíte ampla: coleta interrompida por sete imports de `numpy` ausente no ambiente recém-criado; nenhum teste de produto foi executado nessa tentativa.
- Correção ambiental: sincronização dos extras `v3` e `test` já declarados no projeto, sem mudança de código.
- Reexecução da suíte completa: **1.585 passed, 2 skipped**.
- Testes direcionados do módulo: **16 passed**.
- Ruff: **All checks passed**.
- Pyright via ambiente do projeto: **0 errors, 0 warnings**.
- `git diff --check`: sem erros de whitespace; apenas aviso esperado de conversão LF/CRLF no checkout Windows.
- Build isolado de sdist e wheel: concluído; o wheel contém `GarimpoInvestimentos/profit_recovery_v1.py`.
- O pytest exibiu um aviso de cleanup em diretório temporário protegido após concluir os testes; não houve falha de teste.

## 11. Artefatos

Diretório: `C:\Cripto\operacao\saidas\reuse-verify-gap`

| Artefato | SHA-256 |
|---|---|
| `BASELINE_V1.json` | `6DC31A97AEE92939D395820A65619D8DB36113C18302CE95F9AE29F551C60E29` |
| `LEVEL2_EXECUTION.json` | `19ACE5AA7FF6F12021FAD4710840834994976196EB44CEE050BAC5BA43F14BBE` |
| `BTC_CAUSAL_LEDGER_V2.json` | `EF4064A63D88F3DA107D9BBB6FA9A5F3EE53C6CC354DF6001C1995399ED85A37` |
| `ETH_CAUSAL_LEDGER_V2.json` | `4BA27E74B42654DB47098EA8FDDBB52E47B9FA66FB1FD5EF7D564D289BE02F28` |
| `SOL_CAUSAL_LEDGER_V2.json` | `348C613A4355E86F0A41D96102EF99D910F66B45EC4CF928F0E692D6DBA99A7E` |

Hashes dos inputs:

- ETH: `F7DF37A93394DFE6BB83F0E63040D8F77D4ED40E2776D79B9AD082057C1D7E4B`
- SOL: `57EBEA7FBE67B4089BB2C25B79D83537B654F290C6FC4A7D887799C2BAFDDA49`
- BTC e demais metadados completos: registrados em `LEVEL2_EXECUTION.json`.

## 12. Próximo incremento, sem iniciá-lo

Congelar os bytes e hashes atuais como protocolo prospectivo e iniciar coleta append-only de observações **posteriores** ao freeze, com:

1. candles/eventos recebidos com `event_time`, `received_at`, fonte e hash imutável;
2. bid, ask, profundidade, latência, decisão, acknowledgement e resultado de paper fill;
3. deduplicação por episódio e denominador que preserve falhas e misses;
4. configuração PR122 intocada por no mínimo 60 episódios independentes ou 180–365 dias;
5. decisão final pelos critérios GO/NO-GO/INCONCLUSIVE já congelados.

Este incremento não foi iniciado automaticamente.
