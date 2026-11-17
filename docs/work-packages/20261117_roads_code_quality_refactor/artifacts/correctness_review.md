# Roads refactor correctness review

## Verdict and scope

**Source review: accept; no medium/high correctness findings identified.** This
verdict covers the source snapshot below, not final runtime acceptance or deployment.
Candidate native matrix, full-project comparisons, and final regression receipts
remain required before package closure.

Reviewer: `/root/roads_contract_review` (independent reviewer).
Reviewed: 2026-11-17 22:59 UTC.
Comparison base: `96555f2f95326350d2d7007c19327378ea831ab0`.
Candidate HEAD: `8d943c5abe386aee6b064074e8ee9b77fdb1e953` with dirty `roads.py` and five untracked execution
collaborators. The table binds the actual reviewed source, including those files.
No production/test source was modified by this reviewer.

## Findings

No medium/high correctness or regression findings were identified. No source
change is requested by this review. Additional bounded warning logging in
`_unrutted_execution._move_candidate_to_status` makes the prior broad diagnostic
continuation visible; membership handling and continuation remain the same.

## Evidence and inspection

An AST comparison confirmed that all existing `Roads` method argument lists,
return annotations and decorators are unchanged, with no added or missing facade
methods. Every named helper extracted from those methods has an identical body
AST. The two deliberately decomposed coordinators are `prepare_segments` and
`run_roads_wepp`; they received separate control-flow review.

For execution, a normalized primitive-statement comparison mapped `roads` back
to `self`, `results` fields to the original run-local variables, and terrain/trace
fields to their original locals. The unmatched original statements were run-local
initializers, the two factored summary dictionaries, the returned candidate-plan
dictionary, trace-call indirection, and the intentionally replaced strip-failure
control flags. Manual review covered those transformations and their call sites.
This structural evidence complements tests; it does not prove arbitrary runtime
inputs or native behavior exhaustively.

The reviewer traced point-source routing, lazy trace initialization, input
materialization, native execution, missing-PASS failure, success counters and
logging. Early returns stop only the current contributor, preserving the original
loop continuation. Native and trace failures retain per-contributor evidence and
aggregate into the same terminal failed-attempt path. Native runner dependencies
are passed explicitly from the facade, preserving its existing monkeypatch seams.
Shared module objects retain raster/lifecycle/comparison monkeypatch visibility.

For unrutted execution, selection and per-hillslope ordering, candidate planning,
width scaling, small-remainder compensation, emitted-area checking, strip and
remainder execution were checked against the original source. A failed candidate
still prevents that hillslope's execution; a failed native strip still permits
sibling attempts before terminal failure aggregation. RUPC-02 placement, source
membership, OFE role order, policy markers and area fields remain unchanged.

DEM and distance-to-channel dataset scopes retain their original lifetimes.
Run-local dataclasses are never assigned to `Roads` or serialized. The facade
retains lifecycle decorators, state-transition lock scopes, invalidation ordering,
watershed/report/publication ordering, failure persistence, and the final removal
of runtime template/readback attributes. Upload cancellation rollback was not
moved or weakened.

## Valid-state and error matrix

| State or condition | Required preserved outcome | Review coverage |
| --- | --- | --- |
| Disabled/no prepared state | Same actionable preflight failure before execution | Facade preflight and existing stale-prepare checks retained |
| No eligible contributors | Baseline-equivalent result with zero executed counters | Default result fields, empty loops, summary and accounting path inspected |
| Populated additive/mixed inputs | Same routing and ordered scientific input assembly | Point-source flow, deferred unrutted handling, shared counters inspected |
| Legacy/unbound parameterization | Existing read-only preview and Prepare-before-Run behavior | Named helper body parity and unchanged facade mutation boundaries |
| Invalid dimensions or missing required inputs | Same explicit failure/skipped evidence | Unrutted candidate and fit-failure branches inspected |
| Native contributor or watershed failure | Retained diagnostics; no current publication | Per-contributor catch/return paths and facade final failure handler inspected |
| Failed preparation after invalidation | Existing error contract and durable failure | Facade try/lock/invalidation boundaries inspected |
| Partial publication/retry | Existing freshness and retention behavior | Publication sequence and unchanged lifecycle consumers inspected |
| Cancellation during upload | Existing rollback semantics | `BaseException` boundaries retained in facade |

Malformed/hostile path and persistence behavior is not claimed solely from this
matrix. Existing safety helpers and production boundary tests remain required;
security review is a distinct gate.

## Generated-artifact and runtime limitations

The retained baseline validation artifact reports 527 native tests, including
516 profile cases, and five baseline project controls with immutable source and
baseline checks. Those are baseline evidence, not proof of this candidate.
At this review time candidate validations are in flight. Acceptance still needs
candidate input/output comparisons, binary/source identity, fresh output and
report readback, failure/currentness checks, and broad-suite disposition. No
claim of native equivalence, project parity, or final local acceptance follows
from AST equivalence or this source verdict alone.

Existing tests predominantly enter through the facade, which is useful for
checking wired collaborators and compatibility. Final receipts must identify
both dirty source state and the source tree actually mounted by the container;
a pass from an earlier source snapshot cannot qualify this review snapshot.

## Reviewed source SHA-256

Paths below are relative to `wepppy/nodb/mods/roads/`.

| File | SHA-256 |
| --- | --- |
| `roads.py` | `a53920220275bc46afc2ba405f061788c3621b87fc22b4c0bcbd3a3796775321` |
| `_constants.py` | `a84566a6d3f294d51efaee0736c9f0448c613f23b0cbaa1e275e3fc04b99d810` |
| `_execution.py` | `9b818fa58c6a24e6bd16688323eccd31cfed01376bc7ff0bd5827851c38b3a02` |
| `_inputs.py` | `31c51b50f207cde9fb7a130d02738ddee3b4bccd7045957e25442a94063559d6` |
| `_management_inputs.py` | `f92d3b2ab7d6a8a2025d41e94d8f93d683d583fd51f04d17199f2331bc63ca3f` |
| `_native_runner.py` | `cc553403ea447b9eb8044e10df50e59db7a00235b9921341d4456a2f61210e20` |
| `_parameterization_support.py` | `362ac0339308df1ec41b362aaca2de654ef25763713cba79019177d0b986b33f` |
| `_pass_routing.py` | `4e954fb59c108d21ebbb67a2deadda027cd01d4c8182bc9b37e0217cd5ef6d47` |
| `_point_source.py` | `307234e49c0709399c10677aacfcb4b73bc0e411b2ec8dc1d903d1628a4898f7` |
| `_prepare.py` | `b77a2208c634d2e8f5189a5c84e80320b34ce9d8f10977d389cce82baf1b340d` |
| `_queries.py` | `f2fc4179d65b9eda931ac823abdffa86d0ce7d3fa3b73bc2796695b8739832a3` |
| `_reporting.py` | `493a509c8d2cc4e23a7993cede9dc1b9b044587b984d804a898587a8e3820a82` |
| `_slope_inputs.py` | `fd23e48ca799755eb4e36a16fdc1e3fe49fdd0dc2cfe7c184150637ab8ba459b` |
| `_soil_inputs.py` | `fcbdf4d840cf9cd555f79eae79de5a90cba33e78d47740e3149c9a5c935fe595` |
| `_spatial.py` | `02b84f6bffd77f95854736dd842874e067aa29f31d1e38034c3439b57f04137e` |
| `_unrutted_execution.py` | `b565c56b24520e086b11e1f36906774c020d1ade4b34f730f8f3f097fc283380` |
| `_unrutted_native.py` | `756768a5bc611e7a71aa6c2f168827fc984d3a845c7fb7c09e7a023e74e69a74` |
| `_unrutted_planning.py` | `33288212743d590a2b885dc2460a50308fb28c1ebd19f4b9dcf18c559ea58f44` |
