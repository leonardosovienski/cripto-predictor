# Arquitetura Consolidada — GarimpoInvestimentos + DPL

> Estado em 2026-07-01, após o ciclo de auditoria e as 5 tarefas de consolidação.
> Fontes: auditoria externa (conversa), [AUDITORIA_DPL.md](AUDITORIA_DPL.md) (interna),
> [DECISAO_MERGE_DPL_DISCOVERY.md](DECISAO_MERGE_DPL_DISCOVERY.md) (ADR do merge).

## 1. Os dois subsistemas e como se relacionam

**GarimpoInvestimentos** (previsão): descoberta de candidatos (`--discover`, momentum +
trending com filtros de stable/wrapped/liquidez) → análise (LLM + indicadores → score
0-100 com carimbo do juiz e flag de divergência) → histórico → **backtest com pedágio
estatístico** (Spearman + IC95% via block bootstrap pareado; veredito validado/RUÍDO).

**DPL** (dados): contratos `DataProvider`/`MarketDataPoint` → providers (Binance,
CoinGecko, Kraken, Fear&Greed) → routers (fallback sequencial | consenso por mediana)
com Circuit Breaker → **Feature Store bitemporal** (SQLite; `timestamp × published_at ×
vintage`; as-of join anti-lookahead) → serving offline.

**Relação:** a DPL é a camada de dados sobre a qual o Garimpo passa a operar
(ingestão separada de análise). O plano de junção está no ADR do merge (D1-D3):
discovery escolhe **o que** analisar; DPL fornece **os dados**; o carimbo `Fonte`
protege o backtest da troca de fonte no meio da série.

**Estado das branches:** `claude/clever-mclean-16f6d8` = DPL Fases 1-3 completas
(+ Fases 4-5 de ações/futebol, fora deste escopo) · `claude/frosty-goldstine-1092c9` =
`--discover` (`799cd27`) + controle positivo (`e00e776`). **Merge pendente de aprovação
do ADR.**

## 2. Plano de 5 passos (atualizado)

| # | Passo | Estado |
|---|-------|--------|
| 1 | Migration 0002 aditiva (C-04) | ✅ **Feito** — migração 0005 + teste de preservação (`789f568`/`9a06a22`) |
| 2 | Merge DPL + discovery com carimbo `Fonte` | ADR escrito (`a9465aa`); **aguarda aprovação**; carimbo no mesmo PR do merge |
| 3 | Equivalência DPL vs. coleta direta | Pendente — ampliar de 1 ativo × 1 instante para N ativos × janela (C-08); atenção ao `change_*` (dia-calendário vs rolling 24h) |
| 4 | Trocar CSV → Feature Store como histórico oficial | Pendente — **só após** passos 2-3; backtest estratifica por `Fonte` na transição |
| 5 | Validação estatística do edge | Controle positivo ✅ **feito** (`e00e776`); restam: auditoria de look-ahead do HMM, Deflated Sharpe, modelo de custos |

## 3. Registro de atribuição (correção do histórico)

- **`--discover`**: implementado pelo assistente de arquitetura (esta linha de sessões),
  a pedido do Leo, com os alertas de viés documentados no código e no commit.
- **DPL (Fases 1-5)**: desenvolvida na branch própria sob direção do Leo (commits
  assinados Claude Opus 4.8); **revelada** ao auditor externo após a auditoria original.
- **Verificação independente da DPL**: executada pelo auditor externo (esta sessão) —
  suíte re-executada, smokes ao vivo reproduzidos (fallback, ingestão de 200 candles,
  degradação do consenso), evidências conferidas no git.

## 4. Formulações precisas (linguagem oficial do projeto)

- O discovery **"torna a seleção de universo sistemática e auditável, com edge ainda
  não medido"** — ele gera candidatos; quem valida é o backtest.
- A Feature Store é **"bitemporal com proveniência parcial"** — `ingestion_provenance`
  existe, mas sem hash de conteúdo nem `code_version` populado; reprodutibilidade
  bit-a-bit ainda não é garantida (ADR-015 pendente).

## 5. Nota consolidada: **5,5/10**

| Dimensão | Nota | Observação |
|----------|------|------------|
| Engenharia de dados | 8,0 | Bitemporal + anti-lookahead testado; proveniência parcial |
| Engenharia de software | 7,5 | 85 verdes (DPL) + 39 verdes (Garimpo); telemetria; smokes reais |
| Arquitetura | 7,0 | Camadas claras (coleta/seleção/análise/validação); DPL ainda no domínio (ADR-002 pendente) |
| Validação estatística | 5,0 | Controle positivo fecha a infalsificabilidade; edge segue não demonstrado |
| Gestão de risco | 3,0 | Custos e position sizing ausentes |

## 6. Riscos ainda vivos

1. **Look-ahead no HMM** (repo v2, não auditável daqui): decodificação deve ser filtrada,
   nunca suavizada full-sample — sem prova disso, nenhum walk-forward de lá é interpretável.
2. ~~Falta de controle positivo~~ → **fechado** por `e00e776`: pipeline comprovadamente
   detecta edge sintético (validado, IC>0) e rejeita ruído AR(1) (RUÍDO). Sem essa suíte
   verde, nenhum veredito do backtest é interpretável.
3. **Múltiplos testes sem correção**: cada ativo/configuração testada é uma tentativa;
   falta Deflated Sharpe Ratio + registro de tentativas (`trials`) no pedágio.
4. **Custos não modelados**: taxas, funding e slippage ausentes de qualquer veredito;
   edge bruto ≠ edge líquido.
5. Herdados da auditoria interna da DPL: consenso nunca fundiu dado real (C-03),
   equivalência em amostra mínima (C-08), promoção ao core pendente (C-02).
