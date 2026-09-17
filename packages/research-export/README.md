# Frozen report export for Cain L0

> Current engineering and reading order: [project continuity](../../CONTINUAR_AQUI.md). Dated audit results belong to their recorded commits, not automatically to the installed exporter.
>
> Before reusing exported scientific statements, read the [evidence errata](../../docs/ERRATA_AUDITORIA_20260915.md). H6 has observed n=84, while the preserved power table uses reference n=60. The exporter transports literal admitted sources and does **not** apply the errata or include it automatically. Preserve the historical source and accompany its interpretation with the correction.

This small producer-owned distribution does not import the research pipeline. The Snapshot exporter supports only `charters/scientific_state.json` and `docs/EVIDENCE_REGISTRY.md`. These are historical reports, not certified experiment reproductions. Read repository instructions and freeze policies before admitting them.

## Install the current producer

The [package manifest](pyproject.toml) declares `crypto-research-export==1.0.1`, Python `>=3.11`, and `predictor-research-snapshot>=1.0.1,<2`. For the pinned integration described in [the integration guide](../../docs/FINAL_INTEGRATION_AUDIT.md), the producer uses Snapshot `1.0.1`. The full Crypto application keeps its separate Python `>=3.13,<3.15` requirement.

Use an isolated producer environment and a wheel directory containing the verified exporter and contract artifacts from the intended source revisions:

```powershell
python -m pip install --no-index --find-links C:\Cripto\cain-l0\wheels predictor-research-snapshot==1.0.1 crypto-research-export==1.0.1
python -m pip check
crypto-research-export --help
```

These commands install packages; documentation changes do not run them or update an operational environment. If the required wheels are absent, stop and obtain/build the intended artifacts through the documented integration process. Do not downgrade to `1.0.0` to make this example resolve. A version number alone does not certify artifact bytes: verify the source revision, provenance and SHA-256 before installation.

**Legacy receiver is separate:** the pinned CAIN receiver retains its Snapshot `1.0.0` reader in a different environment. That is not the producer dependency and must not be upgraded or copied into the producer environment merely to make their version numbers equal. See [current and historical integration combinations](../../docs/FINAL_INTEGRATION_AUDIT.md).

## Snapshot export

```powershell
crypto-research-export --root C:\Cripto\cain-l0-exporter-20260911 --admission C:\Cripto\cain-l0\admission.json --output C:\Cripto\cain-l0\publications\new.json --exported-at 2026-09-11T07:00:00Z
```

The historical root and timestamp above are example syntax, not the current checkout or time. Select the intended source checkout and supply the actual export time, or preserve the original timestamp for an explicitly identified exact replay. Never backdate a new export to imply historical scientific availability.

Each admitted input must have a previously checked SHA-256. Changed input or a source changing during export is rejected. The admission file contains policy `crypto-frozen-reports-local/1`, `read: true`, `sources` (relative path to SHA-256 map), `code_revision`, and `exporter_revision` (commit or source digest, never an invented commit).

The destination must be outside the source checkout and, on the documented Windows PC, inside `C:\Cripto`. Existing output is never overwritten. The main Crypto CLI recognizes `research-export` before importing the pipeline if this optional distribution is installed. Its help and export dispatch do not load scientific internals.

States are literal source values. H<n> identifies a hypothesis status report, not a trial attempt; CLAIM-CR-* identifies a documented claim. Event, registration and historical availability times remain null when absent. Revisions preserve exact support; differing revisions coexist without pretending receipt time determines truth. Narrative reasons remain in evidence; structured `reason=null` is a limitation.

No hypotheses, trials, authorizations or scientific data are created or changed. The fixture suite is independent of the predictor test suite and avoids its imports/fixtures. Do not silently change source hashes or broaden the allowlist to transport a correction as if it were part of an old admission.

## Optional Bundle export

Bundle export is a separate interface. The `bundle` extra adds `predictor-research-bundle==1.0.0`; install `crypto-research-export[bundle]==1.0.1` only in the auxiliary producer environment with the verified shared wheel available. Sources, command arguments, fingerprints and limits are documented in [RESEARCH_BUNDLE_V1.md](../../docs/RESEARCH_BUNDLE_V1.md).
