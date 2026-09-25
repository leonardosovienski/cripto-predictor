# 2026-09-24 — Prompt 1: gate de segurança dos segredos (cripto-predictor / GarimpoInvestimentos)

Modo: **somente leitura**. Clone local `~/predictors/repos/cripto-predictor`, HEAD `174573df4884` (= `origin/main` no último fetch, 2026-09-24 ~08:36 UTC; árvore idêntica ao commit qualificado `341d270`), sem alterações locais. Nenhum `.env` carregado, nenhuma rede, nenhuma API externa, nada instalado, nenhum arquivo do repositório alterado. Saídas brutas ao lado deste arquivo: `scan_historico.json`, `scan_arquivos_compactados.json`; scripts em `~/predictors/runtime/cripto/tools/redacted_secret_scan.py` e `redacted_archive_scan.py`.

## A. SECRET_ROTATION_GATE = **BLOCKED**

`docs/evidence/secret-rotation-attestation.md` **não existe** (PROVEN: `ls` no HEAD). A rotação das 5 credenciais do incidente é só DECLARED (confirmação verbal do dono registrada em 2026-08-19). A revogação das chaves **antigas** e a verificação de uso indevido seguem abertas como `EXTERNAL_BLOCKER`, e o próprio código publica isso (`old_key_revocation_external_check_pending: True`). Outras 7 classes de credencial consumidas pelo código não aparecem em nenhum registro de rotação.

## B. Evidências do bloqueio / rotação

| evidência | status | classificação | localização |
|---|---|---|---|
| Atestação humana de rotação | ausente | PROVEN (ausência) | `docs/evidence/secret-rotation-attestation.md` |
| Registro canônico do incidente: 5 credenciais (`GEMINI_API_KEY`, `SERP_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY`) "rotacionadas, confirmado pelo dono"; revogação das antigas e uso indevido = `EXTERNAL_BLOCKER` | `ROTATED_CONFIRMED_BY_OWNER_2026-08-19` | DECLARED | `docs/SECURITY_INCIDENT_SERPAPI.md:3,19-27` |
| Estado original do incidente | `BLOCKED_PENDING_SECRET_ROTATION` (preservado como histórico) | DECLARED | `docs/SECURITY_INCIDENT_SERPAPI.md:15`; `HANDOFF_HISTORICO_ATE_20260917.md:97,127,180` |
| Marcadores de segurança | novas chaves `YES`; antigas revogadas `UNVERIFIED`; ação externa `VERIFY_OLD_KEY_REVOCATION` | DECLARED | `docs/RELATORIO_FINAL.md:180-182` |
| Estado científico cita o incidente | `security_incident = ROTATED_CONFIRMED_BY_OWNER_2026-08-19` | DECLARED | `charters/scientific_state.json:7` |
| Código publica o estado | `security_status = ROTATED_CONFIRMED_BY_OWNER_2026-08-19`, `old_key_revocation_external_check_pending = True` | PROVEN (o código emite o campo); o fato descrito é DECLARED | `GarimpoInvestimentos/plugin.py:55-56` |
| Errata consolidada: rotação confirmada; revogação a verificar | — | DECLARED | `docs/ERRATA_2026-08-21.md:37-48,63` |
| Instrução do dono: manter as chaves atuais, sem revogar como pré-requisito; revogação histórica não verificada | — | DECLARED | `docs/evidence/remaining_dependencies_20260910/access_check.json:8,11`; `docs/CONFERENCIA_CHAT_20260910.md:30`; `docs/AUDITORIA_AMPLIADA_20260910.md:97` |
| Documento que ainda diz "continua BLOCKED_PENDING_SECRET_ROTATION" (com nota de superação no topo) | inconsistente | DECLARED | `docs/H5_ACOMPANHAMENTO_2026-07-25.md:10-11 × 140-141` |
| Commit da reconciliação | "rotação confirmada pelo dono" | PROVEN (o commit existe); o conteúdo é DECLARED | `a97978c` (2026-08-19) |
| Verificação antiga dos pacotes (659 MB, 427 ZIPs) sem correspondência com os segredos configurados | — | DECLARED (não reexecutável: compara com valores que não tenho nem devo ter) | `docs/evidence/remaining_dependencies_20260910/review_snapshot.md:262` |

## C. Achados do secret scanning (nenhum valor exibido)

gitleaks e trufflehog: **NOT_RUN**, porque não estão instalados (WSL e Windows; `command -v` vazio) e não foram instalados. Como substituto, rodei inspeção local só de objetos Git (`git cat-file`), com as regras usuais do gitleaks para chaves Google, OpenAI-like, Groq, Cerebras, GitHub, AWS, Slack, Telegram, webhooks, blocos de chave privada e atribuições `*_key/secret/token/password = <valor>`. Ela imprime só regra, arquivo, linha, commit e a forma do valor (tamanho e entropia).

Cobertura: todas as refs locais (main + 4 tags; 496 commits; 6038 objetos com caminho; 4545 blobs de texto) e o conteúdo de 96 arquivos compactados do histórico (`.zip`, `.gz`, `.whl`, zip dividido `.001+.002`), descompactados em memória.

| tipo | arquivo | commit | estado | evidência / classificação |
|---|---|---|---|---|
| `credential_assignment` (`a_token`, 80×) | `docs/evidence/aave_validation_20260910/history/*.json` (28), `docs/evidence/dependency_execution_20260910/aave/*.json` (15) | `3e602118a61e`, `25807a354402` | presente no HEAD | **Falso positivo PROVEN**: os 80 valores são o mesmo endereço de contrato EVM público (`^0x[0-9a-f]{40}$`), e o `scripts/scan_secrets.py` do repo já isenta esse caso |
| `openai_like_key` (`sk-…`, 2×) | `tests/test_secrets_telemetry.py:13` | introduzido em `a21331e99f0f`, também em `0b2fdbaa518a` | removido do HEAD (hoje a string é concatenada, `:14`) | **Fixture sintética PROVEN**: teste do detector (`find_secrets("leak …")`); 30 de 31 pares de caracteres consecutivos são ascendentes (tipo "abc…") |
| `credential_assignment` (`topic_token`/`publication_token`, 13×) | `docs/continuity_20260910/revisao-20260910.zip` → `…/executor_preflight02/sources/7539a8fb….json` | — | presente no HEAD (dentro do zip) | **Falso positivo provável**: campos de resposta SerpAPI/Google News (identificadores de tópico e publicação); nenhuma atribuição de `api_key` no arquivo |
| arquivos sensíveis commitados | só `.env.example` e `GarimpoInvestimentos/.env.example` (valores vazios); dentro de zips/wheels só `.env.example` e `cacert.pem` público; 16 `secrets.log` internos são saídas antigas de scanner, sem padrão de chave | 496 commits | — | PROVEN: nenhum `.env` real, `pipeline.env`, `.pem` privado ou chave |
| árvore do HEAD pelo scanner do repo | `scripts/scan_secrets.py`, com `env -i … python3 -I` | HEAD | — | PROVEN: `finding_count: 0` |

Limites (UNKNOWN):
- Refs remotas não presentes no clone, `refs/pull/*`, forks e branches apagadas: sem acesso nesta etapa, porque consultar o remoto é chamada externa.
- Conteúdo binário não compactado (SQLite, parquet, imagens) não foi inspecionado.
- Os 5 logs históricos do incidente estão fora do repositório e, por regra do projeto, não são abertos.

## D. Controles preventivos

| controle | existe? | classificação | evidência |
|---|---|---|---|
| `.env` no `.gitignore` | sim | PROVEN (config) | `.gitignore:1` |
| `.gitignore` cobre `pipeline.env`, `*.env`, `.env.*`, `*.pem`, `*.key` | **não** | PROVEN (lacuna) | só o padrão `.env` exato; `pipeline.env` vive fora do repo (PC 1) |
| `.env.example` sem valores | sim (2 arquivos, 12 chaves vazias cada) | PROVEN | `.env.example:9-36`; `GarimpoInvestimentos/.env.example:11-47` |
| hook de pre-commit de secret scan | configurado | PROVEN (config) | `.pre-commit-config.yaml:8-14` (`secret-scan` → `python scripts/scan_secrets.py .`) |
| hook instalado | não, neste clone | PROVEN (neste clone) / UNKNOWN (nos clones do PC 1) | `.git/hooks/pre-commit` ausente |
| secret scan no CI | sim, e funcionando | PROVEN | `.github/workflows/ci.yml:31`; run [35925694691](https://github.com/leonardosovienski/cripto-predictor/actions/runs/35925694691) tentativa 2 (341d270, mesma árvore do HEAD), job `quality`: `finding_count: 0` |
| testes de segredos e redação | sim, passando | PROVEN | suíte local de hoje em 341d270: `test_security_redaction` 6, `test_secrets_telemetry` 4, `test_settings` 5, `test_distribution_security` 3, `test_secret_assignment_boundaries` 2, `test_test_environment_isolation` 1 → 21/21 passed |
| campos de credencial fora do `repr` | sim | PROVEN (config) | `GarimpoInvestimentos/config.py:30-50` (`Field(default="", repr=False)`) |
| secret scanning / push protection do GitHub | — | UNKNOWN | exige consultar a API do GitHub (proibido nesta etapa) |
| documentação de rotação/revogação | sim | DECLARED (conteúdo) | `docs/SECURITY_INCIDENT_SERPAPI.md` |

## E. Ações humanas necessárias (sem valores)

Classes de credencial que o código consome (`GarimpoInvestimentos/config.py:30-50`, `.env.example`), todas vindas do `pipeline.env` fora do repo:

1. **Do incidente de 2026-08-19** (rotação só DECLARED; revogação das antigas pendente): `GEMINI_API_KEY`, `SERP_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY`.
2. **Consumidas pelo código e fora de qualquer registro de rotação**: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `NEWSAPIAI_API_KEY`, `MEDIASTACK_API_KEY`, `CRYPTOPANIC_AUTH_TOKEN`, `COINGECKO_API_KEY`, `ALERTA_WEBHOOK_URL` (a URL do webhook é credencial).
3. **Aceitas pelo código sem variável de ambiente** (`external_intelligence/providers/nansen.py`, `santiment.py`): só se você tiver chaves Nansen/Santiment.
4. Nenhuma chave de exchange ou broker aparece no código (modo `RESEARCH_ONLY`; `capital_permission = FORBIDDEN`).

O `docs/evidence/secret-rotation-attestation.md` precisa ter:
- data;
- cada classe acima, com o estado: rotacionada, e a antiga **revogada**; ou "não exposta / não utilizada", com o motivo;
- quem fez;
- como confirmou: por exemplo, a chave antiga aparece como revogada ou excluída no painel de cada provedor, e o que foi possível verificar de uso indevido antes da rotação.

Sem valores, sem fragmentos.

## Busca ampliada (pedido do dono: "procura até achar"), 2026-09-24 ~14:05 UTC

| onde | o quê | resultado |
|---|---|---|
| GitHub, 7 repos do stack (cripto, cain, ecosystem, core, ops, brasileirão, stocks) + `predictor-qualification` | `git fetch --all --tags --prune`; `git log --all` e `ls-tree` de `origin/main` por `*secret-rotation-attestation*`, `*rotation*attest*`, `rotation`, `rotac` | **nenhuma atestação**. Só `ecosystem-predictor/SECURITY_INCIDENT_SECRET_ROTATION.md` (abaixo) |
| WSL inteiro (`find / -xdev`) | nomes com rotation/rotação/attestation+secret; binários `gitleaks*`/`trufflehog*` | só o doc do ecossistema (em 3 cópias) e este relatório; nenhum binário (só logs de checksum do gitleaks dos runs de stocks) |
| Windows C:, E:, D:, F: (537.415 arquivos, sem as pastas de sistema e de jogos) | mesmos padrões de nome, mais `security_incident` | **nada** além da cópia deste relatório |
| histórico Git do cripto | `garimpo_fase1_*.log` (os 5 logs vazados) e `*.log` operacionais | 0 em qualquer commit (PROVEN); 0 atribuições `api_key=<valor>` no histórico e nos compactados (PROVEN) |

Documento novo para a tabela B:

| evidência | status | classificação | localização |
|---|---|---|---|
| Incidente SerpAPI do ecossistema: "**SUPERSEDED em 2026-09-03**. A credencial foi rotacionada. Varredura segura do cripto-predictor confirmou ausência dos cinco logs incidentais em todo o histórico Git… `SERPAPI_CURRENT_FILES=CLEAN`, `SERPAPI_GIT_HISTORY=CLEAN`" | superseded | rotação: DECLARED. "Logs fora do Git": **PROVEN nesta sessão** (0 caminhos no histórico) | `ecosystem-predictor/SECURITY_INCIDENT_SECRET_ROTATION.md` (topo; `c35928e`, 2026-09-03) |
| Mesmo documento, §8: checklist humano (1 revogar, **2 confirmar que a chave antiga falha com 401/403**, 3 configurar a nova, 4 ciclo real, 5 destino dos 5 logs, **6 registrar data, quem fez e evidência**) | **todos os itens desmarcados** | DECLARED (checklist aberto) | mesmo arquivo, §8–§9 |

Ferramentas: gitleaks e trufflehog não estão instalados em lugar nenhum desta máquina. O ecossistema já tem um jeito validado de rodar o **gitleaks 8.24.3**: o workflow `stocks-secrets.yml` do repo de evidência baixa o binário num runner descartável do GitHub Actions, confere o checksum publicado e roda com `--redact`. Usar isso para o cripto exige criar um workflow (commit) e baixar a ferramenta, o que é proibido neste prompt de somente leitura. Fica como proposta, dependendo de autorização.

**Conclusão da busca: o gate continua BLOCKED.** A atestação que o prompt exige ("escrita por mim", isto é, pelo dono) não existe em nenhum lugar acessível. Ela não pode ser produzida pelo agente.

**STOP**: SECRET_ROTATION_GATE ≠ CLEARED. Parei aqui: nenhum teste, predictor ou backtest foi rodado nesta etapa.

## Adendo de 2026-09-25: anexos versionados

Na revisão completa, constatei que este relatório citava anexos que só existiam em `~/predictors/runtime/cripto`,
fora do repositório. Eles agora estão em `docs/evidence/2026-09-24-prompt1/`, copiados byte a byte como foram
executados em 2026-09-24:

| arquivo | sha256 |
|---|---|
| `scan_historico.json` | `4fada449…` |
| `scan_arquivos_compactados.json` | `55f593ce…` |
| `redacted_secret_scan.py` | `e1dfd149…` |
| `redacted_archive_scan.py` | `c1ba8295…` |

As varreduras registram, de cada achado, só regra, arquivo, linha, commit e a "forma": comprimento, classes de
caractere e entropia. Não há valor nem prefixo; conferi campo a campo antes de versionar.

A pasta foi excluída do ruff (`pyproject.toml`, `extend-exclude`), como os outros artefatos arquivados em
`docs/`, para os scripts ficarem idênticos ao que rodou.

**Desfecho do gate, posterior a este relatório:** o dono dispensou a atestação em 2026-09-24
(`WAIVED_BY_OWNER`, **não** `CLEARED`; registrado em `2026-09-24-prompt2-auditoria-tecnica.md`, linha 10).
`docs/evidence/secret-rotation-attestation.md` continua inexistente, e as 7 classes sem registro de rotação
continuam pendentes.
