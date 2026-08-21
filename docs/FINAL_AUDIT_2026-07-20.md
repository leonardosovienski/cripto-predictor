# Auditoria final de 2026-07-20 — CONTEÚDO PERDIDO

> **Registro de perda, não o relatório.** Até 2026-08-21 este arquivo continha 15
> bytes: literalmente o texto `[Binary file]`, seguido de duas quebras de linha —
> um placeholder de ferramenta no lugar do conteúdo.
>
> O relatório **nunca existiu neste repositório**. O arquivo foi adicionado já
> quebrado, com esses mesmos 15 bytes, no commit `728d374` ("consume
> predictor-core/ops from published releases, harden CI/container", PR #8) — é a
> única revisão que o toca em todo o histórico (`git log --all`). Portanto o texto
> original não é recuperável daqui: ele ficou no ambiente onde a auditoria de
> 2026-07-20 foi conduzida e só o placeholder foi commitado.

O arquivo foi mantido em vez de apagado por duas razões: `HANDOFF.md` o referencia
(apagar trocaria uma perda conhecida por um link quebrado silencioso), e a perda em si
é informação de auditoria — o mesmo princípio que faz o projeto registrar
`H5_RAW_DATA=LOST` em vez de omitir a lacuna.

Nada foi reconstruído de memória. Para o que aquela rodada de 2026-07-20 produziu e
que **está** versionado, ver:

- `GarimpoInvestimentos/trials.json` — a H6 (`h6-sinal-invertido-d7`) foi
  pré-registrada em 2026-07-20T07:01:59Z, com o mecanismo dedicado de maturação
  implementado no mesmo dia (`556f5ad`).
- [HYPOTHESES.md](HYPOTHESES.md) §H6 — o pré-registro e suas erratas.
- [HANDOFF.md](../HANDOFF.md) — o adendo "Hardening operacional 2026-07-20"
  (`scripts/feature_store_backup.py`, backup/restore verificável).
- [BACKUP_RESTORE.md](BACKUP_RESTORE.md) — o runbook que saiu dessa rodada.

Estado corrente do projeto: [../README.md](../README.md) ·
índice de erratas: [ERRATA_2026-08-21.md](ERRATA_2026-08-21.md).
