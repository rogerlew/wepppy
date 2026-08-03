# Produce Stevens Canyon synchronization-sensitivity figures

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Produce evidence showing how the selected channel peaks respond when
undisturbed hillslope hydrographs are desynchronized. A reader must be able to
inspect each figure and its Markdown sidecar, reproduce every lane, and remove
all experimental source changes without touching the baseline source tree.

## Progress

- [x] (2026-08-03 16:48 UTC) Source archaeology and experiment design complete.
- [x] (2026-08-03 16:48 UTC) Confirmed `wepp_ui.txt` presence in both production
  projects and local hillslope fixtures.
- [x] (2026-08-03 17:00 UTC) Staged the undisturbed routing fixture from
  read-only WEPP1 inputs.
- [x] (2026-08-03 17:05 UTC) Reproduced baseline channel output exactly.
- [x] (2026-08-03 17:16 UTC) Executed three volume-preserving dispersion lanes.
- [x] (2026-08-03 17:18 UTC) Validated full-period completion and unchanged
  day-203 channel volumes.
- [x] (2026-08-03 17:21 UTC) Generated figures, sidecars, and interpretation.
- [x] (2026-08-03 17:21 UTC) Verified cleanup and baseline source integrity.

## Surprises & Discoveries

- Observation: `wepp_ui.txt` is intentionally empty; successful open, not file
  content, sets `ui_run=1` and dispatches `watbal_hourly`.
  Evidence: `src/main.for` and identical empty-file SHA-256
  `e3b0c44298fc...b855` in both production projects.
- Observation: direct `htcs` affects only nonrectangular `chrqin` hydrographs;
  day 203 has three material contributors in that branch.

## Decision Log

- Decision: Never patch the baseline checkout. Create an isolated git worktree
  under the ablation root, record its commit, and delete it through `git
  worktree remove` after copying binaries and patch evidence.
  Rationale: cleanup is structural and independently verifiable.
  Date/Author: 2026-08-03 / Codex.
- Decision: Keep `wepp_ui.txt` as a required zero-byte sidecar and require the
  hourly-water-balance startup marker in baseline hillslope evidence.
  Rationale: file presence selects the hourly path.
  Date/Author: 2026-08-03 / Codex.

## Outcomes & Retrospective

The experiment produced a reproducible baseline and three full-period timing
lanes. Moderate dispersion attenuated day-203 upstream peaks by 6-11%, but the
inversion persisted. High dispersion amplified selected downstream peaks,
showing that synchronization response is non-monotonic. The direct `htcs` lane
did not cross the pass-format compatibility gate and was excluded. The baseline
source remained clean at its original commit.

## Context and Orientation

The production undisturbed run is
`/geodata/wc1/runs/st/stabilized-housecleaning` on WEPP1. Hillslope pass files
contain fixed runoff volumes, peaks, durations, and computed times of
concentration. `src/chrqin.f90` converts those values into channel-entry time
series. The experiment changes only that conversion and routes the resulting
flows through the unchanged channel network.

## Plan of Work

Copy only required run controls, 138 pass shards, shared sidecars, and
comparator outputs into `/wc1/ablation`. Record checksums. Build source in a
disposable worktree. First reproduce the unmodified 100-year watershed result.
Then run one mechanism per lane: contributor-indexed `htcs`, followed by
deterministic low/medium/high timing dispersion. Preserve supplied runoff
volume and reject lanes with mass-balance drift. Summarize day 203 and the full
event record at reaches 169, 172, 173, and 193. Generate SVG or PNG plots under
the investigation `figures/` directory, with a same-stem `.md` sidecar for
caption, method, interpretation, limitations, source data, and reproduction.

## Concrete Steps

Commands and exact outputs will be added as the fixture and runner are created.

## Validation and Acceptance

The baseline must complete 100 years and reproduce selected raw channel peaks
within parser/output precision. Every mutation lane must complete, conserve
routed input volume within documented numerical tolerance, and emit its frozen
configuration and seed. Every image must have a Markdown sidecar and pass doc
lint. The baseline checkout commit and `git status --short` must match their
pre-experiment values after cleanup.

## Idempotence and Recovery

All generated payloads live below a named `/wc1/ablation` root. Setup aborts on
unexpected existing content unless it matches the recorded manifest. Source
cleanup uses `git worktree remove` on the explicit experimental worktree; it
never uses `git reset --hard` or broad deletion. The baseline tree is verified,
not repaired, by comparing commit, status, and tracked-file checksum manifests.

## Artifacts and Notes

Large pass shards and raw lane outputs stay under `/wc1/ablation`. Compact
manifests, tables, scripts, figures, and interpretation live in the
investigation directory.

## Interfaces and Dependencies

Use the existing GNU Fortran build, WEPP watershed run contract, DuckDB/Python
analysis environment already present in WEPPpy, and Matplotlib for scientific
plots. Do not add dependencies or alter production services.
