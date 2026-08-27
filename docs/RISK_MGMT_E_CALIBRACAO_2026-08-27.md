# Gestão de risco intratrade e calibração de thresholds — infra (2026-08-27)

## O que mudou

Duas lacunas apontadas na auditoria de lucratividade foram fechadas do lado
de **infraestrutura de código**, não de resultado:

1. **Stop-loss / take-profit intratrade** (`GarimpoInvestimentos/v3/backtest_v3.py`,
   `_find_barrier_return`). Antes desta revisão, todo sinal da V3 só era
   avaliado no horizonte fixo (24h/48h) — sem corte de perda entre a entrada
   e a saída. Agora `run_wfa` aceita `stop_loss_bps` / `take_profit_bps`
   (default `0.0` = desligado, comportamento idêntico ao anterior). A
   barreira caminha hora a hora sobre o spot 1h já coletado, sem lookahead
   (usa só closes ≤ t), e corta o P&L no cruzamento — o IC continua medindo
   o sinal cru contra o retorno do horizonte cheio, então a métrica de
   "o sinal prediz direção" não é contaminada pela gestão de risco.
   CLI: `--stop-loss-bps` / `--take-profit-bps`.

2. **Thresholds calibráveis** (`GarimpoInvestimentos/v3/signal_engine.py`).
   `_FR_ZSCORE_THRESHOLD` (2.0) e `_MIN_REGIME_CONFIDENCE` (0.60) eram
   constantes fixas, nunca otimizadas. `generate_signal` agora aceita
   `fr_zscore_threshold` / `min_regime_confidence` como overrides (defaults
   preservam o comportamento anterior). `backtest_v3.run_threshold_grid`
   varre uma grade de combinações, rodando o WFA completo (retrain do HMM
   por fold, IS/OOS disjuntos, purge) para cada uma.
   CLI: `--fr-thresholds ... --confidence-thresholds ...`.

## O que isso NÃO é

Nenhum destes dois pontos foi validado contra dados reais nesta revisão —
o ambiente onde o código foi escrito não tem acesso de rede (Binance
bloqueada) nem cópia local dos CSVs de `data/v3/` (não versionados). Ou
seja: **a lógica está testada unitariamente e é mecanicamente correta**
(ver `tests/test_v3_backtest_barriers.py`, `tests/test_v3_signal_engine.py`),
mas ninguém rodou `run_wfa`/`run_threshold_grid` fim-a-fim com dados de
mercado para saber se SL/TP ou um threshold diferente melhora o PSR/MaxDD
dos trials já fechados (`trials.json`).

Isso importa por dois motivos:

- **`run_threshold_grid` escolhendo a melhor combinação pelo agregado OOS
  de todos os folds já rodados é, ele mesmo, uma forma de overfitting de
  seleção** (mesma classe de risco que `analyzers/pbo.py` existe para
  mitigar do lado LLM). O resultado de uma grade nunca deve ser lido como
  veredicto GO — deve virar uma hipótese nova, pré-registrada em
  `docs/HYPOTHESES.md` com corte temporal (só previsões após o registro
  contam), e só então validada em dado fresco. O docstring de
  `ThresholdGridResult` documenta isso.
- **SL/TP reduz a variância de cauda mas não cria edge.** Se o sinal
  (funding/OI + regime) não tem poder preditivo líquido — como os trials
  `v3-hmm-funding-oi-fr90/fr21/fr90-h48` já mostraram (edge bruto pequeno,
  vira negativo após custos) — cortar a perda máxima por trade reduz o
  MaxDD mas não transforma um Spearman/PSR ruim em bom. O ganho esperado
  de SL/TP aqui é sobretudo em MaxDD e não em PSR/IC — os dois indicadores
  que os gates GO/NO-GO já usam.

## Próximo passo real (fora deste ambiente)

Rodar, com dados reais coletados via `pipeline.py`:

```
python -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT \
    --stop-loss-bps 50 100 200 \
    --take-profit-bps 100 200 400

python -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT \
    --fr-thresholds 1.5 2.0 2.5 3.0 \
    --confidence-thresholds 0.55 0.60 0.65 0.70
```

Qualquer combinação que bata PSR ≥ 0.80, IC_CI_lower > 0 e MaxDD < 20%
deve ser tratada como candidato a **nova trial pré-registrada** em
`docs/HYPOTHESES.md`/`trials.json` — não como autorização de capital
(nenhum resultado de grid-search sozinho autoriza; ver `docs/RELATORIO_FINAL.md`).
