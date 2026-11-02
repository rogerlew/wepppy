# MIPA-01 producer repair checkpoint

## Authority and status

User instruction: `execute docs/work-packages/20261102_mofe_input_producer_audit/`.
This starts execution of M1 and authorizes preparing the bounded producer repairs.
The previous audit-only session restriction no longer describes this session.
Separate native repair, deployment and existing-project mutation remain excluded.

The operator approved the reviewed decisions and standalone contract commit on
2026-11-02 with “approved. proceed”. Two independent reviews passed. This
checkpoint records that ratification before production edits; implementation may
start after its standalone ancestor commit is recorded in the tracker. Native
repair, deployment and existing-project regeneration remain excluded.

Starting WEPPpy revision: `3c4b6fe839a4caea62b5f92bb16ba482de7ab703`.
wepppyo3 HEAD: `4d4c075421c4013cba99a0addc76482229e7f3f7`.
Both workspaces contain unrelated changes. Preserve them and the rock/water
evidence. Do not switch branches, rebuild shared binaries or stage entire trees.
The Rust tree currently has unrelated calendar/hill_hbp edits; coordinate any
later build without changing its installed release artifact.

## Contract set and exact delta

The proposed durable specification is
[MOFE input identity](../../../schemas/mofe-input-identity-contract.md), cross-linked
from the existing management and Disturbed mapping contracts. Existing
[single user-defined inputs](../../../schemas/single-user-defined-inputs-contract.md),
[WEPP input](../../../schemas/wepp-run-input-contract.md),
[soil horizon boundaries](../../../schemas/soil-horizon-boundary-contract.md),
[NoDb persistence](../../../schemas/nodb-persistence-concurrency-contract.md),
[RQ errors](../../../schemas/rq-response-contract.md),
[whole-soil ownership](../../../schemas/whole-soil-water-capacity-contract.md),
artifact observability and generated-artifact validation remain unchanged.

The proposed decisions are: preserve independent chronological source calendars
over a logical common repeating period and expand directly to exactly N years
without eagerly allocating that period; preserve all plant
references including residue; enumerate all staged crop scenarios; represent
different PMET coefficient contexts with collision-checked eight-character keys
and corresponding generated reference graphs; preserve existing Disturbed lookup
and fallback values while using actual segment assignments; apply soil eligibility
and 9005 texture per element; order RAP blocks numerically; reject zero/negative/
nonfinite enabled buffers and intervals that serialize to zero, without silent
merging. Positive overlong buffers and ignored `min_length` keep existing behavior.

These are intended behavior changes where the previous canonical contracts do not
specify calendar alignment, native key collisions or enabled zero-buffer handling.
They are not presented as unchanged-contract conformance fixes to evade the
checkpoint. Existing mapping/cover/upload precedence remains binding.

Rationale: first-element or first-row reuse can yield successful but scientifically
misassigned inputs. Calendar truncation, implicit buffer disabling and coefficient
first-wins selection are rejected because they lose approved element identity.
Rejecting all mixed calendars or same-crop/different-texture projects would also
remove legitimate behavior; the proposal preserves them through explicit identity.

## Compatibility and regression plan before data mutation

No source runs or persisted schemas change in M1. Later repairs keep keys,
filenames, native record formats, source upload bytes and single-OFE parameter
values. Generated crop aliases and corrected calendar contents may change; all
dependent references must change together in generated copies. No hidden migration
or automatic repair of old outputs is permitted. Regeneration is the compatibility
boundary, and old generated artifacts are not retroactively declared correct.

M2 must prove all staged crops have the intended coefficients, including repeated
names across hillslopes, shared scenario graphs, rotations and reversed PMET row
order. Count any graph expansion against the selected native capacity; do not cap
or alter native limits. Retain before/after input and output differences where
native acceptance is available. No parameter defaults/formulas change; any needed
fallback or classification change requires a separate ADR before implementation.

M3 must serialize/reparse ordinary and deduplicated 1/2- and 2/3-year combinations,
multiple source rotations, nonmultiple simulation durations and operations 10/12.
Include coprime calendar periods with small N to prove bounded expansion. Any
standalone full-period preallocation failure must name an existing applicable
limit, not introduce a speculative resource restriction.
Test reversed developed/forest soil order, preserved uploads and ordinary/debug
9005 output; twelve ordered RAP blocks in both writers; buffer and explicit-slope
limits, endpoint precision and total length. Reproduce stale/count-mismatched decks,
multi-OFE stack members and equal map boundaries before choosing added guards.

The state matrix, exceptional error policy, output inventory and supported
archive/restore behavior are in the proposed canonical contract. No route/queue
behavior or NoDb locking change is intended. Existing partial failure remains
visible; direct tests must establish no false success and successful normal retry.

## Security and validation scope

M1 is isolated fixture execution and documentation, with no production boundary
change. Planned repair triage is high for changes involving generated-file
publication or staged reference rewriting: obtain a dedicated implementation
security review and prove valid-state noninterference. Contract reviews are not
security approval for unimplemented file writes. No upload, auth, path, subprocess
or runtime identity redesign is authorized.

The renewed baseline uses the running `weppcloud` container via `wctl`, Python
3.12.16 at `/opt/venv/bin/python`. Management evidence binds individual source
hashes in [observations](m1_management_baseline_v1/observations.json) and a
[manifest](m1_management_baseline_v1/manifest.json). Actual Python writers still
omit the second crop, point OFE2 residue at OFE1, lose the second calendar year
and emit an expanded file that fails readback. These are failed producer checks,
not passing acceptance.

The [soil baseline](m1_python_baseline_v1.json) remains an AST-method probe only.
The [Rust baseline](m1_rust_baseline_v1/readback.json) binds the installed extension
`7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad`;
zero/negative buffers and the tiny interval still generate invalid slopes.
It does not establish source-to-binary provenance or full WEPP execution.

Existing focused tests passed: 21 tests across `test_multiple_ofe.py`,
`test_rotation_stack.py`, `test_pmetpara_prep.py` and
`test_wepp_multi_ofe_management_propagation.py`. This contrast confirms missing
regressions. No full suite is necessary before production changes exist.

An additional [calendar boundary probe](m1_calendar_baseline_v2/observations.json)
isolates MAN-03 without MOFE synthesis: an ordinary two-rotation source changes
its second rotation's yearly reference on write/read; expansion to four years
actually emits eight and fails parsing. An isolated in-memory single-rotation
normalization retains the intended references and yields exactly four readable
years. This is a diagnostic experiment, not an implemented or native-validated
repair. Version 1 is retained; version 2 adds intended-reference comparison.

M4 actual-project selection, supported clone, exact native binary and 9005 consumer
binding remain pending. NATIVE-01/02/03 remain open; this checkpoint cannot approve
unrestricted heterogeneous native execution. Obtain separate native authority if
repair is required, retaining the existing scientific HOLD.

## Review and ancestor receipt

Two independent read-only contract reviews are retained:
[correctness](m1_contract_correctness_review.md) and
[scope/governance](m1_contract_scope_review.md). Initial correctness findings
COR-01/02/03 require bounded calendar expansion, repeat-invocation identity
provenance, and native-token-safe aliases. The canonical proposal now specifies
direct N-year expansion without eager common-period allocation; validated
machine-readable original-name/context comments and idempotence across repeated
scalar/mapping calls and archive/restore; and aliases restricted to letters,
digits and underscore with a leading letter. Exact collision checking remains
required. These are contract clarifications, not implemented behavior.

The scope review's low observations concern common-period allocation and stale
audit-only present-tense wording. The first is covered above; package/plan text
now distinguishes original audit provenance from current M1 execution. Both
reviewers independently confirmed the revised text and passed design readiness
with no unresolved findings. Initial findings remain in their review records.
Ratification and commit authority are now granted. The ancestor
must include only this checkpoint, proposed canonical amendments, review artifacts
and relevant package status; no unrelated dirty files. Record its SHA in the
tracker before production edits. No ancestor commit exists yet.

## Final M1 checks

Package doc-lint passes all eleven Markdown files with zero errors/warnings.
The three affected schema documents and project board also pass. Relative file
links across fourteen package/schema Markdown files resolve, three retained
management/calendar manifests verify, and all ten production/fixture hashes
recorded by the management baseline remain unchanged. Spelling previews and
scoped `git diff --check` pass. No production change, native build/run, shared
release artifact replacement or existing-project mutation occurred.
