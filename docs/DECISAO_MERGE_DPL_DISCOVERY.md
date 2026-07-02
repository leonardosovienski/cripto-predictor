# Decisão de Merge — DPL (Fases 1-3) + `--discover`

> ADR informal. Contexto: `claude/clever-mclean-16f6d8` (DPL) e `claude/frosty-goldstine-1092c9`
> (`--discover`, commit `799cd27`) divergem de `a78580c` e ambas modificam `main.py`.
> Princípio orientador: **o discovery escolhe O QUE analisar; a DPL fornece OS DADOS.**

## D1 — Symbol_map para altcoins: fallback assumido, sem mapa dinâmico

Ativos descobertos (morpho, kaspa, …) não constam no `symbol_map` de Binance/Kraken →
cairão **sempre** no CoinGecko. **Decisão: aceitar e documentar; NÃO implementar symbol_map
dinâmico agora.** Motivos: (a) os ids do discovery são nativos do CoinGecko — o provider
funciona para qualquer id sem mapa; (b) Binance/Kraken estão bloqueadas nesta região — um
mapa dinâmico não compraria nada hoje; (c) mapeamento automático por ticker é perigoso
(colisão de símbolos → preço errado **silencioso**, pior que fonte única). Trade-off: a
redundância multi-fonte fica restrita aos 7 majors; o risco de fonte única se concentra
justamente nos candidatos do discovery — registrado, mitigado pela telemetria
(`data.fallback`) e pelo carimbo D2. **Gatilho de revisita:** consenso validado ao vivo
(C-03 resolvido) **e** edge comprovado em algum ativo descoberto.

## D2 — Carimbo `data_source`: coluna `Fonte`, gravada na montagem do resultado

- **Chave no resultado / coluna CSV+XLSX:** `data_source` / `Fonte` (precedente: `judge`/`Juiz`).
- **Valores:** `direct` (coleta acoplada à rede, pré-DPL) · `dpl:fallback` · `dpl:consensus`.
  O valor registra a **política**; a verdade granular (qual provider entregou cada candle)
  já vive na telemetria e em `raw_market_data.source`/`ingestion_provenance` — não duplicar.
- **Momento da gravação:** em `main.py`, na montagem do `resultado` (mesmo ponto do carimbo
  do juiz), derivado do caminho de dados usado na análise. Persistido por `append_history`.
- **Backfill:** linhas históricas sem a coluna leem-se como `direct` (default no load do backtest).
- **Backtest:** estratifica por `Fonte` e trata a transição como quebra de série — nunca
  correlacionar scores de fontes distintas numa amostra única sem estratificar (mesma regra
  já adotada para juízes distintos).

## D3 — `main.py`: base DPL, enxerto do discovery, descoberta é online

- **Base textual do merge: o `main.py` da DPL** (reestruturou o fluxo em ingestão/serving;
  a coleta direta na análise morre). O commit do discovery é **re-aplicado por cima**, não
  mergeado textualmente.
- **Universo:** grupo mutuamente exclusivo `--assets | --discover N` (vem do discovery).
  A lista resolvida alimenta qualquer modo.
- **`--discover` exige `--ingest`:** descoberta é rede por natureza; análise é offline por
  design. `--discover` sem `--ingest` → erro do argparse com dica ("descubra+ingira; depois
  analise offline"). Fluxo típico: `main.py --ingest --discover 10` → `main.py --summary`.
- **Análise sem `--assets`:** deixa de usar só `DEFAULT_ASSETS` — analisa **todos os símbolos
  presentes na Feature Store** com features frescas (novo `FeatureStore.list_symbols()`),
  para que o resultado da descoberta ingerida seja analisável sem redigitar a lista.
- **`--mode`:** inalterado (só afeta `--ingest`). **Cache/--no-cache:** inalterados.

## Decisões tomadas

1. Altcoins descobertas = CoinGecko-only via fallback natural; sem symbol_map dinâmico (revisita: pós C-03 + edge).
2. Carimbo `Fonte` ∈ {`direct`, `dpl:fallback`, `dpl:consensus`}, gravado na montagem do resultado; backfill = `direct`; backtest estratifica.
3. Merge com base no `main.py` da DPL; discovery re-aplicado como enxerto (`--assets | --discover`).
4. `--discover` só com `--ingest`; análise sem `--assets` lê o universo da Feature Store.
5. Ordem de execução: este documento aprovado → merge de `799cd27` na branch da DPL → carimbo implementado no mesmo PR do merge (nenhuma linha de histórico nova sem `Fonte`).
