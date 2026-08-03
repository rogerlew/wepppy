# Run the Stevens Canyon contributor-indexed `htcs` ensemble

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Determine whether hillslope-specific lateral-flow timing, represented by
WEPP's computed `htcs` value, can materially change the undisturbed channel
peaks that exceed the burned case. The deliverable is a reproducible ensemble
with figures showing both the focal day and comparable events, while leaving
the production projects and baseline source checkout unchanged.

## Progress

- [x] (2026-08-03 18:00 UTC) Opened a separate follow-on work package.
- [x] (2026-08-03 19:10 UTC) Built a restored text-reader control; focal peaks
  exactly reproduce the archive, with full-record drift disclosed.
- [x] (2026-08-03 19:30 UTC) Built and reviewed contributor-indexed `htcs`.
- [x] (2026-08-03 21:15 UTC) Completed 300 corrected deterministic lanes after
  rejecting an initial fixed-column-width batch.
- [x] (2026-08-03 22:00 UTC) Validated target volumes and analyzed focal,
  full-record, and magnitude-matched responses.
- [x] (2026-08-03 22:30 UTC) Produced figures and sidecars, updated conclusions,
  and verified cleanup and baseline integrity.

## Surprises & Discoveries

- Observation: A clean rebuild at the baseline commit selects the newer binary
  HBP mode-2 reader, but the public project fixture contains text
  `H*.pass.dat` shards. The existing baseline executable and object files are
  text-pass compatible, so the compatibility gate must use an isolated relink
  from those exact objects before changing only `chrqin`.
  Evidence: the previous direct-source lane stopped on missing `H1.hbp`, while
  the baseline executable completed all 100 years from the text shards.

## Decision Log

- Decision: Treat this as experimental source behavior, not a production model
  change or restoration of known-correct physics.
  Rationale: source history does not explain why `htcs` was disabled, and the
  dormant expression is incorrectly indexed for a channel call site.
  Date/Author: 2026-08-03 / Codex.
- Decision: Require exact selected-output parity from an unmodified isolated
  relink before accepting the experimental build method.
  Rationale: this separates link/build compatibility from the `htcs` effect.
  Date/Author: 2026-08-03 / Codex.

## Outcomes & Retrospective

The inversion persists under contributor-indexed `htcs` and all tested spatial
variation. Reach 169 is timing-sensitive, but the outlet median response is no
larger than `1.31%` in magnitude. Full-record response is sparse, and too few
magnitude-matched events exist to infer a general trend. The next experiment
should swap burned and undisturbed hillslope hydrographs into a common routing
state and add process-level runoff attribution.

The first ensemble was rejected because its replacement field was one column
too wide. Exact line-length and non-selected-field gates now prevent recurrence.
The baseline objects also could not reproduce the archived legacy reader;
same-build pairing and explicit provenance were essential.

## Context and Orientation

The staged undisturbed watershed fixture is under
`/wc1/ablation/stevens-canyon-synchronization-20260803/input/undisturbed/wepp`.
Its 138 text pass shards contain a computed time of concentration named `htcs`.
`src/chrqin.f90` constructs each lateral inflow hydrograph but currently uses
`td / 2.67` as peak time. The dormant `htcs(ielmt)` expression uses the channel
index and must instead resolve `nhleft(ielmt)`, `nhrght(ielmt)`, or
`nhtop(ielmt)` according to the contributor being routed.

The burned comparator is observational input only. The experiment reroutes the
undisturbed hillslope records and does not rerun hillslope hydrology. A
coefficient of variation is the standard deviation of a multiplier divided by
its mean; the planned values are 0.10, 0.25, and 0.50.

## Plan of Work

Create a new ablation root and copy the baseline `src` build tree, preserving
its existing objects. Relink without recompiling and replay the staged fixture.
Compare selected raw outputs with the accepted baseline lane. If parity holds,
edit only the copied `chrqin.f90`, resolve the actual contributing hillslope,
set peak time from its `htcs`, and clip it away from zero and runoff duration.
Compile only that object and relink against the proven legacy-pass objects.

Run a direct-`htcs` lane, followed by deterministic ensembles at coefficients
of variation 0.10, 0.25, and 0.50. Each realization will use fixed
hillslope-level multipliers across all events. Use paired seeds across
variation levels and preserve every pass-record runoff volume, supplied peak,
and duration. First run enough realizations to estimate stability, then extend
to at least 100 per condition if runtime and numerical acceptance remain
tractable. Analyze the focal event, all events where undisturbed exceeds burned,
and events matched on routed runoff or peak magnitude.

## Concrete Steps

All commands run from `/home/workdir/wepppy` unless stated otherwise. Large
inputs and outputs remain under
`/wc1/ablation/stevens-canyon-htcs-ensemble-20260803`. Compact scripts, tables,
figures, and captions belong under the investigation directory. Exact commands
and observed hashes will be added as milestones complete.

## Validation and Acceptance

The unmodified relink must complete 100 years and reproduce selected baseline
channel peak and volume files byte-for-byte or with a documented parser-level
tolerance. The experimental executable must consume text pass shards and emit
the watershed completion marker without runtime-error signatures. Each lane
must retain unchanged pass runoff volume, peak, and duration fields; routed
channel volume differences must be quantified. Every figure requires a
same-stem Markdown sidecar with caption, method, interpretation, limitations,
and source-data references. Documentation must pass scoped `wctl doc-lint`.

## Idempotence and Recovery

Never modify `/workdir/wepp-forest_260430_baseline`. All source and object
changes occur in the named ablation root. Record the baseline commit, status,
binary hash, and tracked-file hashes before work and verify them after cleanup.
Cleanup removes only an explicitly recorded experimental build directory and
retains compact evidence; it never uses `git reset --hard` or a broad recursive
target.

## Artifacts and Notes

The preceding study and its accepted baseline live in
`docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/` and
`/wc1/ablation/stevens-canyon-synchronization-20260803`. This package must not
alter those historical lane outputs.

## Interfaces and Dependencies

Use the existing pinned GNU Fortran toolchain, baseline object files, WEPP text
pass contract, Python analysis environment, and Matplotlib. Add no external
dependencies. The source change is experimental and must pass the repository's
Fortran code and QA review gates before conclusions are handed off.

Revision note (2026-08-03): Initial plan created to execute the follow-on
experiment requested after the synchronization-dispersion study.
