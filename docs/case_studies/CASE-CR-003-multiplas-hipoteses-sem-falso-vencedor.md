# CASE-CR-003 — Sete hipóteses, zero GO: disciplina de múltiplas tentativas sem
promover um falso vencedor

**Fonte:** `charters/scientific_state.json`, `GarimpoInvestimentos/trials.json`,
`docs/ADR-015_experiment_registry_e_trava_de_poder.md`,
`GarimpoInvestimentos/analyzers/pbo.py`.

## Claim
Ao longo de sete hipóteses registradas (H1–H7), nenhuma foi promovida a capital
real, e o projeto manteve controles estruturais (trava de poder, PBO/CSCV,
registro append-only) para impedir que a família com melhor número aparente
fosse escolhida por acaso amostral.

## Protocolo
- `scientific_state.json`: `capital_authorized=false`,
  `leverage_authorized=false`, `llm_direct_trading_authorized=false` como
  estado de governança, não como decisão pontual de uma trial.
- `ADR-015`: toda trial NOVA exige um atestado de controle positivo/negativo
  (`scripts/attest_harness.py`) antes de poder ser registrada — o juiz precisa
  provar que detecta um efeito plantado e rejeita ruído puro antes de emitir
  qualquer NO-GO/GO real.
- `analyzers/pbo.py` (PBO via CSCV, Bailey/Borwein/López de Prado/Zhu):
  complementa o DSR perguntando não "este Sharpe sobrevive ao desconto por N
  tentativas", mas "o PROCESSO de escolher a melhor configuração é frágil?" —
  medindo com que frequência a melhor IS cai na metade pior OOS.
- `frozen_families: ["funding_oi_hmm_v3"]` no charter: a família H1–H3 está
  travada contra reabertura ou reparametrização silenciosa.

## Result
Status real por hipótese (charter, campo `hypotheses`):

| Hipótese | Trial | Status |
|---|---|---|
| H1 | v3-hmm-funding-oi-fr90 | CLOSED_NO_GO |
| H2 | v3-hmm-funding-oi-fr21 | CLOSED_NO_GO |
| H3 | v3-hmm-funding-oi-fr90-h48 | CLOSED_NO_GO |
| H4 | v2-dpl-gemini-h7 | CLOSED_INSUFFICIENT_SAMPLE |
| H5 | v2-dpl-multi-h7 | CLOSED_NO_GO |
| H6 | h6-sinal-invertido-d7 | COLLECTION_ONLY_IMMATURE |
| H7 | (não registrada em trials.json) | REGISTERED_NOT_ACTIVATED |

Nenhuma linha é GO. Nenhuma foi "resgatada" via reparametrização pós-hoc — a
H3 (horizonte 48h), por exemplo, é tratada como aprendizado ("o sinal é de
vida curta") e não como convite a testar 36h/60h sem tese causal nova.

## Failure mode evitado
O documento de backlog condicional (`docs/HYPOTHESES.md`, item B2) registra
explicitamente a recusa de uma variação tentadora: recombinar features da
família H1–H3 já refutada "sem tese nova é convite a p-hacking" — e exige
mecanismo causal novo por escrito antes de ativar.

## Lesson
A ausência de um "vencedor" depois de sete tentativas não é falha do projeto:
é o resultado esperado de um domínio (microestrutura cripto de curto prazo)
onde o próprio material do projeto documenta, de forma consistente, que
custos e ausência de edge genuíno dominam. A infraestrutura (trava de poder,
PBO, registro append-only, famílias congeladas) é o que torna esse "zero GO"
verificável em vez de apenas alegado.
