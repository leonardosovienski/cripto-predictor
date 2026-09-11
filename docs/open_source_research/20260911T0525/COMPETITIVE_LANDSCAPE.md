# Competitive landscape — 20260911T0525

Escopo: transferência de capacidades para o HEAD e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f. A rodada 20260911T0233 permanece baseline: 53 candidatos triados, 23 revisões focadas, sem tratar isso como auditoria integral de 23 projetos. Esta rodada aprofundou oito referências delimitadas, reutilizou o survey e implementou cinco capacidades. Não há ranking global de “melhor plataforma”.

C0 = alegação/documentação; C1 = código localizado e inspecionado; C2 = também testes pertinentes lidos; C3 = componente externo executado; C4 = comparação diferencial executada. O nível pertence à função/claim, nunca ao repositório inteiro. Nenhum dos oito frameworks foi instalado ou executado integralmente nesta rodada. Testes locais aprovados não elevam o framework externo a C3/C4.

## Referências aprofundadas

| Referência fixada | O que foi verificado | Testes lidos | Nível | Licença observada e decisão |
|---|---|---|---|---|
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade/blob/243ddaef420f64ae3978ddacd6ffff706e8fb0d7/freqtrade/plugins/pairlist/VolumePairList.py) | VolumePairList.filter_pairlist e composição com filtros; AgeFilter | tests/plugins/test_pairlist.py: casos de composição/ordem/seed | C2 | GPL-3.0; conceito de composição, sem copiar código |
| [stefan-jansen/alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded/blob/f0a07c22d554e4b4036983cc80320b432714fe7e/src/alphalens/performance.py) | factor_information_coefficient e quantile_turnover | tests/test_performance.py: IC/turnover | C2 | Apache-2.0; reimplementação limpa com Spearman nativo |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot/blob/2bfaccc48dd49e71a5b6d9b3011808e127dd00cd/hummingbot/core/data_type/in_flight_order.py) | InFlightOrder: atualizações parciais, acumuladas e idempotentes | test/hummingbot/core/data_type/test_in_flight_order.py: updates repetidos e múltiplos | C2 | Apache-2.0; referência sem importar conectores |
| [skfolio/skfolio](https://github.com/skfolio/skfolio/blob/085485b0f35576c1b36b4c4253cb7b944fee0c6f/src/skfolio/model_selection/_combinatorial.py) | CombinatorialPurgedCV.split: purge/embargo por contagem de linhas | tests/test_model_selection/test_combinatorial.py: split e regressão | C2 | BSD-3-Clause; contrato local forward por tempo, não clone CPCV |
| [mlflow/mlflow](https://github.com/mlflow/mlflow/blob/3b3760a077bc85c757eed4886bba47d970793875/mlflow/store/tracking/file_store.py) | FileStore.create_run/log_batch: separação de metadados/artefatos | tests/store/tracking/test_file_store.py: create_run | C2 | Apache-2.0; registro mínimo local, sem servidor |
| [microsoft/qlib](https://github.com/microsoft/qlib/blob/79633dd9506ea689e5400dea0197717b5b3d74b7/qlib/data/dataset/handler.py) | DataHandlerLP.fit_process_data e separação infer/learn | Não aprofundados nesta rodada | C1 | MIT; backlog de processadores, não integração Qlib |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean/blob/8ee075a39918f2df6fe9e0a5944e366fb60d10dc/Engine/DataFeeds/UniverseSelection.cs) | UniverseSelection: adições/remoções e subscriptions | Não aprofundados nesta rodada | C1 | Apache-2.0; conceito no backlog; PortfolioConstructionModel não verificado |
| [robertmartin8/PyPortfolioOpt](https://github.com/robertmartin8/PyPortfolioOpt/blob/a6638d2e06dae6f444fd022cfd4b3c528902a85b/pypfopt/efficient_frontier/efficient_frontier.py) | EfficientFrontier.min_volatility/efficient_return | tests/test_efficient_frontier.py: retorno-alvo e estrutura | C2 | MIT; adapter opcional no backlog, solver não instalado |

Recibos de downloads, SHA-256, commit e erros em UPSTREAM.json e UPSTREAM_SUPPLEMENT.json. Caminhos LICENSE/engine inicialmente indisponíveis foram corrigidos quando localizados. HTTP 404 de um caminho não significa ausência da capacidade nem rejeição científica. Licenças acima são as observadas nos arquivos; nenhum trecho externo foi incorporado à implementação proprietária.

A documentação de [fill models do Nautilus](https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models/) distingue modelos e profundidades de livro. Ela apoia manter separadas simulação determinística, hipótese probabilística e calibração empírica; não demonstra que nosso cenário tenha posição em fila ou impacto realista. Essa leitura atual é documental; não herda automaticamente o nível de outro trecho revisado na rodada anterior.

## Cobertura A–X e decisão local

| Área | Capacidade | Estado e ação |
|---|---|---|
| A | Ingestão | CCXT e coletores nativos; preservar; expansão multivenue é G14 |
| B | Modelo de dados | Identidade/recibos nativos; SpotContract novo é apenas spot sintético; G12 |
| C | Universo dinâmico | G02 entregue; histórico completo continua G11 |
| D | Pesquisa transversal | G01 entregue; G10 é comparação externa restante |
| E | Features | Preservar feature store; G07 fit/infer por fold |
| F | ML workflows | Preservar baselines; Qlib C1 inspira contrato, não adotar engine |
| G | API de estratégia | CLI research entregue; não substituir TradeIntent |
| H | Backtest | Preservar backtest; não instalar outro engine sem workload |
| I | Execução simulada | Lifecycle nativo preservado; G04 caixa/latência sintéticos |
| J | Derivativos | G12/G13 pendentes, sem promoção por demo spot |
| K | Portfólio | Risco nativo existe; G06 solver de pesos pendente |
| L | Risco | Beta, HHI, drawdown, reconciliação nativos; KEEP_NATIVE |
| M | Microestrutura | Livro local, sequências e market fill nativos; G08 fila calibrada |
| N | Market making | Hummingbot como referência; nenhuma estratégia ativada |
| O | Relative value | G01 residualização e G04 caixa habilitam cenários; economia sem validação |
| P | Opções | G16; survey QuantLib herdado, sem nova implementação |
| Q | On-chain | Reusar evidências anteriores; origem independente ainda essencial |
| R | DeFi | G17; índices Aave e outras fontes herdados, sem nova coleta financeira |
| S | Eventos/alternativos | G18; sem extração nova sem contrato temporal |
| T | LLM | Pilotos congelados preservados; sem agente operando |
| U | Validação | G03 entregue; F05 não retunado; G15 estudo separado |
| V | Tracking | G05 entregue; não substitui registry de hipóteses/trials |
| W | Observabilidade | Preservar logs/guards; drift estatístico G20 |
| X | UX | CLI demo/run/list/verify/compare entregue; UI G19 |

## Correção importante da comparação

O projeto já possui `trading/execution.py:apply_fill/cancel/reconcile/OrderBookLedger`, `trading/portfolio.py:beta/concentration_hhi/aggregate_leverage/DrawdownTracker`, `trading/microstructure.py:LocalOrderBook/simulate_market_fill` e `trading/binance_spot_collector.py:BinanceSpotCollector`. Portanto, “execução parcial”, “risco” e “websocket/L2” não são gaps genéricos. O ganho novo é a composição das análises e a contabilidade de reservas por venue/moeda com valores decimais no cenário. O teste diferencial nativo verifica apenas as transições comuns, não equivalência de todos os estados de reconciliação.
