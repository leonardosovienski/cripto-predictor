# 04-cripto, revisado em 2026-09-25 (depois da execução dos Prompts 1 a 4)

Esta é a sequência de prompts do guia "Prompts por repositório" para o cripto (e para o Stocks, trocando repo e
ativos), corrigida com o que a execução de 2026-09-24/25 mostrou. **O original continua valendo onde não há
mudança.** Aqui vão só as regras novas do cabeçalho e os trechos corrigidos de cada prompt, com o motivo de cada
correção. A auditoria completa está em `docs/evidence/2026-09-25-revisao-completa.md`.

## Regras novas para todos os prompts (acrescentar ao cabeçalho)

1. **Dispensa da atestação.** O Prompt 1 só previa `CLEARED` pela atestação. Na prática, o dono dispensou a
   atestação no chat, e isso ficou registrado só no relatório do Prompt 2.
   - Correção: se o dono dispensar, o agente cria `docs/evidence/secret-rotation-waiver.md` com a data, o texto
     exato da dispensa, quem dispensou, as classes de credencial ainda sem rotação e as restrições que continuam
     valendo (nenhum código do projeto roda com credencial nem com rede).
   - O Prompt 2 aceita **a atestação ou a dispensa registrada**. O gate fica `WAIVED_BY_OWNER`, nunca `CLEARED`.
2. **Anexos versionados de verdade.** O `.gitignore` do cripto ignora `*.jsonl`. O `git add` da pasta de
   evidência pulou o ledger do 3c sem aviso, e os anexos dos Prompts 1 e 2 ficaram fora do repositório.
   - Correção: tudo o que o relatório cita vai em `docs/evidence/AAAA-MM-DD-promptN/`.
   - Antes do commit, confira com `git status --ignored` e `git ls-files` que nenhum arquivo citado ficou ignorado.
3. **Um PR por prompt.** Não misture no mesmo PR correção de etapa anterior ou aprovação de política.
4. **Sem `git merge`, nem local.**
   - Para trazer um commit de outra branch, use `cherry-pick` numa branch nova a partir do `main`.
   - Se o dono fizer squash-merge de uma PR anterior, recrie a branch cumulativa sobre o `main` novo, em vez de
     empilhar.
5. **Aprovação humana é explícita.** Aprovar limiar de política, abrir holdout ou dispensar gate exige
   palavras do dono sobre **aquele** ato. Delegação genérica ("pode escolher", "resolve tudo") não é aprovação,
   e o agente nunca marca `APPROVED` por conta própria.
6. **Proveniência que sobrevive ao squash.** Commits que provam ordem (pré-registro antes da execução, código
   antes do resultado) ficam em branches publicadas que **não** são apagadas, e o relatório cita o SHA e a branch.

## Prompt 2: pré-condição (substitui os itens 1 e 2)

```text
PRÉ-CONDIÇÃO (verifique primeiro)
1. Leia docs/evidence/secret-rotation-attestation.md ou docs/evidence/secret-rotation-waiver.md. Se nenhum
   existir, PARE e me avise.
2. Com atestação: compare com os achados do Prompt 1. Se alguma classe de credencial não estiver coberta,
   PARE e reporte.
3. Com dispensa: registre SECRET_ROTATION_GATE = WAIVED_BY_OWNER (nunca CLEARED). Nenhum código do projeto
   roda com credencial nem com rede até existir a atestação.
```

## Prompt 3a: registro de tentativas (substitui a última frase do item 4)

```text
Toda execução vira registro no TrialLedger do predictor_core. Se ele não existir, ou se o registro de
tentativas do projeto for protegido (ex.: trials.json no conjunto protegido da qualificação), use um ledger
equivalente append-only e encadeado por hash, versionado no repositório, e registre como dívida técnica.
Inclusive as execuções ruins. Nada é sobrescrito.
```

## Prompt 3b: política de decisão (acrescentar ao item 4)

```text
- A política nasce PROPOSED. Só o dono a aprova, com palavras explícitas sobre ela. Até lá, toda decisão é
  NO_DECISION.
- A política precisa cobrir, além de seeds/DSR/PBO/baselines/qualidade de dados:
  (a) a regra de seeds para modelo DETERMINÍSTICO (ex.: "1 seed basta se o modelo não amostra"), senão um
      modelo determinístico nunca decide;
  (b) o limiar de redundância da deduplicação do Prompt 4 (|ρ|, com a métrica);
  (c) a regra para hipótese que não é estratégia (IC/Spearman: IC95, poder mínimo, n mínimo), senão ela sai
      sempre NO_DECISION.
- DSR: se V[SR] não for estimável (Sharpes das tentativas sem base comum registrada), o DSR é N/A e a decisão é
  NO_DECISION. Nunca use PSR no lugar do DSR.
- PBO: CSCV padrão (Bailey et al. 2017). Se quiser purga entre blocos, declare como variante e justifique.
```

## Prompt 3c: checkpoint e pré-registro (acrescentar)

```text
- Checkpoint já presente no disco (baixado por outra sessão): pode usar sem baixar de novo, SE o sha256 bater com
  o oid LFS publicado na revisão fixada. Registre a origem da cópia.
- O pré-registro usa o TEMPLATE COMPLETO do Prompt 4, item 4: mecanismo esperado, features, target, período de
  desenvolvimento e de avaliação, universo, custos, protocolo, métricas primária e secundárias, política (id,
  versão, sha256), número máximo de variantes, seeds, holdout (ou "sem holdout" com o motivo) e critérios de
  GO/NO_GO/NO_DECISION. Grave-o no ledger de pré-registros e commite ANTES da primeira previsão.
- Deduplicação antes do backtest (Prompt 4, item 6), se houver séries dos fatores existentes. Se não houver,
  registre UNKNOWN.
```

## Prompt 4: holdout e deduplicação (substitui a primeira frase dos itens 5 e 6)

```text
5. Holdout selado: antes de selar, defina QUAIS avaliações ele reserva (ex.: só a avaliação final de hipóteses
   novas que o citarem no pré-registro) e o que fazer com a coleta PROSPECTIVA de hipóteses já registradas (ex.:
   H7, H8), cujo dado novo cairia na janela. Se isso depender de decisão do dono, pergunte antes de selar.
   Registre intervalo, identificador/hash (ou a regra do hash, para janela futura), momento da selagem e
   condições objetivas de abertura. Abrir exige aprovação humana registrada; nunca consultar iterativamente.
6. Deduplicação: o limiar vem da política versionada. Se a política não tiver limiar, a deduplicação é N/A e
   vira pendência para o dono. Não use 0,99 sem aprovação.
```

## O que ficou igual

- Prompt 1 inteiro (a stop condition estava correta: faltava só o caminho da dispensa, coberto acima).
- Prompt 2, itens 3 a 9.
- Prompt 3a, itens 1 a 3 e testes.
- Prompt 3b, itens 1 a 3 e testes.
- Prompt 3c, itens 2 a 4 e entrega.
- Prompt 4, itens 1 a 4 e 7, e a entrega.
