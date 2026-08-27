# Fechamento de engenharia — 2026-08-27

Esta rodada fecha os itens residuais de engenharia sem alterar charter, trial,
gate, amostra ou veredito cientifico existente.

## Controles fechados

- **F-06:** `TradeIntent` exige familia cientifica, trial e fingerprint. O adapter
  executavel nao possui bypass para familia congelada.
- **F-07:** toda intencao materializa o identificador e a friccao round-trip do
  modelo canonico; classe desconhecida e spot nao calibrado falham antes da
  criacao da intencao. Funding futuro nao e inventado no instante do sinal.
- **F-13:** `--output-dir` ganha precedencia no bootstrap oficial; se `core.paths`
  ja tiver sido importado com outro caminho, o processo falha alto em vez de
  aceitar a flag e escrever no destino antigo.
- **F-14:** `uv.lock` completo fixa artefatos e hashes, inclusive
  `predictor-core==2.3.0` e `predictor-ops==3.1.0`; `uv lock --check` valida o lock.
- **F-16:** o orcamento de API e persistente e transacional em SQLite, portanto
  vale entre reinicios e processos.

## Deliberadamente nao alterado

F-11 nao pode ser "corrigido" retrospectivamente dentro da H6 sem violar o
pre-registro. As exigencias de estratificacao por juiz, poder, custo e fonte
paralela estao congeladas prospectivamente em `NEXT_TRIAL_SCIENTIFIC_GATE.md`.
H6 e todo o estado cientifico permanecem byte a byte fora do escopo desta rodada.

## Verificacao

- testes direcionados de trading, bootstrap e hashes: 64 aprovados;
- suite ampla: 811 aprovados, 2 ignorados e 1 desmarcado apenas porque o ambiente
  local tem `predictor-core==2.2.0`, enquanto projeto e lock exigem 2.3.0;
- wheel local construida e inspecionada pelo teste de seguranca de distribuicao;
- `uv lock --check` aprovado.
