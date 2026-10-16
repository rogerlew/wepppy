# MACA selector contract checkpoint

Starting HEAD: `88c8c9fdc`. Recorded 2026-10-16 UTC. Existing uncommitted EDDE,
NoScaling and attribution work is prior authorized work, not this implementation.
Operator approval: "okay. let's implement the selection anf patch the client".
The earlier local checkpoint-commit authorization persists; do not deploy.

Intended change: additive `maca_projection` request / `_maca_projection` saved
state, 40 allowed pairs, existing default, deterministic CCSM4 r6 member.
Source boundaries: pure MACA registry, downscaled client, Climate facade/stub,
parser/build helper, climate catalog/template, RQ validation mapping and tests.
No queue dependencies, auth changes, model transformations or new output schemas.

Applicable authority: new MACA selection contract and ADR-0097; project-owned
config capability eligibility (unchanged IDs/choices), RQ response/error and
controller state, NoDb persistence/concurrency, seed and precipitation scaling,
controller presentation, artifact observability/generated-artifact validation.
Add cross-references for the new field; do not rewrite unrelated owner contracts.

Compatibility/regression plan before data mutation: add one field, no rename or
bulk rewrite. Missing legacy field and new projects use old implicit default;
omission preserves current choice. Read-only controls and saved capabilities
retain authority. Existing PRN/CLI formats and native generation stay intact.
Read generated precipitation/date content; state/job success alone is insufficient.

| State/input | Expected behavior |
| --- | --- |
| New/legacy absent field | GFDL-ESM2G/RCP8.5 |
| Existing valid choice, field omitted | Preserve choice |
| Explicit valid pair | Persist under parse lock and use at build |
| Explicit empty/null/non-string/unknown/path-like | Local validation failure, rollback, no enqueue |
| Stored malformed field | Selected empty UI placeholder; omission/build fails explicitly |
| Another climate mode with hidden selector field | Ignore mode-specific field |
| Empty/populated climate output directory | Existing build behavior and visible artifacts |
| Provider/native generation failure | Existing failed-job behavior; no source substitution |
| Working/failed/completed | Normal status and browser/download artifact/log visibility |
| Prepared climate | Read actual wepp/runs/p*.cli values |
| Archive/restore | Canonical roundtrip preserves artifact bytes and saved selection |

Expected selection errors use the canonical MACA validation policy and current
RQ validation envelope. Other existing year/provider/CLIGEN errors retain their
existing contracts. Security impact low: exact identifiers only, existing endpoint.
Two independent read-only contract reviews must pass before checkpoint commit.
