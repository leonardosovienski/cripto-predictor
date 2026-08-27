# Inventario de dados e testes retrospectivos — 2026-08-27

## Escopo e reproducibilidade

Esta nota registra o que foi encontrado e reproduzido localmente no commit
`76bab876b7ec7b2ca7ae9dab1a0d2fd4d3435e07`. Os dados brutos nao fazem parte do
Git: o runtime resolve `DATA_DIR`, `OUTPUT_DIR`, `CACHE_DIR` e `LOGS_DIR` para
`C:\predictor\data` nesta maquina. Nenhuma credencial e nenhum banco foi
adicionado ao repositorio.

Os numeros abaixo cobrem somente o repositorio atual e `C:\predictor\data`.
Dados apagados, remotos ou mantidos em outra maquina nao foram inferidos.

## Inventario fisico

O diretorio ativo tinha aproximadamente 2.321 arquivos e 5,40 GB no inventario
estavel. WAL, SHM e locks podem variar enquanto processos estao abertos.

### Dados primarios unicos

| Conjunto | Registros | Periodo |
|---|---:|---|
| BTC spot 1h | 48.912 | 2021-01-01 a 2026-07-31 |
| ETH spot 1h, baixado para a replicacao desta nota | 48.912 | 2021-01-01 a 2026-07-31 |
| BTC open interest 5 min | 628.511 | 2021-01-01 a 2026-08-07 |
| BTC funding | 6.114 | 2021-01-01 a 2026-07-31 |
| ETH funding | 6.114 | 2021-01-01 a 2026-07-31 |
| Sinais HMM BTC | 12.018 | 2021-01-31 a 2026-07-31 |
| Sinais HMM ativos | 246 (110 long, 136 short) | mesmo periodo |
| Eventos de microestrutura V3 | 2.929.367 | 2026-08-18, cerca de 6h38 |

O cache Binance Vision continha 2.246 ZIPs: 2.045 arquivos diarios de metricas
BTC, 67 klines mensais BTC, 67 funding mensais BTC e 67 funding mensais ETH.
Para a replicacao ETH foram baixados os klines mensais publicos necessarios e
materializados em `C:\predictor\data\v3\ETHUSDT\spot_1h.csv`.

### Feature Store ativa

| Tabela | Linhas |
|---|---:|
| `raw_market_data` | 5.738 |
| `raw_signals` | 2.146 |
| `features_aligned` | 15.412 |
| `ingestion_provenance` | 168 |
| `observation_scorecards` | 36 |
| `predictions` | 86 |
| `predictions_archive` | 86 |
| `predictions_archive_chain` | 86 |

Archive e chain protegem as mesmas 86 previsoes e nao sao observacoes novas.
Existiam 84 previsoes aceitas pelo loader do backtest, 65 maduras em D+1, quatro
maduras em D+7 e nenhuma madura em D+30 na leitura de 2026-08-27.

Os resultados historicos documentam 440 previsoes da H5 e cinco da H4, mas as
linhas brutas nao existem nos bancos encontrados. Nao podem ser reanalisadas.

### Copias e derivados que nao devem ser somados

- `feature_store_backup_antes_limpeza.db`: 2.365.074 `raw_signals`, zero previsoes;
- dois bancos de reconstrucao: 1.182.824 `raw_signals` cada, zero previsoes;
- banco pre-live: 102 sinais, zero previsoes;
- dois backups de microestrutura sobrepostos ao banco atual;
- `garimpo_backtest.csv`, relatorios CSV/XLSX, archives, scorecards e snapshots.

Nao foi localizado backup semanal valido das 86 previsoes. Hash chain detecta
adulteracao, mas nao recupera perda fisica do banco.

## Reproducao das hipoteses V3

Configuracao comum: BTC, 6.114 fundings, 2.037 dias, aproximadamente 6.004
FeatureVectors, WFA 180 dias IS / 7 dias purge / 30 dias OOS, Kelly 0,5, taxa
taker 10 bps, slippage 5 bps e funding real.

| Hipotese | Configuracao | PSR | Spearman | IC inferior | MaxDD | Folds GO | Resultado |
|---|---|---:|---:|---:|---:|---:|---|
| H1 | fr90, 24h | 0,1546 | +0,0828 | -0,0944 | 12,61% | 0 | NO-GO |
| H2 | fr21, 24h | 0,2873 | +0,0320 | -0,1779 | 10,38% | 0 | NO-GO |
| H3 | fr90, 48h | 0,0745 | -0,0026 | -0,1793 | 23,57% | 0 | NO-GO |

H1 e excessivamente esparsa por combinar funding extremo, OI crescente, regime
permitido e confianca minima. H2 muda apenas a janela do mesmo mecanismo e
aumenta ruido. H3 alonga um mecanismo transitorio, aumenta carry/exposicao e
viola tambem o limite de drawdown. Nenhuma familia deve ser reaberta.

Na H3, a serie persistida tinha 3.953 periodos OOS: 130 com posicao ativa,
54 retornos positivos, 76 negativos e 3.823 flats. O retorno log liquido
acumulado foi -0,2106, aproximadamente -19% composto.

## Candidato ortogonal 4h rejeitado

O draft `trend-following-binance-spot-4h-v1` foi testado como pesquisa
retrospectiva: long/caixa, close acima da media de 42 barras, entrada na barra
seguinte e 15 bps por transicao. Resultado total BTC 2021-2026: +54,2% bruto,
-62,0% liquido, contra +59,1% de buy-and-hold, Sharpe liquido -0,45 e MaxDD
74,9%. O turnover destruiu o candidato; ele nao deve ser registrado.

## Pre-registro exploratorio daily e replicacao ETH

Antes de baixar ou inspecionar os klines ETH completos, foi congelada a regra:

- familia `spot_daily_trend_long_cash_v1`;
- BTC desenvolvimento e ETH replicacao obrigatoria;
- dias UTC completos, decisao somente no fechamento;
- posicao em D+1 se `close_D > SMA200_D`, caso contrario caixa;
- posicoes `{0, 1}`, sem short, leverage, HMM, funding/OI ou LLM;
- 15 bps por entrada ou saida;
- moving-block bootstrap, bloco 30 dias, 2.000 amostras, seed 42;
- sucesso separado nos dois ativos: retorno e Sharpe liquidos positivos, limite
  inferior do IC95 da media > 0, superar buy-and-hold e MaxDD < 30%;
- capital permanece nao autorizado qualquer que seja o resultado.

### Resultado observado

Foram avaliados 1.838 dias, de 2021-07-19 a 2026-07-30.

| Metrica | BTC | ETH |
|---|---:|---:|
| Retorno bruto | +109,2% | +244,7% |
| Retorno liquido | +94,7% | +230,5% |
| Buy-and-hold | +103,9% | +2,4% |
| CAGR observado aproximado | 14% a.a. | 27% a.a. |
| Sharpe liquido | 0,37 | 0,53 |
| MaxDD | 36,4% | 38,5% |
| IC95 da media liquida, bps/dia | [-5,16; +13,30] | [-4,26; +16,03] |
| Dias posicionado | 973 | 874 |
| Transicoes | 48 | 28 |
| Participacao dos cinco melhores dias positivos | 5,2% | 5,7% |

O retorno e economicamente interessante e o drawdown e menor que o buy-and-hold,
mas o gate foi reprovado: BTC nao superou buy-and-hold, ambos os intervalos
cruzam zero e ambos excedem MaxDD de 30%. O custo spot e uma premissa preliminar,
nao calibrada contra execucao real. BTC e ETH tambem sao correlacionados e nao
constituem duas replicacoes totalmente independentes.

## Projecoes e interpretacao correta

Os CAGR de 14% e 27% sao taxas anualizadas do periodo observado, nao previsoes de
retorno futuro. Nao ha base cientifica para projetar esses valores adiante.

Uma trial prospectiva pode manter a SMA-200 congelada e coletar novos dados em
paper trading. Ela nao deve alterar SMA, custos, horario, ativos ou gate depois
desta leitura. Qualquer filtro de volatilidade, reducao de risco ou novo ativo
constitui hipotese nova, com novo pre-registro e dado OOS ainda nao observado.

## Estado final

- H1-H5 permanecem encerradas conforme o charter;
- H6 permanece imatura e nao foi julgada com quatro observacoes D+7;
- o candidato 4h foi rejeitado;
- o candidato daily apresentou retorno positivo, mas falhou no gate completo;
- nenhuma hipotese tem edge validado;
- capital, leverage e trading direto por LLM permanecem nao autorizados.
