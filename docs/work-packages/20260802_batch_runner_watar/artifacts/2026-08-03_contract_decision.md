# SURF-02C Batch Runner WATAR Contract Decision

**Date**: 2026-08-03 01:52 UTC
**Starting implementation revision**:
`593e0601a8ded6b171e541b33fd3f59155a965a2`
**Composed owners**: DOM-01, SURF-02A, SURF-02B
**Classification**: Operator-authorized bounded cross-owner enhancement,
SURF-02C / GOV-00A-M1F
**Security impact**: High

## Operator Decision

The operator asked Codex to add ash transport (WATAR) to Batch Runner with the
same retry patterns as existing stages, required WEPP completion, Batch Runner
UI integration, and AshPost wiring. The operator then asked Codex to verify the
work would be contract first, approved and published the work-package scaffold,
and directed Codex to execute `20260802_batch_runner_watar`.

On 2026-08-03 Roger Lew then explicitly stated, "Roger Lew authorizes the
recommended contract." That statement approves the exact recommended choices:
a bounded cross-owner enhancement path composing DOM-01 and SURF-02A/B without
advancing them; timestamp-authoritative retry; successful AshPost no-data
completion; generic directive UI; inline leaf execution; Batch Runner use of
the existing Ash-owned timestamp; clone-only base inputs; and old-state
directive normalization. It is not approval to alter ash science, parameter
defaults, formulas, units, output schemas, authentication, or other Batch
Runner stages.

## Normative Contract

The canonical finite contract is recorded in
`docs/work-packages/20260802_batch_runner_watar/artifacts/field_matrix.md`.
In summary:

1. Batch Runner exposes one directive with slug `run_watar` and label
   `Run WATAR`. It represents the combined Ash simulation and AshPost pipeline.
2. The directive is stored with existing Batch Runner run directives and is
   rendered and saved through the existing generic directive UI. It introduces
   no standalone Batch Runner payload field or endpoint.
3. WATAR is eligible for a leaf only when the leaf contains `ash.nodb`. When
   `ash.nodb` is absent, `run_watar` is excluded from completion proof even if
   its batch directive is enabled.
4. An eligible WATAR stage may begin only when the same leaf has non-null
   `TaskEnum.run_wepp_hillslopes` and `TaskEnum.run_wepp_watershed` timestamps.
   Single-storm climates are rejected explicitly because WATAR requires daily
   hillslope water output. Before WATAR, Batch Runner calls the existing
   `ensure_hillslope_interchange`, `ensure_totalwatsed3`, and
   `ensure_watershed_interchange` helpers in that order, then requires
   `wepp/output/interchange/H.pass.parquet`, `H.wat.parquet`, and
   `totalwatsed3.parquet`. A helper exception or still-missing file fails the
   leaf explicitly and leaves `run_watar` unset.
5. Batch execution uses the copied leaf `Ash` controller state: stored fire
   date, initial white/black ash depths, model, transport mode, rasters, and
   advanced parameters. Batch Runner must not introduce alternative defaults or
   reinterpret scientific values.
6. `Ash.run_ash` remains the synchronous owner of hillslope ash simulation,
   `AshPost.run_post`, output versioning/documentation, query-engine catalog
   publication, and the final `TaskEnum.run_watar` timestamp. Batch Runner must
   not set a duplicate or early timestamp.
7. Completion means `TaskEnum.run_watar` is timestamped only after AshPost
   returns successfully. For a burned/data-producing leaf, that includes its
   current version manifest, generated documentation, datasets, and catalog
   update. For a legitimate no-data leaf, `watershed_daily_aggregated` returns
   `None`; AshPost stores null return-period state, updates the catalog, returns
   successfully without normal datasets/version/docs, and the leaf is complete.
   Any exception leaves the timestamp absent and the leaf failed/incomplete and
   retry eligible.
8. Default Run Batch selection is timestamp-authoritative, matching existing
   Batch Runner stages. It skips a leaf when every enabled applicable
   completion task, including eligible WATAR, is timestamped. A retry with WEPP
   complete and WATAR missing reruns WATAR without rerunning completed upstream
   stages. Classification does not audit WATAR artifact presence, version, or
   catalog state after a valid timestamp. `Remove existing files` retains its
   existing explicit full-rerun semantics.
9. A newly initialized leaf inherits WATAR inputs by the existing `_base` clone.
   This enhancement does not add selective resynchronization of `ash.nodb` into
   already-created leaves. Operators who intentionally change WATAR inputs after
   leaf creation must use the existing `Remove existing files` full-rerun path.
10. Existing batches, including serialized directive maps without `run_watar`,
    load compatibly. Post-load normalization inserts every missing
    `DEFAULT_TASKS` key with enabled state `True`, so an old batch can display,
    disable, save, and reload `run_watar`. It affects completion/execution only
    when `ash.nodb` exists.
11. Batch WATAR acquires sorted combined NoDir maintenance locks for `climate`,
    `landuse`, and `watershed`, using the same archive-form preflight, retry
    attempt count, and linear retry delay as existing Batch Runner root locks.
    It rechecks directory form after acquisition and never invokes the
    standalone RQ wrapper. The existing one-job-per-leaf guard owns `ash/`
    writes; no separate ash-root NoDir lock exists.
12. Existing Batch Runner authorization, CSRF, run-id/path validation,
    active-job guards, NoDb/NoDir locking, RQ response shapes, parent/leaf/
    finalizer topology, and failure metadata remain unchanged.

## Applicable Canonical Contracts

| Canonical contract | Applicability and SURF-02C disposition |
| --- | --- |
| `docs/ui-docs/controller-contract.md` | Governs the generic directive UI, request helpers, lifecycle, and actual-render/controller tests. No shared helper contract changes. |
| `docs/schemas/rq-response-contract.md` | RQ response and error shapes remain unchanged. WATAR runs inside the existing leaf boundary unless implementation evidence requires a separately approved amendment. |
| `docs/schemas/weppcloud-csrf-contract.md` | Existing authenticated Batch Runner mutations and CSRF behavior remain unchanged. |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Existing BatchRunner/Ash persistence, cache, and lock rules apply; no schema removal or lock weakening is allowed. |
| `docs/work-packages/20260727_watar_ui_contract_pilot/artifacts/field_matrix.md` | Existing standalone WATAR fields, parser keys, state, and RQ inputs remain canonical and unchanged. |
| SURF-02C field matrix and GOV-00A-M1F registration | Own the finite cross-owner Batch Runner directive, eligibility, WEPP ordering, AshPost completion, and retry behavior added here. |

No contract conflict was found. This checkpoint adds an operator-approved
bounded enhancement composition of
existing owners; it does not advance or close SURF-02A or SURF-02B and does not
rewrite the verified DOM-01 standalone field contract.

## Compatibility and Data Impact

The change is additive. No user-visible key, column, route, or standalone WATAR
payload is renamed or removed. Old BatchRunner NoDb documents may lack the new
directive key and continue to use the existing enabled-by-default lookup.
Non-WATAR leaves exclude the optional timestamp. WATAR outputs use the current
Ash/AshPost schemas and versioning without mutation. Runtime retry
classification remains timestamp-only; generated-output validation is a
pre-release evidence gate rather than a recurring classifier cost.

This package does not perform a project data/schema mutation. It generates
already-defined WATAR artifacts in additional batch leaf workspaces.

## Security Impact

Security impact is high because an authenticated Batch Runner action will cause
additional expensive model execution and run-tree writes. The implementation
must preserve admin/JWT/CSRF gates, batch leaf path confinement, active-job
guards, existing root locks, explicit failures, and resource-bounded Ash
execution. A dedicated security review is required before closeout.

## Regression and Evidence Plan

Before production edits, add or identify focused tests for:

- directive serialization, snapshot rendering, saving, and old-state loading;
- optional completion with and without `ash.nodb`;
- exact WEPP timestamp prerequisites, single-storm rejection, three approved
  recovery helpers, required interchange files, and explicit failure;
- successful `Ash.run_ash` invocation using persisted state;
- no early timestamp when AshPost fails and successful no-data completion;
- retry selection that reruns WATAR without rerunning completed WEPP;
- old-state disable/save/reload normalization;
- leaf `(False, elapsed)` failure metadata and final batch failure summary;
- no new endpoint, auth, or CSRF surface; and
- non-WATAR backward compatibility.

Generated-output acceptance requires a disposable WATAR-enabled batch leaf with
representative per-hillslope ash parquet, current AshPost datasets and README/
version metadata, catalog publication, a `run_watar` timestamp, and successful
skip/retry evidence. A separate no-data fixture proves successful catalog update
without normal post datasets/docs. The existing RQ topology must not change.

## Checkpoint Gate

Implementation conformance is pending. Production files must not be edited
until this decision, field matrix, GOV-00A-M1F/SURF-02C registration, two raw
independent reviews, and their disposition are committed together as a
standalone ancestor. The ancestor revision must then be recorded in the package
tracker and ExecPlan.
