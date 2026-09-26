# Support uploaded 2006, 2006.2 and 9002 soils

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users of the existing Builder single-input option can upload one-OFE 2006,
2006.2, 7778 or 9002 soils and use them on every hillslope and every non-buffer
OFE (overland flow element). The consumed native input preserves the supplied
version and science values apart from existing explicit soil modifiers.

## Progress

- [x] Trace raw stacking, WSU reader/writer, preparation and native reader.
- [x] Ratify contract checkpoint with two independent reviews; commit before runtime edits.
- [x] Implement admission, explicit preserving WSU path, preparation wiring, metadata and UI.
- [x] Verify generated single/multiple-OFE inputs and native executions; live authenticated RQ and both preparation entry points pass.
- [ ] Close correctness/security findings; update guides and commit.

## Surprises & Discoveries

WSU means `WeppSoilUtil` in `wepppy/wepp/soils/utils/wepp_soil_util.py`.
Its current 2006.2 reader discards the ninth header field; native `input.for`
reads it. Its current serializer excludes both 2006 versions and recomputes
9002 appended values through Rosetta. The existing symbolic-parameter detector
also classifies absent 2006 horizon conductivity as symbolic; preserving uploads
must bypass that conversion. Raw `SoilMultipleOfeSynth` preserves all
records and does not require redesign.

Review caught native REAL collapse of strict inequalities. Validate original
values and additionally native float32 ordering: rounding all fields first
would hide invalid original texture sums or reject valid decimal texture sums.
Both directions now have regressions. Live long-lived development RQ workers
retained old modules; only these disposable failed jobs were retried in a fresh
worker. No service restart or deployment was performed.

## Decision Log

The operator explicitly requested these formats and said "make it so" after
reviewing the preparation concerns. Keep existing catalog/Disturbed writing
unchanged using an explicit preservation option for uploaded soils. Validate
the complete native record layout, including 2006.2 avke, rather than inferring
values. Preserve native 9002 settings without adding WEPPcloud Disturbed.

## Context and Orientation

`wepppy/wepp/single_input.py` admits uploads before source publication in
`wepppy/nodb/single_input_sources.py`. The latter stores immutable bytes and
metadata; only version metadata changes. `wepppy/nodb/core/soils.py` replicates
profiles with the raw stacker. `wepppy/nodb/core/wepp.py` functions `prep_soil`
and `prep_multi_ofe_hillslope` apply saturation, restrictive conductivity and
depth modifiers. `wepp_prep_service.py` supplies the single-OFE worker arguments.
The existing final artifact validator must admit all four versions. The soils
Pure template and durable usage guide must advertise the expanded list.

## Plan of Work / Milestones

First amend the canonical SUDI contract and ADR, record state/compatibility
coverage, obtain two independent read-only reviews, and commit those documents
before any production edits. Existing commit authority continues from the
operator's instruction to commit and execute this feature.

Next extend strict parsing per the canonical version layouts. Preserve avke and
9002 appended values in an explicit WSU mode, serialize from those stored values,
and wire that mode only for uploaded-soil preparation. Preserve-mode kslast
overrides ignore legacy developed-label suppression; exact-horizon clipping
stops at the boundary to avoid duplicate depths. Existing derived bulk density
used for management remains unchanged without converting generated soil files. Existing saturation,
kslast and depth methods act on the parsed objects. Store the actual source
version. Validate native-compatible label tokens and remove standalone comments
from derived soil copies so raw-stacking and native reader agree on record order. Update guidance, keeping .sol/.SOL, one-OFE, size, and project policies.

Finally add malformed and valid fixtures, publication/reuse coverage, and
round-trip assertions across 1, 2, 12 and 32 OFEs. Execute generated inputs with
vendored `wepp_260803`, inspect preserved sentinel hydraulic values, modifiers,
OFE counts, source hashes and nonempty native outputs. Obtain separate final
correctness/security review and resolve medium/high findings.

## Concrete Steps / Validation and Acceptance

Work in `/home/workdir/wepppy` using the running development stack. Run
`wctl run-pytest tests/wepp/test_single_input.py tests/wepp/soils/utils/test_wepp_soil_util.py tests/nodb/test_single_input_sources.py tests/nodb/test_single_input_artifacts.py`.
Extend with focused preparation/template tests, `wctl run-stubtest
wepppy.wepp.soils.utils.wepp_soil_util`, `wctl check-test-stubs`, scoped doc lint,
and `wctl run-pytest tests --maxfail=1`. Record actual results and any unrelated
failures; do not change unrelated paths. Tests must observe generated files,
not only object state, and native execution must succeed for all formats.

## Compatibility and Regression Plan

No existing metadata keys or enum values change; version strings expand
additively. Existing 7778 uploads, absent/empty sources, reusable sources,
replacement failure, rebuild and source archive/restore keep their current
semantics. New formats use the same publication boundary and error contract.
Untrusted malformed bytes fail before publication; missing populated sources
retain the existing explicit repair error. Working, failed and completed job
observability remains unchanged. Legacy unchecked and ordinary dataset inputs
must retain their parser/serializer behavior. No queue or binary changes.

## Idempotence and Recovery

Use temporary test directories and immutable source publication. Re-running
tests must not mutate accepted sources. Revert amendment commits to withdraw
new admission; archive affected runs and use compatible code to process them.
Do not relabel source versions or silently convert saved projects.

## Artifacts and Notes

Retain contract reviews and validation/native evidence in this package's
`artifacts/`. The earlier 20260925 package is immutable historical evidence.

## Interfaces and Dependencies

Extend WSU with an opt-in preservation argument, default false, and matching
.pyi signature. Preparation worker tuples may gain optional trailing flags;
legacy positional tuples retain behavior. No dependency additions.

## Outcomes & Retrospective

Pending implementation and native acceptance.
