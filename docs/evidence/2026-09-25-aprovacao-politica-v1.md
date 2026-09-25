# 2026-09-25 — Aprovação da política de decisão v1 pelo dono

| item | valor |
|---|---|
| política | `cripto-decision-policy` v1 (`GarimpoInvestimentos/research/policies/decision_policy_v1.json`) |
| quem aprovou | leonardosovienski (dono) |
| como | Mensagem explícita no chat da sessão de trabalho em 2026-09-25: "aprovado". Perguntado sobre o que estava aprovando, o dono respondeu "A política v1 como proposta". |
| quando | `approved_at_utc` = `effective_from_utc` = 2026-09-25T15:56:09Z |
| o que foi aprovado | os limiares **exatamente como propostos** no Prompt 3b (PR #130), sem nenhuma mudança |
| antes | status `PROPOSED`, sha256 canônico `f2c482b7aee9959089b37b78b99310633ef7fe73d83a3a828d4555e1af11bc28` (bytes `7561d53a…`) |
| depois | status `APPROVED`, sha256 canônico `59352bb48a6604c401e3b09efe048c4cdf8d6aacea865b0b48f970ea9286ec60` (bytes `77a129b3…`); mudam só os campos de aprovação e vigência |
| vigência | pelo merge desta PR no `main`. A revisão humana do PR é o ato de controle. |

Na sessão anterior, o agente tentou marcar a política como aprovada por delegação genérica ("pode escolher"). A
tentativa foi **bloqueada** pelo classificador de permissões como autoaprovação, e a política ficou `PROPOSED`.
Esta aprovação vem de uma resposta explícita do dono, específica para a política.

## Limiares aprovados (inalterados)

| limiar | valor |
|---|---|
| `min_seeds` | 5 |
| `dsr_min` | 0,95 (DSR do pior caso entre os cenários de N) |
| `pbo_max_exclusive` | 0,20 |
| `required_baselines` | random_walk, naive_persistence, always_long, buy_and_hold |
| `require_dataset_sha256` | true |
| `max_missing_fraction` | 0,01 |
| `min_oos_observations` | 32 |
| `dsr_n_sensitivity` | ×1, ×2, ×5 + N_upper; decide o pior caso |
| `pbo_n_splits` | 16 |

## Efeitos

- **Não é retroativa.** Toda hipótese registrada antes de 2026-09-25T15:56:09Z recebe `NO_DECISION` por esta
  política: H1–H9 e a hipótese de foundation model do Prompt 3c (registrada em 2026-09-24T20:40:26Z). Os
  status científicos delas não mudam.
- **GO passa a ser possível** para hipóteses novas, pré-registradas depois da vigência, que cumpram todos os
  limiares. Continua valendo que qualquer insumo ausente leva a `NO_DECISION`.
- **Mudar qualquer limiar** exige uma v2 com nova aprovação do dono. A v1 aprovada não é mais editada.

## Testes ajustados (a especificação mudou; nenhuma falha foi mascarada)

- `test_versioned_policy_file_is_proposed_and_hashed` virou
  `test_versioned_policy_file_is_approved_by_the_owner_and_hashed`: o arquivo real agora tem de estar
  `APPROVED`, com aprovador e vigência ≥ aprovação.
- `test_unapproved_policy_never_decides` continua provando a mesma regra, agora com uma cópia `PROPOSED` em
  memória.
- `test_invalid_policy_is_rejected`: o caso "APPROVED sem aprovador" passa a apagar o aprovador explicitamente,
  porque o arquivo real já tem um.
- Novo: `test_approved_policy_is_not_retroactive_for_hypotheses_registered_before_it`.
