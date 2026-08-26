# Peak-Flow Census Data-Contract Compatibility and Regression Plan

## Scope and Timing

This plan was written before reusable census code or schemas were added. It
governs the faithful extraction of the accepted Phase 2A pilot behavior from
`tools/peakflow_phase2a_pilot.py`. The committed Phase 2A artifacts and the
immutable evidence rooted at
`/home/workdir/peakflow-phase2a-evidence/8162d509d69cb4da` remain read-only
compatibility authorities.

The extraction is additive. It does not change the Phase 2A `1.0.0` files,
their hashes, columns, units, null meanings, or the existing pilot tool. New
census documents use their own versioned schemas and retain enough provenance
to relate each new record to the old evidence without rewriting it.

## Existing Contract Inventory

The Phase 2A JSON schemas cover the scenario manifest, eight-hillslope pilot
selection, fixed 64-terminal summary, and exit report. Their serialized
authorities are under
`docs/work-packages/20260808_peakflow_phase2a_pilot/artifacts/`. The scenario
manifest pins the source commit, observer SHA-256, two scenario authorities,
input-tree hashes, and 140-hillslope counts. The pilot selection pins the
selection and baseline evidence hashes. The terminal summary fixes 64
requested and terminal trials and links the Parquet ledgers by size and hash.

The external Parquet artifacts have these logical contracts:

- `baseline-inventory.parquet` has one row per scenario and hillslope. It
  records identifiers, soil and cover values, terrain/path covariates, event
  and solver counts, runtime, and trace/pass hashes. Physical and temporal
  units are carried in names such as `_mm_h`, `_m`, `_m2`, and `_s`.
- `baseline-events.parquet` has one observer solver-call row keyed by scenario,
  hillslope, year, day, OFE, and ordinal. Depths are meters, rates and peaks
  are meters per second, durations are seconds, and solver or forcing fields
  describe the accepted observer result.
- `terminal-ledger.parquet` has one row per pilot trial. It records status,
  runtime, return code, output locators and hashes, before/after input hashes,
  the sole changed input, and mutation realization. Its flattened columns vary
  by hillslope and mutation family, so the new terminal JSON contract will use
  structured maps while leaving this ledger unchanged.
- `event-pairs.parquet` outer-joins observer calls on scenario, hillslope,
  year, day, OFE, and ordinal. Baseline and mutant measurements use explicit
  suffixes. Missing events are null and distinguished by presence booleans;
  they are never converted to numeric zero. Candidate and diagnostic flags
  are booleans.

Downstream compact artifacts include `mutation-terminal-summary.json`, storage
manifests, `candidate-events.csv`, the exit report, and later routing evidence.
The reusable local-census engine must reproduce the mutation summary and event
pair semantics. Routing topology, watershed runs, channel outputs, replay
adjudication, and their storage manifests are deliberately outside the new
planning and execution contracts.

## Additive Census Contracts

The census layer introduces independently versioned study-manifest,
trial-plan, terminal, and validation-report JSON contracts. Existing Phase 2A
fields retain their names and meanings when represented. New required fields
bind records to a canonical manifest, ordered plan, source input, observer
executable, schema, and evidence root. Readers must reject unsupported major
schema versions; compatible additions require optional fields or a minor
version increment.

A study manifest declares site and scenario names, read-only input
authorities, input-tree hashes, an executable path and SHA-256, an evidence
root, discovery filename patterns, mutation families, screening floors, and
any explicit population exception. The study ID is the SHA-256 of the
canonical manifest with no embedded ID field.

A trial plan contains ordered trial records and frozen input authorities. Its
plan ID is the SHA-256 of the canonical ordered records plus authority hashes.
Each record states requested, eligible, or excluded status; an excluded record
has a stable reason. Eligible records include the exact relative input file,
structured field or line/token positions, source value, requested change,
expected realized value, source-file hash, and an evidence-relative output
locator. Trial IDs combine readable site/scenario/hillslope/family/direction
components with a plan-ID suffix.

A terminal records one explicit planned trial's terminal disposition and binds
the plan, trial, input, executable, and schema hashes. Mutation realization
records before and after file hashes and the exact field values. Reuse is
allowed only when all binding hashes match. A validation report reports totals,
hash verification, invalid records, and whether completeness was established;
it never treats a missing or stopped terminal as success.

All JSON is UTF-8 with sorted keys, two-space indentation, and a trailing
newline. Canonical identifier hashing uses sorted-key compact JSON with no
insignificant whitespace. Paths stored in portable plan records are relative
to their declared root except for explicitly declared authority roots. Source
trees are read-only. Evidence locators must resolve beneath the evidence root.

## Compatibility and Regression Checks

Before handoff, automated tests and generated summaries must establish all of
the following:

- The old pilot artifacts retain their committed SHA-256 values and the new
  engine reads rather than rewrites them.
- Planning the frozen eight-hillslope pilot produces exactly 64 eligible trial
  identities and the same scenario, hillslope, family, and direction matrix.
- Validation of immutable Phase 2A evidence reports 64 complete terminals,
  64 trials with exactly one changed input, 14,157 outer-joined rows, 30
  baseline-only rows, 25 mutant-only rows, 697 candidate rows, and 61 trials
  with a candidate.
- Representative full-precision baseline, mutant, delta, and flag values are
  compared directly against `event-pairs.parquet`; no rounding is introduced.
- Pairing retains baseline-only and mutant-only rows as null measurements plus
  presence flags. Zero remains a measured zero.
- Mutation tests prove first-horizon Ksat factors of `0.99` and `1.01` and
  paired `inrcov`/`rilcov` deltas of `-0.01` and `+0.01`. Missing tokens,
  clipping, serialization erasure, and extra changed files fail explicitly.
- A non-Topanga synthetic site with noncontiguous, nonnumeric-in-sequence
  hillslope IDs plans without source edits. Scenario population mismatch fails
  unless the manifest records an explicit exception.
- Repeated planning from identical authorities is byte-for-byte equal. A
  changed manifest, authority hash, ordered record, or eligibility result
  changes the applicable content ID.
- Path tests reject source or evidence escapes, symlink escapes, unpinned or
  hash-mismatched executables, shell interpretation, implicit all-selection,
  and terminal reuse with any binding mismatch.
- The generated Topanga plan totals recompute from its records and include no
  watershed executable, route command, channel hydrograph, routing closure, or
  channel-output locator. No full-census terminal or outcome ledger is created.

Generated-run regression checks cover the bounded validation fixture only:
copied run inputs must hash to the source authorities before mutation; exactly
one declared soil or management file may differ afterwards; observer trace and
hillslope pass hashes must be retained; and every terminal must remain below
the evidence root. The complete Topanga plan is planning evidence only and may
not generate run artifacts in this package.

## Compatibility Disposition Rules

Any changed Phase 2A denominator, metric, null meaning, unit, event key,
screening flag, or mutation realization is a scientific compatibility failure
and blocks preparation GO. Any undisclosed schema removal or rename is a data
compatibility failure. Any path, symlink, executable, subprocess, or terminal
reuse violation is a security failure. Failures must be recorded explicitly in
the preparation disposition; they must not be hidden by fallback behavior.
