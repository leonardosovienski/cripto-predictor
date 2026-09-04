# Auditoria Arquitetural Independente — Plataforma DPL (Fases 0–5)

> ## ⚠️ ERRATA 2026-08-21
>
> Auditoria de jun/jul-2026, preservada sem reescrita. A branch avaliada
> (`claude/clever-mclean-16f6d8`) não existe mais — o código está na `main`, em
> `GarimpoInvestimentos/dpl/`. Dos achados: **C-02 (promoção ao core) fechou** — os
> contratos, routers e circuit breaker vivem em `predictor_core` e o que restou aqui
> são compat shims; a proveniência ganhou hash de conteúdo (migração `_0012`). A
> crítica central da §8 — "maturidade superestimada pelo número de testes verdes;
> testes provam consistência interna, não correção contra o mundo real" — segue de pé
> e é uma das razões pelas quais o projeto não autoriza capital.
>
> Índice: [ERRATA_2026-08-21.md](ERRATA_2026-08-21.md).

> Auditor externo (não participou da construção). Base: estado real do repositório na
> branch `claude/clever-mclean-16f6d8` + histórico da conversa. Postura: crítica, não
> laudatória. Inferências marcadas como **[INFERÊNCIA]**.

> **Correção factual de partida [OBR]:** o briefing diz que Fases 4–5 são "código não
> iniciado / só especificação". **Falso à data desta auditoria** — o commit `c38c4cb`
> implementa COTAHIST/BCB/StocksDataProvider (F4) e EntityMapper/EventAlignmentEngine/
> Martj42 + stubs (F5), com 74 testes verdes. A auditoria avalia o código real, não o
> briefing. Isso por si só é uma **constatação**: documentação de status divergindo do
> repositório (ver §8, C-01).

---

## 1. Avaliação fase por fase

Notas 0–10 por dimensão. Justificativas curtas. Risco remanescente em Baixo/Médio/Alto.

### Fase 0 — Limpeza e Estabilização do Core
| Dim | Nota | Justificativa |
|-----|------|---------------|
| Arquitetura | 7 | Princípio correto (core testado antes de propagar), mas é pré-condição, não entrega. |
| Implementação | 3 | **Não executada** no escopo desta branch; commits redteam seguem fora do core. Não há evidência de `test_version.py`/smoke cross-vendor rodando aqui. |
| Testabilidade | 4 | Dependente de um repo (`predictor_core`) que não está nesta árvore. Inauditável daqui. |
| Escalabilidade | 6 | N/A direto. |
| Manutenibilidade | 5 | Drift core↔vendados continua um risco aberto. |
| Observabilidade | 6 | `obs` existe e é usado pelos domínios. |
| **Risco** | — | **Alto** — a base canônica permanece parcialmente não verificada; toda a DPL nasceu no domínio justamente porque o core não estava pronto. |

### Fase 1 — Piloto DPL (redundância cripto)
| Dim | Nota | Justificativa |
|-----|------|---------------|
| Arquitetura | 9 | Ports & Adapters limpo: `DataProvider` (porta) + conectores (adapters) + fachada. Contrato mínimo. |
| Implementação | 9 | CCXT encapsulado, fallback sequencial coerente com restrição de TLS. |
| Testabilidade | 9 | 35 testes, fakes injetáveis, async sem plugin. Smoke ao vivo real (fallback exercido). |
| Escalabilidade | 8 | Adicionar fonte = 1 adapter. |
| Manutenibilidade | 8 | Boa coesão; `sources.json` como ponto único. |
| Observabilidade | 8 | Telemetria `data.fallback`/`unavailable`. |
| **Risco** | — | **Baixo**. |

### Fase 2 — Feature Store + Alignment Engine
| Dim | Nota | Justificativa |
|-----|------|---------------|
| Arquitetura | 9 | Separação ingestão/serving materializada; anti-lookahead via `published_at`. Decisão de não alargar `MarketDataPoint` (features derivadas no domínio) é madura. |
| Implementação | 8 | SQLite/WAL reusando `infra`; formato longo extensível. `to_hard_data` reconstrói o contrato sem poluí-lo. |
| Testabilidade | 9 | 48 testes; anti-lookahead e NaN-por-staleness testados; equivalência live (score 25.0). |
| Escalabilidade | 7 | Formato longo é flexível mas custa em leitura (pivot em memória); ok no volume atual. |
| Manutenibilidade | 8 | Migrações idempotentes. |
| Observabilidade | 8 | `data.ingested`/`materialized`. |
| **Risco** | — | **Baixo-Médio** — equivalência validada num único ativo/instante (BTC). Amostra pequena. |

### Fase 3 — Agregação + Circuit Breaker
| Dim | Nota | Justificativa |
|-----|------|---------------|
| Arquitetura | 8 | `CCXTProvider` base (DRY), agregação preserva `published_at`=máximo (anti-lookahead correto). Dois routers com responsabilidades claras. |
| Implementação | 8 | `asyncio.gather` com tolerância a falha parcial; breaker com relógio injetável. |
| Testabilidade | 9 | 58 testes; outlier, falha parcial/total, ciclo do breaker. |
| Escalabilidade | 7 | Breaker em memória/instância limita ingestão concorrente (reconhecido). |
| Manutenibilidade | 7 | `twap` semanticamente ambíguo (time-weighted de série ≠ consenso cross-source) — risco de confusão de uso. |
| Observabilidade | 8 | `data.aggregated`, `circuit.*`. |
| **Risco** | — | **Médio** — a agregação **nunca rodou ao vivo com sucesso** (Binance+Kraken bloqueadas); só caminho de falha validado live. Fusão provada só offline. |

### Fase 4 — Ações (implementada, não validada com dado real)
| Dim | Nota | Justificativa |
|-----|------|---------------|
| Arquitetura | 9 | **Achado forte**: point-in-time sem mudar o `AlignmentEngine` (revisão = `SignalPoint` com `published_at` próprio). Reuso de `SignalPoint` em vez de novo tipo. Proveniência adicionada. |
| Implementação | 7 | Parser COTAHIST e BCB completos, mas **inéditos contra dados reais**; offsets/escala do COTAHIST são uma fonte clássica de erro. |
| Testabilidade | 8 | 16 testes; fixture sintética COTAHIST, BCB mockado, revisão IPCA point-in-time. **Mas** golden de arquivo real ausente. |
| Escalabilidade | 8 | StocksDataProvider reusa Router/ingestão genérica. |
| Manutenibilidade | 8 | Reuso máximo; pouca duplicação. |
| Observabilidade | 7 | Herdada; falta evento de "revisão detectada" (`data.signal_revised` foi desenhado, não implementado). |
| **Risco** | — | **Médio-Alto** — risco concentrado no parser COTAHIST (layout) e na calibração de `publish_lag` do BCB. Sem validação com arquivo real, é uma promessa testada contra si mesma. |

### Fase 5 — Futebol (scaffolding, domínio PARKED)
| Dim | Nota | Justificativa |
|-----|------|---------------|
| Arquitetura | 8 | `EventAlignmentEngine` separado do engine de séries (correto). `EntityMapper` com curadoria obrigatória endereça o pior bug do domínio. |
| Implementação | 6 | Só `Martj42` (CSV) e `EntityMapper` reais; Sofascore/FBref/Odds/Weather são stubs `NotImplementedError`. Honesto, mas é esqueleto. |
| Testabilidade | 7 | 7 testes (mapper, event-asof, martj42). Cobertura boa do que existe. |
| Escalabilidade | 7 | Contrato `MatchDataProvider` plugável. |
| Manutenibilidade | 7 | Limpo, mas a maior parte do valor (estatísticas/odds) ainda não existe. |
| Observabilidade | 5 | Mapper não emite telemetria de `UNMAPPED` (deveria). |
| **Risco** | — | **Médio** — desenho sólido; risco real só aparece quando as fontes de rede forem implementadas (scraping frágil, mapeamento em escala). |

---

## 2. Visão global da evolução

- **Consistência:** alta. Todas as fases respeitam o mesmo eixo (contrato → adapter → router → store → serving) e o anti-lookahead via `published_at` atravessa todas. **[INFERÊNCIA]** a consistência sugere um único arquiteto/linha de raciocínio, o que é bom para coerência e ruim para *bus factor* (ver §7).
- **Mudanças de direção:** duas, ambas justificadas e aditivas: (a) fallback sequencial → agregação concorrente (F1→F3); (b) acesso direto a API → serving offline da Feature Store (F2). Nenhuma reescrita destrutiva.
- **Decisões que envelheceram mal:** poucas. A mais questionável é o **formato longo** de `features_aligned` — elegante para extensibilidade, mas o serving faz pivot em memória; em futebol event-level pode escalar mal. Ainda não dói, mas é candidato a revisita (ver ADRs).
- **Refazer?** Nada exige refação. A Fase 0 deveria ser *fechada* (não refeita). A equivalência da Fase 2 deveria ser *ampliada* (mais ativos/datas).
- **Incremental vs saltos:** majoritariamente incremental. O único salto de complexidade real é a Fase 4+5 entregues juntas num commit — muito código de uma vez, parte dele não exercível no ambiente. Isso reduz a confiança proporcionalmente ao volume.

---

## 3. Arquitetura emergente

Padrões que **de fato** se manifestaram (com evidência):

| Padrão | Manifestação |
|--------|-------------|
| **Ports & Adapters (Hexagonal)** | `DataProvider`/`SignalProvider`/`MatchDataProvider` são portas; conectores são adapters; domínio fala só com a fachada. |
| **Feature Store / Offline-first** | `--ingest` (write) vs serving (read); pipeline 100% offline para análise. |
| **Event-time / Bitemporalidade** | `timestamp` (evento) vs `published_at` (disponibilidade) vs `vintage` (coleta) — três tempos. Isto é **bitemporal de fato** (tempo de validade × tempo de transação), padrão sofisticado e correto para backtesting. |
| **CQRS leve** | Escrita (ingestão) e leitura (serving) fisicamente separadas, modelos distintos (`raw_*` vs `features_aligned`). |
| **Circuit Breaker / Bulkhead parcial** | Breaker por fonte; falha de uma não derruba a agregação. |
| **Strategy** | Políticas de router (fallback/consensus) e de agregação (median/mean/twap) plugáveis. |
| **Hub-and-Spoke** | Intencional, ainda **não realizado**: a DPL está no domínio cripto, não no core. É aspiração, não fato (ver §6). |

**Observação crítica:** o padrão bitemporal (§ event-time) emergiu de forma quase acidental na Fase 4 e é o ativo arquitetural mais valioso da plataforma — mas não está nomeado nem documentado como tal. Risco de erosão por desconhecimento.

---

## 4. Revisão dos ADRs (001–013)

| ADR | Veredito | Comentário / gatilho de reabertura |
|-----|----------|-----------------------------------|
| 001 Hub-and-spoke + vendoring | **Válida** | Mantida pela restrição corporativa. |
| 002 DPL no core | **A revisitar** | A DPL **está no domínio**, não no core. ADR descreve um alvo ainda não atingido. Gatilho: promoção (ADR-009). |
| 003 Forward-fill + published_at | **Válida e reforçada** | Sobreviveu a 5 fases; base do anti-lookahead. |
| 004 Circuit Breaker | **Válida com ressalva** | Em memória/instância. Gatilho de reabertura: ingestão multi-processo. |
| 005 Feature Store local | **Válida** | SQLite atende. |
| 006 CCXT | **Válida** | DRY confirmado com Kraken. |
| 007 SignalPoint p/ macro | **Válida** | Reuso correto. |
| 008 Vintage/point-in-time | **Válida e superada para melhor** | A implementação descobriu que o as-of por `published_at` já resolve — **mais simples que a ADR**. A ADR deveria ser *atualizada* para refletir que não houve mudança no engine. |
| 009 Promover ao core pós-F4 | **Pendente / em risco** | F4 está implementada mas no domínio; a promoção não ocorreu. Gatilho: agora. |
| 010 SQLite, não Parquet | **Válida** | YAGNI correto. Gatilho: futebol event-level. |
| 011 published_at por lag configurável | **Válida, não validada** | Lag do BCB/COTAHIST nunca calibrado contra realidade. |
| 012 event-asof | **Válida** | Implementada como classe separada, como previsto. |
| 013 EntityMapper curadoria | **Válida** | Implementada; falta telemetria de UNMAPPED. |

**ADRs faltantes que deveriam existir [OBR]:**
- **ADR-014 — Modelo bitemporal explícito** (timestamp × published_at × vintage): nomear e proteger o padrão mais valioso.
- **ADR-015 — Estratégia de versionamento de dataset/feature/código** (reprodutibilidade exige hash de dados+código; hoje só há `ingestion_provenance` parcial).
- **ADR-016 — Contrato de testes do parser COTAHIST** (golden file real obrigatório antes de produção).
- **ADR-017 — Política de evolução de schema da Feature Store** (migração modificou a migration 0002 in-place — ver C-04).

---

## 5. Maturidade

| Escopo | Nível | Justificativa |
|--------|-------|---------------|
| Fase 0 | Experimental | Não fechada; base canônica parcialmente não verificada. |
| Fase 1 | **Maduro** | Testado, validado live, padrão estabelecido. |
| Fase 2 | **Estável→Maduro** | Sólida; equivalência validada em amostra pequena. |
| Fase 3 | **Estável** | Lógica testada; agregação não validada live. |
| Fase 4 | **Experimental→Estável** | Código completo, sem validação com dado real. |
| Fase 5 | **Experimental** | Scaffolding; metade são stubs. |
| **Plataforma (todo)** | **Estável, NÃO "Plataforma"** | Para ser "Plataforma" (reutilizável por novos domínios) faltam: promoção ao core, 2º domínio rodando de fato, e documentação do contrato bitemporal. Hoje é uma DPL **monodomínio madura com extensões não validadas**. |

---

## 6. Lacunas, débitos e riscos técnicos

- **Planejado e não feito:** Fase 0 (core testado/commitado); promoção da DPL ao core; validação live de agregação e de stocks; `data.signal_revised`; dashboard de telemetria.
- **Débitos técnicos:**
  - Migration `0002_raw_signals` foi **modificada in-place** (mudança de PK) — quebra a premissa de idempotência para qualquer DB já existente; só funciona porque os DBs são descartáveis. **Risco se houver dado durável.**
  - `twap` cross-source vs série: ambiguidade semântica não resolvida.
  - Serving faz pivot em memória (formato longo) — não escala para event-level.
  - `.env` copiado para o worktree (segredo duplicado, ainda que gitignored).
- **O que pode quebrar nas Fases 4/5 "como desenhadas":**
  - COTAHIST: offsets/escala errados → preços silenciosamente errados (alto impacto, sem golden real).
  - BCB: `publish_lag` mal calibrado → lookahead ou atraso; revisões podem chegar com `published_at` que o modelo bitemporal não captura se a API não expõe a data de revisão real (**[INFERÊNCIA]**: assumi que `published_at = ref + lag` aproxima a divulgação; a data real de revisão do BCB pode diferir).
  - Futebol: scraping frágil; `EntityMapper` em escala exige curadoria massiva.
- **Dependências externas:** CCXT/exchanges (bloqueadas no ambiente), SGS/BCB, arquivo COTAHIST, fontes esportivas. Nenhuma validada de ponta a ponta aqui.

---

## 7. Riscos estratégicos

| Risco | Avaliação |
|-------|-----------|
| **Adoção por outros domínios** | Médio-Alto. A DPL ainda vive em `GarimpoInvestimentos/dpl/`. Um novo domínio teria que importar de um domínio cripto — quebra a narrativa hub-and-spoke. Promoção ao core é pré-requisito de adoção. |
| **Manutenção a longo prazo** | Médio. Bitemporalidade e anti-lookahead são sutis; sem documentação nomeada, um mantenedor novo pode introduzir lookahead sem perceber. |
| **Evolução (ex.: renda fixa)** | Baixo-Médio. Renda fixa (curvas, marcação a mercado, feriados) provavelmente cabe no `SignalPoint`+series-asof; o modelo bitemporal ajuda. Mas curvas (term structure) podem precisar de um 3º contrato. |
| **Acoplamento organizacional** | **Alto**. **[INFERÊNCIA]** Toda a plataforma evoluiu por uma única linha de decisão (o "arquiteto" da conversa). Bus factor = 1. A DPL evolui presa ao ritmo do domínio cripto. |

---

## 8. Constatações e recomendações

| # | Constatação | Evidência | Impacto | Recomendação | Prioridade |
|---|-------------|-----------|---------|--------------|-----------|
| C-01 | Status documentado diverge do código | Briefing diz F4/5 "não iniciado"; commit `c38c4cb` implementa | Decisões tomadas sobre premissa falsa | Sincronizar docs↔repo; tratar HANDOFF/dossiê como fonte derivada do git | Alta |
| C-02 | DPL não promovida ao core | Reside em `GarimpoInvestimentos/dpl/` | Bloqueia adoção multi-domínio; contradiz ADR-002 | Executar promoção (ADR-009) antes de iniciar stocks como repo separado | Alta |
| C-03 | Agregação **parcialmente** validada com dado real (2026-09-04) | Consenso Binance+Kraken (`--mode consensus`) rodado na máquina de produção — 199 candles reais fundidos. **COTAHIST/BCB seguem sem golden real** — só a agregação de cripto foi fechada, a parte de stocks continua aberta | Confiança da agregação de cripto deixa de ser só sintética; stocks (COTAHIST/BCB) continuam pendentes | ~~Validar em ambiente sem bloqueio~~ (feito p/ cripto); golden de COTAHIST real ainda falta | Média (rebaixado de Alta — metade do escopo fechado) |
| C-04 | Migration 0002 alterada in-place | `feature_store.py` mudou PK de `raw_signals` | Quebra idempotência; perigoso com dado durável | Adotar migrações somente-aditivas (ADR-017); nova migração para mudança de PK | Alta |
| C-05 | Padrão bitemporal não documentado | 3 tempos no código, sem ADR | Erosão por desconhecimento; risco de lookahead acidental | Escrever ADR-014; guia "como não vazar futuro" | Alta |
| C-06 | Fase 0 aberta | Sem evidência de core testado/commitado | Base canônica frágil | Fechar Fase 0 antes da promoção | Média |
| C-07 | `twap` ambíguo | `aggregation.py` mistura conceitos | Uso incorreto futuro | Renomear/separar TWAP-de-série de consenso-cross-source | Média |
| C-08 | Equivalência F2 em amostra mínima | 1 ativo, 1 instante | Generalização frágil | Backtest comparativo em N ativos × janela | Média |
| C-09 | Stubs de futebol misturados ao código "pronto" | `football_stubs.py` | Falsa sensação de completude | Marcar claramente "desenho"; não contar nos testes de prontidão | Baixa |
| C-10 | Bus factor = 1 | Linha única de decisão | Risco de continuidade | Revisão por 2º engenheiro; documentar invariantes | Média |

---

## 9. Perguntas que eu faria ao time

1. **Reprodutibilidade:** como vocês versionam *datasets*? Hoje há `ingestion_provenance` mas sem hash do conteúdo nem do código (`code_version` é passado mas não populado). Um backtest de 6 meses atrás é reproduzível bit-a-bit?
2. **Promoção ao core:** qual o critério objetivo de "DPL madura"? F4 já é o 2º domínio — por que ainda não promoveu?
3. **BCB revisões:** a API SGS expõe a *data real* de revisão, ou vocês aproximam com `ref + lag`? Se aproximam, o point-in-time é aproximado, não exato — isso é aceitável para o backtest?
4. **COTAHIST:** existe um golden file real validado contra um terminal/fonte independente? Os offsets foram conferidos com o layout oficial vigente da B3?
5. **Feature Store em escala:** o formato longo + pivot em memória aguenta futebol event-level (milhões de linhas)? Há plano de migração para colunar?
6. **Multi-instância:** a ingestão será single-process para sempre? Se não, o que acontece com o Circuit Breaker em memória?
7. **Equivalência:** a validação de score 25.0 cobre quantos ativos/datas? Há teste de regressão de equivalência contínuo?
8. **Governança:** quem aprova a promoção de uma primitiva domínio→core? Há um 2º revisor, ou bus factor = 1?

---

## 10. Parecer executivo

**Parecer: Sim, com ressalvas.**

**Motivos principais:**
1. A espinha dorsal (Ports&Adapters + Feature Store offline + anti-lookahead bitemporal) é **tecnicamente sólida e rara** — melhor que a média de plataformas quant internas.
2. A evolução foi disciplinada, incremental e aditiva; nenhuma decisão exige refação.
3. A cobertura de testes (74, determinísticos) é boa **para o que é exercível offline**.
4. Porém, **a confiança é desproporcional à validação real**: agregação e stocks nunca rodaram com dado verdadeiro; a DPL não foi promovida; a Fase 0 está aberta.
5. Risco organizacional concreto (bus factor 1, docs divergindo do código).

**Bloqueadores (impedem ir para produção, não para continuar desenvolvendo):**
- B-1 (C-03): ~~validar agregação~~ (cripto fechado 2026-09-04, ver tabela acima)
  ~~e stocks~~ com dados reais + golden COTAHIST (stocks/COTAHIST/BCB seguem
  abertos).
- B-2 (C-04): corrigir a estratégia de migração antes de qualquer Feature Store durável.
- B-3 (C-02/C-06): fechar Fase 0 e promover a DPL ao core antes de abrir o repo de stocks.

**Próximos passos recomendados (ordem):**
1. **Fechar a base:** Fase 0 (core testado/commitado) + ADR-014 (bitemporal) + ADR-017 (migrações aditivas) + corrigir C-04. *(destrava confiança)*
2. **Promover a DPL ao `predictor_core`** (ADR-009) — pré-requisito para stocks como domínio separado e para qualquer adoção.
3. **Validar com dado real** num ambiente sem bloqueio: agregação Binance+Kraken; ingestão COTAHIST real com golden; calibrar `publish_lag` do BCB contra divulgações conhecidas.
4. **Ampliar a equivalência** (C-08) e adicionar regressão contínua.
5. **Só então** investir nas fontes de rede da Fase 5.
6. **Mitigar bus factor:** revisão independente e documentação dos invariantes anti-lookahead.

> **Síntese do auditor:** arquitetura de alta qualidade, **maturidade superestimada pelo número de testes verdes**. Os 74 testes provam *consistência interna*, não *correção contra o mundo real*. Aprovo a continuidade do desenvolvimento; **não** aprovaria uso em produção/decisão financeira sem resolver B-1..B-3.


