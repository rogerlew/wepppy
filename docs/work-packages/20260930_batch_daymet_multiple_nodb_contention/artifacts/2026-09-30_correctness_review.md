# Correctness and User-Experience Review - Batch Daymet Multiple NoDb Contention

## Metadata

- **Package**: `docs/work-packages/20260930_batch_daymet_multiple_nodb_contention/`.
- **Reviewer**: independent correctness-review agent, Codex; 2026-09-30.
- **Scope**: Daymet extraction, PRISM routing, full Climate build router,
  batch startup/resync ownership, recovery publication, and real-file tests.
- **Commit context**: uncommitted candidate based on
  `bbace6023575d29ca00a26f1ad2a7776e957fc8a`.
- **Canonical contracts**: `docs/schemas/nodb-persistence-concurrency-contract.md`,
  "Writer Ownership and Mutation Topology"; `docs/schemas/climate-parquet-lineage-contract.md`,
  "Daymet acquisition source preservation"; artifact observability and generated-artifact
  validation standards.
- **Related security artifact**: `artifacts/2026-09-30_security_review.md`.

## User Outcome and Source Conformance

Observed Daymet with spatial mode Multiple must finish a concurrent batch leaf,
preserve unrelated durable edits, and publish scientifically equivalent climate
inputs. Relevant input changes must reject superseded collection. Failure must
preserve the generation present when the failing stage began, retain useful
attempted work, and omit whole-build completion.

The extraction retains Daymet numerical calls and argument values. Collection
runs outside the controller lock. The existing finalizer locks, hydrates durable
state, compares captured inputs, applies explicit derived fields, and dumps once.
Observed/ObservedPRISM enter the existing bounded PRISM finalizer. The full router
defers its legacy early metadata/file reset until successful finalization; direct
Daymet calls retain their sidecars and existing subclimate state. Supported string
years become integers after successful finalization.

Atomicity is per finalized stage. In a full Multiple build, successful Daymet
replacement remains committed if subsequent PRISM collection fails; the previous
whole-build hillslope generation has already been removed. The subclimate
mappings remain unset, `has_climate` is false, `sub_summary` returns None, and
normal WEPP preparation rejects the incomplete climate. Completion, export and
event hooks do not run. This follows the ExecPlan's explicit fresh-finalized
Daymet→PRISM sequence and the canonical NoDb transaction rules. No requirement
for a combined atomic build was found; that redesign is not part of this repair.

Batch hillslope entry acquires existing effective and lexical climate-root guards
before startup/reset/resync. Their deterministic acquisition excludes a duplicate
even when reset changes a projection's effective path. Acquisition retry does
not replay callback failure. Startup retains live Climate controller tokens.
Resync uses normal locked fresh hydration and atomic persistence.

No scientific formula/default, queue edge, RQ result shape or controller schema
change was found. This is conformance repair under unchanged normative behavior.

## Valid-State and Input Matrices

New regressions reside in `tests/nodb/test_batch_daymet_multiple_contention.py`.
Names below identify exact fixtures; broad counts do not imply exhaustive coverage.

| State | Valid? | Required outcome | Direct evidence |
| --- | --- | --- | --- |
| Climate directory absent | Yes | Create and publish valid outputs | `test_observed_build_valid_state_matrix`, `absent` cases |
| Climate directory present-empty | Yes | Build without requiring old derived files | State matrix, `empty` cases |
| Populated accepted outputs | Yes | Preserve last committed stage on failure; replace on successful stage | State matrix, `populated` cases; Daymet failure test; real CLIGEN replay |
| Supported legacy string years | Yes | Persist parsed integer years after success | `test_daymet_direct_preserves_sidecars_and_normalizes_legacy_years`, integer/string cases |
| Malformed changed year | No | Superseded failure; retain old accepted output and failed attempt | `test_daymet_build_failure_retains_previous_and_attempted_artifacts`, `malformed` case |
| Relevant concurrent year edit | Yes | Preserve edited intent; reject publication | Daymet failure test, `relevant` case |
| Unrelated same-size edit | Yes | Preserve edit through Daymet and PRISM finalization | `test_daymet_multiple_same_size_rewrite_survives`, both phases |
| Duplicate entry / projection reset | Yes | One cooperating climate owner; successor enters after release | `test_batch_leaf_guard_excludes_duplicate_before_and_after_root_reset`, plain/projection cases |
| Standalone Climate writer active | Yes | Automatic startup does not revoke its token | `test_batch_startup_preserves_live_standalone_climate_token` |
| Current/legacy resync with unrelated edit | Yes | Normal legacy enum admission; hydrate after acquisition, preserve edit and apply only input delta | `test_batch_climate_resync_hydrates_under_lock_and_preserves_unrelated_edit`, current/legacy cases |
| Daymet collection / NoDb replace failure | Exceptional | Keep accepted generation and attempted CLI/PRN/status | Daymet failure test, `collection`/`dump` cases |
| PRISM worker / NoDb replace failure | Exceptional | Keep accepted generation and attempted hillslope CLI/status | `test_observed_prism_retains_failed_attempt`, both cases |
| Full Multiple build: Daymet succeeds, PRISM fails | Exceptional partial build | Retain committed Daymet and failed PRISM attempt; no whole-build readiness/completion or downstream WEPP consumption | `test_multiple_prism_failure_retains_committed_daymet_and_blocks_wepp` |
| Working and failed attempts | Yes | Browse/download and ZIP/restore preserve bytes and status | `test_observed_attempt_browser_archive_restore`, Daymet/PRISM × working/failed |
| Unknown commit recovery | Exceptional | Explicit failure; retain accepted/attempted generations visibly | `test_unknown_commit_recovery_records_remain_visible_and_archivable` |
| Managed/unmanaged output projection | Yes/No | Supported projection works; escaping/unmanaged direct builder rejects | Existing `test_direct_climate_build_directory_containment`; root projection identity test |

The 12-case full-build matrix separates root state (absent/empty/populated)
from mode (Observed/ObservedPRISM) and spatial mode (Single/Multiple). It uses
producer seams while retaining real routing, publication, serialization, reload
and completion ordering. Numerical replay separately uses real scientific tools.
Required malformed/missing controller state is exceptional, not optional empty
artifact state; normal NoDb hydration retains its explicit failure contract.

## User-Reachable Error and Partial-State Policy

| Condition | Classification | User-visible result and partial state | Contract basis |
| --- | --- | --- | --- |
| Relevant input changed | Expected conflict | Explicit superseded error; preserve durable edit and accepted artifacts | Long-running collect/finalize contract |
| Required state/input malformed or missing | Exceptional | Validation/read exception; no derived publication | Required-read/durable hydration contract |
| Acquisition, CLIGEN or PRISM worker failure | Exceptional | Existing domain exception; visible failed attempt and last finalized generation remain; incomplete full Multiple build is not ready for WEPP | Collection failure leaves controller unmodified during that stage; artifact observability |
| NoDb lock unavailable/lost, or intervening precommit rewrite | Expected contention/exceptional ownership loss | Explicit lock/stale rejection; no stale-object dump retry | NoDb ownership/stale-write contract |
| NoDb replacement failure | Exceptional | Explicit error; reversible publication restores accepted artifacts and retains attempted work | Atomic persistence/publication contract |
| Post-replace commit cannot be read | Exceptional | Explicit unknown outcome; retain generations; no completion timestamp | Existing finalizer contract and artifact observability |

Batch domain errors continue through the existing wrapper/classification. A failed
parent or successful RQ wrapper alone does not prove successful leaf artifacts.
An occupied or abandoned Climate token requires the existing explicit operator
recovery workflow; automatic startup no longer revokes that controller's token.

## Generated Artifact Evidence Chain

| Stage | Direct evidence | Result |
| --- | --- | --- |
| Persisted intent | Full mode/state matrix and Observed/Multiple router; captured years/station/settings | Pass locally for named fixtures |
| Reloaded state | Normal `Climate.load_detached` after unmocked serializer/finalizer transactions | Pass |
| Generated intermediates | Real CLIGEN Daymet CLI/PRN/source parquet; real 12-band GeoTIFFs, GDAL sampling and pyo3 PRISM revision; semantic equality with legacy numeric baseline and relative SHA-256 manifest construction | Pass for bounded offline fixture |
| Exact consumed input | Actual `WeppPrepService.prep_climates` copies candidate `_1.cli` to `wepp/runs/p1.cli`; real ClimateFile frame and bytes match | Pass |
| User-facing artifact inspection | Actual browse/download routes and canonical archive/restore functions in container test harness | Pass locally; deployment identities pending |
| Execution / cluster result | Exact candidate image/revision, RQ tree, fresh output and dashboard on open-wepp.org | Pending separate cluster gate |

Only remote acquisition is supplied offline in numerical replay; CLIGEN, GDAL,
pyo3 revision, ClimateFile parsing, serialization, publication and downstream
copy are real. The one-year synthetic fixture proves bounded numerical parity;
it does not certify all climate datasets or reproduce cluster load/path identity.

Independent selections passed: Daymet/PRISM persistence/retention/legacy
**10 tests**; ownership **5 tests**; real-numeric/archive **5 tests**; final
state/recovery **13 tests**; final legacy/full-Multiple failure selection **3 tests**.
Parent validation reports **35/35** in the final new module. The initial fixture
cache-path error was corrected without mocking
lock ownership. An old-path selector during the module move collected zero
selected tests and was rerun against the new path. The two original pre-fix
stale-write failures remain in `artifacts/2026-09-30_writer_attribution.md`.

## Findings and Post-Fix Disposition

| ID | Severity | Finding / correction | Status |
| --- | --- | --- | --- |
| COR-01 | High | `wepppy/nodb/batch_runner.py` startup/reset/resync bypassed climate ownership and startup revoked live Climate locks. Dual root guards, acquisition-only retry, preserved Climate tokens, and fresh locked atomic resync pass direct ownership/current/legacy regressions. Source-level defect corrected; actual Kubernetes writer remains unattributed. | Resolved locally |
| COR-02 | Medium | `wepppy/nodb/core/climate_observed_build.py` omitted legacy year normalization. Successful finalization now assigns both parsed integers; string/integer readback cases pass. | Resolved |
| COR-03 | Medium | Initial tests used text doubles instead of scientific/generated/consumer evidence. Real CLIGEN and GDAL/pyo3 PRISM replay matches the legacy numerical baseline, source parquet/PRN semantics and exact downstream hillside CLI bytes/rows. | Resolved for bounded local fixture |
| COR-04 | Medium | Hidden deleting stages discarded failed work and rollback consumed its only copy. Visible status-bearing attempts retain originals while publication consumes redundant copies. Working/failed attempts and unknown-outcome recovery pass real browse/download and canonical ZIP/restore byte checks. Current canonical inventory records these obligations. | Resolved locally |

## Review Checks

- [x] Current canonical intent and conformance-fix classification are named.
- [x] Valid root states and input/mode combinations are reviewed separately.
- [x] Direct unmocked tests exercise changed locks, hydration, serialization,
  artifact replacement/rollback, preparation copy and archive/restore boundaries.
- [x] Scientific producer/consumer doubles are supplemented with actual CLIGEN,
  GDAL/pyo3, real format parsing and exact consumed-input evidence.
- [x] Relevant edits reject publication; unrelated edits survive.
- [x] Expected empty artifact state remains valid; malformed required state fails.
- [x] Failed work, status and recovery records remain visible and archivable.
- [x] Full Multiple second-stage failure preserves the committed Daymet stage,
  rejects WEPP readiness and omits completion/export/event hooks.
- [x] Local validation, cluster acceptance, deployment and recovery claims are distinct.
- [ ] Exact candidate passes production-equivalent open-wepp.org integration.

## Artifact Observability Gate and Residual Risk

Comparable module: Climate. Ordinary successful artifacts remain under `climate/`:
Daymet source parquet, PRN/PAR/CLI, radiation provenance CSV, CLIGEN diagnostics,
PRISM rasters, hillslope CLI and exported CLI parquet. Visible `daymet-build-*`
and `prism-build-*` directories retain working/failed attempts with
`build-status.json`; successful redundant copies are cleaned. Recovery copies
use visible `derived-backup-*`. Historical hidden copies are not migrated or
deleted. The current inventory and rationale are in
`docs/schemas/climate-parquet-lineage-contract.md#daymet-acquisition-source-preservation`;
operator behavior is in `docs/dev-notes/batch-climate-rap-finalization.md`,
"Batch ownership" and "Publication and recovery".

Root guards retain the existing six-hour TTL without renewal. Local evidence does
not establish maximum cluster phase duration, cross-node resolved path spelling,
shared Redis identity, production UID/GID/mount parity or the incident writer.
The wrapper covers hillslope climate ownership; it does not prove exclusion
across the later watershed lifecycle. Broader parameter/wind/leap-year and large
spatial datasets retain existing coverage and require representative cluster
evidence. No deployment, original batch replay, affected-run repair or incident
resolution is proved by this review.

## Verdict

- **Local correctness gate**: pass for the reviewed candidate and focused evidence.
- **Unresolved findings**: High 0; Medium 0; Low 0.
- **Release recommendation**: local review permits the next gate; broad regression
  must pass before the separately authorized exact-candidate cluster integration.
  Cluster release and package closure remain on hold until that evidence exists.
- **Highest completion claim**: implemented and locally validated for the recorded
  persistence, numerical and artifact fixtures; not environment validated.
- **Reviewer sign-off**: independent correctness-review agent, 2026-09-30.
