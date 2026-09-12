# Frozen report export for Cain L0

<!-- DOC-SYNC-20260912 -->
> **Estado de publicação em 12/09/2026:** leia [a continuidade atual](../../PUBLICATION_STATUS_20260912.md). Branch `validation/retest-six-20260911`. O código deste projeto foi publicado na branch indicada. O candidato CAIN Supply permanece sem aprovação de estabilização. Afirmações anteriores de “sem push” descrevem a etapa histórica anterior à autorização.
<!-- /DOC-SYNC-20260912 -->


This small producer-owned distribution does not import the research pipeline.
It supports only `charters/scientific_state.json` and `docs/EVIDENCE_REGISTRY.md`.
These are documented historical reports, not certified experiment reproductions.
Read current repository instructions and freeze policies before admitting them.

Install the `predictor-research-snapshot==1.0.0` wheel and this wheel into an isolated
environment. This utility requires Python >=3.11; the full Crypto application keeps
its >=3.13 requirement and dependencies. No source-path injection is required.

```powershell
python -m pip install --no-index --find-links C:\Cripto\cain-l0\wheels crypto-research-export==1.0.0
crypto-research-export --root C:\Cripto\cain-l0-exporter-20260911 --admission C:\Cripto\cain-l0\admission.json --output C:\Cripto\cain-l0\publications\new.json --exported-at 2026-09-11T07:00:00Z
```

The timestamp above is syntax only: supply the actual export time, or preserve the
original timestamp for an exact replay. Each admitted input must have a previously
checked SHA-256; changed input or a source changing during the export is rejected.
An explicit admission file contains policy `crypto-frozen-reports-local/1`, `read:
true`, `sources` (relative path to SHA-256 map), `code_revision`, and
`exporter_revision` (commit or source digest, never an invented commit).

The destination must be outside the source checkout, within C:\Cripto on this PC.
Existing output is never overwritten. The main Crypto CLI also recognizes
`research-export` before importing the pipeline, if this optional distribution is
installed. Its help and export dispatch do not load scientific internals.

States are literal source values. H<n> identifies a hypothesis status report, not a
trial attempt; CLAIM-CR-* identifies a documented claim. Event, registration and
historical availability times remain null when absent. Revisions include exact
support; differing revisions coexist without pretending receipt time determines
truth. Narrative reasons remain in exact evidence; structured `reason=null` is
explicitly a limitation. No hypotheses, trials, authorizations or scientific data
are created or changed. The source fixture suite is independent of the predictor
test suite and avoids its imports/fixtures.
