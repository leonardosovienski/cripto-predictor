# Consolidacao em main — 15/09/2026

O dono autorizou integrar as branches uteis e manter somente main, preservando os arquivos locais.

- `publish/auditoria-20260915` (`9064c984972d678b2492c205803549a126604824`) acrescentava as correcoes e evidencias da auditoria; foi integrada integralmente.
- A atualizacao de CI que ja estava em main (`15600c7`) foi preservada. O merge `58f4e57` altera, em relacao ao checkpoint testado, somente esses dois arquivos de workflow.
- A main foi enviada e seu SHA remoto conferido antes de remover a branch incorporada. Nenhum force push de main foi usado.
- Restou somente main entre as branches locais e remotas. Tags, snapshots, worktrees historicos, dados e configuracoes permanecem preservados.

Validacoes de codigo: [auditoria tecnica](AUDITORIA_TECNICA_20260915.md). Nao houve mudanca adicional de runtime nesta consolidacao. Os recibos locais anteriores continuam em `C:/Cripto/operacao/relatorios/AUDITORIA_COMPLETA_20260915` e `C:/Cripto/operacao/relatorios/PUBLICACAO_20260915`.
