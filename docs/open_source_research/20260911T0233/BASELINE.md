# Baseline factual — 20260911T0233

Fotografia local observada em 2026-09-11T02:35:30.637402+00:00. Checkout `C:\Cripto\pesquisa-20260909`, branch `research/aave-validation-20260910`, HEAD `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`. `git ls-remote` confirmou o mesmo SHA em main. A alteração preexistente de `docs/NEXT_CHAT_PROMPT.md` foi preservada; não fizemos reset, stash, commit, push ou merge.

Autoridade desta rodada: pedido atual para executar os dois arquivos fornecidos, no modo RESEARCH_AND_BENCHMARK. Autorizações mais amplas de integração/publicação no mandato antigo não foram herdadas. Regras locais de `C:\Cripto\AGENTS.md` lidas; trabalho sem subagentes. Um clone iniciado antes de localizar essa regra foi interrompido e preservado em `C:\Cripto\clone-incompleto-open-source-20260911`; não foi usado como baseline.

## Estado científico e proteção

Charter [charters/scientific_state.json:1](https://github.com/leonardosovienski/cripto-predictor/blob/e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f/charters/scientific_state.json#L1): H1/H2/H3/H5 CLOSED_NO_GO; H4/H6/H9 CLOSED_INSUFFICIENT_SAMPLE; H7/H8 REGISTERED_NOT_ACTIVATED. Nenhuma autorização de capital/alavancagem/trading LLM. H6/H9 insuficientes não são refutações. Manifestos de congelamento antigos têm escopo histórico; as linhas posteriores são separadas.

Carry manual v2: janela de entrada 12/09/2026 00–01 UTC. LLM pareado v3: 12/09 a 04/12 12–13 UTC, último target possível 13/12; executor congelado `595f120` em área própria. Não foram lidos resultados futuros, alterados protocolos, atualizados hashes desses executores ou acionadas coletas. Não executamos avaliadores econômicos/harness oficiais, treinamento, sweep, observadores ou serializados externos.

## Ambiente efetivamente identificado

| Componente | Versão instalada |
| --- | --- |
| predictor-core | 3.2.0 |
| predictor-ops | 4.1.0 |
| numpy | 2.5.1 |
| scipy | 1.18.0 |
| scikit-learn | 1.9.0 |
| ccxt | 4.5.70 |
| hmmlearn | 0.3.3 |
| pytest | 8.4.2 |
| ruff | 0.16.1 |
| httpx | 0.28.1 |
| pandas | NOT_INSTALLED |


Python 3.13.14; Windows-11-10.0.26200-SP0. Dependências declaradas em pyproject são faixas, com resolução em uv.lock; pacote declara licença Proprietary. pandas não instalado. Nenhuma instalação foi feita. Core/Ops estão instalados; shims internos não são novas implementações independentes.

## Fluxos confrontados

1. Discovery CoinGecko escolhe candidatos com momentum/trending, volume e exclusão de stable/wrapped/staked ([GarimpoInvestimentos/collectors/discovery.py:18](https://github.com/leonardosovienski/cripto-predictor/blob/e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f/GarimpoInvestimentos/collectors/discovery.py#L18)). Isso atende uma triagem direcional; usar essa exclusão como universo de toda pesquisa impediria investigar staking e rendimento.
2. Fase1 ingere DPL e serve snapshot para features, prefiltro, notícias/LLM e persistência ([GarimpoInvestimentos/phase 1.py:207](https://github.com/leonardosovienski/cripto-predictor/blob/e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f/GarimpoInvestimentos/phase1.py#L207)). CCXT provider faz validação OHLCV e descarta barra aberta. Manifesto fixa sete símbolos Binance e seis Kraken; CoinGecko amplia discovery, mas não prova cobertura histórica admissível.
3. Features diárias v4 exigem intervalo diário, duplicatas ausentes e sufixo contíguo. Volume base × close é aproximação da moeda de cotação, com flag, não volume exato nem conversão USDT/USD ([GarimpoInvestimentos/dpl/feature_engineering.py:66](https://github.com/leonardosovienski/cripto-predictor/blob/e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f/GarimpoInvestimentos/dpl/feature_engineering.py#L66)).
4. Feature Store persiste snapshots e inputs com hash; raw_market_data usa upsert. Snapshot não é recibo HTTP integral, e sua existência não torna toda a base imutável ([GarimpoInvestimentos/dpl/feature_store.py:182](https://github.com/leonardosovienski/cripto-predictor/blob/e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f/GarimpoInvestimentos/dpl/feature_store.py#L182); [GarimpoInvestimentos/dpl/snapshots.py:43](https://github.com/leonardosovienski/cripto-predictor/blob/e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f/GarimpoInvestimentos/dpl/snapshots.py#L43)).
5. Backtest usa Spearman/IC e helpers Core; V3 separa HMM, features, WFA e custos. Funding realizado está separado do cenário de funding constante do CostModel. V3 retorna UNVALIDATED; família HMM congelada não ganha permissão por testes sintéticos ([GarimpoInvestimentos/v3/backtest_v3.py:1072](https://github.com/leonardosovienski/cripto-predictor/blob/e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f/GarimpoInvestimentos/v3/backtest_v3.py#L1072)).
6. Pesquisa de carry/basis, altcoins e Aave vive também em scripts e dados externos ao Git. Planejador v3 verifica clocks/identidade, e o coletor Aave verifica reserva, bloco/sucessor e índice. Isto confirma capacidade de pesquisa parcial, não execução em conta.

## Dados observados em modo somente leitura

SQLite aberto com mode=ro e PRAGMA query_only: 200 barras, 3 previsões, 2 market_snapshots e 1 prediction_inputs. Apenas contagens, schema e campos de identificação dos snapshots foram examinados; textos LLM, credenciais e transcrições privadas não foram expostos.

Snapshot atual v4: available_at=2026-09-10 00:00 UTC, collected_at=02:12:15 UTC. A regra de 26h expira em **11/09 02:00 UTC**, anterior à inspeção. O v3 antigo também não atende o contrato atual. Isso exige dados frescos para novo diagnóstico operacional, mas não bloqueia pesquisa offline. Nenhuma ingestão de renovação foi executada.

Quotas: schema do banco examinado somente leitura; contadores não resetados. Limites documentados 28 ingestões, 8 notícias/provedor, 6 LLMs/provedor por dia UTC não são teto monetário universal. Na continuação foi reservada 1 unidade normal de ingestão para a segunda rota Aave, com 1 tentativa RPC e 0 bytes recebidos; nenhum reset de quota. Requests de documentação e GitHub têm recibos separados.

## Cobertura e checks

Inventário com hashes de 364 arquivos Python em baseline.json. Inventário não equivale a leitura. Foram lidos pontos de entrada/protocolos e trechos de implementação DPL, snapshots, features, discovery/prefiltro, custos, PBO, Spearman, macro, HMM, execução e Aave. Core foi rastreado via shims/versões; não houve auditoria integral do pacote.

33 testes sintéticos locais passaram na execução corrigida do runner. Primeira tentativa: 27 passaram e 6 falharam porque o bloqueio de socket também bloqueava o loopback do asyncio Windows. Ambos os XML/recibos foram preservados; correção somente no runner novo. Benchmark B01/B02 aprovado, ver EXPERIMENTS.

CI YAML lido e execução remota confirmada pelo SHA exato: [run 34541038423](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34541038423), push main, success; quality, all-extras, container e python-314-experimental passaram. O conector inicialmente filtrava apenas eventos de PR; a consulta geral resolveu a lacuna sem presumir falha da CI.

Suíte local completa:1505 passed,1 skipped,428,28s de pytest; runner 431,54s. Rede externa bloqueada no processo de testes, loopback permitido para asyncio Windows. Includes testes que reconstroem 1728 fluxos Aave com Fractions e índices RPC originais. Estes testes reproduzem a contabilidade histórica; não criam novo holdout. B03–B06 complementam B01/B02, com protocolo escrito antes da execução.

Leitura adicional de HMM confirmou fit/scaler no input de treino e forward-only na inferência (regime_engine.py:213,298,446). Isso depende de treino causal fornecido pelo chamador. Equity V3 (backtest_v3.py:378) aloca por eventos e fecha antes de reabrir no mesmo instante, mas carrega alocações ao custo até realização; não é um livro completo de marcação/liquidação. Funding (linha 322) verifica marks observados e sinal, com grid de 8h específico do estudo. Planejador hedge v2 valida livros/lotes e chama o cálculo congelado, cuja comissão e caixa passaram B06.

SHA-256 de charter, trials, lock e documento modificado preexistente em baseline.json. Conferência final renewed em preservation_completion.json. Recibos originais Aave conferidos pela suíte; nenhum rehash integral de todos os backups ou bases enormes é alegado. Novos arquivos de tentativa RPC foram adicionados somente ao local pré-registrado. Nenhuma alteração no código operacional, locks, dependências ou executores congelados.
