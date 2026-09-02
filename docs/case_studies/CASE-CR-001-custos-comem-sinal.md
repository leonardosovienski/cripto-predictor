# CASE-CR-001 — Custos líquidos comem um edge bruto positivo (H1/H2/H3)

**Fonte:** `GarimpoInvestimentos/trials.json` (v3-hmm-funding-oi-fr90/fr21/fr90-h48),
`docs/HYPOTHESES.md`, `GarimpoInvestimentos/v3/costs.py`.

## Claim
Um sinal de regime (HMM 3 estados) sobre desequilíbrio de funding/OI mostrou edge
bruto positivo em backtest, mas foi refutado (NO-GO) assim que custos realistas de
execução foram aplicados — e o veredito se manteve estável sob reanálise em base
estendida.

## Protocolo
- Modelo: GaussianHMM 3 estados, forward causal, condicionado a
  `funding_zscore`, `oi_log_delta`, `leverage_pressure`, retorno/vol realizada.
- Custos: taker 10bps + slippage 5bps por perna + funding real (`v3/costs.py`,
  `CostModel` — canônico para veredito científico em `crypto_perp`).
- Validação: WFA IS/OOS por timestamp; gate PSR ≥ 0.80 ∧ IC_lower(Spearman) > 0 ∧
  MaxDD < 20%, líquido de custos.
- Três configurações registradas como trials separadas (H1 horizonte 24h/fr90,
  H2 janela curta fr21, H3 horizonte 48h) — não reaproveito de tentativa.

## Result
| Trial | Bruto/sinal | Líquido/sinal | PSR | IC_lo Spearman | MaxDD |
|---|---|---|---|---|---|
| H1 (fr90, 24h) | +0.44bps | −0.09bps | 0.445 (BTC) | −0.086 | 29% |
| H2 (fr21, 24h) | +0.07bps | −0.37bps | 0.215 | −0.218 | 25.8% |
| H3 (fr90, 48h) | −0.35bps (já bruto negativo) | −0.75bps | 0.192 | — | 50.3% |

PSR é kelly-invariante: nenhuma fração de sizing salva o resultado. Reanálise
independente (2026-07-09) na base estendida 2021→jul/2026 reproduziu o NO-GO por
caminho diferente: IC_lower −0.079 e reprovação em 0/3 sub-séries no PSR sem
sobreposição de janelas (`scripts/psr_nonoverlap.py`).

## Failure mode
Um "GO histórico" anterior (PSR 0.909, 27/06) foi calculado **pré-custos e
pós-kelly-sweep** — otimizar o sizing antes de aplicar o custo de execução
disfarça um sinal que morre no primeiro contato com fricção real. O caso ilustra
por que o projeto separou `cost_policy.py` como ponto de entrada único e recusa
modelos não calibrados para veredito (`UncalibratedCostModel`).

## Lesson
Custos devem ser aplicados ANTES de qualquer otimização de sizing/posição, e o
modelo de custo usado no veredito precisa estar explicitamente marcado como
calibrado para o instrumento (`CALIBRATED_FOR_VERDICT`). Um Sharpe/PSR bruto
positivo não é evidência de nada até esse passo.
