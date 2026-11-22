# Ablation Testing Protocol

Canonical protocol for troubleshooting WEPP numerical instabilities and undesired
modeling outcomes (including parity regressions).

Incident package contract:
- `docs/ablation/README.md`
- `docs/ablation/TEMPLATE_*.{md,csv}`
- `python tools/ablation_protocol.py init --incident-id <incident_id>`
- `python tools/ablation_protocol.py finalize --incident-id <incident_id>`

## Scope

Use this protocol when any of the following occur:
- Floating-point traps, hangs, stalls, or non-termination in hillslope/channel/watershed runs.
- Large or unexpected output shifts versus a known-good binary.
- Compiler-sensitive behavior changes (for example `ifort` vs `gfortran`).
- Patch stacks that are no longer explainable from evidence.

## Required Principles

1. Evidence before edits.
2. Observability before guessing.
3. One behavioral change group per ablation lane.
4. Roll back no-effect changes.
5. Keep only changes that measurably improve stability, intent, or correctness.
6. Document hypotheses, edits, and outcomes as you go.
7. Guard-only hardening is preferred, but scientifically justified upstream
   mutation lanes are allowed when guard lanes do not close the failure.
8. Upstream mutation lanes must pass explicit scientific-validity and
   non-regression gates before promotion.
9. Upstream mutation lanes must cite active science-contract references or
   explicitly record `model_gap` / `requires_scientific_review`.
10. Promotion requires fuzzy-regression-case execution with documented outcomes
   and documented failures.
11. Decisive watershed pass/fail claims require full configured simulation
    period execution (typically 100 years); truncated-period lanes are
    exploratory only.
12. Large watershed ablations should execute in isolated `/wc1` workspaces on
    `wepp1`/`wepp2`, with large payload trees held out of git.

## Required Workflow

### 1) Establish Reproducible Baseline

Record:
- Run input set (`*.run`, pass files, management files, climate/soil/slope files).
- Binary identity (path, build flags, compiler).
- Expected/known-good comparator binary (if available).
- Exact command used to execute the run.
- Configured simulation period and whether run is exploratory or decisive.

Required replay context (hillslope/watershed):
- Stage target `p<id>.*` files (`.run`, `.man`, `.slp`, `.cli`, `.sol`, `.err`) and
  run-shared context files from the same `runs/` directory.
- For WEPPcloud hillslope replays, treat these as required when present:
  - `wepp_ui.txt`
  - `pmetpara.txt`
  - `snow.txt`
  - `gwcoeff.txt`
  - `chan.inp`
  - `chntyp.txt`
  - `tc.txt`
- Do not assume isolated `p<id>.*` copies are sufficient.

Capture baseline artifacts:
- `stdout.txt`
- `stderr.txt`
- key outputs (`chnwb.txt`, `loss_*.txt`, `soil_*.txt`, `ebe_*.txt`, etc.)
- status marker presence (`WEPP COMPLETED ...`)

Baseline gate before lane conclusions:
- Verify staged replay includes run-shared context inventory and record it in
  `notes.md` and `artifacts/repro/`.
- If stars/crashes are source-only, re-test with full shared context before
  classifying as non-reproducible.
- For watershed durability incidents, do not classify a lane as pass/fail
  decisive unless it completes the full configured period.
- Recommended preflight:

```bash
src_runs="/geodata/wc1/runs/<prefix>/<runid>/wepp/runs"
stage_runs="docs/ablation/<incident_id>/artifacts/repro/staged/runs"
for f in wepp_ui.txt pmetpara.txt snow.txt gwcoeff.txt chan.inp chntyp.txt tc.txt; do
  if [ -f "$src_runs/$f" ] && [ ! -f "$stage_runs/$f" ]; then
    echo "MISSING_SHARED_CONTEXT $f"
  fi
done
```

### 2) Add Observability Signals First

Before adding guards/fixes:
- Enable `wepp_observe.on` in the run directory.
- Add coarse progress markers around candidate failure boundaries.
- Keep observability gated so production behavior is unchanged when observe is off.

Observability requirements:
- Tags must identify phase and context (year/day/element/channel/segment).
- Log should allow unambiguous "last good marker" and "first failing boundary".
- Instrumentation must be minimally invasive.

### 3) Form Semi-Substantiated Hypotheses

Every hypothesis must cite at least one concrete signal:
- last marker before trap,
- stack/backtrace location,
- denominator/state value from logs,
- parity shift tied to specific routine/phase.

Do not proceed with broad patches backed only by intuition.

### 4) Classify Lane Type and Mutation Eligibility

Lane types:
- `O*`: observe-only lane (instrumentation, no behavior change).
- `G*`: guard/hardening lane (numerical boundary checks, fail-fast contracts).
- `U*`: upstream mutation lane (scientific/process-level behavior change).

Upstream mutation (`U*`) eligibility gates (all required):
1. At least one baseline/guard lane was executed and did not close the failure.
2. Proposed mutation is tied to a specific routine/equation and process context
   (for example infiltration/percolation routing, not broad speculative edits).
3. Proposed mutation includes a scientific rationale and expected directional
   effect on model behavior.
4. Scientific invariants and non-regression gates are defined before lane
   execution and frozen for the campaign.
5. `contract_refs` cite active science-contract invariants before execution, or
   the lane records `boundary_disposition=model_gap` or
   `boundary_disposition=requires_scientific_review`.
6. If a campaign already has frozen promotion thresholds (for example paired A/B
   gates), reuse them unchanged unless a governance update explicitly revises
   them.

`tools/ablation_protocol.py finalize` enforces the `contract_refs` and
`boundary_disposition` columns for policy-era `U*` lanes. A `U*` row must either
provide semicolon-separated `SC-...#INV-...` references or set
`boundary_disposition` to `model_gap` or `requires_scientific_review`.
For policy-era incidents with `U*` lanes, finalize also requires
`artifacts/logs/contract_observations.csv`.

### 5) Design Ablation Lanes

Use a matrix with:
- Lane 0: baseline (no behavioral change).
- Guard lanes (`G1..Gn`): one independent hardening change group each.
- Upstream mutation lanes (`U1..Un`): one independent scientific mutation group
  each.
- Optional observe-only lane(s).

Rules:
- Prefer single-file or single-routine deltas.
- Keep write scope disjoint per lane where possible.
- Do not combine behavioral changes unless prior lanes prove necessity.
- Upstream mutation lanes must remain one-mechanism-per-lane.
- For each `U*` lane, define and log expected invariant behavior (for example:
  no negative storages, bounded state transitions, mass-balance sanity).
- For each `U*` lane, populate `contract_refs` in `matrix.csv` with
  semicolon-separated `SC-...#INV-...` references, or leave `contract_refs`
  empty only when `boundary_disposition` is `model_gap` or
  `requires_scientific_review`.

### 6) Execute and Compare

For each lane, capture:
- return code,
- completion marker status,
- last observe marker,
- last parsed progress triplet (if applicable),
- output diffs versus baseline and known-good comparator.
- For upstream mutation lanes, capture invariant checks and non-target deltas.
- For upstream mutation lanes, capture `contract_refs` and confirm the observed
  behavior matches the cited boundary disposition.
- For watershed/mixed incidents, record durability metadata in `matrix.csv`:
  - `durability_lane` (`decisive|exploratory|na`)
  - `configured_simulation_years`
  - `simulated_years_completed`
- `tools/ablation_protocol.py finalize` enforces this contract for policy-era
  watershed/mixed incidents and rejects decisive `PASS` rows that do not
  complete the full configured period.

Classify outcomes:
- `no_effect`: failure signature unchanged.
- `progress_shift`: failure moved downstream/upstream.
- `resolved`: run completes.
- `regression`: stability fixed but parity/output behavior unexpectedly degraded.
- `scientifically_implausible`: failure changed but invariant checks violated.

Execution/storage requirements for large watershed lanes:
- run decisive full-period lanes on `wepp1`/`wepp2` in isolated `/wc1` staging
  workspaces (not in production source trees)
- retain compact logs/diffs/manifests in the incident package
- keep large raw payload mirrors and core dumps outside git (prefer `/wc1`
  holdout paths) and document their location when retained

### 7) Keep / Roll Back Decision

Mandatory rollback policy:
- Roll back any change that does not produce intended effect,
  unless it clearly improves stability, intent, or correctness.
- Roll back broad speculative bundles after extracting only proven minimal fixes.

Keep criteria:
- demonstrable failure-mode improvement,
- evidence-based rationale,
- acceptable parity/regression profile for the intended release scope.
- For upstream mutation lanes, keep is allowed only if:
  - target failure improves per frozen target gate,
  - non-target regressions stay within frozen tolerance,
  - scientific invariants remain satisfied,
  - contract references or model-gap records are complete,
  - observed boundary disposition matches the cited contract,
  - rationale remains scientifically defensible for the modeled process.

### 8) Run Fuzzy Regression Gate (Required)

Before promoting any candidate patch (guard or upstream mutation), run the
fuzzy-regression case set and record results.

Minimum fuzzy-regression case set:
- all incident-triggering seeds (current package repro seeds),
- active fuzzy watchlist seeds for the same scope/profile when available,
- for hillslope incidents, the permanent watchlist in
  `docs/ablation/hillslope_watchlist.csv`,
- release sentinels previously used for non-regression (if defined in package
  contract).

Generated CSV metadata must use LF line endings, matching `.gitattributes`,
before final checksums are computed. Otherwise Git's CRLF-to-LF normalization
changes the committed bytes after they were hashed. Normalize metadata only;
do not rewrite retained native input, output, source or log evidence to satisfy
this requirement. The canonical manifest writer emits LF directly.

Required fuzzy artifacts per promotion candidate:

- `artifacts/logs/fuzzy_case_results.csv`:
  - one row per fuzzy case replay (`case_id`, `seed_id`, `lane_id`,
    `binary_path`, `pass_fail`, `exit_code`, `signal`,
    `success_marker_found`, `stderr_path`, `stdout_path`, `notes`)
- `artifacts/logs/fuzzy_failures.md`:
  - concise failure ledger with signature family, first failing case(s),
    and links to stderr/stdout artifacts.
- `artifacts/logs/contract_observations.csv` when contract invariants are
  observed:
  - one row per contract observation (`case_id`, `contract_id`,
    `invariant_id`, `contract_ref`, `status`, `observed_value`,
    `disposition`, `evidence_path`, `notes`)

Contract-observation pipeline requirements:
- policy-era incidents with `U*` lanes must include
  `artifacts/logs/contract_observations.csv` before finalize can succeed.
- policy-era `contract_observations.csv` files must contain the canonical
  columns listed above.
- policy-era status values must be one of:
  - `satisfied`
  - `violated_expected`
  - `violated_unexpected`
  - `not_applicable`
  - `not_observed`
- policy-era `disposition` values must use the science boundary vocabulary from
  `docs/science-contracts/evidence-classification.md`.
- for each observation row, `contract_ref` must match the composed
  `contract_id#invariant_id`.

Confounder-channel separation reporting (policy era):
- classify each governance-evaluated row as one of:
  - `NUM` (numerical boundary instability),
  - `CONF_PARSE` (parse/EOF/provenance confounder),
  - `MIXED` (causal ordering unresolved or dual-channel evidence).
- do not force unresolved rows into pure numerical or pure parse bins.
- any promotion or re-entry summary that reports numerical-rate outcomes must
  also report `CONF_PARSE` and `MIXED` counts and denominator basis.
- in M18 scope, these fields are artifact-level governance requirements and are
  not finalize-blocking schema fields in `tools/ablation_protocol.py`.

Fuzzy gate pass criteria:
- no fuzzy case that passed in comparator/baseline now fails in candidate, and
- no new failure signature family is introduced without explicit approval.

Fuzzy gate failure criteria:
- any comparator-pass fuzzy case becomes fail on candidate, or
- candidate introduces a new unresolved signature family in fuzzy cases.

Canonical hillslope watchlist execution gate (pre-vendoring):

```bash
python tools/run_hillslope_watchlist.py --binary /workdir/wepp-forest/src/wepp_hill
```

### 9) Promote Minimal Fix

When a lane resolves the issue:
- distill to the smallest patch that preserves the resolved behavior,
- re-run baseline + comparator checks,
- pass fuzzy regression gate,
- keep observability hooks available for future troubleshooting.

### 10) Documentation (Required)

Maintain a live troubleshooting record under `docs/ablation/` (incident package
directory or legacy incident markdown retained under that folder).
Each entry must include:
- Hypothesis ID and evidence.
- Exact source edits (file + routine + rationale).
- Run artifacts/paths.
- Outcome classification.
- Keep/rollback decision and reason.

Minimum sections per incident:
- Problem statement.
- Baseline signature.
- Hypotheses.
- Ablation matrix and results.
- Fuzzy-regression-case results and failure ledger.
- Final patch set.
- Residual risks / follow-up experiments.
- For upstream mutation lanes, also include:
  - scientific rationale and assumptions,
  - `contract_refs` or explicit `model_gap` / `requires_scientific_review`,
  - invariant checklist and results,
  - non-regression gate definition and pass/fail disposition.

For each update cycle, regenerate:
- `artifacts/manifest.csv` and
- `artifacts/checksums.sha256`
using `tools/ablation_protocol.py finalize`.

Resolved hillslope incident promotion requirement:
- If a hillslope incident status is moved to `resolved`, `resolved-and-hardened`,
  or `closed`, add/update its seeds in `docs/ablation/hillslope_watchlist.csv`
  in the same change set.

## Upstream Mutation Gate Contract (Required for `U*` Lanes)

Before running any `U*` lane, freeze and document:
- `contract_refs`: active science-contract invariant references in
  `SC-...#INV-...` format, or an explicit `model_gap` /
  `requires_scientific_review` record.
- `target gate`: what constitutes meaningful target improvement.
- `non-target gate`: tolerated change bounds for non-target slices/cases.
- `scientific-validity gate`: invariant checks that must remain true.
- `sensitivity gate` (if applicable): positive-control detection must remain
  intact.
- `stop-rule`: number of failed candidates before freeze/accepted-upstream
  recommendation.

If a campaign already defines these gates, do not change thresholds mid-cycle.
Any threshold revision requires a separate governance update with rationale.

## Output Parity Guidance

When stability fix changes outputs:
- Determine whether differences originate in hillslope or watershed phases.
- Compare against known-good binary on identical inputs.
- Treat early termination comparisons as structural-only (not scientific parity).
- Do not declare scientific regression without completed-run parity context.

## Guardrail Summary

- No patch piles without attribution.
- No "fixes" that cannot be tied to observed failure boundaries.
- No silent acceptance of no-effect changes.
- No upstream mutation lanes without scientific rationale plus invariant checks.
- No upstream mutation lanes without `contract_refs` or explicit model-gap /
  scientific-review disposition.
- No mutation promotion without explicit non-regression gate pass.
- No promotion without fuzzy-regression-case execution and documented outcomes.
- No handoff without reproducible evidence and documented decisions.
