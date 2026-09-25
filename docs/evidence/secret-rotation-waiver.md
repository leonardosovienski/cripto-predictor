# Dispensa da atestação de rotação de segredos (registro)

**Este arquivo não é `secret-rotation-attestation.md` e não torna o gate `CLEARED`.** Ele registra, num arquivo
próprio, uma dispensa que antes estava só no relatório do Prompt 2. Foi criado na revisão de 2026-09-25.

| item | valor |
|---|---|
| gate | `SECRET_ROTATION_GATE = WAIVED_BY_OWNER` (Prompt 1 terminou em `BLOCKED`) |
| data da dispensa | 2026-09-24 |
| quem dispensou | leonardosovienski (dono) |
| texto exato | O agente parou na pré-condição do Prompt 2 e pediu a atestação. O dono respondeu "nao preciso disso nao". À pergunta de confirmação sobre dispensar a atestação e seguir, respondeu "sim". |
| onde já constava | `docs/evidence/2026-09-24-prompt2-auditoria-tecnica.md`, linha 10 |
| restrições que continuam valendo | nenhum código do projeto roda com credencial, com `.env` ou com rede; nenhuma ordem, nem em testnet. Os Prompts 2 a 4 rodaram assim: testes e avaliações sob `env -i … unshare -rn` e o Chronos com `HF_HUB_OFFLINE=1` |
| leituras de rede feitas fora do código do projeto | só metadados públicos, sem credencial: API do Hugging Face (licença, revisão e oids do checkpoint), JSON do PyPI e a licença via API do GitHub, exigidos pelo Prompt 3c ("verifique agora no model card") |

## O que continua pendente (humano)

Segundo o relatório do Prompt 1 (`2026-09-24-prompt1-secret-rotation-gate.md`):
- a rotação das 5 credenciais do incidente é só DECLARED (confirmação verbal de 2026-08-19);
- a revogação das chaves antigas e a verificação de uso indevido seguem `EXTERNAL_BLOCKER`;
- 7 classes de credencial consumidas pelo código não aparecem em nenhum registro de rotação: `OPENAI`,
  `OPENROUTER`, `NEWSAPIAI`, `MEDIASTACK`, `CRYPTOPANIC_AUTH_TOKEN`, `COINGECKO` e `ALERTA_WEBHOOK_URL`.

Para o gate virar `CLEARED`, o dono cria `docs/evidence/secret-rotation-attestation.md` cobrindo todas essas
classes (data, classes, quem fez, como confirmou, sem valores).
