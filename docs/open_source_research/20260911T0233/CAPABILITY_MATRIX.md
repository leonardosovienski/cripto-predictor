# Matriz consolidada e ordem de decisão

A ordem mestre abaixo usa dependências e ganho de informação. Não é ranking de retorno. K02 já teve seu teste mínimo concluído; por isso a próxima unidade de esforço vai para identidade/validação. BLOCKED_DATA não é reprovado economicamente. Maior C refere-se à claim examinada, nunca à capacidade inteira.

| Ordem | ID/capacidade | Finalidade | C / ação | Estado | Conclusão |
| --- | --- | --- | --- | --- | --- |
| 1 | K01 Identidade, relógios e universo PIT | SCIENTIFIC_ENABLER | C4 / IMPROVE | READY_FOR_EXPERIMENT | B03 accepted one valid snapshot and rejected eight invalid clocks/identity/price cases. Full instrument currency/chain/settlement and historical universe remain outside this snapshot schema. |
| 2 | K05 Validação temporal e multiplicidade do processo inteiro | SCIENTIFIC_ENABLER | C4 / AUGMENT | READY_FOR_EXPERIMENT | B05 retains label 5 ending at 25 in all 3 row-gap folds; explicit end-time purge removes it. New-family interval contract needed; no existing frozen trial modified. |
| 3 | K07 Instrumentos e funding como eventos assinados | SCIENTIFIC_ENABLER | C3 / IMPROVE | READY_FOR_EXPERIMENT | Funding function uses settled marks/signs but expected event coverage is fixed at 8h for this historical design. Do not apply universally to other contracts. |
| 4 | K11 Carteira, concentração e alocação de garantias | SCIENTIFIC_ENABLER | C3 / AUGMENT | CANDIDATE | Existing event-based equity prevents repeated allocation of closed-trade equity; invested positions are carried at allocation until realization. This is not a full mark-to-market liquidation ledger. |
| 5 | K02 Referências diferenciais para métricas e features | ENGINEERING | C4 / KEEP | CANDIDATE | B01/B02 passed. No replacement justified for tested metric/indicators; RSI/MACD not differentially benchmarked. |
| 6 | K03 Corroboração dos índices Aave e liquidez de saída | SCIENTIFIC_ENABLER | C3 / VALIDATE | BLOCKED_DATA | 1728 Aave cashflows reconcile to original indices in full suite. Second endpoint attempted once: ConnectTimeout, one call, zero response bytes. No independent backend evidence. |
| 7 | K04 Ranking cross-sectional com neutralização e turnover | ECONOMIC_STRATEGY | C1 / AUGMENT | BLOCKED_DATA | IC positivo não garante PnL; Alphalens não é independente de SciPy |
| 8 | K06 Replay de fills, fila, atraso e duas pernas | SCIENTIFIC_ENABLER | C4 / AUGMENT | BLOCKED_DATA | B04 agrees on 3 exact VWAPs and rejects 4 invalid inputs. B06 reconciles net hedge capital and rejects insufficient second-leg depth. No probabilistic partial-fill rate inferred. |
| 9 | K08 Vintages macro e calendário conhecido no instante | SCIENTIFIC_ENABLER | C1 / AUGMENT | BLOCKED_DATA | DXY é nome interno; DTWEXBGS não deve ser confundido com todo índice dólar |
| 10 | K12 Lending/staking com taxas realizadas e stress | ECONOMIC_STRATEGY | C1 / AUGMENT | BLOCKED_DATA | Histórico Aave documentado é condicional; não reproduzido nesta rodada |
| 11 | K15 Fluxos on-chain, entidades e stablecoins | SCIENTIFIC_ENABLER | C0 / RESEARCH | BLOCKED_DATA | Métrica atual reconstruída pode carregar informação futura |
| 12 | K18 Carry e basis com custos e capital fragmentado | ECONOMIC_STRATEGY | C1 / VALIDATE | DEFER | Linha já existe; piloto manual v2 depende da janela; não abrir nova variação de BTC sem motivo material |
| 13 | K10 Pares, resíduos e fatores de risco | ECONOMIC_STRATEGY | C0 / RESEARCH | BLOCKED_DATA | Correlação/cointegração não garantem convergência nem liquidez |
| 14 | K09 Eventos, notícias e extração com LLM | SCIENTIFIC_ENABLER | C1 / VALIDATE | DEFER | Janelas futuras e H5 sem inputs não podem ser preenchidos retroativamente |
| 15 | K13 LP concentrada e seleção adversa | ECONOMIC_STRATEGY | C0 / RESEARCH | BLOCKED_DATA | Mais receita de fees não prova lucro; LVR é comparação contra benchmark específico |
| 16 | K14 Opções, superfície IV, skew e Greeks | ECONOMIC_STRATEGY | C0 / RESEARCH | BLOCKED_DATA | Sem histórico admissível; cálculo teórico não comprova fill |
| 17 | K16 Baselines probabilísticos e modelos de estado | SCIENTIFIC_ENABLER | C3 / VALIDATE | DEFER | fit/scaler use supplied training sample; inference runs forward-only and transform. Future leakage still depends on supplying admissible training data; frozen family unchanged. |
| 18 | K17 Transformers, ensembles e RL | ECONOMIC_STRATEGY | C0 / RESEARCH | DEFER | Sofisticação e tuning aumentam seleção; não há ganho incremental comprovado |

## Fichas de capacidade

### K01 — Identidade, relógios e universo PIT

Evidência interna: `GarimpoInvestimentos/dpl/providers/ccxt_base.py:80`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R05, R08, R20, R47, R48, R50.

Mecanismo: Distinguir fechamento convencionado, publicação comprovada e recepção; preservar ativos retirados e contratos. Dados/PIT: Dados brutos versionados por fonte, chain/venue/settlement e universo por data. Risco: Sem isso, cobertura e seleção podem ser confundidas com alpha.

Estado: READY_FOR_EXPERIMENT; acesso: SYNTHETIC_AVAILABLE; live/historical use requires per-source contract. Dependências: nenhuma nova. Resultado: PASS_NARROW_ENGINEERING. Próximo teste: F01.

### K05 — Validação temporal e multiplicidade do processo inteiro

Evidência interna: `GarimpoInvestimentos/analyzers/pbo.py:100`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R01, R25, R27, R28, R43.

Mecanismo: Combinar verificações de fronteira com perdas comparáveis e todas as tentativas. Dados/PIT: Labels com início/fim, lista de variantes, matriz de perdas e desenho de blocos. Risco: PBO existente não deve ser reconstruído; CPCV não implica causalidade operacional.

Estado: READY_FOR_EXPERIMENT; acesso: SYNTHETIC_AVAILABLE; live/historical use requires per-source contract. Dependências: K01. Resultado: DESIGN_LIMIT_DEMONSTRATED. Próximo teste: F05.

### K07 — Instrumentos e funding como eventos assinados

Evidência interna: `GarimpoInvestimentos/v3/backtest_v3.py:322`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R05, R08, R20, R45.

Mecanismo: Separar taxa projetada de cada pagamento e evitar convenções universais de 8h. Dados/PIT: Identificador de contrato, eventos, mark, intervalo histórico e margem. Risco: Não reparametrizar custos das famílias encerradas.

Estado: READY_FOR_EXPERIMENT; acesso: SYNTHETIC_AVAILABLE; live/historical use requires per-source contract. Dependências: K01. Resultado: SCOPED_IMPLEMENTATION. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K11 — Carteira, concentração e alocação de garantias

Evidência interna: `GarimpoInvestimentos/profit_research.py:80`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R28, R29, R30.

Mecanismo: Distinguir retorno sobre margem de retorno sobre todo capital e não somar cenários. Dados/PIT: Equity, caixa por venue/colateral, exposições e cenários de cauda. Risco: Custos pessoais e elegibilidade são desconhecidos.

Estado: CANDIDATE; acesso: SYNTHETIC_AVAILABLE; live/historical use requires per-source contract. Dependências: K01. Resultado: SCOPED_IMPLEMENTATION. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K02 — Referências diferenciais para métricas e features

Evidência interna: `GarimpoInvestimentos/analyzers/indicators.py:26`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R01, R27, R52.

Mecanismo: Detectar erro numérico e dependência do futuro antes de comparar estratégias. Dados/PIT: Sintético e ambiente existente; 100 pares e 231 prefixos executados. Risco: Não testa RSI/MACD/HMM completo, nem poder do bootstrap.

Estado: CANDIDATE; acesso: SYNTHETIC_AVAILABLE; live/historical use requires per-source contract. Dependências: nenhuma nova. Resultado: PASS_NARROW_ENGINEERING. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K03 — Corroboração dos índices Aave e liquidez de saída

Evidência interna: `scripts/recover_aave_history.py:154`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R09, R10, R48.

Mecanismo: Verificar que rendimento histórico vem de índices do contrato correto, não APY anunciado. Dados/PIT: Mesmos blocos, hashes, reserva USDC nativa, implementação histórica e rota RPC adicional. Risco: Mesma cadeia ou backend não são amostras econômicas independentes.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01. Resultado: PARTIAL_CORROBORATION. Próximo teste: F02.

### K04 — Ranking cross-sectional com neutralização e turnover

Evidência interna: `GarimpoInvestimentos/collectors/discovery.py:88`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R22, R42, R52.

Mecanismo: Investigar momentum/resíduos além da seleção heurística atual, separando beta e custo. Dados/PIT: Painel por data com delistings, volumes/custos e elegibilidade histórica. Risco: IC positivo não garante PnL; Alphalens não é independente de SciPy.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01, K05, K07, K11. Resultado: NOT_EVALUATED. Próximo teste: F03.

### K06 — Replay de fills, fila, atraso e duas pernas

Evidência interna: `scripts/plan_btc_hedge_v3.py:20`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R02, R03, R07, R08.

Mecanismo: Estimar intervalo de resultado quando posição de fila e simultaneidade não são conhecidas. Dados/PIT: L2 sequenciado, trades, clocks e cenários de latência/capital. Risco: Snapshots atuais não identificam fila; replay não modela impacto próprio.

Estado: BLOCKED_DATA; acesso: SYNTHETIC_AVAILABLE; live/historical use requires per-source contract. Dependências: K01. Resultado: PASS_NARROW_ENGINEERING. Próximo teste: F04.

### K08 — Vintages macro e calendário conhecido no instante

Evidência interna: `GarimpoInvestimentos/dpl/providers/dxy.py:55`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R50.

Mecanismo: Permitir avaliação causal da informação macro sem backfill conhecido apenas hoje. Dados/PIT: ALFRED/release preservado com intervalo de versão e hora de publicação. Risco: DXY é nome interno; DTWEXBGS não deve ser confundido com todo índice dólar.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K12 — Lending/staking com taxas realizadas e stress

Evidência interna: `scripts/recover_aave_history.py:154`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R09, R10, R13, R14, R15, R51.

Mecanismo: Investigar remuneração de empréstimo/validação de rede descontando saídas e riscos. Dados/PIT: Índices e fluxos realizados, resgate, gas, slashing, depeg e custos. Risco: Histórico Aave documentado é condicional; não reproduzido nesta rodada.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01, K05, K07, K11. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K15 — Fluxos on-chain, entidades e stablecoins

Evidência interna: `GarimpoInvestimentos/dpl/signals.py:1`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R16, R17, R18, R47, R48, R49.

Mecanismo: Distinguir movimento econômico de revisão retrospectiva de rótulos. Dados/PIT: Bloco finalizado, data do indexador e vintage de classificação de entidade. Risco: Métrica atual reconstruída pode carregar informação futura.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K18 — Carry e basis com custos e capital fragmentado

Evidência interna: `scripts/observe_carry_forward.py:1`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R02, R05, R41, R45.

Mecanismo: Segmentação e demanda por alavancagem podem remunerar carry, com risco de saída. Dados/PIT: Spot/perp/futuro compatíveis, cada perna financiada, funding/basis e custos. Risco: Linha já existe; piloto manual v2 depende da janela; não abrir nova variação de BTC sem motivo material.

Estado: DEFER; acesso: UNKNOWN. Dependências: K01, K05, K07, K11. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K10 — Pares, resíduos e fatores de risco

Evidência interna: `GarimpoInvestimentos/collectors/discovery.py:88`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R26, R42.

Mecanismo: Investigar prêmio de risco/valor relativo com hedge e borrow explícitos. Dados/PIT: Painel PIT e hedge negociável com financiamento. Risco: Correlação/cointegração não garantem convergência nem liquidez.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01, K05, K07, K11. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K09 — Eventos, notícias e extração com LLM

Evidência interna: `GarimpoInvestimentos/dpl/snapshots.py:97`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R49, R53.

Mecanismo: Testar extração/classificação antes de tratar score como probabilidade ou sinal. Dados/PIT: Publicação, recibo, texto preservável, versão/prompt; protocolo pareado v3 já registrado. Risco: Janelas futuras e H5 sem inputs não podem ser preenchidos retroativamente.

Estado: DEFER; acesso: UNKNOWN. Dependências: K01. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K13 — LP concentrada e seleção adversa

Evidência interna: `scripts/plan_btc_hedge_v3.py:55`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R11, R12, R44.

Mecanismo: Investigar fees menos perdas relativas, custos e reposicionamento. Dados/PIT: Ticks, swaps, liquidez ativa, gas e benchmark de rebalanceamento. Risco: Mais receita de fees não prova lucro; LVR é comparação contra benchmark específico.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01, K05, K07, K11. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K14 — Opções, superfície IV, skew e Greeks

Evidência interna: `pyproject.toml:16`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R39, R46.

Mecanismo: Separar prêmio de volatilidade de erro de preço e risco de cauda. Dados/PIT: Cadeia histórica bid/ask, expiração, settlement, funding de hedge. Risco: Sem histórico admissível; cálculo teórico não comprova fill.

Estado: BLOCKED_DATA; acesso: UNKNOWN. Dependências: K01, K05, K07, K11. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K16 — Baselines probabilísticos e modelos de estado

Evidência interna: `GarimpoInvestimentos/v3/regime_engine.py:298`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R26, R27, R34, R35, R37.

Mecanismo: Comparar regra simples, linear e probabilístico pela decisão e calibração. Dados/PIT: Treino separado, target fixo, incerteza e erro por regime. Risco: HMM existente não autoriza reabrir família funding_oi_hmm_v3.

Estado: DEFER; acesso: UNKNOWN. Dependências: K01. Resultado: SCOPED_IMPLEMENTATION. Próximo teste: contrato/ablação da composição relacionada; não ativado.

### K17 — Transformers, ensembles e RL

Evidência interna: `pyproject.toml:16`, commit `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. Referências: R31, R36, R38.

Mecanismo: Investigar apenas se simples baseline deixa erro economicamente relevante. Dados/PIT: Dados suficientes, simulador válido, orçamento finito e avaliação não adaptada. Risco: Sofisticação e tuning aumentam seleção; não há ganho incremental comprovado.

Estado: DEFER; acesso: UNKNOWN. Dependências: K01, K05, K07, K11. Resultado: NOT_EVALUATED. Próximo teste: contrato/ablação da composição relacionada; não ativado.

## Scores separados dos gates

Notas de 0–5 são estimativas, não dados econômicos. ENABLER:0,30 ciência+0,20 validação+0,15 evidência+0,10 arquitetura+0,10 incremento+0,10 domínio+0,05 independência. ECONOMIC_STRATEGY:0,20 economia+0,15 ciência+0,15 evidência externa+0,10 independência+0,10 transferência cripto+0,10 execução+0,08 incremento+0,07 validação+0,05 arquitetura. Custo:0,25 implementação+0,20 método+0,15 dependências+0,15 manutenção+0,15 dados+0,10 operação. Valor/custo=20×nota; prioridade=0,70valor+0,30(100−custo).

Mantivemos as notas estimadas iniciais para evitar ajustá-las retrospectivamente ao resultado dos testes. UNKNOWN econômico continua sem score; não vira zero. Os intervalos propagam ±1 limitado a0–5, não são intervalos estatísticos. A sensibilidade 0,6/0,7/0,8 da mistura está no JSON. Sobreposição ampla impede vender pequenas diferenças como ordem robusta.

| ID | Valor | Custo | Prioridade estimada | Faixa ±1 | Gate |
| --- | --- | --- | --- | --- | --- |
| K02 | 82.0 | 15.0 | 82.9 | 62.9–97.2 | KEEP |
| K05 | 87.0 | 41.5 | 78.5 | 58.4–92.1 | READY_FOR_EXPERIMENT |
| K01 | 83.5 | 43.5 | 75.4 | 55.4–90.5 | READY_FOR_EXPERIMENT |
| K03 | 81.0 | 41.0 | 74.4 | 54.4–90.2 | BLOCKED_DATA |
| K07 | 77.0 | 40.0 | 71.9 | 51.9–89.1 | READY_FOR_EXPERIMENT |
| K08 | 78.5 | 50.0 | 69.9 | 50.0–88.5 | BLOCKED_DATA |
| K11 | 73.0 | 47.0 | 67.0 | 47.0–85.6 | CANDIDATE |
| K06 | 73.0 | 70.0 | 60.1 | 40.1–80.1 | BLOCKED_DATA |

Prevalência competitiva, diferença de mercado e diferenciação permanecem UNKNOWN: a amostra de repos não é censo do mercado. Sem desconto numérico de redundância adicional após agrupar linhagens. NO_VERIFIED_ADVANTAGE econômico; controles locais específicos foram verificados, sem superioridade universal.

## Vistas por categoria

| Categoria | Ordem condicional dos mesmos IDs |
| --- | --- |
| Melhorias imediatas | K01 → K05 → K07 → K11 → K02 |
| Novas análises | K04 → K10 → K12 → K14 |
| Filtros/ranking | K01 → K04 → K05 |
| Fontes/datasets | K03 → K08 → K15 |
| Ferramentas | R52 → R27 → R25 → R22 → R07 |
| Features/estratégias | K04 → K12 → K18 → K10 → K13 → K17 |
| Validação | K05 → K01 → K02 → K03 |
| Risco/execução | K07 → K11 → K06 |
| Referências | R05 → R52 → R42 → R43 → R44 |
| Composições | X01 → X02 → X03 → X04 → X05 → X06 |

## Composições e condições de refutação

| ID | Composição | Teste necessário | O que a enfraquece/refuta | Estado |
| --- | --- | --- | --- | --- |
| X01 | Universo PIT + ranking residual + hedge financiado | IC e ganho líquido sobre momentum sob mesmo universo; ablação do hedge e da seleção | Borrow/turnover/beta eliminam incremento; sobreviventes atuais explicam seleção | BLOCKED_DATA |
| X02 | Índice lending + reserva de custos + stress de liquidez/peg | Reconciliar fluxos 1728 casos e segunda rota; stress de saída e custo de capital | Rendimento desaparece com custo/resgate; backend não corroborado | ACCOUNTING_REPRODUCED_SECOND_SOURCE_BLOCKED |
| X03 | Funding/basis + duas pernas + capital segregado | Quantidade líquida, eventos funding e preço de desmonte de perna órfã | Basis positivo não compensa fees/financiamento ou margem intraperíodo | SYNTHETIC_PARTIAL_PASS_FROZEN_FORWARD_PENDING |
| X04 | Fluxo on-chain PIT + surpresa de evento + resposta | Comparar versão conhecida à versão retrospectiva antes de medir sinal | Efeito só existe com rótulos/publicações revisados depois | BLOCKED_DATA |
| X05 | Desconto staking líquido + tempo de fila + risco de resgate | Desconto cobre espera sem recompensas, fees e perda de conversão nos mesmos cenários | Spread some com delay/slashing/saída e capital preso | BLOCKED_DATA |
| X06 | LP + benchmark de rebalanceamento + hedge | Fees menos seleção adversa, gas, rebalanceamentos e hedge pelo mesmo capital | Receita de fees é exposição ao preço ou custo de adverse selection não medido | BLOCKED_DATA |
