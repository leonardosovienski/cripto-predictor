# Survey consolidado — 53 candidatos e 23 revisões focadas

A triagem é ampla; profundidade é por claim. Foram examinadas 16 referências de implementação/cálculo, 4 artigos completos nas seções pertinentes e 3 contratos de dados/produto. Não são 23 certificações integrais de repositórios. Código está fixado por SHA quando aprofundado; recibos e datas estão no registro.

| ID | Referência | Capacidade | Nível/resultado | Decisão |
| --- | --- | --- | --- | --- |
| R01 | [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | leakage e seleção | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R02 | [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | market making e execução | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R03 | [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | engine orientado a eventos | C2 / E1 | Caminhos de código tentados retornaram 404; aprofundamento não concluído |
| R04 | [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | backtest e estratégias | C0 /  | Alternativa de framework, sem necessidade demonstrada de substituir engine |
| R05 | [ccxt/ccxt](https://github.com/ccxt/ccxt) | contratos e conectores | C1 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R06 | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | simulação vetorizada | C0 /  | NOASSERTION: ler licença específica antes de integração; sem pandas instalado |
| R07 | [nkaz 001/hftbacktest](https://github.com/nkaz001/hftbacktest) | fila e latência | C1 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R08 | [bmoscon/cryptofeed](https://github.com/bmoscon/cryptofeed) | feeds de microestrutura | C1 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R09 | [DefiLlama/yield-server](https://github.com/DefiLlama/yield-server) | decomposição de rendimentos | C1 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R10 | [aave/aave-v3-core](https://github.com/aave/aave-v3-core) | índices lending | C1 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R11 | [Uniswap/v3-core](https://github.com/Uniswap/v3-core) | liquidez concentrada | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R12 | [Uniswap/v4-core](https://github.com/Uniswap/v4-core) | pools hooks e taxas | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R13 | [compound-finance/comet](https://github.com/compound-finance/comet) | lending e colateral | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R14 | [lidofinance/core](https://github.com/lidofinance/core) | staking e saídas | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R15 | [morpho-org/morpho-blue](https://github.com/morpho-org/morpho-blue) | lending isolado | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R16 | [coinmetrics/api-client-python](https://github.com/coinmetrics/api-client-python) | dados de rede e mercado | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R17 | [blockchain-etl/ethereum-etl](https://github.com/blockchain-etl/ethereum-etl) | extração on-chain | C0 /  | ETL amplo; avaliar somente se K15 tiver pergunta testável |
| R18 | [graphprotocol/graph-node](https://github.com/graphprotocol/graph-node) | indexação on-chain | C0 /  | Indexador pesado; exigir necessidade antes de nova infraestrutura |
| R19 | [DefiLlama/DefiLlama-Adapters](https://github.com/DefiLlama/DefiLlama-Adapters) | TVL e protocolos | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R20 | [binance/binance-public-data](https://github.com/binance/binance-public-data) | arquivos históricos | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R21 | [quantopian/alphalens](https://github.com/quantopian/alphalens) | fatores e ranking | C0 /  | Mesmo grupo de capacidade R22; ancestral não é réplica independente |
| R22 | [stefan-jansen/alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded) | fatores e ranking | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R23 | [stefan-jansen/zipline-reloaded](https://github.com/stefan-jansen/zipline-reloaded) | calendários e backtest | C0 /  | Comparador adjacente, calendário acionário requer adaptação |
| R24 | [hudson-and-thames/mlfinlab](https://github.com/hudson-and-thames/mlfinlab) | validação financeira | C0 /  | NOASSERTION e manutenção antiga na fotografia; sem instalar ou presumir recursos comerciais gratuitos |
| R25 | [bashtage/arch](https://github.com/bashtage/arch) | bootstrap temporal SPA e volatilidade | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R26 | [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels) | cointegração e modelos de estado | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R27 | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | pipelines e baselines | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R28 | [skfolio/skfolio](https://github.com/skfolio/skfolio) | portfólio e validação | C2 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R29 | [robertmartin 8/PyPortfolioOpt](https://github.com/robertmartin8/PyPortfolioOpt) | otimização e risco | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R30 | [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | risco e carteiras | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R31 | [optuna/optuna](https://github.com/optuna/optuna) | registro de otimização | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R32 | [SeldonIO/alibi-detect](https://github.com/SeldonIO/alibi-detect) | drift e anomalias | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R33 | [deepcharles/ruptures](https://github.com/deepcharles/ruptures) | quebras estruturais | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R34 | [scikit-learn-contrib/MAPIE](https://github.com/scikit-learn-contrib/MAPIE) | incerteza conformal | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R35 | [Nixtla/statsforecast](https://github.com/Nixtla/statsforecast) | baselines temporais | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R36 | [Nixtla/neuralforecast](https://github.com/Nixtla/neuralforecast) | redes temporais | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R37 | [sktime/sktime](https://github.com/sktime/sktime) | avaliação temporal | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R38 | [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | reinforcement learning | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R39 | [lballabio/QuantLib](https://github.com/lballabio/QuantLib) | opções e curvas | C1 / E1 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R40 | [gerrymanoim/exchange_calendars](https://github.com/gerrymanoim/exchange_calendars) | calendários | C0 /  | Calendários úteis somente onde há sessão definida; não impor pregão de ações a cripto 24/7 |
| R41 | [Crypto carry](https://www.bis.org/publ/work1087.htm) | carry e segmentação | C0 / E3 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R42 | [Common Risk Factors in Cryptocurrency](https://www.nber.org/papers/w25882) | ranking fatores mercado tamanho momentum | C0 / E3 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R43 | [Model selection bias](https://jmlr.org/papers/v11/cawley10a.html) | validação aninhada | C0 / E3 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R44 | [Loss versus rebalancing](https://arxiv.org/abs/2208.06046) | LP e seleção adversa | C0 / E3 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R45 | [Binance funding history](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History) | funding liquidado | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R46 | [Deribit API](https://docs.deribit.com/) | opções IV Greeks books | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R47 | [Glassnode API](https://docs.glassnode.com/) | on-chain entidades e revisões | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R48 | [Coin Metrics Community](https://docs.coinmetrics.io/) | métricas de rede e mercado | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R49 | [Dune documentation](https://docs.dune.com/) | SQL e indexação on-chain | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R50 | [ALFRED real time](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) | vintages macro | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R51 | [Lido withdrawals](https://docs.lido.fi/contracts/withdrawal-queue-erc721/) | fila de resgates staking | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R52 | [SciPy Spearman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html) | verificação diferencial de ranking | C4 / E1, E5 | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |
| R53 | [DefiLlama unlocks](https://defillama.com/unlocks) | eventos e emissão | C0 /  | Avançar apenas como alternativa da capacidade indicada; adoção não autorizada. |

## Fichas aprofundadas

C0–C4 expressa inspeção/execução do código; E3 de paper não vira C4. E5 abaixo limita-se a reprodução técnica. Documentação de provider é FACT_DOCUMENTED, sem promover existência de dados contratados.

### R01 — freqtrade/freqtrade

Referência [243ddaef420f64ae3978ddacd6ffff706e8fb0d7](https://github.com/freqtrade/freqtrade); C2; E=E1. Escopo: lookahead.py:66–95; test_lookahead_analysis.py:23–88; docs/lookahead-analysis.md.

**CODE_VERIFIED:** Compara indicadores nas mesmas linhas de execuções completas e truncadas. Os testes lidos verificam acionamento e configuração inválida, não toda sensibilidade do detector.

**INFERENCE / decisão:** Usar o desenho de comparação por prefixos como diagnóstico; sinais não acionados podem escapar e rankings entre pares podem produzir falsos positivos.

Licença do código: GPL-3.0. 2026.8 changes informative caching and VolatilityFilter averaging; 2026.7 changelog records stale re-entry candle correction. A version change can change selection/results.

### R02 — hummingbot/hummingbot

Referência [2bfaccc48dd49e71a5b6d9b3011808e127dd00cd](https://github.com/hummingbot/hummingbot); C2; E=E1. Escopo: arbitrage_executor.py:28–48,123–141,215–264; test_arbitrage_executor.py:48–87.

**CODE_VERIFIED:** Há cálculo de custos das duas pernas e preços normalizados por conversão. A elegibilidade considera tokens com USD no nome intercambiáveis; o teste aceita ETH-BUSD versus ETH-USDT.

**INFERENCE / decisão:** Adapter restrito para comparação de contabilidade. Não importar a elegibilidade como prova de paridade, liquidez de conversão ou financiamento das duas pernas.

Licença do código: Apache-2.0. 2.16.0 records connector rate-limit/timestamp fixes and LP net-PnL correction. Reviewed executor still makes quote-equivalence assumptions.

### R03 — nautechsystems/nautilus_trader

Referência [c993c7dec981ea7eda598ca61fd0a0023cd198cb](https://github.com/nautechsystems/nautilus_trader); C2; E=E1. Escopo: crates/execution/src/models/fill.rs:177–215,1454–1491; current fill-model docs; issue #4966.

**CODE_VERIFIED:** ProbabilisticFillState validates [0,1], seeds RNG, makes 0/1 deterministic; tests assert out-of-range failures. Synthetic liquidity and recorded book are different modes.

**INFERENCE / decisão:** AUGMENT as isolated future reference only. Reproducible random fills are assumptions, not observed execution. Same-timestamp settlement issue is an unreplicated upstream report.

Licença do código: LGPL-3.0. 2.0.0rc4 removes former Cython constraints and changes enums/model configuration. Pin Rust/Python API together; old guessed Cython paths were 404.

### R05 — ccxt/ccxt

Referência [da 331f0aacca29e57ec637531191fa1a314b4146](https://github.com/ccxt/ccxt); C1; E=E1. Escopo: exchange.py:4969–4990,5182–5192; Manual.md, seção OHLCV.

**CODE_VERIFIED:** A base normaliza seis campos OHLCV e recusa métodos não suportados. Suporte uniforme da interface não demonstra suporte em toda venue. No projeto, CCXT 4.5.70 já está instalado.

**INFERENCE / decisão:** KEEP; validar semântica por exchange e produto. O provider local descarta candle aberto, mas fechamento convencional não é recibo real de publicação histórica.

Licença do código: MIT. 4.5.78 release is newer than local 4.5.70; no update justified merely by recency.

### R07 — nkaz 001/hftbacktest

Referência [5f3ec40b2afb764e0fea112f941ed85523ef4e88](https://github.com/nkaz001/hftbacktest); C1; E=E1. Escopo: queue.rs:63–138; latency.rs localizado; documentação Order Fill.

**CODE_VERIFIED:** O modelo conservador inicializa quantidade à frente, reduz com trades e limita pela profundidade; modelos probabilísticos representam incerteza de fila.

**INFERENCE / decisão:** AUGMENT no estudo de fills com limites. Replay não altera o mercado; capacidade e impacto continuam fora da verificação. Não instalar para simular latência institucional local.

Licença do código: MIT. 0.9.4/2.4.4 records converter fixes including structured-array conversion failure. Data conversion is part of experiment provenance.

### R08 — bmoscon/cryptofeed

Referência [e 7a73d7444f0265b4131faa2aec2a2c558fed929](https://github.com/bmoscon/cryptofeed); C1; E=E1. Escopo: binance.py:334–413.

**CODE_VERIFIED:** Book mantém quantidades Decimal, trata remoção de níveis e transmite sequência, horário do evento, recepção e bruto; chama validação de update ID. Funding inclui próximo horário, não apenas pagamento realizado.

**INFERENCE / decisão:** Candidato a feed delimitado de microestrutura. Preservar distinção event/receipt e funding estimado/liquidado; teste de Binance procurado retornou 404, não se infere ausência de testes.

Licença do código: AGPL-3.0-or-later. 2.5.0 described as final 2.x before 3.0; migration burden and AGPL scope matter for adapter choice.

### R09 — DefiLlama/yield-server

Referência [8f426f2f5be528ed6520a6da68be35541fa8cc16](https://github.com/DefiLlama/yield-server); C1; E=E1. Escopo: src/adaptors/aave-v3/index.js:61–101,155–243; README.md.

**CODE_VERIFIED:** Adapter consulta reservas/configuração, exclui congeladas, distingue caixa, dívida e oferta; apyBase nessa seção é liquidityRate/RAY ×100.

**INFERENCE / decisão:** Útil para discovery; não equivale a rendimento realizado composto. Exclusão corrente de reservas não reconstrói universo passado. Renda do estudo local usa razão de índices, que é outro objeto.

Licença do código: UNKNOWN; root license not located. No entries in releases feed; that does not prove no maintenance. Code and source hash are usable research provenance.

### R10 — aave/aave-v3-core

Referência [782f51917056a53a2c228701058a6c3fb233684a](https://github.com/aave/aave-v3-core); C1; E=E1. Escopo: ReserveLogic.sol, getNormalizedIncome; MathUtils.sol:1–37.

**CODE_VERIFIED:** Juro linear entre atualizações usa segundos/365 dias em RAY. O coletor local reconstrói normalized income e arredondamento; a referência aave-v3-core está arquivada desde a fotografia da API.

**INFERENCE / decisão:** VALIDATE, sem tratar o repositório arquivado como implementação atual do proxy no bloco histórico. Corroborar implementação/endereço/bloco e segunda rota RPC. SPDX BUSL-1.1 no arquivo exige análise separada para reuso.

Licença do código: BUSL-1.1 text with Change Date <=2023-01-27, Change License MIT. 1.19.4 changelog techpaper typo correction; archived source, not evidence of current deployed implementation.

### R11 — Uniswap/v3-core

Referência [d0831dc6b8a318df3872b6d68f6de135c9f3ec29](https://github.com/Uniswap/v3-core); C2; E=E1. Escopo: SwapMath.sol:21–96; test/SwapMath.spec.ts:20–80.

**CODE_VERIFIED:** Swap por etapa trata exact-in/exact-out, limite de preço e arredondamento de fees. Testes conferem quantidades exatas e que a etapa não consome toda a ordem quando atinge alvo.

**INFERENCE / decisão:** Referência de cálculo, não estimador de lucro de LP. Precisa ticks, liquidez ativa, custos de reposicionamento e seleção adversa; adiar estratégia até dados e protocolo.

Licença do código: BUSL-1.1 text with Change Date <=2023-04-01, Change License GPL-2.0-or-later. Feed latest entry 1.0.0; protocol age alone does not imply defective arithmetic. Deployment/version and license conversion separate.

### R22 — stefan-jansen/alphalens-reloaded

Referência [f0a07c22d554e4b4036983cc80320b432714fe7e](https://github.com/stefan-jansen/alphalens-reloaded); C2; E=E1. Escopo: src/alphalens/performance.py:28–85; tests/test_performance.py:114–138.

**CODE_VERIFIED:** IC é Spearman por data e ativos, com opção de ajuste por grupo; teste compara DataFrame esperado. Importa SciPy, pandas e outras bibliotecas.

**INFERENCE / decisão:** AUGMENT ranking, IC por data, turnover e exposição. É descendente de Alphalens, não réplica de linhagem independente; SciPy compartilhado reduz independência do cálculo. Calendário e perdas de ativos precisam contrato cripto.

Licença do código: Apache-2.0. Feed entries 0.4.6 and 0.4.5 have nonmonotonic update dates; do not infer latest compatible artifact from feed order alone.

### R25 — bashtage/arch

Referência [704bb70e48372e3ccccdde7da379811657ad0224](https://github.com/bashtage/arch); C2; E=E1. Escopo: multiple_comparison.py:501–565,635–709; tests/test_multiple_comparison.py:61–115.

**CODE_VERIFIED:** SPA trabalha com perdas benchmark e alternativas, bootstrap em blocos e três centramentos; calcula distribuição do máximo e p-values. Tests compare autocovariance-based variance and bootstrap maxima/quantiles explicitly.

**INFERENCE / decisão:** AUGMENT SPA only after interval validity and a registered complete loss matrix; bootstrap block choice and multiple testing remain scientific assumptions.

Licença do código: Permissive custom BSD/MIT-style text; preserve notices/no endorsement. 8.0.0 is mainly Python/NumPy/pandas compatibility. Source tests inspect variance and p-value calculations; no external suite executed.

### R26 — statsmodels/statsmodels

Referência [1d2307006379fd78ed4f921a92d7fe8c069565f7](https://github.com/statsmodels/statsmodels); C2; E=E1. Escopo: _stattools.py:2681–2717; test_stattools.py:1384–1421.

**CODE_VERIFIED:** Cointegração ajusta OLS e ADF dos resíduos; alerta para colinearidade quase perfeita e usa valores críticos apropriados ao desenho. Tests compare Engle-Granger critical values/statistics and explicitly handle identical-series collinearity.

**INFERENCE / decisão:** Candidato para resíduos/pares; ajuste e escolha da janela devem ocorrer dentro de treino. Teste de cointegração não prova spread executável, hedge disponível ou retorno após borrow.

Licença do código: BSD-3-Clause. 0.15.0 changes randomness conventions and tuple returns to NamedTuple, raises minimum dependencies. Adapter needs version contract.

### R27 — scikit-learn/scikit-learn

Referência [8c54c136cac4982a0dac7bee8b8fbcada411fe10](https://github.com/scikit-learn/scikit-learn); C2; E=E1. Escopo: _split.py:1292–1327; test_split.py:1869–1907.

**CODE_VERIFIED:** TimeSeriesSplit separa teste e treino com gap de contagem de linhas e limite opcional de treino; testes verificam índices exatos.

**INFERENCE / decisão:** VALIDATE fronteiras. Gap por linha não equivale a purging por término do label quando horizontes variam; não elimina seleção externa ao split. Já instalado no projeto.

Licença do código: BSD-3-Clause (COPYING). Release 1.9.1 listed; installed 1.9.0 used for B05, no silent dependency upgrade.

### R28 — skfolio/skfolio

Referência [085485b0f35576c1b36b4c4253cb7b944fee0c6f](https://github.com/skfolio/skfolio); C2; E=E1. Escopo: _combinatorial.py:329–362; test_combinatorial.py:26–89.

**CODE_VERIFIED:** Matriz de folds marca purga antes/depois e embargo; testes verificam índices com e sem purga.

**INFERENCE / decisão:** Referência para testar fronteiras. Caminhos combinatórios podem treinar em datas posteriores ao teste; não são automaticamente simulação causal de implantação ou amostras independentes.

Licença do código: BSD-3-Clause. 1.0.6 corrects minimum requirements and development dependency groups; no evidence of improved economic performance.

### R39 — lballabio/QuantLib

Referência [e 06326c4ec955421fc58fbd6b6e33a332535ad80](https://github.com/lballabio/QuantLib); C1; E=E1. Escopo: blackformula.cpp:59–106; test-suite/blackformula.cpp:36–69.

**CODE_VERIFIED:** Black valida desvio padrão e desconto, com caso de volatilidade zero. Teste inspecionado cobre round-trip de volatilidade implícita Bachelier; não certifica toda fórmula Black.

**INFERENCE / decisão:** Referência parcial para opções/Greeks. Falta contrato de quote, settlement, IV e liquidez histórica do instrumento cripto; não pressupor payoff linear em USD.

Licença do código: Permissive QuantLib license with component notices (LICENSE.TXT). 1.43 removes deprecated features and lists a Black-formula fuzzing harness; no full C++ build/bench performed.

### R41 — BIS — Crypto carry

Referência [PDF bytes preserved 2026-09-11; see additional_sources.json and R41 full_receipt](https://www.bis.org/publ/work1087.htm); C0; E=E3. Escopo: PDF 54 pages; data pp.9–10; funding/margin mechanism p.8.

**PAPER_STUDIED:** Estudo diário BTC/ETH, março/2019–janeiro/2022, usa Skew, maturidades constantes e sete venues; complementa com lending e posições CFTC. Carry remunera segmentação/demanda por alavancagem. A própria análise discute perdas na perna futura e funding até convergência.

**INFERENCE / decisão:** Retorno antes de transação e financiamento de referência não é retorno líquido acessível ao projeto. Venues, garantias e dados históricos diferem; não reabrir piloto congelado. Transferível: decomposição por perna, vencimento, margem e caixa.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

### R42 — Liu, Tsyvinski e Wu — Common Risk Factors in Cryptocurrency

Referência [PDF bytes preserved 2026-09-11; see additional_sources.json and R41 full_receipt](https://www.nber.org/papers/w25882); C0; E=E3. Escopo: PDF 48 pages; dados pp.6–8; short BTC pp.29–30.

**PAPER_STUDIED:** Amostra 2014–2018 de 1.707 moedas CoinMarketCap, com filtros de capitalização/dados e winsorização semanal. Examina mercado, tamanho e momentum. Preços agregados e semanas especiais no fim do ano exigem contrato explícito.

**INFERENCE / decisão:** Ao substituir a perna vendida por BTC, momentum de uma, duas e quatro semanas perde significância no estudo. Portanto hedge viável pode mudar a conclusão. Transferível: ranking e atribuição a fatores; não transportar alpha, significância ou disponibilidade histórica de short.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

### R43 — Cawley e Talbot — Over-fitting in Model Selection

Referência [PDF bytes preserved 2026-09-11; see additional_sources.json and R41 full_receipt](https://jmlr.org/papers/v11/cawley10a.html); C0; E=E3. Escopo: PDF 29 pages; método/figuras pp.8–12.

**PAPER_STUDIED:** Kernel ridge classifier em dados sintéticos e múltiplas amostras de validação mostram que minimizar uma estimativa ruidosa de erro pode sobreajustar a seleção. Validação de 64 contra 256 casos ilustra a redução de variância.

**INFERENCE / decisão:** Transferível: seleção de universo, filtros, features e hiperparâmetros deve ficar dentro do desenho avaliado. Não transferir a partição aleatória de classificação IID para séries financeiras; usar cortes temporais e dependência dos labels. Nenhum tamanho de viés local estimado.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

### R44 — Milionis et al. — Automated Market Making and Loss-Versus-Rebalancing

Referência [PDF bytes preserved 2026-09-11; see additional_sources.json and R41 full_receipt](https://arxiv.org/abs/2208.06046); C0; E=E3. Escopo: PDF 65 pages; modelo pp.10–11; método/figura 5 pp.33–35, página 35 renderizada e inspecionada.

**PAPER_STUDIED:** Modelo separa exposição ao preço e fees menos seleção adversa. Assume inicialmente CEX profundo sem fees, preço contínuo, LP passivo e ausência de gas/discretização. Estudo WETH-USDC Uniswap v2 de agosto/2021–julho/2022 aproxima rebalanceamento em frequências distintas.

**INFERENCE / decisão:** Transferível: comparar LP com rebalanceamento, além de hold, explicitando fees, gas e hedge. Não é estratégia automaticamente executável, nem estimativa de LP v3/v4 concentrado. Curvas agregadas não demonstram lucro de uma carteira individual.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

### R47 — Glassnode PIT

Referência [https://docs.glassnode.com/data/point-in-time-metrics](https://docs.glassnode.com/); C0; E=sem validação empírica. Escopo: official data/product contract, 2026-09-11.

**FACT_DOCUMENTED:** PIT congela versões de métricas; computed_at começou a ser registrado em setembro/2024 e não é publicação instantânea. A documentação declara atraso entre computação e API e cobertura PIT dependente da data de início de cada métrica.

**INFERENCE / decisão:** Não retroprojetar rótulos atuais de entidades nem computed_at como acesso imediato. Documentação pública acessível; série e licença específicas não contratadas/verificadas.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

### R50 — ALFRED real-time periods

Referência [https://fred.stlouisfed.org/docs/api/fred/realtime_period.html](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html); C0; E=sem validação empírica. Escopo: official data/product contract, 2026-09-11.

**FACT_DOCUMENTED:** realtime_start/realtime_end selecionam o intervalo de conhecimento; padrão hoje. Consultar hoje uma série antiga sem vintage não reconstrói automaticamente informação passada.

**INFERENCE / decisão:** Datas de vintage não substituem hora intradiária do anúncio. Macro exige vintage, calendário e receipt; nenhuma nova extração econômica aqui.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

### R51 — Lido withdrawal queue

Referência [https://docs.lido.fi/contracts/withdrawal-queue-erc721/](https://docs.lido.fi/contracts/withdrawal-queue-erc721/); C0; E=sem validação empírica. Escopo: official data/product contract, 2026-09-11.

**FACT_DOCUMENTED:** Withdrawal request cria direito de resgate e precisa finalização antes de claim. O contrato documenta que tokens na fila não recebem recompensas do período e continuam sujeitos a perdas.

**INFERENCE / decisão:** Preço de stETH, rendimento e tempo de resgate são objetos distintos. Investigar desconto contra custo/risco da fila; não presumir resgate instantâneo ou paridade.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

### R52 — R52

Referência [SciPy 1.18.0 instalado](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html); C4; E=E1, E5. Escopo: SciPy instalado stats/_stats_py.py:5401–5465; benchmark_result.json.

**CODE_VERIFIED:** Spearman usa rankdata e correlação, sinaliza entradas constantes. A comparação local B01 conferiu 100 casos sintéticos com empates; B02 usou NumPy para SMA/Bollinger.

**INFERENCE / decisão:** KEEP implementações locais no escopo aprovado; referências complementam diagnóstico. Alphalens usa SciPy, portanto não acrescenta uma terceira linhagem independente para essa mesma conta.

Licença do código: UNKNOWN. Método/documentação examinados; sem inferir licença de dados ou redistribuição do artigo.

## Issues e regressões relevantes

| Referência | Estado observado | Uso da evidência |
| --- | --- | --- |
| https://github.com/freqtrade/freqtrade/issues/13547 | closed; 2026-09-08T18:49:52Z | Relato externo, não reproduzido; informa fixture necessária, não defeito confirmado no nosso código |
| https://github.com/freqtrade/freqtrade/issues/13303 | closed; 2026-06-29T18:16:42Z | Relato externo, não reproduzido; informa fixture necessária, não defeito confirmado no nosso código |
| https://github.com/nautechsystems/nautilus_trader/issues/4966 | open; 2026-09-11T02:38:09Z | Relato externo, não reproduzido; informa fixture necessária, não defeito confirmado no nosso código |

Freqtrade #13547 relata falso positivo quando callbacks dependem da whitelist; #13303 relata replay de candles antigos na reentrada do universo. Ambos estavam fechados; o changelog 2026.7 registra correção de reentrada. Não atribuímos o bug histórico ao HEAD inspecionado sem reprodução. Nautilus #4966 permanece aberto e relata índice de settlement diferente entre pernas com mesmo timestamp em 2.0.0rc4: exige fixture de ordenação antes de qualquer adoção para opções.

As releases consultadas cobrem os 15 repositórios aprofundados originalmente. Freqtrade muda semântica de filtros; Hummingbot registra correções em timestamps/PnL; Nautilus migra API para Rust; statsmodels altera retornos/dependências. Recência não equivale a superioridade. Licenças corrigidas: cryptofeed tem AGPL, não MIT presumida; Aave e Uniswap têm datas de conversão no texto. A data passada é informação do próprio arquivo, não parecer sobre todos os componentes/deployments. Yield-server segue UNKNOWN: não copiar código até esclarecer licença. Sem instalação ou vendoring nesta rodada.

## Fontes e contratos comparáveis

| Domínio | Refs | Acesso observado | Contrato mínimo | Limite | Capacidades |
| --- | --- | --- | --- | --- | --- |
| OHLCV/universo | R05 R20 | Publicação de arquivos/documentação acessível; painel antigo local tem lacunas | OHLCV+instrumento+eligibilidade por data+delistings+hash de arquivo | Preço agregado/last não é fill; fonte comum não é independente | K01 K04 |
| Books/trades | R03 R07 R08 | Código/documentação disponíveis; trajetória L2 admissível não localizada nos datasets atuais | Sequência, snapshot inicial, updates, trade flags, event/receipt e resets | Fila/latência/impacto não identificados por snapshots | K06 |
| Funding/basis | R05 R20 R45 | Dados históricos locais e fontes oficiais; cobertura por contrato exige gate | Pagamento por evento e mark, basis por vencimento, quote e margem | Projetado versus liquidado; não impor 8h a todo produto | K07 K18 |
| Opções | R39 R46 | API pública documentada; histórico bid/ask não adquirido | Strike/expiry/style/settlement/currency, IV e bid/ask simultâneos | Mark/Greeks não são preço executável nem lucro hedgeado | K14 |
| Aave | R09 R10 | Histórico e recibos locais presentes; segunda rota ConnectTimeout | 38 fronteiras preservadas, índice/RAY, bloco/sucessor, reserva e proxy | RPC diferente não garante backend independente; liquidez entre fronteiras desconhecida | K03 K12 |
| Staking | R14 R51 | Contrato e documentação acessíveis; histórico de filas não adquirido | Shares/rebase, request/finalization/claim, taxas e penalidades | Período sem recompensa e resgate incerto afetam retorno | K12 |
| LP | R11 R12 R44 | Código/paper disponíveis; dataset de posição v3/v4 não adquirido | Mint/burn/swap, ticks/liquidez ativa, posição, preços, fees, gas, hedge | LVR idealizado e pool agregado não equivalem à posição real | K13 |
| On-chain/entities | R16 R17 R18 R47 R48 R49 | Ferramentas/docs disponíveis; acesso/termos por métrica UNKNOWN | Bloco finalizado, computed_at, publicação, receipt e vintage de rótulo | Reclassificação de wallets pode criar futuro retrospectivo | K15 |
| Stablecoins | R09 R15 R19 R47 | Fontes/código triados; termos de serviços separados | Peg por venue, reserves/claims, concentração, redemption, chain/bridge | Stablecoin e ativo embrulhado não equivalem por nome | K11 K12 K15 |
| Macro | R50 | ALFRED documentação acessível; extração vintage não realizada | Vintage, calendário, anúncio intradiário e disponibilidade | DTWEXBGS não é automaticamente DXY nem preço de decisão | K08 |
| Eventos/news | R49 R53 | Eventos on-chain possíveis; unlocks fonte não extraída; registros privados não abertos | Primeira publicação/correções, timezone, entidade, surpresa e deduplicação | Evento conhecido depois não serve como sinal anterior | K09 |
| Modelos | R31 R34 R35 R36 R37 R38 | Código triado; nenhum peso/modelo remoto executado | Treino/validação isolados, target, calibração e versões de pesos | Licença do código não cobre dados/pesos; tuning e regime mudam erro | K16 K17 |

## Independência, transferibilidade e resultados desfavoráveis

Alphalens-reloaded deriva de Alphalens e usa SciPy; não são três oráculos independentes para o mesmo IC. CCXT presente em vários engines continua uma dependência comum. Aave e DefiLlama leem a mesma cadeia; duas rotas RPC não criam duas amostras econômicas. Todos os testes locais desta iniciativa foram conduzidos pelo mesmo agente, sem revisão humana independente.

Nenhum resultado econômico externo recebeu E4/E5/E6 local. O paper de fatores oferece um contraexemplo importante: hedge BTC muda significância de momentum; o paper de carry trata margem e financiamento; LVR separa exposição de receita. Essas limitações são mais úteis para formular controles do que importar tabelas de retorno. Transformers/RL, novos lending protocolos e universos adicionais ficaram em triagem: sem necessidade incremental demonstrada, não foram aprofundados por quota artificial.
