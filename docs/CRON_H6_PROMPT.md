# Prompt do cron de acompanhamento da H6 — cópia de referência

> **Esta NÃO é a fonte viva.** O prompt que roda de verdade mora num campo de UI
> (a rotina **"Watch H6 n>=30 (cripto-predictor)"**, `trig_01HFK2HztoqoLR8dcAtUPA6G`,
> segundas 12:00 UTC). Este arquivo existe porque um texto que só vive em UI é
> exatamente a categoria de coisa que se perde ou envelhece em silêncio — o mesmo
> problema que o `h6_status.json` foi criado para resolver do lado do `n`.
>
> **O custo desta cópia, declarado:** passam a existir duas verdades, e elas podem
> divergir. A convenção é: **a UI manda**. Se você editar o prompt na UI, atualize
> este arquivo no mesmo dia; se encontrar divergência, a UI está certa e este
> arquivo está velho.

## Por que o prompt precisou mudar

O prompt original mandava procurar o `n` da H6 em `trials.json` e
`docs/HYPOTHESES.md` — ou seja, em números escritos à mão. Desde o PR #40 existe
`GarimpoInvestimentos/h6_status.json`, gerado pelo `quality_snapshot` na máquina de
coleta: a ponte produção → git. O prompt abaixo troca a fonte autoritativa para
esse artefato, com fallback para o comportamento antigo enquanto ele não existir.

## Ordem de ativação

1. Cole o prompt abaixo na rotina, substituindo o texto inteiro.
2. Na máquina de coleta, rode `uv run python -m GarimpoInvestimentos.quality_snapshot`
   e **commite** o `GarimpoInvestimentos/h6_status.json` que ele gerar.

A ordem entre os dois não é crítica: se o cron disparar antes de o arquivo existir,
ele cai no fallback e conclui em silêncio — que é o comportamento correto.

## O prompt

```
Checagem semanal do n da H6 em leonardosovienski/cripto-predictor (trial
h6-sinal-invertido-d7, critério pré-registrado em docs/HYPOTHESES.md: Spearman IC95
sobre a leitura invertida do score, n>=30, calculado por h6_spearman_verdict em
GarimpoInvestimentos/analyzers/backtest.py).

LIMITE DESTE AMBIENTE, que define todo o resto: você NÃO tem o feature_store.db nem
acesso à máquina de coleta. O n real é calculado lá. Você só enxerga o que está
commitado no git. Nunca estime, infira ou "atualize" o n por conta própria.

FONTE AUTORITATIVA: GarimpoInvestimentos/h6_status.json. É um artefato versionado,
gerado pelo quality_snapshot na máquina de coleta e commitado à mão quando o estado
muda — é a ponte produção->git. Campos: trial, observed_at (quando ESTE estado foi
visto pela primeira vez), n, gate, gate_atingido, fonte_esperada, rho, ic_lower,
ic_upper, veredito, poder, predictive_verdict, economic_verdict,
cost_model_status e capital_authorized. `economic_verdict=NOT_EVALUATED` indica
que o gate mede associação preditiva bruta, não rentabilidade líquida negociável.

Como checar (dar fetch no main do repo, já anexado nesta sessão):
1. Se GarimpoInvestimentos/h6_status.json existir, ele manda. Compare com o que você
   reportou na última checagem.
2. Se ainda NÃO existir, caia para trials.json e docs/HYPOTHESES.md (padrão
   "n=X de 30"), como antes. A ausência do arquivo não é problema a reportar:
   significa apenas que o painel ainda não foi rodado e commitado desde que o
   artefato passou a existir.

Quando NOTIFICAR o usuário:
- gate_atingido == true, ou um veredito publicado: avise citando os números exatos do
  arquivo (n, rho, IC95, predictive_verdict) e lembre que Sharpe isolado ainda
  precisa passar pelo desconto do DSR. Nunca apresente `predictive_verdict` como
  viabilidade econômica quando `economic_verdict=NOT_EVALUATED`. NENHUM gate deste
  ecossistema autoriza capital.
- n mudou de forma relevante desde a última checagem (ex.: cruzou metade do gate):
  uma linha, sem alarde.

Quando NÃO notificar (concluir em silêncio): n inalterado; arquivo ausente; apenas
observed_at diferente sem mudança de n.

NÃO faça: não edite docs/HYPOTHESES.md, trials.json, charters/ nem h6_status.json —
o n só nasce na máquina de coleta, e esses são artefatos de governança. Não abra PR.
Se notar que h6_status.json está muito defasado em relação a trials.json (ex.:
trials.json com sharpe novo e o status parado), reporte a divergência ao usuário em
vez de tentar corrigi-la.
```

## Uma leitura que o prompt deliberadamente NÃO faz

Ele avisa quando `gate_atingido == true`, e para por aí. **Ele não declara a H6
resolvida** — e não deve. O poder do gate em `n=30` é de 14,7% para um efeito real
de rho=0,2 (B12 em `docs/HYPOTHESES.md`), então o primeiro veredito é
subdimensionado. A qualificação dessa leitura é trabalho humano, com a §7 do
`OVERVIEW_E_ROADMAP_2026-08-21.md` na mão — não do cron.

## Campos do artefato, conferidos no código

`h6_status_payload()` em `GarimpoInvestimentos/quality_snapshot.py` emite os quinze
campos citados no prompt. `rho`, `ic_lower`, `ic_upper` e `veredito` são
`null` enquanto `n < gate`: `h6_spearman_verdict` devolve `None` de propósito abaixo
do gate, para não expor correlação prematura como se fosse sinal. O payload preserva
esse silêncio em vez de contorná-lo — se você vir `rho: null`, é a trava funcionando,
não dado faltando.
