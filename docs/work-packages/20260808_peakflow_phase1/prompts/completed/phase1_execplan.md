# Execute Topanga peak-flow audit Gates 0–2

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current.
Maintain it according to `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a developer can run compact Topanga fixtures with a pinned
legacy WEPP build, capture exactly what the peak solver received, and replay
both legacy peak methods in a separate process. The selected-method replay will
prove whether the event packet is complete. The artifacts will distinguish the
legacy mismatched summaries from a diagnostic in which both methods describe
the same post-surplus forcing. This package stops before any watershed census.

## Progress

- [x] (2026-08-08 20:11 UTC) Read repository, work-package, ExecPlan, and
  WEPP-Forest guidance.
- [x] (2026-08-08 20:11 UTC) Locate the pinned source and authoritative Topanga
  run.
- [x] (2026-08-08 21:05 UTC) Scaffold and validate Gate 0 schemas.
- [x] (2026-08-08 21:45 UTC) Freeze compact 1980 and 1986 fixtures.
- [x] (2026-08-08 21:30 UTC) Implement observational packet capture.
- [x] (2026-08-08 21:35 UTC) Implement process-isolated legacy and harmonized replay.
- [x] (2026-08-08 21:50 UTC) Demonstrate parity, replay completeness, domain flags, and negative
  controls.
- [x] (2026-08-08 22:00 UTC) Update evidence and close Gates 0–2.

## Surprises & Discoveries

- Observation: the 1986 reproducer is committed, but the Ksat-35 run accepted
  as the first fixture exists only as prior output and an external run-root
  dependency.
  Evidence: `analyze_hill106_ksat_mutation.py` requires `--burned-ksat35` and
  the Topanga artifact tree contains no corresponding deck.
- Observation: the accepted 1980 values require restrictive-layer record
  `1 10 0.0000108`; the later synchronized project has `0 0.0 0.0` and does
  not reproduce them.
  Evidence: the restored record gives rounded runoff/peak pairs
  `60.121/47.709` and `58.632/92.716`; the no-layer deck gives
  `62.777/49.816` and `61.292/96.688`.
- Observation: selected-method standalone replay matches both observational
  peaks exactly; the legacy APPMTH summaries have `v*` values `1.3753` and
  `4.4017`, while harmonized post-surplus summaries give `0.7449` and `0.9026`.
  Evidence: `artifacts/replay-reports/`.
- Observation: changing version-9002 `ksatfac` from `1.3` to `9.3` changes one
  input token but none of seven canonical output files.
  Evidence: `artifacts/negative-control-result.json`.

## Decision Log

- Decision: write observational packets from a diagnostic patch applied to an
  isolated pinned-source worktree, and perform replay with a standalone tool.
  Rationale: `HDRIVE` mutates COMMON state, so inline shadow calls cannot prove
  observational parity.
  Date/Author: 2026-08-08 / Codex.
- Decision: treat this package as faithful extraction with generated-output
  evidence, not a surrogate solver study.
  Rationale: Gate 1 requires selected-method reproduction.
  Date/Author: 2026-08-08 / Codex.

## Outcomes & Retrospective

Gates 0–2 passed. The main implementation friction was reconstructing the
accepted restrictive-layer deck and isolating mutable COMMON-block solver
state. Immutable packet capture plus a standalone driver made solver replay
auditable without changing observational execution. The full Topanga census,
cross-site work, snow, and OFE experiments remain outside this package.

## Context and Orientation

The governing protocol is
`docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md`.
The accepted 1980 operands are in the preceding Topanga investigation's
`artifacts/hill106-ksat-peakflow-diagnostic.md`. The authoritative inputs are
under `/wc1/runs/ha/hand-to-mouth-drought/wepp/runs`. The acceptance binary
`wepp_260803` identifies its source as commit
`f24c957e3633898e0fd4cbbea5ae08c781f29dba` on the default comparator line. Use
an isolated worktree at that commit. The older `2f65506d…` checkout records the
initial forensic trace but is not the parity authority. `surdra` is a daily depth returned
from overfull soil storage. `IRS` assigns it to subdaily intervals and then
calls either `APPMTH`, an approximate scalar method, or `HDRIVE`, a
characteristic-routing method with shared mutable state.

## Plan of Work

First create JSON Schemas under this package's `artifacts/schemas/` for every
Gate 0 grain, plus examples and tests that validate keys, units, nullability,
and requested versus realized mutations. Next copy only the input files needed
for Hill 106 into compact fixture directories. Create Ksat-35 by changing only
the first-horizon conductivity token and make the checker reject any additional
input difference.

Create a hash-guarded transformation against pinned `irs.for` that is opt-in
through a marker file.
It must record pre- and post-surplus forcing, assignment mode and duration,
solver inputs, method-specific operands, and production peak without invoking
an extra peak method. Build and run it only in an isolated temporary worktree.
Compare every canonical non-diagnostic output against the unmodified build.

Implement a standalone replay executable or tool that reads the immutable
packet. Legacy-input replay preserves the mismatched legacy summaries.
Harmonized replay derives APPMTH summaries from the post-surplus series. The
tool reports APPMTH domain flags and HDRIVE termination metadata. Its selected
legacy replay must match WEPP's production peak within the preregistered
tolerance.

Finally run the 1980 pair, both 1986 pairs, and inactive `kr` or `ksatfac`
control. Update the investigation, tracker, and this plan with generated
evidence. Do not start the census.

## Concrete Steps

Work from `/workdir/wepppy`. Validate documentation with `wctl doc-lint`. Run
new tests through `wctl run-pytest <target>`. Build legacy WEPP from an isolated
worktree using `/usr/bin/gfortran` and the source makefile. Run each hillslope
fixture from its `runs/` directory by feeding the `.run` file to the diagnostic
binary. Store compact evidence under this package and the reusable fixtures
under the multi-site investigation artifacts.

## Validation and Acceptance

Gate 0 passes when every example validates and invalid requested/realized or
event-presence cases fail. Gate 1 passes when declared canonical output parity
holds, packets are immutable and versioned, selected replay matches production,
and counterfactual execution is a separate process. Gate 2 passes when one
command reproduces the full-precision 1980 values, both 1986 anomalies remain
labeled unresolved, and the inactive mutation changes its intended token but
no hydrologic output.

## Idempotence and Recovery

Fixture generation writes to explicit temporary directories before replacing
derived artifacts. Diagnostic source edits occur only in an isolated temporary
source copy.
The shared `/workdir/wepp-forest_260430_baseline` tree must be clean at handoff.
Never overwrite the authoritative `/wc1` run.

## Artifacts and Notes

Record build configuration, hashes, parity reports, and test transcripts in
`docs/work-packages/20260808_peakflow_phase1/artifacts/`. Do not commit bulk
simulation output when a compact fixture and hashes suffice.

## Interfaces and Dependencies

Schemas use JSON Schema Draft 7, the newest vocabulary supported by WEPPpy's
existing `jsonschema 3.2.0` dependency. Python tooling uses the standard library
unless an already-declared WEPPpy dependency is necessary. The immutable event
packet has a schema version and content hash. The replay process accepts only a
packet path and emits versioned JSON; it never imports or calls the running
Fortran process.

## Revision Note

Initial plan authored 2026-08-08 to execute the conditionally accepted Phase 1
scope without broadening into the Topanga census.

Revised 2026-08-08 to use JSON Schema Draft 7 after discovery showed the pinned
validator does not implement Draft 2020-12; no required protocol semantics
depend on the newer vocabulary.

Revised 2026-08-08 after reconstructing the restrictive-layer record required
by the archived 1980 results; the current synchronized project reflects a
later no-restrictive-layer experiment and is not the acceptance deck.

Revised 2026-08-08 after reading the executable sidecar: acceptance builds and
instrumentation use `f24c957e…`; `2f65506d…` is historical trace provenance.
