# Research execution review

Scope: offline research harness and generated figures, not a production change
or release review. Performed by the executing agent; not independent review.

## Input, filesystem and execution boundary

The source project and corrected source tree are read-only. New campaign roots
refuse to overwrite on creation. Model runs get separate fresh input/output
directories. Exact source/current-snapshot hashes are checked. Every path-bearing
token in all 280 run decks was checked to stay within the expected
`../output/H<id>.*` outputs; this is a bounded trusted fixture, not a public-input
service. Model subprocesses use an argument list, no shell interpolation, a
300-second timeout and at most eight workers. No secrets, environment credentials,
production services or network paths are passed to the model.

The frozen plan preserves all 1,120 requested trial identities and their existing
eligibility. Intended mutation values are reparsed after writing. Exactly one
input file may differ per mutant; baselines change none. Missing or partial
terminals cannot be treated as success. Resume verifies retained binary, input,
trace and output hashes; failed partial directories require a separate attempt.

## Observation boundary

The first observer attempt exposed a zero-based array issue: `runoff` and
`peakro` are declared 0:mxelem, unlike `surdra`. The valid companion passes
`runoff(1)` and `peakro(1)` to a write-only routine. The preserved patch has no
solver call, state assignment or arithmetic alteration. Active-observer parity
is byte-identical for all seven canonical outputs on both H106 scenarios.
Observation correctness separately requires final report readback, calendar
mapping, unique keys, finite/nonnegative values and coverage of positive events.
Parity by itself was insufficient to establish observer correctness; the new
regression test specifically rejects the original zero-slot trace.

## Analysis boundary

Raw zero observations are retained. Positive events are outer-paired, with
absence flags and no zero-filling. Figure filters retain the original floors;
sediment remains the printed EBE value, not a higher-precision surrogate.
Ratio guides, directional classification and ties are tested. Plot summaries
count out-of-view values; visually bounded axes do not silently alter denominators.
Figures must be opened after generation before final delivery.

## Test evidence

Existing census tests: 17 passed, one historical integration failure caused by
the old pinned executable path containing a different binary. The nonintegration
subset passes 16 tests (two deselected). This mismatch remains explicitly
retained, not repaired by changing the old manifest.

New research-harness tests cover accurate report readback, zero-slot rejection,
duplicate dates, NaN/infinite/negative values, original directional/tail logic,
and real PNG generation (eight tests passed). Final execution and figure readback results will be
recorded in results.md. A broad production suite is not run: there are no
production Python or Fortran source changes in this work package.
