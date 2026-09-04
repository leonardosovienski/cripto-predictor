# Arquitetura Consolidada — GarimpoInvestimentos + DPL

> ## ⚠️ ERRATA 2026-08-21
>
> Retrato de 2026-07-01/02, preservado sem reescrita. Superados desde então: o
> "**Estado das branches**" do §1 e o "merge pendente de aprovação" do §2 (tudo está
> na `main`; nenhuma daquelas branches existe), a proveniência "sem hash de conteúdo"
> do §4 (fechada pela migração `_0012_provenance_content_hash`) e o risco 5 do §6
> quanto à promoção ao core (C-02, fechada). A nota 6,0/10 do §5 e o veredito NO-GO
> do §7 continuam válidos.
>
> Índice: [ERRATA_2026-08-21.md](ERRATA_2026-08-21.md).

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

**Atualização pós-merge (2026-07-02):** passo 2 ✅ **feito e aprovado** (`e8b2fa3`, 102
verdes, smoke ao vivo com carimbo `Fonte`). Novo pré-requisito **2b** (condição da
auditoria antes de qualquer feature nova): DSR + `trials.json` — ✅ **feito**
(`analyzers/trials.py`, candidato a promoção ao core; registro semeado com as
tentativas v1-direct e v2-dpl; fio no backtest com corte 0.95). Passo 3 em execução.

**Atualização passos 4-5 (2026-07-02, mesmo dia):**
- Passo 3 ✅ **feito** (`6416a71`): indicadores bit-idênticos (bitcoin/kaspa/aave) em
  candles fechados; `change_*` diverge 0,1–7,8pp (semântico) → estratificação obrigatória.
- Passo 4 ✅ **feito** (`c6529a0` + plano de reconciliação `08c2dd3`): Feature Store é o
  histórico OFICIAL (migração 0006 `predictions`, PK ativo+ts); CSV legado absorvido
  idempotentemente (fonte vazia → `direct`, arquivo congelado); backtest lê da store e
  **estratifica por Fonte**; 117 verdes; smoke real (3 linhas absorvidas).
- V3 **resgatada** (`claude/v3-quant-wip` @ `3507809` — estava não-commitada no checkout
  de main) e evoluída lá: auditoria de look-ahead do HMM ✅ (`0b35566`, Risco 1 fechado,
  ver [AUDITORIA_HMM.md](AUDITORIA_HMM.md)) + modelo de custos ✅ (`1beea4e`, Risco 4:
  taker+slippage round-trip e funding real; gate GO/NO-GO agora opera sobre líquido).
- `trials.json`: 4 tentativas registradas (v1-direct, v2-dpl, v3-fr90, v3-fr21).
- Passo 5.3 (veredito com custos + DSR): re-execução do WFA de BTC/ETH em andamento —
  resultado na seção 7. **Achado da telemetria:** o GO histórico de BTC (2026-06-27,
  PSR 0,909) era PRÉ-custos e pós kelly-sweep (4 avaliações no gate de DD) — o veredito
  que vale é o líquido, deflacionado.

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

## 5. Nota consolidada: **6,0/10** (revisada em 2026-07-02; era 5,5)

| Dimensão | Nota | Observação |
|----------|------|------------|
| Engenharia de dados | 8,0 | Bitemporal + anti-lookahead testado; histórico oficial na store; proveniência parcial |
| Engenharia de software | 7,5 | 117 verdes (principal) + 87 (V3); telemetria; smokes reais |
| Arquitetura | 7,0 | Camadas claras; reconciliação V3 planejada; DPL ainda no domínio (ADR-002) |
| Validação estatística | 7,0 | Governança completa (controle positivo + DSR + look-ahead auditado + custos); edge NÃO demonstrado — e agora o NO-GO é confiável |
| Gestão de risco | 5,0 | Custos modelados; gates duros (PSR/IC/DD líquidos); faltam sizing e kill-switch de produção |

A nota sobe pela **qualidade da resposta**, não pelo resultado: o sistema agora
responde "não há edge" com validação em que se pode confiar.

## 6. Riscos da auditoria original — estado final

1. ~~Look-ahead no HMM~~ → **FECHADO** (`0b35566`, [AUDITORIA_HMM.md](AUDITORIA_HMM.md)):
   decodificação causal comprovada em 4 camadas + teste de invariância com contraprova.
2. ~~Falta de controle positivo~~ → **FECHADO** (`e00e776`): pipeline detecta edge
   sintético e rejeita ruído AR(1); re-executado verde em 2026-07-02.
3. ~~Múltiplos testes sem correção~~ → **FECHADO** (`ab346d3`): DSR + `trials.json`
   (4 tentativas). Regra: nenhuma config nova sem registrar a tentativa.
4. ~~Custos não modelados~~ → **FECHADO** (`1beea4e`): fricção round-trip + funding
   real; **e o fechamento foi decisivo** — ver seção 7.
5. Herdados da DPL: ~~consenso nunca fundiu dado real (C-03)~~, ~~equivalência
   pendente p/ ETH/SOL (429)~~ — ambos fechados em 2026-09-04 com dado real, ver
   `docs/RELATORIO_FINAL.md` §10.2. Ainda abertos: promoção ao core (C-02),
   proveniência com hash (ADR-015).

## 7. Veredito do passo 5.3 (2026-07-02): **NO-GO — e é o primeiro veredito confiável**

WFA da V3 (walk-forward IS/OOS, HMM causal auditado, **líquido de custos**:
taker 10bps + slippage 5bps por perna + funding real da janela):

| Métrica | BTCUSDT (n=3.958 OOS, 44 folds) | ETHUSDT |
|---|---|---|
| Retorno médio/sinal | bruto **+0,44bps** → líquido **−0,09bps** | bruto −0,70bps → líquido −1,11bps |
| IC95 do líquido médio | [−1,61; +1,43]bps — cruza zero | [−2,64; +0,26]bps — cruza zero |
| PSR (líquido) | 0,445 | 0,051 |
| DSR (N=4 tentativas) | **≤ 0,445** (corte: 0,95) | ≪ 0,45 |
| IC Spearman (sinal, IC95 lo) | −0,086 | −0,353 |
| MaxDD | 29,0% | 27,0% |
| **Veredito** | **NO-GO** | **NO-GO** |

Leitura: **os custos comem o edge inteiro** (+0,44bps brutos vs ~0,53bps de custo por
sinal no BTC). PSR/Spearman são invariantes à fração de Kelly → **nenhum sizing salva**.
O "GO" histórico de 27/06 (PSR 0,909, kelly-sweep) era artefato de backtest sem custos.
O que dá confiança ao NO-GO: controle positivo verde (o pipeline TEM poder), HMM sem
look-ahead, DSR contando as tentativas, dados point-in-time. **Consequência: a hipótese
funding/OI + HMM, como formulada, está fechada. Produção assistida NÃO autorizada.**
Próximos passos: pivot de pesquisa (novas hipóteses nascem registradas no trials.json
e avaliadas líquidas) + coleta diária do pipeline LLM até o backtest ter n.


