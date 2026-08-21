# Auditoria de Look-ahead — RegimeEngine (HMM da V3) · Risco nº 1

> ## ⚠️ ERRATA 2026-08-21
>
> O veredito desta auditoria (**sem look-ahead**) continua válido e é a base do NO-GO
> da família H1-H3. Só o endereço mudou: o objeto auditado não está mais na branch
> `claude/v3-quant-wip` (que não existe), e sim na `main`, no mesmo caminho
> `GarimpoInvestimentos/v3/regime_engine.py`.
>
> Índice: [ERRATA_2026-08-21.md](ERRATA_2026-08-21.md).

> Passo 5.1 do plano. Auditor: linha de sessões de arquitetura. Data: 2026-07-02.
> Objeto: `GarimpoInvestimentos/v3/regime_engine.py` + uso no `backtest_v3.py`
> (branch `claude/v3-quant-wip`).

## Veredito: **SEM LOOK-AHEAD — alegação do código COMPROVADA** ✅

O risco nº 1 da auditoria original era: "se o backtest atribui regimes com
suavização full-sample, há look-ahead estrutural que invalida todo walk-forward".
A V3 não só evita o erro — ela o evita **por construção documentada**, em quatro
camadas verificadas independentemente:

| # | Camada | Evidência |
|---|--------|-----------|
| 1 | **Decodificação filtrada, não suavizada** | `_forward_causal` implementa o Forward Algorithm manualmente (α_t = B(x_t)·Aᵀα_{t-1}, normalizado por passo). Não há passo backward; `hmmlearn.predict_proba` (forward-backward) não é usado na inferência. |
| 2 | **Scaler congelado no treino** | `fit()` faz `scaler.fit_transform` (in-sample); `predict_series()` usa `scaler.transform` — média/desvio NUNCA são re-estimados na série de inferência (o vetor sutil nº 1 desta classe de bug). |
| 3 | **Walk-forward treina só no IS** | `backtest_v3` particiona IS/OOS por timestamp, treina o engine exclusivamente no IS e infere a série contígua IS+OOS (o IS é só warmup da recursão α); P&L conta apenas pares OOS. Rótulos de estado fixados no fit (Viterbi in-sample apenas para NOMEAR estados — não vaza para o teste). |
| 4 | **Prova automatizada de invariância** | `tests/test_v3_hmm_no_lookahead.py`: truncar a série em t e estendê-la com futuro **não altera nenhum posterior/estado anterior a t** (igualdade exata, cortes em 50/120/199) — com engine sintético E com modelo real treinado por Baum-Welch. |

## Poder do teste (por que ele pegaria a regressão)

O mesmo arquivo contém a **contraprova**: um decodificador suavizado
(forward-backward, γ) implementado dentro do teste, que ao receber dados futuros
**muda o passado** (diff máx > 1e-6 medido). Se alguém trocar a decodificação
causal por `predict_proba`/suavização, o teste de invariância falha — como deve.

## Ressalvas honestas (fora do escopo do risco nº 1, registradas)

1. **Docstring imprecisa** (cosmético): o cabeçalho diz "forward-backward (Viterbi)"
   — forward-backward e Viterbi são algoritmos distintos; a intenção (ambos olham o
   futuro) está certa, o nome não. Corrigir quando tocar o arquivo.
2. **Look-ahead ≠ único viés**: esta auditoria fecha decodificação/scaler/split.
   Seleção de hiperparâmetros (nº de estados, features de emissão) e múltiplos
   testes seguem cobertos por outro mecanismo (DSR + trials.json).
3. Execução: suíte leve (py 3.14) roda invariância com engine sintético (hmmlearn
   é skip); a `.venv_v3` roda o ciclo completo com Baum-Welch. Ambos verdes em
   2026-07-02.

**Consequência**: o Risco nº 1 da matriz passa de "Alta prob. / Crítico" para
**fechado para a decodificação do RegimeEngine** — vereditos do walk-forward da V3
não estão invalidados por look-ahead de regime.


