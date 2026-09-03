# Inventário da camada `trading/` — classificação para reprodutibilidade

> Auditoria de classificação (bloco 20 do congelamento científico), não desenvolvimento.
> Nenhum adaptador novo foi criado; nenhuma execução financeira real foi integrada.
> Toda a camada nasceu do "override de governança 2026-08-14" (`docs/HYPOTHESES.md`):
> infraestrutura de engenharia construída ANTES de qualquer hipótese ter edge validado,
> por decisão explícita do dono — não autoriza capital, não muda gate científico algum.

Verificado nesta rodada: todos os 12 arquivos de `GarimpoInvestimentos/trading/*.py`
têm suíte de teste própria e passam (ver `uv run pytest tests/test_trading_*.py
tests/test_binance_spot_collector.py tests/test_order_book_reconstruction.py`).
Nenhum módulo é consumido por um caminho de execução real de capital — o único
consumidor fora de `trading/`/testes é `jobs.py`, que usa `binance_spot_collector.py`
apenas como coletor `COLLECTION_ONLY` (sem adaptador de ordem, sem credenciais).

| Módulo | Propósito | Testado? | Consumidor real fora de trading/tests | Decisão |
|---|---|---|---|---|
| `contracts.py` | Tipos do contrato econômico (Instrument, TradeIntent, Order, Fill, Position, Settlement) | Sim (consumido por quase todos os outros testes da camada) | Nenhum (fundação interna da camada) | **PRESERVE_FOR_REPRODUCTION** — é o vocabulário comum; remover quebra os demais |
| `cost_policy.py` | Roteamento canônico de modelo de custo por `asset_class` (perp→CostModel calibrado, spot→erro se não calibrado) | Sim | Nenhum | **REUSE** (já listado em `preserved_components`) — lógica de roteamento sem I/O, genérica |
| `costs.py` | Custos walk-the-book para Binance Spot | Sim | Nenhum | **ARCHIVE** — explicitamente NÃO CALIBRADO para veredito (já classificado no manifesto) |
| `execution.py` | Máquina de estados pura do ciclo de vida da ordem (aceita→fill→cancelamento→reconciliação), sem I/O/rede | Sim | Nenhum | **REUSE** — motor puro, sem dependência de domínio cripto específico |
| `microstructure.py` | Simulação de fill contra profundidade real do book (walk-the-book) | Sim | Nenhum | **PRESERVE_FOR_REPRODUCTION** — específico do formato de book da Binance, mas necessário para reproduzir `costs.py`/testes associados |
| `microstructure_quality.py` | Watchdog e scorecards diários da qualidade da coleta prospectiva de microestrutura | Sim | Nenhum | **PRESERVE_FOR_REPRODUCTION** — infraestrutura de observabilidade da coleta, não de execução |
| `portfolio.py` | Risco agregado sobre um conjunto de posições (beta, correlação) — matemática pura | Sim | Nenhum | **REUSE** — não depende de nenhum sinal ter edge validado nem do domínio cripto |
| `report.py` | Relatório read-only de risco de portfólio; nunca autoriza capital nem emite veredito | Sim | Nenhum | **PRESERVE_FOR_REPRODUCTION** — compõe métricas já calculadas, específico do formato do domínio |
| `signal_adapter.py` | Adapter `SignalRecord` (v3/signal_engine.py) → `TradeIntent` executável | Sim | Nenhum | **PRESERVE_FOR_REPRODUCTION** — cola específica do domínio (famílias congeladas bloqueiam a conversão) |
| `store.py` | Persistência append-only, hash de conteúdo, três tempos (evento/recebimento/ingestão) — sempre `COLLECTION_ONLY` | Sim | Nenhum | **REUSE** — padrão de store append-only bitemporal é genérico, não específico de cripto |
| `binance_spot_collector.py` | Coletor público `COLLECTION_ONLY` de microestrutura Binance Spot (sem adaptador de ordem, sem credenciais) | Sim | `jobs.py` (coleta agendada) | **PRESERVE_FOR_REPRODUCTION** — é o único módulo da camada com consumidor real em produção, mas só como coleta, nunca execução |
| `__init__.py` | Docstring do pacote (declara o override de governança) | N/A | N/A | **PRESERVE_FOR_REPRODUCTION** — documentação de proveniência da camada |

## Nenhum módulo classificado como REMOVE_LATER

Todos os 12 arquivos têm teste próprio, propósito documentado no cabeçalho, e
rastreabilidade explícita ao override de governança de 2026-08-14. Não há
código morto órfão na camada `trading/` — é engenharia deliberadamente
construída à frente do sinal, não infraestrutura abandonada.

## O que isso NÃO significa

Esta classificação não autoriza capital, não conecta execução real, e não é
convite a "ativar" a camada. `cost_policy.py` continua recusando classes de
ativo desconhecidas em vez de assumir custo zero, e `costs.py` (spot)
continua bloqueado (`UncalibratedCostModel`) para sustentar qualquer
veredito científico.
