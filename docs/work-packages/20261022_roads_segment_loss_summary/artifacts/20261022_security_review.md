# Security review: Roads segment loss summary

## Metadata

- Package: `20261022_roads_segment_loss_summary`.
- Reviewer: independent integration_contract_review agent, 2026-10-22.
- Context: contract checkpoint `bac3042b1`; runtime changes in the working tree.
- Scope: `wepppy/nodb/mods/roads/_segment_loss_summary.py`, its Roads facade and
  controller integration, `tests/nodb/mods/test_roads_segment_loss_summary.py`,
  shared destination checks, CSV conversion and catalog discovery.
- Producer SHA-256:
  `ec7748c28f68415bafa5fddf73d38196d27f0906d6ba6573cc294f821878f097`.
- Test-module SHA-256:
  `6821fc5b52966615ce2842dadf9ef050684e0b082e6e3cf16fa2d5500ee94453`.
- Roads facade SHA-256:
  `4c371d014710f34c4355ee963d8a120c941645f832a6440eb31108581dcd6772`.
- Controller tests SHA-256:
  `811829b87eb07129d4a458ed5010e9cb512043d5306f9045a9e25f96a92db88d`.
- Related review: [contract integration review](20261022_contract_review_integration.md).
- Independent correctness: [final review](20261022_correctness_review.md), PASS.

## Security triage decision

Security impact is high because this changes a project file publication boundary.
A dedicated review is required. No new endpoint, credential, queue, subprocess,
network integration, native binary or dependency is introduced.

The threat model is the existing authorized Roads lifecycle, with one producer
per run and ordinary shared project readers. Run-root authorization remains with
existing browser/download routes. The review covers invalid persisted inputs,
source drift during production, filesystem aliases and publication failure; it
does not assert arbitrary adversarial concurrent directory-swap protection.

Valid states include populated native profile inputs, an existing empty or
skipped/failed-only manifest, legacy records lacking optional description/status,
and legacy climate without an explicit start year. Missing manifest or completed
sources, malformed identities/metrics/calendars and destination aliases are
contracted errors. Single-storm behavior remains unchanged.

## Findings

No confirmed high or medium code finding in the reviewed implementation.
No low finding is being accepted as an unrecorded exception.

| ID | Severity | Surface | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| EVID-01 | Gate evidence | Full user workflow and artifact observability | Reviewed retained UM1, canonical archive/restore and live Chromium/browser/download receipts and their executable scripts; details below | None for this security gate | Closed |

## Verdict

- Local publication/source-isolation checks: pass.
- Package security gate: pass for the reviewed implementation and local workflow.
- Unresolved code findings: high 0, medium 0, low 0.
- Release recommendation: security permits package closure once the package
  owner's remaining broad validation gates are dispositioned. No production
  deployment or production parity claim is authorized here.

## Surface checks

### Valid states and input safety

The producer creates a typed empty table without opening PASS/WAT or validating
an absent calendar. The final facade resolves model/climate state lazily only
after finding populated records; the separate correctness review identified and
closed the earlier eager-loading defect with actual empty-facade regressions.
It preserves omitted legacy status, optional descriptions
and the unclassified profile scope. Populated data uses the native geometry
validator and DuckDB over fixed source paths. Selected identifiers are registered
as a typed relation, not interpolated into SQL. Column expressions are static.
Required PASS NULL/nonfinite checks occur before aggregation; generated results
are checked for nonfinite values. No receiving-hillslope fallback remains.

### Filesystem and source identity

At `_segment_loss_summary.py:185`, shared destination validation rejects aliased
Roads parents and symlink members before source consumption or candidate writes.
The caller-supplied directory must resolve to the canonical Roads interchange
directory. Manifest resolution must match the canonical run-relative path.
The manifest and both consumed Parquets are hashed before their content is used,
then checked after reduction and again after writing the candidate.

The exclusive candidate open uses mode 0666 with the process umask; an existing
summary's mode is copied before writing. Publication fsyncs the candidate and
atomically replaces only the canonical summary. Publication failures raise an
explicit exception containing the retained visible candidate path. Source files
and the previous canonical output are not truncated, deleted or rewritten.

### Lifecycle, permissions and retained evidence

The facade delegates without changing NoDb persistence or queue wiring. The
existing controller returns ready resources only after the producer succeeds;
the existing run boundary records failure and re-raises on exceptions.
Candidates use the contracted visible `roads_segment_loss_summary.pending-*`
name. Successful publication consumes its candidate; failed candidates remain
available for inspection. Independent testing confirmed retry and native catalog
discovery with a retained failed candidate.

No auth, session, CSRF, secret, subprocess, network or supply-chain surface changed.
The existing shared CSV converter is reused and field-unit metadata does not
rename the existing headers. Schema metadata retains source hashes and policy.

## Validation evidence

Inspected `/tmp/roads-segment-focused-final.log`: canonical wctl run of the
source-summary and Roads controller modules completed with 76 passed and two
existing dependency deprecation warnings in 13.83 seconds. These include the
three actual empty-facade states. These are implementer-run results, not
represented as independently rerun pytest coverage.

Independent reviewer execution used `wctl exec -T weppcloud python -` and temporary
filesystem roots, the real native geometry API, DuckDB, PyArrow writer, shared
CSV converter and native-backed catalog builder. Runtime identity was uid 1000,
gid 993, supplementary group 993. Results:

- A manifest mutation injected after the real Parquet writer completed was
  detected by the second source check. Old summary bytes were unchanged and a
  readable two-row candidate remained. Retry and catalog discovery succeeded.
- Source-Parquet, manifest and output-directory aliases each failed before
  publication; previous output bytes were unchanged.
- Populated CSV headers exactly matched the original columns plus the appended
  provenance columns. No field-unit suffixes appeared.
- Empty manifest with absent sources and absent calendar produced the complete
  zero-row schema and a header-only CSV.
- On final review, a new real writer probe injected replacement failure, then
  archived and restored its retained candidate through canonical archive helpers.
  The candidate was an archive member and restored bytes plus mode 0640 matched.
  [Retained receipt](20261022_failure_candidate_archive_review.json) records the
  result. This independently covers failure evidence beyond the populated UM1
  archive's four core lineage files; only orchestration callbacks were isolated.

The committed test scenarios additionally cover no-export annualization, mixed
profile/remainder scope, invalid source values, duplicate/missing dates and years,
mode/umask, replacement failure, retained candidates and post-reduction drift.
The fixture dates deliberately exercise native key acceptance; they are not a
substitute for real UM1 calendar and source comparisons.

### Reviewed retained end-to-end evidence

Reviewed each receipt against its retained script, without treating a receipt's
boolean flags as independent proof of more than the script actually checks:

- [UM1 receipt](20261022_um1_validation.json) and [script](validate_um1.py): the
  actual Roads summary facade regenerates the isolated copy; every one of 34
  output rows is compared against original-source PASS sums and WAT areas. It
  records 4,810.818379721261 kg/year sediment, 216 protected scratch artifacts
  unchanged and 46 original Parquets unchanged. The independent correctness
  reviewer separately recomputed all six annual metrics and area-derived values.
- [Archive receipt](20261022_archive_validation.json) and
  [script](validate_archive.py): canonical `project_rq_archive` archive/restore
  operates on real files. Restored summary, both source Parquets and manifest
  preserve bytes and modes. Queue/status/lock/cache callbacks are deliberately
  isolated; this is not proof of live queued archive orchestration.
- [Browser receipt](20261022_browser_validation.json) and
  [script](validate_browser.py): real Chromium loads the live browse listing;
  live Parquet and CSV requests return HTTP 200 through existing authorization
  and feature DB checks. A short-lived run-scoped token derives from an existing
  active administrative account; no authentication result is mocked and no token
  is retained. Downloaded Parquet bytes match the restored file; CSV has 34 rows,
  the existing names plus appended provenance, matching per-row sediment and
  empty unavailable buffer aliases.

All three receipts bind the same generated summary SHA-256:
`68fa7acb7c2786efa83d0e24eaeeca1fa070d955a4ca41603be9cce66b910dc2`.
The validation process identity is uid 1000/gid 993. The live browser/download
evidence proves local service read access to the restored artifact.

## Residual risk and sign-off

Existing single-writer/run-access assumptions remain. Pre/post content hashes do
not prove arbitrary concurrent adversarial filesystem safety or a crash-durable
directory entry after replacement. No new guarantee of either is claimed.
The evidence establishes local container writer and live reader behavior, not
production-host mount/identity parity, every user-role authorization combination,
or the complete Roads hydrology/queue lifecycle. Existing access code is unchanged.

Reviewer signs off the inspected security and integration boundaries. EVID-01 is
closed and the independent correctness review is PASS. Package-wide broad-gate
disposition remains with the owner and is not replaced by this security review.

## Artifact observability gate

Canonical inventory: manifest, native H.pass/H.wat inputs, canonical summary,
visible failed candidates and existing Roads lifecycle logs. No hidden output,
CSV shadow or browser endpoint is added. Local writer failure/retry, live project
browser/download visibility and canonical archive/restore bytes, modes, core
lineage and failed-candidate member coverage are proven by the checks above. The artifact observability
gate passes within the stated local workflow and orchestration limits.
