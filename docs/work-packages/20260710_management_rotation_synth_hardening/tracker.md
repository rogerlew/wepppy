# Tracker - Management Rotation Synthesizer Hardening

> Living incident tracker for the AgFields `ncrop` overflow repair.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-10 19:26 UTC
**Current phase**: Closed
**Last updated**: 2026-07-10 20:24 UTC
**Next milestone**: Separate incident for residue-operation random roughness
**Security impact**: `low`
**Dedicated security review**: `no`

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Scanned the source run directory and isolated one failure family across all
  119 attempted hillslopes (2026-07-10 19:26 UTC).
- [x] Scaffolded the package, active ExecPlan, compatibility plan, and root tracker
  entry (2026-07-10 19:26 UTC).
- [x] Captured exact canola/oats fixtures and the p3733 17-year schedule.
- [x] Patched structural reuse, reachability pruning, residue-index remapping,
  and the 20-plant pre-write check.
- [x] Passed the focused rotation suite (8 tests), management suite (21 tests),
  module stubtest, repository stub check, broad-exception gate, and doc lint.
- [x] Replayed the generated p3733 management through `wepp_260430_hill`; the
  `ncrop` error is gone and the next error is the source plant's invalid `hmax=0`.
- [x] Completed code review, QA, validation summary, full-suite baseline
  disposition, root tracker lifecycle, and ExecPlan archive.
- [x] Reopened package, authored ADR-0016, and captured the exact 2017.1 source.
- [x] Implemented 2017.1/raw-98.4 normalization, source/comment preservation,
  additive provenance, active-plant exclusion, and legacy-state compatibility.
- [x] Passed 31 combined backend/rotation tests and all focused repository gates.
- [x] Replayed p3733: `ncrop` and `HMAX` errors are absent; separate
  `frcfac.for:184` random-roughness SIGFPE disposition is recorded.
- [x] Refreshed code review, QA, validation, UI acceptance status, and closure.

## Timeline

- **2026-07-10 18:46 UTC** - RQ job
  `5ced742c-5b8c-45ea-8d5e-054987448d24` failed after the first surfaced future
  raised for sub-field 3733.
- **2026-07-10 19:26 UTC** - Scanned all 119 `.err` files. Every attempted run
  reports `ncrop` above 20; observed values range from 34 through 50.
- **2026-07-10 19:26 UTC** - Reproduced `p3733`: one canola source plus sixteen
  identical oat sources produces 17 simulation years, 50 plant definitions, and
  136 operation definitions before the repair.
- **2026-07-10 19:42 UTC** - Exact regression passed after repair with 17 years,
  3 reachable plants, 10 operations, 1 initial condition, 17 surfaces, and 17
  yearly scenarios.
- **2026-07-10 19:48 UTC** - Real-binary replay advanced beyond `ncrop` and
  exposed `L179_weed` with `hmax=0`; no model parameter was altered.
- **2026-07-10 20:06 UTC** - Package reopened by maintainer request. All ten
  Jim-interface managements in the source archive contain the same residue-only
  `L179_weed` zero-height placeholder.
- **2026-07-10 20:24 UTC** - ADR-0016 ingestion milestone completed and package
  re-closed with review/QA disposition.

## Decisions Log

### 2026-07-10: Preserve stack-and-merge chronology

**Context**: The user expected spring operations to be combined with fall
operations. Inspection confirms that `stack-and-merge` already normalizes the
management rotations, removes a setup year as a standalone simulation year,
and either merges its distinct surface operations into the prior year or reuses
the retained year's already-combined surface.

**Decision**: Preserve that timeline behavior and repair definition reuse only.

**Impact**: The fix cannot reorder operation dates or change the 17-year crop
schedule. Tests will assert the retained schedule and surface operations.

### 2026-07-10: Deduplicate by model structure, not scenario name

**Context**: Prefixes make identical definitions look different by name. Names
are reference keys, not model parameters.

**Decision**: Compare reusable scenario objects while excluding graph pointers
and the top-level scenario name. Keep descriptions and all model data in the
signature, then remap references to the first canonical definition.

**Impact**: Exact repetitions are compacted, while definitions with any data or
description difference remain distinct.

### 2026-07-10: Treat residue-addition indices as scenario references

**Context**: `iresad` is a one-based plant scenario index but was parsed as an
integer, so prefixing and compaction could silently redirect residue additions.

**Decision**: Parse it with the same `ScenarioReference` mechanism as initial and
yearly plant references.

**Impact**: Both synthesis modes preserve the intended residue type as section
indices change, and reachability retains the referenced residue plant.

### 2026-07-10: Do not synthesize a replacement for invalid `hmax`

**Context**: Once `ncrop` was fixed, WEPP rejected `L179_weed` because `hmax=0`.

**Decision**: Preserve the uploaded parameter and document a source re-export as
the next project-level action.

**Impact**: The synthesizer repair remains parameterization-neutral. The current
project cannot complete WEPP until its plant source is corrected.

### 2026-07-10: Normalize the systematic residue placeholder at ingestion

**Context**: The maintainer identified `L179_weed` as Jim-interface output and
requested ZIP-ingestion normalization. All ten source files reproduce the same
zeroed applied-residue scenario.

**Decision**: Supersede the prior re-export-only handoff. Apply ADR-0016's
`0.00001 m` floor only when a nonpositive plant is referenced by residue-addition
operations and is not referenced as an active yearly or initial plant.

**Impact**: Newly ingested final managements pass WEPP's positive-`hmax`
validation while archived 2017.1 sources and active-crop parameters remain
unchanged. Provenance makes the fallback visible.

## Risks and Issues

- **Reference corruption** (`medium`): mitigate with full serialized round-trip
  and reference-resolution assertions.
- **Cross-year surface mutation** (`high`): never canonicalize surface or yearly
  scenarios; they remain isolated per synthesized segment.
- **Hidden distinct-plant overflow** (`medium`): fail before write when more than
  20 structurally distinct plant scenarios remain.
- **Dirty working tree overlap** (`low`): preserve the separate active AgFields UI
  package changes and touch only management-specific files plus shared docs.
- **Zero random roughness** (`high`): open outside-package finding; current binary
  SIGFPEs at `frcfac.for:184` after the height fallback clears validation.

## Validation

- Focused combined AgFields backend and rotation tests: 31 passed.
- Full management tests: 21 passed before the reopened milestone; rotation tests
  remain included in the final combined run.
- `stubtest` for the synthesizer: passed.
- Repository test-stub check: passed.
- Broad-exception changed-file gate: passed with net delta zero.
- Documentation lint: 17 files, zero errors and warnings before final archival;
  final closeout is re-linted.
- Full Python suite: stopped at the unrelated, independently reproduced Batch
  Runner fixture failure after 2,074 passed and 41 skipped.

## Handoffs

- Create a separate incident package before changing residue-operation `rro` or
  adding a `frcfac` denominator guard. The current evidence is captured in QA-06.
