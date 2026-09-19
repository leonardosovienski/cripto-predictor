# PROFIT RECOVERY EXECUTION

**Corte:** 2026-09-19  
**Branch:** `profit-recovery-20260919`  
**Base:** `origin/main` em `1b2bee85f552667ed74a17e5da3526b62541d2d2`  
**Worktree:** `C:\Cripto\work\profit-recovery-20260919`  
**Capital:** proibido; nenhuma ordem, conta, pagamento ou agenda foi ativada.

## Resultado executivo

Foi implementado o primeiro loop econômico causal versionado, separado de H1–H9 e de `SHADOW_REFERENCE_CLOSE_ONLY`. Ele agora consegue:

```text
candle PIT diário
→ candidato PR122
→ ledger causal independente do catálogo oracle
→ outcome pós-sinal em 1/3/7 dias
→ forecast expanding-window com maturação temporal
→ custo com classe de evidência e break-even
→ TRADE / WATCH / NO_TRADE
→ paper V2 por quotes/depth explícitos
→ carteira, custos, PnL líquido e MaxDD
→ ORACLE_MLTT separado de POLICY_MLTT
→ protocolo prospectivo hashado
```

O sistema ainda **não encontrou nem provou edge líquido prospectivo**. No replay BTC disponível, todos os 11 candidatos ficaram `WATCH`: custos são assumidos, as coortes causais são pequenas e não existem quotes/books históricos para fill realista. A trial está `NOT_READY`, não ativa.

## Baseline inicial e versões realmente consumidas

| Objeto | Estado verificado |
|---|---|
| relatório canônico | hash `6637DE6F...E64`, conferido integralmente |
| checkout operacional | `C:\Cripto\pesquisa-20260909`, `bd4ff602...`, não alterado |
| remoto atual usado como base | `1b2bee85...`, contém PR #122 |
| branch de trabalho | `profit-recovery-20260919`, baseada em `origin/main` |
| Core | fonte exige 3.2.1 |
| Ops | fonte exige 4.2.0–<5 e pin 4.2.1 |
| banco consumido | `C:\Cripto\operacao\saidas\feature_store.db`, somente leitura/immutable |
| cobertura ativa | 200 candles BTC 1d, 2026-02-21 a 2026-09-08; publicação até 2026-09-09 |

## Implementações

### Linha nova, sem alterar comportamento histórico

Arquivo principal: `GarimpoInvestimentos/profit_recovery_v1.py`.

- `ORACLE_OPPORTUNITY_CATALOG`: usa MFE/MAE futuro, sempre marcado `ORACLE_DIAGNOSTIC` e nunca alimenta forecast.
- `CAUSAL_OPPORTUNITY_LEDGER`: candidato deriva somente das informações publicadas em `t`; outcome é anexado depois como avaliação.
- custo V1: fee, spread, slippage, latência, funding, borrow e infraestrutura, com `ASSUMED`, `ESTIMATED`, `OBSERVED_MARKET`, `PAPER_VALIDATED`, `REAL_FILL_CALIBRATED` ou `STRESSED`.
- `BREAK_EVEN_EDGE`: round trip em bps convertido em retorno.
- `POST_SIGNAL_EDGE_PREDICTOR`: média/variância expanding-window por classe, direção e horizonte, consumindo apenas outcomes amadurecidos antes do candidato.
- economic gate: `TRADE` exige amostra mínima, custo observado, limite inferior líquido positivo e `P(net>0) >= 0,60`; caso contrário produz `WATCH`/`NO_TRADE` com razão.
- `REALISTIC_PAPER_V2`: quote timestamp, bid/ask, depth, marketable fill, partial fill/reject, fee, spread, latência, entry/exit e net PnL; nunca faz rede.
- carteira V1: cash, realized/unrealized PnL, fees, funding, exposições, equity curve, turnover e MaxDD.
- baselines comparáveis: always-flat, buy-and-hold, momentum 1/7/30d, breakout 20d, média móvel, mean reversion e direção PR122.
- métricas oracle-relativas explicitamente diagnósticas e MLTT causal separado.
- status operacional separado em configuração, habilitação, heartbeat, scan, freshness, alerta, entrega e blind time.
- trial prospectiva completa e hashada, mas mantida `NOT_READY` por blockers reais.
- CLI integrada: `cripto-predictor profit-recovery ...`.

### Preservação

Não foram alterados: H1–H9, charters, scientific state, thresholds do PR #122, paper V3 histórico, cost policy histórica, banco, configuração privada, dados restaurados, agenda ou runtime instalado. O worktree operacional principal continuou limpo.

## Artefatos e hashes

| Artefato | SHA-256 | Natureza |
|---|---|---|
| `BTC_REPLAY_V1_1_20260919.json` | `0F42A50077F2F1550FCBD95FFA2AAE971BFC271F4607A3BCB17CC225053B4EC7` | replay PIT/retrospectivo BTC |
| `RADAR_STATUS_20260919.json` | `2BA732F88BBCF34A01E6EF54E7F29FEEACD320A88568BDC9E85DB05D817C004F` | observação operacional |
| `PROSPECTIVE_TRIAL_V1.json` | `2982870B1BCB48607B8702670AB2B0463D49B755500B1C2D6D0C7FBDA6C33753` | protocolo `NOT_READY` |
| `PAPER_PORTFOLIO_SYNTHETIC_CONTROL_V1.json` | `6D3623D25384D6CEAC79D5D74DC68B780E4DD00E45BE12F3D5E1E84AF91ED413` | controle de engenharia sintético |

Diretório: `C:\Cripto\operacao\saidas\profit-recovery`.

Versões anteriores do replay geradas durante desenvolvimento foram preservadas e não são a referência final. `V1_1` corrige MFE/MAE para usar highs/lows intraday; os outputs antigos não foram apagados.

## ORACLE_OPPORTUNITY_CATALOG

Foram encontrados 26 clusters oracle BTC em horizonte de 7 dias e limiar perfeito-futuro de 5%. Esse número só responde “onde havia movimento futuro”; não responde previsibilidade. `ORACLE_MLTT=1,764149` é soma diagnóstica de retornos MFE por evento, não carteira, capital ou valor capturável.

## CAUSAL_OPPORTUNITY_LEDGER

Foram gerados 11 candidatos por transições PR122 em tempo causal. Todos possuem features disponíveis em `t`, preço do sinal, retorno anterior, outcome posterior, MFE, MAE, custo, forecast e decisão. O outcome não participa da geração do candidato.

| Resultado pós-sinal sob custo assumido | Eventos |
|---|---:|
| positivo | 6 |
| não positivo | 5 |
| total | 11 |
| decisões `TRADE` | 0 |
| decisões `WATCH` | 11 |

Classificação: 3 `NOT_CAUSALLY_PREDICTABLE`, 5 `NOT_ECONOMIC_AFTER_COSTS`, 3 `NOT_VERIFIED`. Nenhum caso foi promovido a `CAPTURABLE_MISSED_OPPORTUNITY`, pois isso exigiria política causal aprovada e execução plausível.

## Replay obrigatório de agosto

| Campo | Resultado |
|---|---|
| candle/candidate timestamp | 2026-08-19 00:00 UTC |
| first observable/actionable | 2026-08-20 00:00 UTC, após publicação do candle fechado |
| classe/direção | `STRONG_MOVE / bull` |
| preço no sinal | 69.334,79 USDT, close proxy |
| 1d / 3d / 7d | +7,1214% / +10,23% / +9,2231% |
| relative volume 20d | 2,7466x nos candles salvos |
| SMA50 / RSI | +8,2908% / 74,36 |
| movimento já ocorrido | +9,2231% em 7d |
| retorno futuro close-to-close 3d | +11,1634% |
| custo estimado | 35 bps, `ASSUMED` |
| retorno futuro líquido modelado | +10,8134% |
| MFE / MAE intraday | +14,6611% / -0,6239% |
| forecast causal em t | +0,9894% bruto; +0,6394% líquido esperado; n=1 |
| incerteza / P(net>0) | indisponível com n=1 |
| decisão | `WATCH`, amostra abaixo de 20 |
| paper entry/exit/PnL | indisponível: sem quotes/depth históricos |
| drawdown de carteira | indisponível: não houve trade |
| capturabilidade | `NOT_VERIFIED` |

Conclusão: o PR #122 teria detectado o movimento, mas somente depois do fechamento diário. Havia retorno posterior no proxy de close, porém a política causal não possuía evidência para distinguir continuação de esgotamento. O número de volume difere da referência aproximada 2,41x porque o replay derivou `quote volume = volume × close` a partir dos 21 candles preservados; nenhuma calibração foi feita para aproximar o caso conhecido.

## Setembro

No último candle disponível, 2026-09-08 publicado em 09/09 00:00 UTC, o detector produz `PERSISTENT bull` a 78.455,80, com 30d +20,8842%, preço +12,0882% sobre SMA50, 3d -1,72%, MACD histogram negativo e RSI 49,73. Não há candle posterior no store para avaliar retorno pós-sinal. Classificação: `NOT_VERIFIED`. A referência aproximada +22,41%/+11,5% não foi forçada; a divergência foi mantida.

## Coorte e baselines

Resultados sobre os mesmos 11 timestamps causais, horizonte 3d e custo assumido de 35 bps:

| Regra | mean net/evento | hit rate | Limite |
|---|---:|---:|---|
| always-flat | 0,0000% | 0,0% | referência |
| buy-and-hold | -1,0442% | 36,4% | mesma coorte |
| momentum 1d | +2,3885% | 54,5% | adaptativo/retrospectivo |
| momentum 7d | +2,3885% | 54,5% | adaptativo/retrospectivo |
| momentum 30d | +2,1331% | 45,5% | adaptativo/retrospectivo |
| breakout 20d | +2,4962% | 36,4% | poucos trades implícitos |
| MA trend | +2,3474% | 54,5% | adaptativo/retrospectivo |
| mean reversion 1d | -3,0885% | 18,2% | NO-GO nesta coorte |
| direção PR122 | +2,3885% | 54,5% | não OOS; idêntica a momentum nesta coorte |

Essas médias **não são edge validado**: n=11, somente BTC, período usado para construir/conhecer PR122, dependência temporal, custos assumidos e fills inexistentes. A igualdade PR122/momentum simples demonstra que complexidade incremental ainda não foi provada. O candidato mais forte para pesquisa é continuação/momentum simples pós-alerta, mas sua evidência é apenas `RETROSPECTIVE_ADAPTIVE_CANDIDATE`.

Métricas oracle-relativas diagnósticas:

- matched oracle events: 8/26;
- Opportunity Miss Rate: 69,23%;
- detection latency média: 165h, afetada pela definição oracle anterior ao movimento e cadência diária;
- Economic Alert Precision após custos assumidos: 54,55%;
- False Opportunity Rate: 45,45%;
- Alert Delivery Rate e Capture Rate: indisponíveis.

## Custos, decisão, paper e carteira

O custo mínimo está implementado e calcula break-even por venue/instrument/order type. No replay, 10 bps de fee por perna + 5 bps spread round trip + 10 bps slippage = 35 bps. Evidência: `ASSUMED`; não é custo observado.

O gate econômico existe e foi consumido pelo replay. Todos os resultados foram `WATCH`, provando que a interface não transforma `BULL/STRONG_MOVE` automaticamente em trade.

O `REALISTIC_PAPER_V2` foi integrado e executado em controle sintético com quote, depth, fill, fee e saída. A carteira calculou PnL líquido/equity/MaxDD. Esse controle prova contratos e contas básicas, não realismo de mercado. O replay real ficou `NOT_AVAILABLE_MISSING_QUOTES`, sem inventar fills.

## Radar operacional

```text
SCHEDULE_CONFIGURED=false
SCHEDULER_ENABLED=NOT_VERIFIED
HEARTBEAT_OBSERVED=false
LIVE_SCAN_OBSERVED=false
FRESH_DATA_OBSERVED=false
ALERT_CREATED_OBSERVED=false
ALERT_DELIVERY_OBSERVED=false
BLIND_TIME_MEASURABLE=false
```

O PR #122 está na branch-base, mas o runtime ativo continua no checkout anterior e não há agenda/heartbeat/state observados. O P0-A não foi encerrado. A agenda não foi ativada porque `C:\Cripto\AGENTS.md` proíbe ativar agendamentos nesta execução; isso é um blocker de autorização operacional, não uma omissão silenciosa.

## Trial prospectiva

Trial: `profit-recovery-prospective-v1`  
Hash da especificação canônica: `fb33eed46841c8251297f61e416bd2282134a88a34fb4827cc259d842c3f61a5`  
Estado: `NOT_READY`.

O protocolo fixa BTC/ETH/SOL, thresholds PR122, target líquido 72h desde primeira quote executável, baselines, entrada/saída, sizing, risco, mínimo de 60 eventos independentes e 180 dias, máximo de 365 dias e critérios GO/NO-GO/INCONCLUSIVE. Não foi ativado porque os pré-requisitos abaixo ainda falham.

## Estado P0

| P0 | Estado | CODE | TEST | RUN/OUTPUT | Evidência econômica |
|---|---|---:|---:|---:|---|
| A — radar operacional | BLOCKED | PR122 + status | sim | status real | sem scheduler/heartbeat |
| B — replay/ledgers | PARTIAL | sim | sim | BTC real | ETH/SOL ausentes |
| C — cost model | PARTIAL | sim | sim | 35 bps assumed | não observado/paper-validado |
| D — predictor pós-sinal | PARTIAL | sim | sim | 11 forecasts | n pequeno, não OOS |
| E — decision engine | ENGINEERING_COMPLETE | sim | sim | 11 WATCH | sem TRADE validado |
| F — paper realistic | PARTIAL | sim | sim | sintético | real quotes ausentes |
| G — portfolio/risk/net PnL | PARTIAL | sim | sim | sintético | nenhuma carteira real-paper |
| H — regressões econômicas | PARTIAL | sim | sim | casos favoráveis/adversos | regimes/dados reais incompletos |
| I — prospective trial | NOT_READY | spec hashada | schema/test | artefato | tempo/dados/operação pendentes |

## Validação técnica

- Baseline focada inicial precisou corrigir o modo de invocação porque `CRIPTO.cmd` fixa o cwd no checkout operacional; nenhum código falhou nessa primeira tentativa.
- 221 testes focados: PASS.
- Nova suíte: 14 testes: PASS.
- Suíte integral antes do build: 1.581 PASS, 1 SKIP, 2 FAIL exclusivamente porque `dist/` ainda não existia.
- Wheel e sdist construídos com sucesso em `dist/`.
- Build final repetido após as últimas mudanças; distribuição + módulos impactados: 146 PASS.
- Wheel instalado sem dependências num venv limpo sob `C:\Cripto\operacao\temporarios`; import retornou `profit-recovery/v1`, `capital_permission=False` e trial `NOT_READY`.
- Ruff check/format: PASS.
- Pyright focado: 0 erros, 0 warnings.
- `git diff --check`: PASS.
- Aviso persistente de cleanup do pytest: `PermissionError` no symlink `pytest-current` após a conclusão; não altera os resultados.

Não se declara a suíte integral pós-build como executada por inferência: os dois failures de pré-requisito foram reexecutados e passaram, mas a suíte inteira não foi repetida após o build neste corte.

## Vereditos progressivos

```text
SCHEDULE_CONFIGURED=false
SCHEDULER_ENABLED=NOT_VERIFIED
HEARTBEAT_OBSERVED=false
LIVE_SCAN_OBSERVED=false
ALERT_DELIVERY_OBSERVED=false

MISSED_OPPORTUNITY_LEDGER_AVAILABLE=true
AUGUST_REPLAY_AVAILABLE=true

COST_MODEL_AVAILABLE=true
COST_MODEL_MARKET_OBSERVED=false
COST_MODEL_PAPER_VALIDATED=false
COST_MODEL_REAL_FILL_CALIBRATED=false

POST_SIGNAL_FORECAST_AVAILABLE=true
POST_ALERT_EDGE_PROVEN_OOS=false
ECONOMIC_DECISION_AVAILABLE=true
REALISTIC_PAPER_AVAILABLE=true
PORTFOLIO_NET_PNL_AVAILABLE=true

PROSPECTIVE_TRIAL_STATE=NOT_READY
PROSPECTIVE_EDGE_DEMONSTRATED=false
REALISTIC_PAPER_PROFIT_DEMONSTRATED=false
```

`REALISTIC_PAPER_AVAILABLE` e `PORTFOLIO_NET_PNL_AVAILABLE` significam que os engines versionados existem, são integrados e passaram controle sintético. Não significam que custos ou lucro foram validados com mercado.

## BLOCKERS_TO_PROFIT

| ID | Transição | Evidência/impacto | Implementação/teste restante | Critério de conclusão | Status |
|---|---|---|---|---|---|
| B01 | mercado→radar | sem schedule/heartbeat/scan | instalar versão revisada e agenda autorizada; observar ciclos | scheduler habilitado, heartbeat/live scan e freshness dentro do SLA | BLOCKED_AUTHORIZATION |
| B02 | universo→breadth | DB BTC-only/stale | ingestão PIT BTC/ETH/SOL | ≥99% cobertura congelada, gaps publicados | BLOCKED_DATA |
| B03 | alerta→forecast | n=11; agosto n comparável=1 | coleta temporal independente | ≥60 eventos independentes/≥180d | BLOCKED_TIME |
| B04 | forecast→líquido | 35 bps assumidos | quotes/book/fee/funding observados | cost evidence ≥OBSERVED_MARKET e stress | BLOCKED_DATA |
| B05 | decisão→paper | replay sem quotes | feed PIT de quotes/depth e latency | order→fill/reject→exit reconciliado | BLOCKED_DATA |
| B06 | alert→recipient | sem ACK/SLA | receipt/ACK e denominador de delivery | ≥99% delivery+ACK na trial | BLOCKED_OPERATION |
| B07 | paper→portfolio | somente controle sintético | trades futuros do paper V2 | equity/net PnL/custos/MaxDD reconciliados | BLOCKED_TIME |
| B08 | trial→veredito | trial NOT_READY | resolver B01–B06 e congelar estado READY | critérios predefinidos sem mudança material | OPEN |

## Respostas finais

**Se uma oportunidade começar amanhã, o sistema observará automaticamente?** Não no runtime atual: não há agenda, heartbeat ou live scan observados.

**Perceberá enquanto ainda houver retorno?** O detector diário pode perceber no próximo fechamento; agosto teve retorno proxy posterior, mas a latência e a disponibilidade de edge variam. Não há garantia.

**Distingue continuação de esgotamento?** Ainda não. O predictor existe, mas a coorte comparável é pequena e não OOS.

**Estima líquido/custos/incerteza?** A interface e o cálculo existem; custo observado e incerteza adequada ainda não.

**Produz TRADE/WATCH/NO_TRADE por razão verificável?** Sim como engine. Nos dados reais disponíveis produziu 11 `WATCH`; nenhum `TRADE`.

**Simula entrada/posição/saída realisticamente?** O paper V2 aceita quotes/depth reais e representa partial/reject; só foi executado em controle sintético. Dados reais históricos suficientes não existem.

**Mede PnL líquido/risco?** O engine de carteira mede, mas não há trades real-paper para uma medida econômica.

**Registra capturado e deixado na mesa?** Sim, com oracle separado da política. `POLICY_MLTT=0` neste replay porque a política causal não autorizou trades; isso não significa ausência de oportunidades, apenas ausência de valor capturável por uma política congelada aprovada.

**Candidato mais forte hoje:** continuação/momentum simples pós-alerta. Mecanismo: persistência direcional após aceleração/volume. Evidência: média retrospectiva líquida assumida de +2,3885% por candidato em n=11, igual a baselines momentum simples e não independente. Veredito: `CANDIDATE_NOT_VALIDATED`.

**Edge plausível e generalizável encontrado?** Plausível para pesquisa, não demonstrado. A trial preparada é a `profit-recovery-prospective-v1`, estado `NOT_READY`; não foi ativada nem disfarçada como coleta prospectiva.

## Próxima ação objetiva

Resolver B01 e B02 sob autorização operacional: instalar a branch revisada no runtime de QA, configurar sem ativar até aprovação explícita uma agenda dedicada de radar/market-data, garantir BTC/ETH/SOL PIT e iniciar somente quando heartbeat/freshness/ACK/quotes observados permitirem mudar a trial para `READY_FROZEN`. Isso não autoriza capital nem reabre H1–H9.
