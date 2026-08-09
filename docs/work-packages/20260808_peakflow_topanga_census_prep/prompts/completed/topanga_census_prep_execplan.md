# Prepare a Durable Engine and Freeze the Topanga Census Matrix

**Completed 2026-08-09**: Implemented the reusable engine, reproduced pilot
evidence with a bounded generated trial, froze 1,088 eligible Topanga trials,
closed security/code/QA gates, and published a preparation GO disposition.

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current throughout execution.

## Purpose / Big Picture

After this package is complete, an operator can describe a peak-flow mutation
study with a versioned manifest, generate a deterministic trial plan for any
compatible site, execute a small validation fixture, and verify local
hillslope mutation metrics without editing Python source. Topanga will have a
frozen complete trial matrix ready for a separate execution package. This
package must not execute that full matrix.

## Progress

- [x] (2026-08-09 04:22 UTC) Scaffold the preparation package and record the
  preparation-then-execution sequence.
- [x] (2026-08-09 04:39 UTC) Wrote and linted the data-contract compatibility
  and regression plan before code or schema changes.
- [x] (2026-08-09 05:01 UTC) Published the complete Phase 2A hard-coded
  assumption inventory before extraction.
- [x] (2026-08-09 05:28 UTC) Implemented the reusable engine, schemas, and CLI.
- [x] (2026-08-09 05:59 UTC) Proved 64-trial pilot parity, exact generated
  h106 output parity, and synthetic second-site planning.
- [x] (2026-08-09 06:09 UTC) Froze and validated the complete Topanga plan:
  1,120 requested, 1,088 eligible, and 32 excluded records.
- [x] (2026-08-09 06:18 UTC) Completed security, code, and QA review gates with
  no unresolved medium or high finding.
- [x] (2026-08-09 06:22 UTC) Published the preparation GO disposition and
  execution-package handoff contract.

## Surprises & Discoveries

- Observation: the proven Phase 2A tool already separates hillslope mutations
  from routing commands, but its module constants, selection input, output
  package, and 64-trial assertion are pilot-specific.
  Evidence: `tools/peakflow_phase2a_pilot.py` defines `RUN_ROOT`, `SCENARIOS`,
  `HILLSLOPE_IDS`, `PACKAGE`, and the fixed trial-count assertion.
- Observation: the accepted Phase 2A terminal Parquet physically flattens
  hillslope-specific input-hash map keys into sparse columns.
  Evidence: `terminal-ledger.parquet` has 119 columns for 64 rows, including
  `input_hashes_before.p106.sol` and analogous columns per selected hillslope.
  The reusable JSON terminal therefore needs structured maps while preserving
  the old file unchanged.

## Decision Log

- Decision: split preparation from execution into separate work packages.
  Rationale: the exact eligibility and trial matrix must freeze before new
  full-census outcomes exist, and the reusable engine must prove parity before
  consuming the larger compute budget.
  Date/Author: 2026-08-09 / requesting operator and Codex.
- Decision: prepare a faithful extraction, not a surrogate rewrite.
  Rationale: the Phase 2A mutation, observer, outer-join, and screening
  semantics are accepted evidence and must not drift during generalization.
  Date/Author: 2026-08-09 / Codex.
- Decision: place reusable logic under `wepppy/wepp/peakflow_census/` and keep a
  thin operator CLI at `tools/peakflow_census.py`.
  Rationale: site-independent contracts belong in importable, tested code;
  command parsing and human-facing execution stay in `tools/`.
  Date/Author: 2026-08-09 / Codex.
- Decision: supersede the first generated Topanga plan instead of overwriting
  it after resolving the observer executable locator.
  Rationale: the first plan pinned the accepted binary hash but named an
  unresolved locator. The existing clean WEPP-Forest worktree at commit
  `ea25ad79` contains `src/wepp_hill` with the accepted SHA-256, so a newly
  content-addressed plan is required and the earlier bytes remain preserved
  under `artifacts/superseded/`.
  Date/Author: 2026-08-09 / Codex.

## Outcomes & Retrospective

Complete with GO. The manifest-driven engine plans arbitrary compatible sites,
executes only explicit selections, preserves Phase 2A mutation, observer, and
outer-pairing behavior, and enforces content and path bindings. The immutable
pilot evidence and one newly generated bounded trial both prove parity. The
frozen Topanga plan contains 1,120 requested, 1,088 eligible, and 32 excluded
records and no routing concept. The only incomplete environment-level check is
canonical container pytest, blocked by the known full `/tmp` condition; local
focused suites and all other gates pass. No full-census outcome was produced.

## Context and Orientation

The multi-site study is specified in
`docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md`.
Phase 2A proved 64 mutations across eight Topanga hillslopes and two scenario
strata. The current implementation is `tools/peakflow_phase2a_pilot.py`; its
mutation runner copies one hillslope input deck, modifies exactly one soil or
management file, runs the complete hillslope history with an observer-enabled
WEPP binary, and retains a trace plus hillslope pass. Its event pairing outer
joins baseline and mutant solver calls so an absent event is not confused with
zero.

A study manifest is a versioned JSON document naming a site, scenario input
authorities, approved executable and hash, evidence root, hillslope discovery
rules, mutation families, and screening policy. A trial plan is an immutable
JSON or Parquet enumeration of every requested, eligible, or excluded mutation
before model outcomes exist. A terminal disposition records whether one
planned trial completed, failed, or stopped and links its immutable evidence.

The full Topanga census is local-only. It includes first-horizon Ksat at
`0.99x` and `1.01x` and paired `inrcov`/`rilcov` at `-0.01` and `+0.01` in the
burned and undisturbed strata. Cover probes that cannot realize both directions
without clipping are excluded with a reason. Watershed routing, channel
hydrographs, canopy, LAI, and cross-site execution are not part of this plan.

## Plan of Work

First create
`docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/data-contract-compatibility-plan.md`.
It must inventory the Phase 2A schemas and downstream artifacts, define an
additive compatibility strategy, and list regression checks for pilot evidence
and generated run artifacts. Do this before editing code or schemas.

Next inventory the hard-coded assumptions in
`tools/peakflow_phase2a_pilot.py`. Preserve that tool and its committed evidence
as a compatibility authority. Create `wepppy/wepp/peakflow_census/` with small
modules for typed manifests, planning, mutations, observer parsing, event
pairing, terminal persistence, and validation. Create
`tools/peakflow_census.py` as a thin CLI. Do not add an external dependency.

The planner must discover hillslope identifiers from declared scenario inputs,
not a numeric range in source. It must validate that scenario strata cover the
same declared hillslope population or record an explicit site-manifest
exception. Mutation adapters must record the exact file, line or structured
field, requested change, source value, expected realized value, and before/after
hashes. They must reject clipping, missing tokens, extra changed files, and
values erased by serialization.

Make all identifiers content-derived. The study ID must hash the canonical
manifest. The plan ID must hash the ordered trial records and input authorities.
The trial ID must remain readable while also binding site, scenario, hillslope,
parameter family, direction, and plan ID. Writes must remain below the declared
evidence root; source authorities are read-only. Existing terminal artifacts
may be reused only when their plan, input, executable, and schema hashes match.

Define commands that plan without executing, validate a plan, execute an
explicit bounded selection, pair events, and validate artifacts. The execution
command must require an explicit plan and selection; it must never default to
"all". The future execution package may deliberately pass the frozen complete
selection after its own authorization gate.

Build tests under `tests/wepp/peakflow_census/`. Unit tests cover manifest
validation, content IDs, mutation realization, boundary exclusions, path-root
constraints, outer joins, flags, and retry rules. Integration tests use the
existing Phase 2A evidence to prove all 64 pilot trials, terminal counts,
14,157 event pairs, 30 baseline-only rows, 25 mutant-only rows, 697 candidate
rows, and representative full-precision metrics remain unchanged. A synthetic
second-site fixture with non-Topanga names and noncontiguous hillslope IDs must
plan successfully without code changes.

After parity passes, author the Topanga study manifest and generate the complete
trial plan without running it. Record exact denominators by scenario and
mutation family, every exclusion reason, expected runtime, expected retained
bytes, binary and input hashes, and the future external evidence locator. Verify
that the plan contains no watershed binary, channel output, routing closure, or
route command.

Finally complete the dedicated security review, code review, and QA review.
Publish `artifacts/preparation-disposition.md` with GO only if every acceptance
gate passes. That disposition names the frozen plan hash and instructs the next
agent to create a separately dated
`YYYYMMDD_peakflow_topanga_census_execution` package. Do not scaffold or run the
execution package before GO.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Inspect the current authority and record the compatibility plan:

    git status --short
    rg -n "RUN_ROOT|SCENARIOS|HILLSLOPE_IDS|64|PACKAGE|route" \
      tools/peakflow_phase2a_pilot.py

Run focused tests during implementation:

    wctl run-pytest tests/wepp/peakflow_census
    wctl run-pytest tests/investigations/test_peakflow_phase2a_pilot.py

The final planner interface must support commands equivalent to:

    wctl run-python tools/peakflow_census.py plan \
      --study-manifest docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-study-manifest.json \
      --output docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json

    wctl run-python tools/peakflow_census.py validate-plan \
      --plan docs/work-packages/20260808_peakflow_topanga_census_prep/artifacts/topanga-trial-plan.json

The preparation package may run only a bounded explicit validation selection,
such as the frozen Phase 2A trial IDs. It must not invoke an unrestricted full
Topanga execution.

Before handoff run:

    wctl run-pytest tests/wepp/peakflow_census
    wctl run-pytest tests/investigations/test_peakflow_phase2a_pilot.py
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260808_peakflow_topanga_census_prep

If the repository-wide suite is blocked by the known container `/tmp` capacity
condition, record the exact failure and retain passing focused evidence; do not
misreport the broad suite as passing.

## Validation and Acceptance

Acceptance is generated behavior, not only a scaffold. A clean checkout must
be able to validate the study manifest, generate the same plan twice with byte
equality, reproduce Phase 2A pilot metrics from immutable evidence, and plan a
synthetic second site. The Topanga plan must enumerate every requested trial,
mark each as eligible or excluded, and provide totals that recompute from its
records. No full-census terminal or outcome ledger may exist in the preparation
evidence root.

The security gate fails if a manifest can escape declared source or evidence
roots, redirect through a symlink, select an unpinned binary, or introduce shell
interpretation. The scientific gate fails if pilot metrics change, events are
inner-joined, missing events become zeros, cover values clip, or routing enters
the plan. Any failed gate produces a NO-GO disposition and keeps the execution
package blocked.

## Idempotence and Recovery

Planning is side-effect-free except for an atomic write of the requested plan
artifact. Repeating it with the same authorities must be byte-identical. Use
temporary files plus atomic replacement for manifests and ledgers. Never edit
`/wc1` scenario authorities or Phase 2A evidence. A stopped validation run keeps
its terminal record and may resume only after every bound hash matches.

Do not delete or overwrite a frozen plan. A legitimate contract or eligibility
change creates a new plan ID and updates the preparation decision log before
any execution authorization.

## Artifacts and Notes

Commit schemas, compatibility analysis, synthetic fixtures, Topanga manifests,
the frozen plan, compact parity summaries, reviews, and the final disposition.
Keep generated model traces and passes outside Git and record their locators,
sizes, hashes, formats, and retention policy.

## Interfaces and Dependencies

Use the Python standard library plus dependencies already present in WEPPpy;
do not add a package. The reusable package should expose stable equivalents of:

    load_study_manifest(path: Path) -> StudyManifest
    plan_trials(study: StudyManifest) -> TrialPlan
    apply_mutation(trial: PlannedTrial, run_dir: Path) -> MutationRealization
    execute_trial(trial: PlannedTrial, context: ExecutionContext) -> Terminal
    pair_events(baseline: DataFrame, mutant: DataFrame, trial: PlannedTrial) -> DataFrame
    validate_artifacts(plan: TrialPlan, terminals: Iterable[Terminal]) -> ValidationReport

Exact dataclass field layouts may evolve through the compatibility plan, but
the serialized schemas, units, nullability, content identifiers, and Phase 2A
parity expectations must be explicit before implementation.

Revision note (2026-08-09): Initial plan created to enforce the operator's
preparation-then-execution sequence and prevent another Topanga-specific
one-off.

Revision note (2026-08-09 04:39 UTC): Recorded the completed pre-code data
contract gate and the sparse legacy-terminal schema discovery so execution can
continue from the published compatibility authority.

Revision note (2026-08-09 06:22 UTC): Recorded completed implementation,
generated pilot parity, the frozen Topanga matrix, review gates, the known
container `/tmp` exception, and the final GO handoff.
