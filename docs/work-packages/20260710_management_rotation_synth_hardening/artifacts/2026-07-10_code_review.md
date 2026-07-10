# Code Review - Management Rotation Synthesizer Hardening

## Metadata

- Package: `20260710_management_rotation_synth_hardening`
- Reviewer: Codex
- Date: 2026-07-10
- Scope: management parsing, reference remapping, structural reuse,
  reachability pruning, WEPP limit preflight, tests, fixtures, and documentation

## Review Findings

### CR-01 - Residue addition used an implicit, unremapped plant index

- Severity: high
- Status: resolved
- Evidence: `OpLoopCropland.iresad` was parsed as a raw integer while every other
  cross-section index used `ScenarioReference`. Prefixing or deduplicating plants
  therefore left residue additions pointing at the wrong global plant index.
- Resolution: parse `iresad` through the existing plant-scenario reference
  factory. Generic remapping now covers it in both synthesis modes. The
  end-to-end regression proves segment two points to `SEG2_L179_weed`; the
  p3733 regression proves structural reuse points to canonical `L179_weed`.

### CR-02 - Surface and year definitions must not be canonicalized

- Severity: high
- Status: resolved by design
- Evidence: setup-year composition can append operations to a prior surface.
  Sharing that surface with other years would mutate multiple simulation years.
- Resolution: only plant, operation, initial-condition, contour, and drainage
  definitions are canonicalized. Surface and year definitions remain isolated.

### CR-03 - Dead definitions could retain invalid or excessive section entries

- Severity: medium
- Status: resolved
- Evidence: a normalized two-rotation source may drop a setup year but retain its
  now-unreachable plant and initial-condition definitions.
- Resolution: traverse the final graph from the management loop and retain only
  reachable section definitions. Residue-addition references participate in the
  traversal, so referenced residue plants are not accidentally removed.

### CR-04 - Generic structural comparison could over-collapse scenarios

- Severity: medium
- Status: resolved by conservative identity
- Evidence: names differ after prefixing but model content may also differ subtly.
- Resolution: the signature excludes graph pointers and only the top-level name;
  it retains class, land use, description, all model values, sequence order, and
  canonical references. Any model-data or description difference stays distinct.

### CR-05 - Source management contained systematic zero-height residue plants

- Severity: high for the project retry; outside synthesizer scope
- Status: resolved in reopened ingestion milestone
- Evidence: the repaired p3733 management reaches plant validation and reports
  `HMAX <= 0.0 FOR CROP INDEX 2 (name=L179_wee)` for the referenced applied-residue
  plant. The regression confirms synthesis preserves `hmax=0.0` rather than
  inventing a replacement.
- Resolution: ADR-0016 applies the minimum serialized positive height at ZIP
  ingestion only to residue-only references. Both formats are covered; archived
  2017.1 input remains byte-identical and provenance reports the exact delta.

### CR-06 - Height normalization exposes zero-random-roughness SIGFPE

- Severity: high for project completion; outside authorized ingestion scope
- Status: open follow-up, explicitly dispositioned
- Evidence: p3733 replay clears `ncrop` and `HMAX <= 0`, enters simulation, and
  receives SIGFPE at `frcfac.for:184` (`rrc / rroinr`) after `RES_2` supplies
  zero random roughness.
- Disposition: do not normalize `rro` under this package. It is an operation
  parameter with separate scientific and Fortran-guard alternatives that need
  their own incident evidence and parameterization decision.

### CR-07 - Normalization could accidentally change an active crop

- Severity: high
- Status: resolved
- Evidence: the same plant section can be referenced from residue operations,
  yearly scenarios, and initial conditions.
- Resolution: candidate references are computed semantically. Any yearly or
  initial reference excludes the plant from fallback even if a residue operation
  also references it; regression sets the active canola height to zero and
  proves it remains unchanged.

### CR-08 - Raw 98.4 rewrite could discard source notes

- Severity: medium
- Status: resolved
- Evidence: parsed management serialization does not retain free header comments.
- Resolution: capture the leading comment block before rewrite and restore it
  after serialization. The raw fixture regression preserves its conversion note.

## Compatibility Review

- Historical management files remain readable.
- `end-to-end` keeps append semantics and now fixes residue-index prefixing.
- `stack-and-merge` keeps crop years, OFEs, surface chronology, and referenced
  model values while compacting names and numeric indices.
- No queue, route, NoDb, or persisted schema changes are introduced.

## Verdict

Pass for synthesis and ADR-0016 ingestion normalization. All findings in the
authorized scope are resolved. CR-06 remains a separately scoped project-level
blocker and is deliberately not hidden by expanding the fallback.
