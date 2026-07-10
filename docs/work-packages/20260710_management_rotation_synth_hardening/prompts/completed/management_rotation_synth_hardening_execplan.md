# Repair AgFields management rotation synthesis and residue ingestion

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current.
Maintain it according to `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, an AgFields project may repeat the same crop management across
many years without generating one new copy of every plant and operation
scenario per year. The exact 17-year schedule that failed in
`sacral-self-discipline` will still contain 17 simulation years and the same crop
and operation data, but its management file will remain within WEPP's limit of
20 plant scenarios and will complete through the current hillslope binary.

This is faithful repair of wired production behavior, not scaffold or surrogate
discovery. Acceptance requires generated-output evidence from the current WEPP
binary path, in addition to unit tests.

## Progress

- [x] (2026-07-10 19:26Z) Captured the RQ failure, representative sub-field, and
  complete failed-run histogram.
- [x] (2026-07-10 19:26Z) Scaffolded this work package and compatibility plan.
- [x] (2026-07-10 19:34Z) Added hermetic copies of the canola and oat source managements plus the
  17-entry schedule manifest.
- [x] (2026-07-10 19:36Z) Added the exact regression, which demonstrated 50 plant
  definitions before the patch and 3 reachable definitions after it.
- [x] (2026-07-10 19:42Z) Implemented canonical reuse, graph reachability pruning,
  and complete scenario-reference remapping.
- [x] (2026-07-10 19:42Z) Added an explicit pre-write check for WEPP's
  20-plant-scenario limit.
- [x] (2026-07-10 19:54Z) Documented setup-year composition and definition reuse.
- [x] (2026-07-10 19:50Z) Ran targeted tests and the wired binary replay; the
  incident error is gone and the next source-input error is recorded.
- [x] (2026-07-10 19:56Z) Completed review, QA, broad gates, validation artifact,
  unrelated full-suite baseline disposition, and closeout.
- [x] (2026-07-10 20:06Z) Reopened by maintainer request and inventoried the
  systematic Jim-interface residue placeholder across all ten source files.
- [x] (2026-07-10 20:06Z) Authored ADR-0016 and the additive compatibility plan.
- [x] (2026-07-10 20:12Z) Added exact 2017.1 ingestion fixture and normalization tests.
- [x] (2026-07-10 20:14Z) Implemented residue-only `hmax` normalization and
  provenance for both formats.
- [x] (2026-07-10 20:18Z) Replayed p3733 and dispositioned the independent
  `frcfac.for:184` random-roughness boundary.
- [x] (2026-07-10 20:24Z) Refreshed review, QA, validation, trackers, and closeout.

## Surprises & Discoveries

- Observation: The WEPP process returned zero but the run was correctly rejected.
  Evidence: `p3733.err` contains `ncrop read as 50` and no successful-completion
  marker; `wepp_runner.run_hillslope` requires the marker rather than trusting
  return code alone.
- Observation: Every attempted hillslope failed for the same limit.
  Evidence: all 119 `.err` files contain `ncrop read as`; the histogram is 34:52,
  35:26, 36:10, 37:5, 38:4, 39:5, 40:1, 41:3, 42:4, 44:1, 45:2, 46:1,
  47:1, 48:2, 49:1, 50:1.
- Observation: The expected spring/fall composition path already exists.
  Evidence: `stack-and-merge` normalizes multiple one-year rotations, trims a
  setup year, and merges distinct setup surface operations into the prior year.
  The oat source's retained crop year shares the setup year's surface, meaning
  its spring and fall operations are already combined and remain sorted.
- Observation: The immediate overflow is definition duplication, not extra years.
  Evidence: the p3733 source sequence correctly produces 17 simulation years but
  expands two canola and three oat plant definitions into `2 + 16 * 3 = 50`.
- Observation: `iresad` was an unmodeled cross-section reference.
  Evidence: it is documented and serialized as a plant scenario index but was
  held as a raw integer, so later segment prefixing could silently target a
  different global plant. Parsing it as `ScenarioReference` makes remapping and
  reachability correct.
- Observation: Fixing `ncrop` exposed invalid source data rather than another
  synthesis error.
  Evidence: the wired binary accepts `ncrop=3` and then reports `HMAX <= 0.0` for
  referenced residue plant `L179_weed`. The fixture value is `hmax=0.0` before
  and after synthesis.
- Observation: The zero height is systematic Jim-interface output.
  Evidence: all ten preserved 2017.1 files in the source run contain
  `L179_weed` with zero `hmax`, `cuthgt`, `rdmax`, and `xmxlai`; each is used as
  an applied-residue plant rather than an active crop.
- Observation: A positive height clears validation but reveals a distinct
  operation-state failure.
  Evidence: probes with `0.00001 m` and `0.01 m` both advance into simulation,
  then SIGFPE at `frcfac.for:184` because random roughness is zero. This package
  must not silently broaden into operation normalization.

## Decision Log

- Decision: Canonicalize only reusable definition sections: plants, operations,
  initial conditions, contours, and drains.
  Rationale: Surface and yearly scenarios are timeline state and sharing them
  could let a later boundary merge mutate earlier years.
  Date/Author: 2026-07-10 / Codex.
- Decision: Use a recursive structural signature that excludes object-graph
  pointers and only the top-level scenario name.
  Rationale: Prefixes are reference keys, while descriptions and serialized data
  must remain part of conservative equivalence.
  Date/Author: 2026-07-10 / Codex.
- Decision: Do not author a parameterization ADR.
  Rationale: The repair preserves every referenced model value and operation date;
  it compacts equivalent definitions and enforces an existing binary input limit.
  Date/Author: 2026-07-10 / Codex.
- Decision: Treat elimination of the `ncrop` failure on the current binary path
  as generated-output acceptance for this scoped repair, while retaining the
  independent `hmax=0` source defect as an explicit project retry blocker.
  Rationale: Correcting `hmax` requires a scientifically valid source value and
  is explicitly outside this parameterization-neutral synthesizer package.
  Date/Author: 2026-07-10 / Codex.
- Decision: Reopen the package and implement ADR-0016 at the ZIP-ingestion
  boundary.
  Rationale: The maintainer identified the placeholder's provenance and
  explicitly authorized normalization. Ingestion retains the original source,
  can expose provenance, and prevents invalid final files from entering mapping.
  Date/Author: 2026-07-10 / Roger Lew and Codex.

## Outcomes & Retrospective

The synthesizer now produces a compact, reference-correct 17-year management:
3 plants and 10 operations replace 50 and 136, with the setup/crop composition
unchanged. The exact incident failure is absent on the current binary path. The
replay usefully revealed that the source archive itself contains an invalid
zero-height residue plant; preserving that parameter rather than guessing a fix
keeps this package scientifically neutral and gives the next operator action a
precise input name and error.

The repository-wide test gate reached 2,072 passes and 41 skips before the known
unrelated Batch Runner fixture-path failure. Its isolated reproduction fails in
`clear_nodb_file_cache` because the test patches `batch_runner_mod.get_wd` but
the helper resolves `/wc1/batch/...` through a different import. No Batch Runner
file is touched by this package.

The reopened milestone is complete. AgFields ingestion now treats Jim-interface
residue placeholders as a documented compatibility boundary: qualifying
nonpositive heights become `0.00001 m`, originals and notes are preserved, and
provenance makes the change inspectable. Active plants remain untouched. The
current binary clears `ncrop` and `HMAX` and reaches simulation year 2 before a
separate zero-random-roughness SIGFPE. Refusing to absorb that operation value
into the same fallback kept the scientific decision narrow and reviewable.

## Context and Orientation

`wepppy/nodb/mods/ag_fields/ag_fields.py` builds a crop name for each observed
year, reads its mapped `.man` file, and calls
`ManagementRotationSynth(stack, mode='stack-and-merge')`. The synthesizer lives
in `wepppy/wepp/management/utils/rotation_stack.py`. A WEPP management file has
named sections such as plants and operations; other sections hold
`ScenarioReference` objects that serialize to one-based numeric indices.

The synthesizer deep-copies each source and prefixes later names so references
do not collide. Before this repair it then appended all prefixed definitions,
including exact repetitions. For the representative p3733 schedule this yielded
50 plant definitions, above WEPP's fixed 20-definition input limit. The source
run directory contains 119 attempted `.man`, `.run`, `.slp`, and `.err` sets;
the remaining sub-fields were canceled when the first future failure surfaced.

`tests/wepp/management/test_rotation_stack.py` owns focused regression coverage.
Run-derived fixtures belong under `tests/wepp/management/fixtures/` and must not
depend on `/wc1` at test time. `wepppy/nodb/mods/ag_fields/README.md` is the
durable operator/developer contract for AgFields synthesis.

## Plan of Work

The original milestone first copied the two exact source managements and a small manifest describing the
17-source sequence into the test fixture directory. Add a regression that loads
those files, synthesizes the sequence, and asserts 17 years, bounded section
counts, valid references, and successful write/read round-trip.

Then refactor name remapping in `rotation_stack.py` so all references are found
by their declared section type. Add a conservative recursive signature for
scenario definitions, canonicalize reusable sections in dependency order, and
remap duplicate names to the first retained definition. Do not canonicalize
surface or year sections. Validate the final plant count before returning or
writing and report the count and WEPP limit when it is exceeded.

Update the AgFields README with the normalized-rotation, setup-year merge, and
definition-reuse contract. Run focused tests, serialize and re-read the exact
fixture output, then construct a temporary run file using p3733's slope, soil,
and climate support and execute the current configured hillslope binary. Do not
write back into the source run.

Finally run management-adjacent and repository gates, write code-review, QA, and
validation artifacts, update the living plan and both trackers, and move this
plan to `prompts/completed/` only when no required work remains.

For the reopened milestone, add the preserved 2017.1 canola source as a fixture.
In `wepppy/nodb/mods/ag_fields/ag_fields.py`, identify residue-only plant
references semantically, apply ADR-0016 before downgrade or final installation,
preserve 98.4 header notes, and attach additive normalization provenance. Cover
both archive formats and active-plant exclusion before replaying p3733.

## Concrete Steps

Run from `/home/workdir/wepppy`:

    wctl run-pytest tests/wepp/management/test_rotation_stack.py
    wctl run-stubtest wepppy.wepp.management.utils.rotation_stack
    wctl check-test-stubs
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260710_management_rotation_synth_hardening --path wepppy/nodb/mods/ag_fields/README.md
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    git diff --check

The generated-output smoke must use a temporary destination and the binary
selected by the source project's configuration. It must record the executable,
management counts, return status, and successful-completion marker in the
validation artifact.

## Validation and Acceptance

The run-derived test must fail against the old code because `result.ncrop` is 50
instead of at most 20. After the repair it must report 17 simulation years, no
more than 20 plants, and a compact operation section while retaining distinct
canola and oat inputs. Calling `str(result)`, writing it, and reading it again
must succeed so every reference is proven resolvable.

The limit test must synthesize more than 20 structurally distinct plant
definitions and receive an actionable `ValueError` before a file is written.
Existing end-to-end tests must remain green and preserve their append semantics.

The binary smoke proves this package when the generated management no longer
reports the incident's `ncrop` error and advances to simulation or a separately
identified source-input validation boundary. A successful-completion marker is
still required before the AgFields project itself can claim end-to-end success;
the current fixture cannot produce it until `L179_weed` is corrected upstream.

## Idempotence and Recovery

Fixture tests and documentation checks are repeatable. The source project is
read-only evidence; all generated smoke files go to a temporary directory. If a
test exposes a reference mismatch, inspect the canonical-name map and do not add
a fallback that hides the missing reference. If the full suite fails outside
the touched management scope, reproduce the first failure alone and record the
evidence without weakening the targeted gate.

## Artifacts and Notes

The incident inventory and compatibility plan are stored under `artifacts/`.
The final package will add code-review, QA, and validation summaries. The fixture
files record their original paths and SHA-256 hashes in their README.

## Interfaces and Dependencies

No new external dependency is allowed. `ManagementRotationSynth` keeps its
existing constructor, `build`, and `write` public signatures. Its type stub must
continue to match those methods. The implementation uses existing `Management`,
`Loops`, `ScenarioReference`, and `SectionType` classes from
`wepppy.wepp.management.managements`.

Revision note (2026-07-10, Codex): Updated after implementation and wired binary
replay to record reference compaction, the implicit `iresad` defect, and the
independent invalid `L179_weed` source parameter that blocks project completion.

Revision note (2026-07-10, Codex): Closed after focused and broad validation,
review/QA disposition, and isolated reproduction of the unrelated full-suite
Batch Runner baseline failure.

Revision note (2026-07-10, Codex): Reopened by explicit maintainer request for
ADR-0016 residue-only `hmax` normalization during AgFields ZIP ingestion.

Revision note (2026-07-10, Codex): Re-closed after exact dual-format ingestion
coverage, current-binary replay, updated review/QA disposition, and repository
gates.
