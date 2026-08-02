# ADR-014 — Modelo Bitemporal (timestamp × published_at × vintage)

**Status:** Aceita · **Data:** 2026-06-30 · **Origem:** auditoria arquitetural (C-05).

## Contexto

O ativo arquitetural mais valioso da DPL emergiu de forma quase implícita ao longo das
Fases 2–4: a plataforma rastreia **três tempos distintos** para cada dado. Sem nomeá-los
e protegê-los explicitamente, um mantenedor futuro pode colapsá-los e reintroduzir
*lookahead bias* silencioso — o pior tipo de bug num sistema de backtesting, porque não
quebra nada: apenas torna os resultados otimisticamente falsos.

Este ADR torna o modelo **explícito, nomeado e auditável**.

## Decisão

Todo dado na DPL carrega até três instantes temporais, com papéis rígidos e distintos:

| Tempo | Campo | Pergunta que responde | Papel |
|-------|-------|----------------------|-------|
| **Tempo do evento** | `timestamp` | *Quando o fato ocorreu?* (candle, mês de referência do IPCA, kickoff) | Define a grade do as-of join e o cálculo de `max_staleness`. |
| **Tempo de disponibilidade** | `published_at` | *Quando o fato se tornou público?* | **Governa o anti-lookahead.** Um dado só pode entrar numa observação se `published_at <= momento_da_decisão`. |
| **Tempo de transação** | `vintage` | *Quando nós coletamos/gravamos este valor?* | Distingue **revisões**: o mesmo `(fonte, série, timestamp)` pode ter múltiplos valores coletados em momentos diferentes (ex.: IPCA revisado). |

Isto é, formalmente, um **modelo bitemporal** (valid-time × transaction-time) com um
terceiro eixo de disponibilidade pública — mais rico que o bitemporal clássico de bancos
de dados, porque separa "quando ficou público" de "quando coletamos".

### Invariantes (NÃO NEGOCIÁVEIS)

1. `published_at >= timestamp` sempre (validado em `MarketDataPoint` e `SignalPoint`).
2. O alinhamento (`AlignmentEngine`, `EventAlignmentEngine`, agregação) **só** filtra
   por `published_at` contra o instante de decisão — **nunca** por `timestamp`.
3. Revisões são **pontos separados** com `published_at` próprio. O as-of por
   `published_at` então escolhe automaticamente o vintage vigente em cada data — sem
   lógica especial. *(Foi a descoberta que simplificou a Fase 4: ADR-008.)*
4. A agregação multi-fonte usa `published_at = max` entre as fontes (o consolidado só
   "existe" quando a última fonte publicou).
5. NUNCA usar o "valor mais recente" (último vintage) num backtest em data T — usar o
   vintage cujo `published_at <= T`.

## Exemplo (point-in-time correto)

IPCA de março: divulgado em 10/abr (v1=0,40), revisado em 15/mai (v2=0,43).

```
SignalPoint(name=ipca, timestamp=31/mar, value=0.40, published_at=10/abr, vintage=t1)
SignalPoint(name=ipca, timestamp=31/mar, value=0.43, published_at=15/mai, vintage=t2)
```

- Backtest em **20/abr** → as-of `published_at <= 20/abr` ⇒ v1 (0,40). Correto: a revisão
  ainda não existia.
- Backtest em **20/mai** → ⇒ v2 (0,43).

Usar 0,43 no backtest de 20/abr seria lookahead — invisível sem este modelo.

## Alternativas consideradas

- **Um único timestamp** (colapsar os três): simples, mas reintroduz lookahead e impede
  reprodutibilidade point-in-time. **Rejeitada.**
- **Bitemporal sem `published_at`** (só valid+transaction time): não distingue "ocorreu"
  de "ficou público" — insuficiente para mercados onde há defasagem de divulgação.
  **Rejeitada.**
- **Tabela de revisões separada**: mais "limpa" no papel, mas o as-of por `published_at`
  já resolve com pontos separados — abstração desnecessária. **Rejeitada (YAGNI).**

## Consequências

- **Positivas:** anti-lookahead estrutural; reprodutibilidade point-in-time; revisões
  tratadas sem código especial; o mesmo modelo serve séries (cripto/ações) e eventos
  (futebol).
- **Negativas / riscos:** o modelo é sutil; exige disciplina. **Mitigação:** este ADR +
  testes que falham se o alinhamento usar `timestamp` em vez de `published_at`
  (`test_alignment_point_in_time_*`, `test_event_align_*`).
- **Impacto futuro:** qualquer novo domínio/fonte DEVE preencher `published_at`
  corretamente (lag de divulgação real). Calibração errada de lag é o risco residual
  (ver auditoria B-1, ADR-011).

## Relacionadas

[[ADR-003]] (forward-fill + published_at), [[ADR-008]] (vintage), [[ADR-011]] (lag de
publicação), [[ADR-012]] (event-asof). Ver também [DPL_FASES_4_5.md](DPL_FASES_4_5.md)
e a auditoria [AUDITORIA_DPL.md](AUDITORIA_DPL.md) (C-05).


