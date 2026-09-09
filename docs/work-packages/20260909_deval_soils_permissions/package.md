# DEVAL soils permissions repair

## Incident and scope

On wepp1, job `8f5235c2-dec2-432e-9cfb-8db389283175` failed at
2026-09-09 21:16:02 UTC for `last-ditch-illusion/disturbed9002`:
`IOError: Failed to open local file .../soils/soils.parquet` with errno 13.
The populated, valid parquet was owned by UID 1002/GID 130 with mode 0600;
the renderer uses UID 1000/GID 993 and supplementary GID 130.

Scope: restore readable publication of `Soils.dump_soils_parquet` output and
recover this report. Preserve atomic replacement, data, and orchestration.
This restores the existing shared-filesystem render obligation in
`docs/schemas/weppcloudr-render-execution-contract.md`, Common Orchestration
Responsibilities; it does not change report behavior or schema.

## Precedent and cause

- July 22 commit `1dcce3bbaf` replaced direct parquet writing with an atomic
  temporary-file write. Temporary mode 0600 became the published file mode.
- August 14 commit `a5eb4867a` changed the renderer to a non-root identity.
- September 4 commit `14b46625b` and the completed
  `20260821_weppcloudr_execution_backend_refactor` package repaired shared
  groups and fencing/export paths, but did not correct parquet publication.
- `docs/standards/hardening-lifecycle-standard.md` governs this recurrence.

The existing atomic publication mechanism is retained. Explicit mode 0644
restores readable generated data, including rewrites of affected 0600 files.
No periodic chmod, additional retry, or renderer identity change is introduced.
Report route authorization and run directory access remain the access boundary.

## Compatibility and regression evidence

No keys, columns, values, paths, or model artifacts change. The only intended
artifact difference is readable permissions. Test actual parquet creation and
replacement with prior modes 0600/0640/0644 under umask 0077; read back contents
and verify temporary-file cleanup. Empty summary retains its existing no-op.
Hostile paths and authentication are outside this unchanged writer boundary.

The live check regenerates the affected parquet with the candidate method in
an isolated worker-container process, compares its DataFrame with the original,
and renders it using the deployed renderer identity. A file backup permits
restoration if data parity fails. This canary does not deploy the source fix.

## Signals and lifecycle

Hypothesis: explicit publication permissions eliminate this errno-13 failure
after soils regeneration. Health signals are readable regenerated parquet,
unchanged data, and successful RQ report completion. Danger signals are changed
data, permission failure after a rewrite, or other render errors.

Use recurrence-triggered observation: future DEVAL permission failures or
renderer identity changes require a fresh incident referencing this record.
Retain the canary backup until permanent rollout passes the write-to-render
check. The one-file chmod is incident recovery; the writer correction replaces
it as the durable solution. No scheduled mitigation is added.

Security impact is low: read access to generated soil summary data is restored
within the existing run tree; no write privilege or endpoint access is added.
