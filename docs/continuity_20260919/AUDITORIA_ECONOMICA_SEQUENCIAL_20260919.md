# Auditoria econômica sequencial, causal e orientada a lucro — Cripto Predictor

**Data de corte:** 2026-09-19 (America/Sao_Paulo)  
**Modo:** READ_ONLY sobre produto, código, configuração, dados, thresholds, trials, agenda e capital  
**Pergunta de auditoria:** o sistema consegue transformar uma nova oportunidade de amanhã em detecção, classificação, previsão, decisão, entrega, execução paper, risco e P&L líquido demonstrável?

> **Resposta curta: não.** Existem componentes úteis de pesquisa, preservação, integração e controle. O PR #122 adiciona um detector determinístico de movimentos já observados, mas não demonstra valor futuro, não está no runtime ativo auditado e não fecha decisão, fill, custos, risco e P&L líquido. Nenhuma autorização de capital foi criada ou inferida.

## 1. Executive Summary

O sistema está em estado de **pesquisa economicamente incompleta**. A instalação ativa usa o checkout local `bd4ff602a52e6669b71332b0276c12497f02001e`, enquanto `origin/main` remoto está em `1b2bee85f552667ed74a17e5da3526b62541d2d2` e contém o PR #122. O banco operacional contém somente BTC diário, termina em 2026-09-08/09 e não sustenta operação corrente ou breadth multiativo. Não foi encontrada tarefa agendada correspondente durante esta auditoria.

O PR #122 corrige uma cegueira operacional específica: identifica aceleração, tendência, persistência, extensão por RSI e breadth, preserva estado, deduplica alertas e tenta novamente uma entrega falha. Isso é boa engenharia de observação. Seus thresholds, porém, foram demonstrados em testes de regressão que incluem episódios conhecidos; não há validação temporal independente, estimativa de retorno futuro, calibração, custo executável, paper fill ou P&L.

As famílias científicas permanecem corretamente fechadas ou inativas. H1–H3 são `CLOSED_NO_GO`; H4, H6 e H9 são `CLOSED_INSUFFICIENT_SAMPLE`; H5 é `CLOSED_NO_GO` com direção oposta; H7–H8 são `REGISTERED_NOT_ACTIVATED`. O próprio plugin declara `supports_prediction=False`, `capital_permission=FORBIDDEN` e resultado econômico histórico sem GO. Os 113 testes focados aprovados nesta auditoria confirmam contratos de software, não edge nem lucro.

**Conclusão:** preserve a disciplina científica e os componentes bons, mas não promova o sistema. Primeiro é necessário um experimento prospectivo congelado e uma execução paper realista, com custos observáveis, baselines comparáveis e decisão por evento. Até lá, `REAL_CAPITAL_READY=false`.

## 2. Snapshot principal auditado

| Item | Snapshot verificado | Estado |
|---|---|---|
| Checkout operacional | `C:\Cripto\pesquisa-20260909` | limpo, branch `main` |
| HEAD local/instalado | `bd4ff602a52e6669b71332b0276c12497f02001e` | anterior ao PR #122 |
| `origin/main` remoto | `1b2bee85f552667ed74a17e5da3526b62541d2d2` | verificado via `ls-remote` |
| PR #122 head | `7b8f839b4eae6d233d44a2b39939323f373cd666` | mergeado no remoto |
| Pacotes ativos | Cripto 1.1.0; Core 3.2.1; Ops 4.2.1 | Cripto em editable local |
| Python | 3.13.14 | ativo pelo launcher oficial |
| Banco | `C:\Cripto\operacao\saidas\feature_store.db` | aberto somente leitura |
| Cobertura de mercado ativa | BTC 1d, 200 candles, 2026-02-21 a 2026-09-08 | stale e monoativo |
| Signals externos | Fear & Greed, 200, até 2026-09-09 | stale |
| Predições | 3, BTC/Gemini, 2026-09-09 | sem operação atual |
| Snapshots imutáveis | 2 market snapshots; 1 prediction input | insuficiente para replay histórico completo |
| Agenda | nenhuma tarefa correspondente encontrada | observação pontual, não prova universal |
| Permissão de capital | `false` / `FORBIDDEN` | preservada |

## 3. Contexto reconstruído do histórico

A evolução observada separa quatro linhas: (a) score LLM D+7; (b) funding/OI/HMM V3; (c) estudos históricos de carry/altcoin; (d) radar determinístico do PR #122. Elas não devem ser colapsadas. Resultados negativos, insuficientes e inativos foram preservados; estudos condicionais históricos não reabrem H1–H9 nem validam capital.

O documento colado foi tratado como mandato e fonte de perguntas, não como prova do estado atual. Estado foi confrontado com Git, código, testes, runtime, banco e documentação versionada.

## 4. Repositórios/componentes auditados

| Escopo | Profundidade | Observação |
|---|---|---|
| `C:\Cripto\pesquisa-20260909` | código, docs, testes, runtime e banco | principal |
| `origin/main` do Cripto | commits/diffs e código do PR #122 | remoto atual, não instalado |
| Predictor Core 3.2.1 | contrato/versão e uso pelo Cripto | dependência ativa |
| Predictor Ops 4.2.1 | deployment e integração | instalado; sem agenda ativada |
| CAIN | superfície de integração fixada | não auditado como estratégia de lucro |
| Ecosystem Predictor | contrato Snapshot/Bundle fixado | não auditado como estratégia de lucro |

## 5. Relações entre repositórios

`Cripto -> Core/Ops` fornece ingestão, armazenamento, contratos e operação. `Cripto -> Snapshot/Bundle -> CAIN/Ecosystem` exporta evidência de pesquisa e interoperabilidade. Essa segunda via não pertence ao caminho de dinheiro e não converte automaticamente evidência em previsão, decisão ou P&L. O teste integrado fixou CAIN `5ba4177...`, Ecosystem `6a99852...`, Core 3.2.1 e Ops 4.2.x; o CAIN local atual não é esse snapshot exato.

## 6. Contradições CHAT × DOCS × CODE × TESTS × RUNTIME

| Alegação/expectativa | Evidência divergente | Resolução |
|---|---|---|
| “PR #122 resolve oportunidades perdidas” | detecta movimentos observados; não estima retorno futuro | correção de observabilidade, não edge |
| “main atual tem radar” | remoto sim; instalação editable aponta para HEAD local anterior | não está no runtime ativo |
| “breadth está disponível” | código exige ≥2 ativos; DB ativa só possui BTC | não operacional no snapshot |
| “paper trading mede lucro” | ledger usa reference close; relatório soma retornos brutos | não mede P&L de carteira executável |
| “custos estão modelados” | parâmetros são assumidos; `CALIBRATED_FOR_VERDICT` é vazio | simulação não é calibração |
| “tests/CI provam capacidade” | 113 testes locais + 16 checks do PR aprovam engenharia | não provam mercado, semântica ou lucro |
| “integração CAIN valida produto” | E2E é sintético e fixa commits | valida intercâmbio, não resultado econômico |

## 7. Cronologia relevante

| Data | Evento | Leitura econômica |
|---|---|---|
| 2026-07 | H4/H5 encerradas | H5 mostrou direção oposta; H4 baixa amostra |
| 2026-09-04 | H6/H9 encerradas; H7 tentou e abortou | insuficiência/harness, sem novo edge |
| 2026-09-07–10 | auditorias e controles temporais | melhor correção/reprodutibilidade futura |
| 2026-09-09 | últimos signals/predições ativos | operação depois ficou stale |
| 2026-09-15 | HEAD local `bd4ff602` | runtime editable atual |
| 2026-09-18 | PR #122 mergeado em `1b2bee85` | detector existe no remoto, não no runtime |
| 2026-09-19 | esta auditoria | sem promoção, agenda ou capital |

## 8. Limitações de evidência

- Não houve acesso ao histórico integral de todos os chats; foram usados o mandato fornecido, o estado local/remote e o histórico preservado no repositório.
- O replay dos episódios de agosto/setembro é retrospectivo: os thresholds já conhecem esses casos por testes.
- H5 não possui todos os inputs brutos originais; reprodução exata permanece impossível.
- OOHLCV histórico sofre `upsert` e não preserva todas as vintages/recebimentos; snapshots imutáveis começaram tarde.
- Não existem fills pessoais, livro executável histórico completo, extratos de fees, rejeições ou latência real suficientes.
- A ausência de tarefa agendada foi verificada neste host/sessão; não é prova sobre outros hosts.

## 9. Objetivo econômico formal

Para cada decisão em tempo `t`, o sistema deveria maximizar retorno líquido ajustado a risco, estritamente com informação disponível em `t`:

`net_pnl = filled_qty * (exit_fill - entry_fill) - fees - spread - slippage - funding - borrow - latency/adverse_selection`

O sucesso requer vantagem incremental sobre baselines sob o mesmo universo, relógio, exposição, capacidade e custos; IC temporal e drawdown devem ser reportados. Score, estado, alerta ou retorno bruto isolado não satisfazem o objetivo.

## 10. Arquitetura real

`fontes -> FeatureStore -> (LLM score | V3 signal | PR122 radar) -> artefatos/alertas`

Existe uma biblioteca separada de `trading` para intent, custos, execução simulada e portfólio. Ela não é consumida pelo fluxo ativo do radar. A V3 tem gate econômico dentro de backtest e paper teórico, mas a família está congelada e o modelo de custo não é calibrado. O fluxo ativo termina em análise/artefato, não em posição economicamente reconciliada.

## 11. Caminho econômico atual

| Elo | Estado | Resultado |
|---|---|---|
| observação | parcial/stale | BTC diário até 08/09 |
| detecção | código remoto apenas | regressão sintética/episódios conhecidos |
| previsão | não demonstrada | radar não prevê; LLM/V3 sem GO |
| decisão | desconectada | gate V3 não alimenta radar/runtime |
| alerta | implementação remota | sem evidência operacional/receipt |
| entrada/fill | ausente | reference close não é fill |
| posição/risco | componentes isolados | sem carteira ativa integrada |
| saída | ausente no radar | horizontes não são regras executáveis |
| custos | assumidos | nenhum calibrado para veredito |
| P&L líquido | indisponível | relatório é bruto/descritivo |

## 12. Localização exata dos breaks

| ID | Break | Evidência | Efeito |
|---|---|---|---|
| BREAK-01 | observação corrente | DB stale e BTC-only; sem agenda encontrada | cobertura/breadth falham |
| BREAK-02 | detecção → previsão | radar classifica passado/presente | não há edge futuro |
| BREAK-03 | previsão → decisão | scores não calibrados; gate V3 isolado | não há ação causal |
| BREAK-04 | decisão → entrega | PR #122 não instalado; webhook sem ACK/SLA | entrega não provada |
| BREAK-05 | alerta → fill | paper usa close de referência | execução irreal |
| BREAK-06 | fill → risco/saída | componentes não integrados | posição não gerida |
| BREAK-07 | custos → P&L | custo assumido; nenhum modelo calibrado | líquido não mensurável |
| BREAK-08 | P&L → avaliação | sem trial prospectiva ativa | edge não demonstrado |
| BREAK-09 | causalidade/PIT | OHLCV por upsert e vintages incompletas | replay integral impossível |

## 13. Componentes bons que devem ser preservados

- Registro de hypotheses/trials, selos, estados congelados e resultados negativos.
- Snapshots imutáveis, hashes e proveniência introduzidos para dados novos.
- WFA com folds/purge e HMM ajustado por fold, mantendo `UNVALIDATED` como veredito final.
- PR #122: recusa gaps, transições, deduplicação, retry, telemetria e independência de LLM/capital.
- Guard `CALIBRATED_FOR_VERDICT` vazio, impedindo promoção por mera existência de um modelo.
- Tipos, state machine, store, reconciliação e simulador microestrutural como componentes isolados.
- Contratos Snapshot/Bundle com combinação exata de commits e controles sintéticos.
- Isolamento de credenciais/caminhos e `capital_permission=false`.

## 14. Falhas históricas relevantes

H1 perdeu o pequeno bruto sob custo assumido; H2 não atingiu evidência; H3 perdeu edge bruto e teve MaxDD de 50,3%; H4 parou em n=5; H5 mostrou correlação oposta; H6 ficou underpowered; H7 falhou no harness sem resultado; H8 não foi ativada; H9 teve somente 1/45 folds avaliável. Estudos de carry possuem cenários positivos e negativos, mas não são execução prospectiva e dependem de hipóteses de custos/capacidade.

## 15. O que PR #122 corrigiu

Corrigiu a ausência de um radar determinístico anterior ao LLM para movimentos grandes/persistentes. Implementou aceleração 1d/3d/7d, persistência 30d, direção, extensão RSI, breadth, gap guard, estado durável, deduplicação, escalada/reversão, retry e eventos operacionais. Mantém `capital=false` e natureza informacional.

## 16. O que PR #122 não corrigiu

Não define retorno futuro, probabilidade, distribuição, horizonte econômico, validade, entrada, saída, size, custo, fill, risco ou P&L. Não valida falsos positivos/negativos, latência econômica, valor pós-alerta ou estabilidade OOS. Não está instalado no runtime auditado, e o DB ativo não sustenta breadth. Webhook aceito não equivale a recebimento humano/ACK.

## 17. Auditoria dos thresholds do PR #122

| Threshold | Função | Evidência | Veredito |
|---|---|---|---|
| 1d ≥ 5% + volume ≥ 1,5x | aceleração | hardcoded + regressão conhecida | candidato, não OOS |
| 3d ≥ 8% | aceleração | hardcoded + regressão | candidato |
| 7d ≥ 10% | aceleração | hardcoded + regressão | candidato |
| 7d ≥ 5% + MACD | tendência | regra heurística | não calibrado |
| 30d ≥ 15% + SMA50 | persistência | regra heurística | não calibrado |
| RSI ≥70/≤30 | risco de extensão | flag, não decisão | sem valor futuro medido |
| breadth: ≥2 ativos com 1d ≥5% | regime amplo | teste sintético | inviável no DB BTC-only |

Não há origem empírica pré-registrada, grid congelada, curva de sensibilidade, múltiplos testes, holdout temporal ou custo econômico comum. Os episódios-alvo não podem ser chamados OOS.

## 18. Inventário H1-Hn

H1–H9 estão detalhadas na Matriz E (§46). Nenhuma família está simultaneamente ativa, causalmente íntegra, economicamente calibrada e aprovada.

## 19. Auditoria de targets/labels

- LLM: próximo close diário após D+7; explícito, mas retorno bruto e score ordinal não calibrado.
- V3: forward 24h/48h e barreiras; o target é quantificável, porém usa proxy spot/custos assumidos e séries sobrepostas.
- Radar: não possui label futuro; seus estados são propriedades da janela observada.
- Paper: close de referência não é label de fill executável.

`MODEL_TARGETS_ECONOMICALLY_DEFINED=FAIL` no sistema, apesar de definições parciais em experimentos.

## 20. Auditoria dos outputs

`opportunity_score` 0–100 é ordinal; não é probabilidade nem retorno líquido. `strength` V3 é intensidade de funding × probabilidade de regime; não é retorno previsto. `WATCH/PERSISTENT/STRONG_MOVE` são estados descritivos. Dispersão de amostras LLM é proxy de variação, não incerteza preditiva calibrada. Nenhum output ativo deve ser interpretado como sizing ou ordem.

## 21. Auditoria dos baselines

Há majority-class e diagnósticos pontuais, além de referências históricas, mas não uma suíte comparável sob mesmo relógio, universo, exposição, custo e capacidade. Faltam ao radar: always-flat, buy-and-hold, momentum simples, breakout, média móvel e mean reversion, todos event-time e net. `BASELINES_AVAILABLE=FAIL` para decisão econômica.

## 22. Classes de oportunidade

O radar cobre parcialmente trend/momentum, movimento idiossincrático e risk-on/off via breadth. RSI apenas sinaliza extensão. Breakout, reversal, news, macro, liquidity/order-flow, squeeze, leverage dislocation, carry e DeFi não têm detectores economicamente validados. Classes não devem compartilhar automaticamente thresholds ou vereditos.

## 23. Auditoria do Opportunity Radar

**Implementação:** boa separação da LLM, cálculo contíguo, estado e retry.  
**Evidência:** unit/regression tests e 16 checks do PR.  
**Ausências:** implantação, cobertura multiativo, trial prospectiva, target futuro, baselines, decisão e execução.  
**Veredito:** `DETECTION_PROVEN=FAIL` como capacidade operacional/econômica; apenas a implementação de regressão está confirmada.

## 24. Replay econômico PIT

Os episódios aproximados de 19/08 e 09/09 estão incorporados nos testes do detector e, portanto, são **in-sample para esta regra de aceitação**. O replay comprova que a regra atual os reconheceria com candles fornecidos, desde que completos. Não comprova que o threshold existia antes, que o dado chegou a tempo, que o alerta seria recebido, nem que haveria retorno líquido posterior. Classificação: `RETROSPECTIVE_COUNTERFACTUAL`, não prospectiva.

## 25. Regressões adversariais

Confirmadas no código/testes: direção bear simétrica, quiet market, gaps recusados, estado/dedup, reversão, retry e breadth sintético. Ausentes: spike seguido de reversão, baixa liquidez, stale feed, venue divergence, clock drift, revision/vintage, partial book, reject/partial fill, alert late, webhook 2xx sem consumo, custo adverso e dependência cross-asset. Estes testes são P0 antes de qualquer claim econômico.

## 26. Dados × horizontes

O store ativo tem somente BTC 1d; 3d/7d/20d/30d são derivados desses candles. Existem dados restaurados de spot/perp/funding/OI fora do fluxo ativo, com lacunas documentadas. Não há alinhamento operacional completo entre frequência da decisão e quotes/book/fills. Matriz completa no §44.

## 27. Universo

Configuração default cita BTC/ETH/SOL, mas `phase1` escolhe primeiro `store.list_symbols("1d")`; como BTC já existe, o fallback default não entra e o universo permanece BTC. Isso bloqueia breadth e cria viés de disponibilidade. A unidade de decisão, elegibilidade, delist/listing, liquidez e capacidade não estão congeladas para um trial econômico.

## 28. LLM

O prompt define horizonte D+7 e avisa que score não é probabilidade/retorno líquido. H5, a maior amostra, teve rho -0,166 com IC95 inteiramente negativo na direção oposta. H4/H6 foram insuficientes. A LLM não deve ser usada hoje como preditor, filtro ou engine de decisão; H8 como gerador de hipóteses continua não ativada.

## 29. Modelos quantitativos

V3/HMM possui WFA/purge e controles úteis, mas usa proxy spot para produto derivativo, custo/fill não calibrados e PSR IID diagnóstico sobre retornos sobrepostos. `strength` não é forecast. H1–H3 fecharam NO-GO; H9 é inconclusivo. O radar é uma regra determinística descritiva, não modelo de retorno.

## 30. Economic Decision Engine

`economic_gate.py` estima média signed in-sample com HAC e só libera `SHADOW_TRADE` se limite conservador líquido superar hurdle. É conceitualmente útil, porém opt-in no backtest, não calibrado em produção, não ligado ao radar e incompatível com família congelada como caminho de promoção. Não existe engine ativa evento→ação.

## 31. Custos

V3 assume 10 bps taker + 5 bps slippage por perna e funding constante; não é calibração pessoal. A camada spot pode walk-the-book e representar spread/depth/fee/latency, mas está desconectada e sem dados observados suficientes. `CALIBRATED_FOR_VERDICT=frozenset()`. `COST_MODEL_VALIDATED=FAIL`.

## 32. Paper trading

O paper V3 exige família aberta; `funding_oi_hmm_v3` está congelada. Registra sinal no modo `SHADOW_REFERENCE_CLOSE_ONLY`, sem order, bid/ask, queue, reject, partial fill ou fee observado. O relatório declara retornos brutos descritivos e `cum_pnl` é alias para soma de retornos, não patrimônio. `REALISTIC_PAPER_EXECUTION_AVAILABLE=FAIL`.

## 33. Risk/portfolio

Há código para exposição, beta/correlação, concentração/HHI, drawdown e reconciliação. Não há portfolio ledger ativo alimentado pelo radar, limites pré-trade vinculantes, kill switch econômico testado end-to-end ou risco pós-fill. Capacidade de componente: `PASS`; capacidade operacional: `FAIL`.

## 34. Execution

A state machine, adapter simulado, idempotência e reconciliação são testados, mas não realizam I/O com exchange nem recebem intents do fluxo ativo. Não existem evidências de fill, rejeição, partial fill, cancel, timeout, venue outage ou slippage real no caminho auditado.

## 35. Operação/alertas

O PR #122 grava alerta local antes do webhook, mantém estado e tenta novamente enquanto a oportunidade está ativa. `delivery_pending` pode permanecer verdadeiro quando webhook não está configurado. Não há ACK do destinatário, SLA ou métrica de end-to-end latency. O código não está instalado e nenhuma agenda correspondente foi encontrada. `ALERT_DELIVERY_RATE` não é mensurável hoje.

## 36. Preservação/PIT

`raw_market_data` usa chave `(source,symbol,interval,ts)` e upsert que sobrescreve OHLCV/published_at; não preserva todas as revisões. `raw_signals` tem melhor suporte a vintage. A migração 0019 introduziu snapshots imutáveis e inputs de predição, mas o DB possui só 2 e 1, respectivamente, e não recupera o passado. `PIT_CAUSALITY_AUDITABLE=FAIL` para a cadeia inteira.

## 37. Integrações multi-repo

O audit E2E com commits fixos valida instalação limpa, schema, hashes, relógios, policy e materialização de quatro fontes sintéticas. Isso é evidência forte de contrato técnico. Não mede forecast, semântica, fill, custo ou lucro. CAIN/Ecosystem ficam fora da cadeia de P&L; não se deve atribuir a eles sucesso econômico do Cripto.

## 38. Documentação

A documentação local é conservadora e explicita `UNVALIDATED`, perdas, baixa amostra e lacunas. Porém está atrasada em relação ao remoto com PR #122, enquanto o runtime também está atrasado. Portanto “current/main” precisa sempre informar SHA e se significa fonte remota, checkout local ou instalação. Nenhum documento deve chamar alertas de oportunidades lucrativas sem target líquido prospectivo.

## 39. `STRATEGY_RESULT`

`NO_VALIDATED_ACTIVE_STRATEGY`. H1–H3/H5 são NO-GO; H4/H6/H9 insuficientes; H7/H8 inativas; radar não é estratégia de retorno. Não há edge prospectivo nem profit demonstrado.

## 40. `CRIPTO_RUNTIME_RESULT`

`PARTIAL_RESEARCH_RUNTIME_NOT_ECONOMICALLY_OPERATIONAL`. Core/Ops e controles locais funcionam; o runtime ativo está no SHA anterior, a coleta está stale/monoativo, o radar não está instalado e decisão→fill→net P&L permanece quebrado.

## 41. `CAIN_CAPABILITY_RESULT`

`ENGINEERING_INTEGRATION_PASS; SEMANTIC_AND_ECONOMIC_NOT_VERIFIED`. A combinação pinada demonstra intercâmbio de evidência e controles sintéticos. Não demonstra qualidade semântica, forecast ou lucro; o checkout CAIN local atual não foi tratado como o snapshot pinado.

## 42. Matriz mestre

| Capacidade | Implementada | Testada | Ativa | Evidência econômica | Veredito |
|---|---:|---:|---:|---:|---|
| ingestão/proveniência | sim | sim | parcial | não | PARTIAL |
| LLM D+7 | sim | sim | não confiável | negativa/insuficiente | FAIL |
| V3/HMM | sim | sim | congelada | NO-GO/insuficiente | FAIL |
| radar PR122 | remoto | sim | não | nenhuma prospectiva | FAIL operacional |
| alert delivery | remoto | simulação | não | nenhuma | FAIL |
| decision engine | parcial | sim | não integrado | nenhuma aprovada | FAIL |
| execution simulator | sim | sim | não integrado | sem calibração | PARTIAL |
| paper realista | não | não | não | nenhuma | FAIL |
| risk/portfolio | componente | sim | não integrado | nenhuma | PARTIAL |
| net P&L | não | não | não | nenhuma | FAIL |
| CAIN evidence interchange | sim | sintético | snapshot pinado | não econômica | PASS técnico |

## 43. Matriz caminho do dinheiro

| Etapa | Artefato atual | Proveniência/PIT | Métrica | Break |
|---|---|---|---|---|
| fonte | candle/signal | parcial | cobertura/freshness | BREAK-01/09 |
| feature | indicadores | parcial | gaps | BREAK-09 |
| detector | estados PR122 | regressão | trigger | BREAK-02 |
| forecast | score/strength | não calibrado | rho/PSR diagnóstico | BREAK-03 |
| decision | gate V3 isolado | fold-local | conservative mean | BREAK-03 |
| alert | arquivo/webhook | estado local | sem ACK/SLA | BREAK-04 |
| order/fill | inexistente no fluxo | — | — | BREAK-05 |
| position/risk | biblioteca isolada | — | — | BREAK-06 |
| exit | inexistente | — | — | BREAK-06 |
| cost | parâmetros assumidos | não observado | stress apenas | BREAK-07 |
| P&L | soma bruta | não carteira | não líquido | BREAK-07/08 |

## 44. Matriz dados × horizontes

| Dado | Frequência ativa | Cobertura ativa | Horizonte usado | Problema |
|---|---|---|---|---|
| BTC OHLCV Binance | 1d | 200 dias até 08/09 | 1/3/7/20/30d | stale; upsert |
| ETH/SOL OHLCV | ausente no DB ativo | zero | breadth | bloqueado |
| Fear & Greed | 1d | até 09/09 | contexto LLM | stale |
| Funding/OI/perp restaurado | 1h/8h/dia, fora do ativo | lacunas | 24/48h | não operacional |
| News/macro | variado | incompleto | D+7/regime | availability-time parcial |
| Book/quotes/fills | não persistido para trial | ausente | segundos/minutos | execution impossível |

## 45. Matriz modelo × valor econômico

| Modelo/regra | Output | Target futuro | Calibrado | Net/OOS | Valor atual |
|---|---|---:|---:|---:|---|
| LLM | score 0–100 | D+7 bruto | não | H5 negativo | nenhum |
| HMM V3 | direction/strength | 24/48h proxy | não | NO-GO/UNVALIDATED | nenhum |
| gate V3 | SHADOW/NO_TRADE | mean signed IS | não | backtest-only | pesquisa |
| radar PR122 | estado/direção | nenhum | não | não | observabilidade |
| trading simulator | fill/P&L hipotético | n/a | não | desconectado | engenharia |

## 46. Matriz H1-Hn

| H | Hipótese | Estado preservado | Evidência/limite |
|---|---|---|---|
| H1 | funding/OI+HMM 24h | CLOSED_NO_GO | +0,44 bps bruto → -0,09 líquido assumido; PSR .445 |
| H2 | funding curto | CLOSED_NO_GO | PSR .215; edge insuficiente |
| H3 | 48h | CLOSED_NO_GO | bruto negativo; MaxDD 50,3% |
| H4 | LLM D+7 | CLOSED_INSUFFICIENT_SAMPLE | n=5 |
| H5 | LLM multi-juiz D+7 | CLOSED_NO_GO | rho -0,166, IC95 [-.266,-.057], n=440 |
| H6 | score invertido | CLOSED_INSUFFICIENT_SAMPLE | rho -.057, IC cruza 0, n=84 |
| H7 | macro/DXY HMM | REGISTERED_NOT_ACTIVATED | harness abortou; sem resultado válido |
| H8 | LLM gera hipóteses | REGISTERED_NOT_ACTIVATED | implementado, não coletado |
| H9 | OI/volume | CLOSED_INSUFFICIENT_SAMPLE | PSR .162; 44/45 folds insuficientes |

## 47. Matriz classes de oportunidade

| Classe | Cobertura atual | Evidência futura | Próximo tratamento |
|---|---|---|---|
| trend/momentum | radar parcial | nenhuma | trial própria |
| breakout | não explícita | nenhuma | detector/label separados |
| reversal/mean reversion | RSI só risco | nenhuma | trial separada |
| market-wide risk | breadth | sintética | universo multiativo |
| idiossincrática | estado por ativo | nenhuma | baseline cross-sectional |
| news/event | ausente | nenhuma | availability-time rigoroso |
| macro shock | H7 inativa | nenhuma | não ativar sem controle |
| liquidity/order-flow | ausente | nenhuma | book/quotes PIT |
| funding/OI/leverage | V3/H9 | NO-GO/insuficiente | preservar fechamentos |
| squeeze | ausente | nenhuma | dados de liquidação/borrow |
| basis/carry | estudos históricos | condicional | trial especialista |
| yield/DeFi | histórico Aave | cenários | capacidade/risco próprios |

## 48. Matriz CHAT × DOCS × CODE × TESTS × RUNTIME

| Objeto | Chat/mandato | Docs | Code | Tests | Runtime | Síntese |
|---|---|---|---|---|---|---|
| oportunidades perdidas | exige resolver | admite pesquisa | detector remoto | regressão passa | ausente | não resolvido economicamente |
| H1–H9 | pede inventário | estados claros | guards | passam | congeladas/inativas | preservar |
| paper | pede realismo | declara teórico | reference close | contratos passam | sem execução | FAIL |
| custos | pede líquido | admite ausência | modelos assumidos | matemática passa | não calibrado | FAIL |
| CAIN | pede separação | audit pinado | contratos | E2E sintético | snapshot distinto | técnico apenas |

## 49. Matriz de integrações entre repos

| Origem → destino | Contrato | Snapshot verificado | Resultado | Limite |
|---|---|---|---|---|
| Cripto → Core | store/prediction | Core 3.2.1 | funcional | dados stale |
| Cripto → Ops | config/policy/runner | Ops 4.2.1 instalado | funcional | sem agenda ativa |
| Cripto → Snapshot | evidence source | 1.0.1 no audit pinado | PASS técnico | sintético |
| Snapshot/Bundle → CAIN | source/hash/clock/policy | CAIN `5ba4177...` | PASS técnico | não semântico/econômico |
| Ecosystem → CAIN | Bundle 1.0 | `6a99852...` | PASS técnico | checkout atual difere |

## 50. Métricas econômicas ausentes

Opportunity miss rate, detection latency event-time, false opportunity rate, economic alert precision, post-alert net return, capture rate, delivery/ACK rate, quote-to-fill latency, reject/partial fill, realized spread/slippage/fees/funding, capacity, turnover, net expectancy IC, incremental return vs baseline, portfolio equity, MaxDD, exposure, tail loss, calibration/Brier/reliability e estabilidade por regime/classe. Sem denominador congelado, nenhuma taxa deve ser estimada.

## 51. Experimento prospectivo central

**Objetivo:** testar se o primeiro alerta PR122 por evento possui valor futuro líquido incremental, sem alterar thresholds e sem capital real.

1. Congelar SHA, thresholds, universo BTC/ETH/SOL, venue, relógio UTC, fontes e hashes antes da primeira observação.
2. Garantir coleta PIT multiativo e quotes/book executáveis; registrar `observed_at`, `available_at`, `decision_at`, `delivered_at` e ACK.
3. Unidade: primeiro alerta após estado inativo; sinais sobrepostos do mesmo ativo/estado não contam como novas decisões.
4. Target primário: retorno líquido 72h entre primeiro VWAP marketable disponível até 5 minutos após decisão e VWAP de saída 72h; 24h/168h secundários. Sem MFE/oracle.
5. Paper: ordem fixa pequena pré-definida, partial/reject reais do simulador, fees por tier documentado, spread/book, slippage, funding/borrow quando aplicável; custos com tags `OBSERVED` ou `ASSUMED`.
6. Baselines no mesmo relógio/exposição: always-flat, buy-and-hold exposure-matched, momentum 7d simples e breakout 20d.
7. Amostra: mínimo 180 dias e 60 eventos independentes; máximo 365 dias. Menos que 60 no prazo resulta `INCONCLUSIVE`, sem baixar threshold.
8. GO somente se: lower 95% block-bootstrap de expectativa líquida > 0; diferença líquida contra o melhor baseline predefinido com lower 95% > 0; PF líquido > 1,10; MaxDD ≤15%; cobertura PIT ≥99%; entrega+ACK ≥99%; e resultado permanece positivo com +50% de stress nos custos.
9. NO-GO se upper 95% da expectativa líquida ≤0 ou upper 95% incremental ≤0, ou se upper 95% sob stress ≤0. Demais casos: `INCONCLUSIVE`.
10. Qualquer mudança material cria trial/version nova; não reaproveitar amostra para retune e confirmação.

## 52. Teste de generalização

Estratificar antes da coleta por `trend`, `persistence`, `breadth` e direção. O GO agregado não autoriza classe individual sem mínimo de 20 eventos e consistência de sinal. Reservar o último terço temporal como holdout intocado; estimativas/desenvolvimento usam somente os dois primeiros terços, e uma única abertura do holdout resolve o trial. BTC/ETH/SOL e regimes high/low volatility devem ser reportados separadamente. Não generalizar para news, reversal, carry, squeeze ou DeFi.

## 53. Roadmap P0/P1/P2

**P0 — provar/refutar:** alinhar fonte/runtime por SHA; restaurar coleta PIT multiativo; instrumentar denominadores/ACK; ligar decisão paper a fills realistas; calibrar custos; congelar e executar o experimento central; produzir net P&L e baselines.  
**P1 — robustez:** adversariais, estabilidade por classe/regime/ativo, calibração, capacity, ablações e generalização temporal.  
**P2 — escala/capital:** somente após P0/P1 GO independente; limites, kill switch, reconciliação, incidentes, canary e autorização humana explícita. Nada de P2 agora.

## 54. Critério exato de resolução de cada P0

| P0 | Resolvido quando | Não resolve |
|---|---|---|
| fonte/runtime | SHA implantado = SHA auditado; heartbeat e freshness dentro do SLA | checkout remoto apenas |
| dados PIT | ≥99% dos eventos com vintages/clocks/hash e sem overwrite silencioso | snapshots ocasionais |
| cobertura | BTC/ETH/SOL realmente ingeridos e gaps quantificados | defaults em config |
| alerta | delivery+ACK ≥99%, latência p50/p95 publicada | webhook 2xx isolado |
| paper | order→fill/reject/partial→position→exit reconciliado | reference close |
| custos | parâmetros por evidência de venue/tier/book e stress | constantes plausíveis |
| decisão | regra congelada usa apenas informação disponível | gate backtest isolado |
| avaliação | critérios §51 resolvidos sem retune/peeking | testes/CI verdes |
| P&L | equity líquida reconciliada com decomposição de custos | soma bruta de trades |

## 55. `BLOCKERS_TO_PROFIT`

`[STALE_SINGLE_ASSET_DATA, PR122_NOT_DEPLOYED, NO_FUTURE_TARGET_FOR_RADAR, UNCALIBRATED_OUTPUTS, NO_COMPARABLE_BASELINES, THRESHOLDS_NOT_OOS, NO_PROSPECTIVE_EDGE, NO_REALISTIC_PAPER_FILLS, NO_VALIDATED_COST_MODEL, DISCONNECTED_RISK_EXECUTION, INCOMPLETE_PIT_VINTAGES, NO_NET_PORTFOLIO_PNL, NO_ACTIVE_VALIDATED_STRATEGY]`

## 56. `READY_FOR_PROFIT_RESEARCH`

`CONDITIONAL_YES`. A base é adequada para continuar pesquisa controlada porque preserva falhas, guards e componentes testáveis. Está pronta apenas após corrigir freshness/cobertura e congelar o protocolo prospectivo. Não está pronta para claim de lucro, trial adaptativa disfarçada ou capital.

## 57. Gates econômicos finais

| Gate | Resultado | Razão decisiva |
|---|---|---|
| A — `ECONOMIC_LOOP_STRUCTURALLY_COMPLETE` | **FAIL** | forecast/decision/fill/exit/net P&L desconectados |
| B — `PROSPECTIVE_PREDICTIVE_EDGE_DEMONSTRATED` | **FAIL** | nenhuma trial atual aprovada |
| C — `REALISTIC_PAPER_PROFITABILITY_DEMONSTRATED` | **FAIL** | paper é reference-close/gross |
| D — `REAL_CAPITAL_OPERATIONAL_READINESS` | **FAIL** | A–C falham; capital proibido |

### Vereditos obrigatórios

```text
FULL_CHAT_REVIEWED=PARTIAL
RELEVANT_REPOSITORIES_IDENTIFIED=YES
RELEVANT_REPOSITORIES_AUDITED=PARTIAL
CHAT_REPO_CONTRADICTIONS_MAPPED=YES
CROSS_REPO_ECONOMIC_PATH_MAPPED=YES

PIT_CAUSALITY_AUDITABLE=FAIL
MODEL_TARGETS_ECONOMICALLY_DEFINED=FAIL
BASELINES_AVAILABLE=FAIL
PREDICTIONS_CALIBRATED=FAIL
DETECTION_PROVEN=FAIL
POST_ALERT_EDGE_PROVEN=FAIL
THRESHOLDS_VALIDATED_OUT_OF_SAMPLE=FAIL
REALISTIC_PAPER_EXECUTION_AVAILABLE=FAIL
COST_MODEL_VALIDATED=FAIL
NET_PNL_MEASURABLE=FAIL

ECONOMIC_LOOP_COMPLETE=false
PROSPECTIVE_EDGE_DEMONSTRATED=false
REALISTIC_PAPER_PROFIT_DEMONSTRATED=false
REAL_CAPITAL_READY=false

STRATEGY_RESULT=NO_VALIDATED_ACTIVE_STRATEGY
CRIPTO_RUNTIME_RESULT=PARTIAL_RESEARCH_RUNTIME_NOT_ECONOMICALLY_OPERATIONAL
CAIN_CAPABILITY_RESULT=ENGINEERING_INTEGRATION_PASS_SEMANTIC_AND_ECONOMIC_NOT_VERIFIED
```

## Evidência e validações executadas

| Verificação | Resultado | Força/tipo |
|---|---|---|
| `git status`, `rev-parse`, `ls-remote` | local limpo; drift `bd4ff602` → `1b2bee85` | forte / observado |
| `CRIPTO.cmd status` e metadados Python | editable local; capital false; versões registradas | forte / runtime |
| FeatureStore read-only | contagens/cobertura/snapshots acima | forte / observado |
| testes focados | **113 passed em 57,39s** | forte para engenharia; não econômica |
| limpeza pytest | `PermissionError` após sucesso em symlink temporário | limitação operacional, sem falha de teste |
| PR #122 | 16 checks e merge; sem reviewer registrado | forte para CI, fraca para edge |

Referências locais centrais: `README.md:16,67-84`; `docs/HYPOTHESES.md:1313-1321`; `docs/REVISAO_COMPLETA_20260909.md:23-24`; `docs/AUDITORIA_AMPLIADA_20260910.md:31,55-59,90`; `GarimpoInvestimentos/v3/economic_gate.py:3-5,83-103`; `GarimpoInvestimentos/v3/backtest_v3.py:1074-1076`; `GarimpoInvestimentos/v3/paper_report.py:1,92-93`; `GarimpoInvestimentos/trading/cost_policy.py:17`; `GarimpoInvestimentos/plugin.py:44-50`.

## Encerramento

Para a pergunta final — se uma nova oportunidade amanhã pode ser detectada, classificada, prevista, decidida, entregue, executada em paper, gerida em risco e convertida em P&L líquido provado — a resposta é **não no sistema atualmente instalado**. A fonte remota pode detectar/classificar alguns movimentos observados; todos os elos economicamente decisivos seguintes permanecem não demonstrados. A recomendação é executar somente o P0 prospectivo congelado, sem ativar capital e sem reabrir hipóteses encerradas.
