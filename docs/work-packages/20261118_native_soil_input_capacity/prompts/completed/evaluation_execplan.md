# Evaluate separate native soil input capacity

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Determine whether WEPP can accept the eleven input horizons produced by adding
a 200 mm boundary to a ten-horizon SSURGO profile, while retaining ten-layer
calculation storage and historical behavior. Deliver an isolated prototype and
measured recommendation; do not deploy, vendor, or relax production Python checks.

## Progress

- [x] Identified source profile and global-capacity output hazards.
- [x] Created isolated WEPPpy worktree and requested native default-branch worktree.
- [x] Inventory current native reader, fixtures, and source profile limits.
- [x] Build baseline and prototype with separate input storage.
- [x] Run 40 reader tests, 80 exact state comparisons, full hillslope and MOFE cases.
- [x] Full native pytest: 1785 passed; both smokes, 31 watchlist cases, provenance passed.
- [x] Complete twelve portable watershed runs; verify 731 finite channel rows each.
- [x] Retain evidence and recommendation; update tracker and outcomes.

## Surprises & Discoveries

The shared `/workdir/wepp-forest` checkout is on `kernelized-abandoned`, not the
canonical integration branch. Fetched default branch is
`wepp_260430_negmeltfix_comparator`, commit
`7d4cf4b5ab24bbc825515d54f25a035062b826bb`. That branch already discards surplus
input records after clamping their count. Prior analysis of the abandoned branch
is not release evidence. Both shared checkouts contain unrelated work and remain
untouched.

## Decision Log

The operator authorized native capacity evaluation on 2026-11-18. Use a task
branch from fetched default HEAD, with baseline and candidate built from that
same source. Keep calculation count/depth and property formulas unchanged.
Global `mxnsl` expansion and horizon consolidation are excluded because they
introduce unrelated output/state or physical-parameter changes.

## Context and Orientation

WEPPpy task root is `/workdir/wepppy-native-soil-capacity`; native task root is
`/workdir/wepp-forest-native-soil-capacity`. Both use branch
`eval/native-soil-input-capacity`. Native `src/input.for` reads source horizons,
clips depths at 1800 mm and aggregates into calculation layers. Its local source
arrays and shared `solth1` currently use `mxnsl=10`. `src/pmxnsl.inc` also controls
calculation arrays and outputs and must remain unchanged. Python
`wepppy/wepp/soils/horizon_boundary.py` rejects generated counts above ten; that
production contract remains unchanged during this evaluation.

## Plan of Work

First inspect the default-branch instructions and reader. Inventory the failing
run cache read-only to establish observed source-count requirements. Build an
unchanged baseline with system gfortran. Retain a bounded candidate input capacity
and its rationale in the evidence; use local source-depth storage while leaving
shared calculation arrays unchanged. Preserve operation order and formulas.

Next create deterministic tests that execute the actual reader with native state
inspection and complete hillslope simulations. Include counts around both limits,
multiple OFEs, supported formats, shallow/deep profiles and restrictive records.
Compare baseline and candidate for supported old inputs. Use analytical expected
aggregation for new inputs and equivalent subdivisions away from the 200 mm
special handling. Run bounds-checking probes and retain output hashes/results.

Finally run available broader native regression gates as appropriate to evaluation,
report any failures separately from prototype defects, and produce a recommendation
with explicit release and production integration requirements.

## Concrete Steps

From native task root, pin `PATH=/usr/bin:/bin:$PATH`, build with `make -C src wepp`
and `make -C src wepp_hill` sequentially. Preserve baseline executables outside
`src` before candidate rebuilding. Add a deterministic evaluation runner under
`tools/` and tests under `tests/`; record final commands here once created.
Use `wctl --project-dir /workdir/wepppy-native-soil-capacity doc-lint --path`
for work-package Markdown files. The installed wrapper otherwise targets the
shared checkout and can report zero validated files. Native documentation uses
`markdown-doc lint` directly because native source has no WEPPpy Compose config.

## Validation and Acceptance

An accepted prototype reads the full supported input count without changing
`mxnsl`, rejects unsupported counts explicitly, and preserves old-input numerical
results. Native state inspection must verify depths, conductivity and storage
parameters. Execution must reach the real native reader and generated output;
a compile-only or surrogate implementation is insufficient. Actual Zepol replay
is supplementary evidence. Passing evaluation is not release qualification.

## Idempotence and Recovery

Work only in task worktrees and disposable evaluation directories. Keep baseline
executables and compiler/source identities. Do not overwrite production run files,
vendored executables or shared source. Rebuild candidate outputs in task-owned
paths; repeat runs in fresh output directories.

## Artifacts and Notes

Retain commands, baseline/candidate identities, compact generated-state comparisons,
failures, and the final recommendation under this package's `artifacts/` directory.
Native tests and prototype remain in the native task worktree, with a retained patch
for cross-repository review. No external dependency is introduced.

## Outcomes & Retrospective

Candidate `fd7e0a5a6526ae217a58eb5bb2c491d75273610d` passes targeted
validation, all 31 watchlist cases, 1785 full-suite tests, and twelve complete
portable watershed runs. Original inputs preserve exact outputs. Separate input
capacity is supported for follow-up production integration; no production behavior
changed. The larger fixture lacks routing inputs and contributes only hillslope
parity; native completion checks prevented its helper false success from being
counted as a watershed pass.

Revision 2026-11-19 UTC: recorded native default-branch findings, committed
prototype, completed native regression and portable watershed checks, limitations, and
production integration requirements.
