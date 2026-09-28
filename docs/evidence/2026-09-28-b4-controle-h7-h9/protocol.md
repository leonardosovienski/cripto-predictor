# 2026-09-28 — B4 item 7: controle do H7/H9 (`extra_features=()`) — protocolo

Gravado e publicado **antes** de qualquer download ou execução, como nas triagens anteriores (protocolo antes do
download).

## Origem e autorização

- **Pendência:** `docs/HYPOTHESES.md`, B4, item 7 ("Falta o controle — e ele nunca foi rodado") e "Lacunas conhecidas" item 3. O desenho está no runbook `docs/MAQUINA_DE_PRODUCAO.md`, seção "O controle do H7/H9, quando for rodar". Tudo isso já estava versionado antes deste protocolo.
- **Autorização do dono (2026-09-28, sessão Claude Code no PC 2):**
  - rodar o controle da família congelada `funding_oi_hmm_v3` em modo diagnóstico;
  - reconstruir o histórico com dados públicos do `data.binance.vision`, neste PC, porque a máquina de produção (`C:\predictor`) não está aqui;
  - publicar o resultado em `docs/evidence` por PR, sem tocar `trials.json`.
- **Por que agora:** a tentativa de 2026-09-05 falhou por dois motivos. Não havia histórico de OI fora da produção, e o `data.binance.vision` estava bloqueado no ambiente de auditoria. Aqui o Vision é acessível.

## Dados

- **Coleta:** o importador do próprio domínio, `python -m GarimpoInvestimentos.v3.vision_ingest --symbol BTCUSDT --start-date 2021-01-01 --end-date 2026-09-03`.
  - funding mensal, OI pelo dataset `metrics` (diário, 5 min) e klines spot 1h;
  - cada zip é conferido contra o `.CHECKSUM` publicado (`binance_vision._download_zip`);
  - grava os mesmos `funding.csv`, `oi.csv` e `spot_binance_1h.csv` do caminho REST.
- **Janela:** o data lake de produção começava em 2021-01-01 ("2021→jul/2026") e era estendido diariamente até o dia anterior. O H9 rodou em 2026-09-04, então o fim é 2026-09-03. Nada toca o holdout selado `cripto-holdout-btcusdt-20260926-20270326`.
- **Destino:** `DATA_DIR`, `CACHE_DIR`, `OUTPUT_DIR` e `LOGS_DIR` fora do repositório. O ledger de runtime do `backtest_v3` (`CRIPTO_RUN_LEDGER`, não versionado) também fica fora, e uma cópia vai para esta pasta.
- **Código:** commit `905ab7a` do `main` (v1.2.0rc3 + adapter), venv do `uv.lock` (`--all-extras`).

## Execução (idêntica ao runbook, nenhuma outra flag)

```
python -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT                         # braço A: baseline
python -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT --use-oi-volume-ratio   # braço B: H9
```

Tudo no default: fee 10 bps, slippage 5 bps, horizonte 24 h, `fr-window` 90. **Os dois braços na mesma janela.**

## Checagens

1. `git status --short GarimpoInvestimentos/trials.json` vazio antes e depois.
2. **Validade:** o braço B precisa reproduzir `Sharpe ≈ −1,0041` e `PSR ≈ 0,1621`, o veredito do H9 de 2026-09-04.
   - Se não reproduzir, o harness ou os dados diferem do H9, e a comparação **não** fala sobre o −1,0041 do H9.
   - Nesse caso o resultado é reportado como controle **sobre os dados públicos reconstruídos**, com a divergência explícita. Nada é ajustado para forçar a reprodução: nem janela, nem flag, nem parâmetro.
3. Extrair de cada log: `Folds`, `PSR agregado`, `IC Spearman`, `Max Drawdown`, `Sharpe agregado`.

## Leitura (tabela do runbook, definida antes do dado)

| Resultado | Leitura |
|---|---|
| A ≈ B ≈ −1,0 | a covariável é inocente; o −1,0041 vem do período ou do harness |
| A ≈ 0 e B ≈ −1,0 | acrescentar covariável exógena degrada de verdade; o H7 está condenado por razão mecânica |
| A pior que B | inesperado; o desenho do teste precisa de revisão |

## O que isto não é

- Não reabre o H9, que segue fechado, nem reparametriza a família congelada.
- Não registra trial, não consome tentativa do DSR e não toca `trials.json`, `charters/`, `HYPOTHESES.md` nem o holdout.
- Não autoriza capital.

## Emenda 1 (2026-09-28, antes da segunda execução)

**O que aconteceu na primeira execução**, com o código do `main` `905ab7a` sobre os dados reconstruídos: os dois braços falharam antes do WFA (`CRASHED` no ledger de runtime).

- O `feature_builder` descartou 6.118 dos 6.207 instantes de funding e montou **0** vetores.
- Causa: desde `9d89871` (2026-09-10, depois do H9), o builder exige cadência **exata** de 8 h em toda a janela de funding.
- Os instantes do `fundingRate` do Vision trazem milissegundos de ruído (`1609459200002`, `1609488000006`…), então quase toda janela falha.
- Os logs ficam em `logs/main-905ab7a/`. Não é resultado do controle: é incompatibilidade entre o harness atual e o importador Vision do próprio domínio, e fica registrada como achado.

**Correção de desenho, pelo próprio runbook:** a checagem de validade exige o **mesmo harness do H9** ("se não bater, o harness mudou").

- O H9 rodou em 2026-09-04 com o código de `e3ee0af` (#88, mergeado às 15:20 −03:00, antes do veredito em `8af1e4f`, 15:56).
- A checagem de cadência exata não existia nesse código.
- Os dois braços passam a rodar com o harness `e3ee0af`: worktree destacado, venv do `uv.lock` daquele commit (Core 3.0.0, o pin da época), mesmos CSVs, mesmos comandos, nenhuma outra flag.
- Janela, parâmetros, critério de validade e tabela de leitura **não mudam**.

## Emenda 2 (2026-09-28, antes da terceira execução)

**O que aconteceu:** com o harness `e3ee0af`, os dois braços de novo montaram 0 vetores (logs em `logs/h9-e3ee0af-tentativa1/`).

**Causa, confirmada no código e por replicação do laço (6.096 instantes passam o join):**
- naquele commit, o `backtest_v3` e o `vision_ingest` leem e gravam `data/v3/<símbolo>/spot_1h.csv`;
- o arquivo só passou a se chamar `spot_binance_1h.csv` em `9d89871` (2026-09-10), com as mesmas colunas;
- o harness do H9 não achou o arquivo e montou o índice de preços vazio.

**Correção:** o mesmo CSV, **byte a byte**, fica disponível com o nome da época (`spot_1h.csv`, sha256 igual ao de `spot_binance_1h.csv`). Nenhum dado, janela, flag ou parâmetro muda.
