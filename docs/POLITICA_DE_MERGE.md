# Política de merge — por que o `main` quebrou três vezes em 2026-09-04/05

> **Ação pendente do dono:** duas caixas em *Settings → Branches → regra do `main`*.
> Ver "O conserto" no fim. Nenhuma mudança de código resolve isto.

## O que aconteceu

Em pouco mais de 24h o `main` foi corrompido silenciosamente **três vezes**:

| # | O que se perdeu | Como |
|---|---|---|
| 1 | Fix de `covariance_type="diag"` (PR #86) | squash-merge descartou o hunk |
| 2 | Fix de `predict()` dentro do laço de retry (PR #90) | squash-merge descartou o hunk |
| 3 | `main` inteiro inoperante (PRs #92 + #93) | merge combinou duas versões do mesmo fix |

A terceira foi a pior: `v3/macro_features.py` ficou com a cópia duplicada de
`_add_business_days` (do #92) **e** a linha de import do #93, que não traz
`timedelta`. Qualquer chamada a `build_dxy_return` com o lag default levantava
`NameError`. A covariável DXY do H7 ficou inoperante, e 10 testes falhavam no
`main`. Corrigido no PR #94.

## O diagnóstico ERRADO, registrado de propósito

Durante a auditoria eu afirmei três vezes que *"o CI valida a branch do PR, nunca
o `main` resultante"*, e propus criar um workflow novo para rodar a suíte em push
para `main`.

**Isso está errado.** `.github/workflows/ci.yml` declara `on: push:` **sem filtro
de branch** — o CI já roda no `main` a cada merge, e sempre rodou. Um workflow
novo seria puro ruído.

Fica registrado porque o erro é instrutivo: a conclusão parecia óbvia e
explicava os fatos, mas nunca tinha sido conferida contra o histórico de runs.

## O diagnóstico CORRETO

O CI não falhou em rodar. **Nada espera por ele.**

Linha do tempo real do terceiro incidente (runs do workflow "CI"):

```
06:34:48   PR #92 mergeado  -> c3d5223 no main         CI verde
06:35:36   "Merge branch 'main'" na branch do #93      CI FALHOU  (runs 388/389)
06:35:42   PR #93 mergeado  -> db6cf44 no main         6 SEGUNDOS DEPOIS
```

Nenhum CI termina em 6 segundos. O merge aconteceu com os checks **ainda
rodando**, e eles ficaram vermelhos depois — no PR e no `main`.

E há um segundo mecanismo, mais sutil, que explica por que o híbrido nasceu:

- o CI do PR #93 rodou às **05:21**, contra um `main` que **ainda não continha o
  #92**;
- o #92 entrou às **06:34**;
- ninguém revalidou o #93 contra o `main` novo antes de mergear às **06:35**.

Ou seja: o resultado verde do #93 era **verdadeiro e obsoleto ao mesmo tempo**.
Ele atestava um merge contra uma base que já não existia.

Os dois primeiros incidentes têm causa distinta e já corrigida: os fixes perdidos
**não tinham teste que falhasse na sua ausência** (medido por mutação na auditoria
de 2026-09-05; ver `docs/HYPOTHESES.md`). Um CI que roda não pega o que nenhum
teste cobre. Hoje ambos têm cobertura.

## O conserto

**Branch protection, em *Settings → Branches → regra do `main`*:**

1. **Require status checks to pass before merging**
   Impede merge com CI vermelho ou pendente. Teria bloqueado o merge das 06:35:42.

2. **Require branches to be up to date before merging**
   Força revalidar o PR contra o `main` atual antes de mergear. **É a que teria
   impedido o híbrido:** o #93 seria obrigado a incorporar o #92 e rodar de novo,
   e o `NameError` apareceria antes do merge, não depois.

Marcar como obrigatórios os quatro jobs: `quality`, `all-extras`, `container`,
`python-314-experimental`.

Sem a caixa 2, a caixa 1 sozinha **não** teria evitado o incidente 3 — o #93
tinha checks verdes, só que contra a base errada.

## O que este repositório já faz, e que não substitui o acima

- O CI roda em `push` e `pull_request`, incluindo `main`.
- O job `all-extras` instala `hmmlearn`/`numpy`/`scikit-learn` e exercita o núcleo
  HMM. Sem ele, 4 testes viram skip — inclusive
  `test_v3_hmm_no_lookahead.py`, que guarda a afirmação científica central do
  projeto. Quem roda `uv sync --extra test` local vê "verde" sem ter testado HMM.

  E os 4 skips **subestimam** o buraco. Medido em 2026-09-06 no `main` (`3d2e18b`):

  ```
  uv sync --locked --all-extras   ->  978 passed
  uv sync --locked --extra test   ->  944 passed, 4 skipped   (total coletado: 948)
  ```

  A diferença de 30 não aparece como skip: são testes que **nem chegam a ser
  coletados** sem os extras. O skip é visível e conta como aviso; a não-coleta é
  silenciosa. Um `pytest -q` local pode terminar verde tendo executado 3% menos
  testes do que o autor imagina — e é justamente a fatia que cobre o HMM.
- `tests/test_registry_e_scripts_encoding.py` e
  `tests/test_readme_reflete_charter.py` travam classes de deriva que já
  aconteceram de verdade.

Nada disso impede um merge apressado. Só a branch protection impede.

## Regra prática, enquanto as caixas não estiverem marcadas

Depois de **todo** merge no `main`, confirmar o resultado — não o status do PR:

```bash
git fetch origin main && git checkout main && git pull
uv sync --frozen --all-extras
uv run pytest -q
```

Foi assim que os três incidentes foram descobertos: rodando a suíte contra o
`main` real, não confiando no "mergeado com sucesso".
