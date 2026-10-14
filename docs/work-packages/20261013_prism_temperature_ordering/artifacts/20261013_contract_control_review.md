# Independent M1 contract control review

**Reviewer**: governance control agent, `/root/prism_contract_control`.
**Reviewed**: 2026-10-14 01:55 UTC.
**Decision**: approve the amended M1 contract checkpoint; C1 and C2 resolved at contract level after independent re-review. This is a contract review, not implementation conformance or deployment approval.

## Authority and evidence

The operator accepted the midpoint proposal, requested this package and ADR, and then explicitly requested `execute docs/work-packages/20261013_prism_temperature_ordering`. That authorizes the named four writers, matched tests, affected native build/release refresh, and development acceptance. It does not authorize deployment, existing-project rebuilds, new EDDE application integration, unrelated forcing corrections, or a new dependency/service. No emergency or break-glass exception is needed or claimed.

Reviewed WEPPpy base `78295c949bf5832c9d1ffaa5b8c708387f9aa356`, sibling wepppyo3 base `822b6fe1200d980e9eb434547097c976eafcc38f`, package/ExecPlan, contract decision, proposed generic and amended EDDE contracts, ADR-0091/0092, and the current four writers. The sibling worktree was clean; no implementation changes were present in WEPPpy at review. The generated usersum index is unrelated and excluded. This reviewer did not author the proposed contract or implementation and edited only this review artifact.

ADR-0092 records the decision owner, scientific rationale, alternatives, measured prototype evidence, rounding limitations, and rollback. The new canonical schema correctly separates an intended rule from implementation conformance. Durable authority is outside the work package. The generic source-temperature rejection is explicitly a new validation rule; preserve that distinction rather than claiming that the generic writers previously enforced it. Native `cli_revision` currently translates returned I/O errors into `OSError`; EDDE already validates its source and output.

Low security impact is appropriate: bounded arithmetic, existing inputs/output channels, no new egress, credentials, route, process privilege, or deployment topology. A dedicated high-impact security review is not required by the current delta. Native artifact provenance and normal service identity acceptance remain necessary; a source patch cannot demonstrate what the consumer imports.

## Findings

### C1 — Medium, resolved: correction diagnostics lack a durable project destination

The proposed generic contract's Diagnostics and provenance section specifies a native process-output summary and Python logs, but does not identify how those summaries reach the project's inspectable records. Current native output is `println!` in `cli_revision/src/lib.rs`; the NoDb helper directly invokes that function. Project climate logging is a distinct `wepppy.run.<runid>.climate` logger with a `climate.log` file handler (`wepppy/nodb/base.py:_init_logging`). A generic module logger or worker stdout is not, by itself, evidence of capture there.

**Required disposition before checkpoint**: name the existing durable project destination and the bounded delivery mechanism for native and breakpoint correction summaries; retain source/output context, method, count, and magnitude. Avoid global stdout redirection in concurrent builds. The contract must distinguish the standalone API's caller-owned logs from WEPPcloud's project-owned records. Add a direct acceptance assertion that a real project build retains the summary, including a zero-correction case, without cross-project attribution. No new hidden artifact location is justified.

### C2 — Medium, resolved: canonical archive/restore and browser evidence are absent from the acceptance matrix

The package plans generated-to-consumed climate checks and an evidence archive, but these are not the project archive/restore and browser/download checks required by the artifact-observability standard for changed artifact-producing workflows. The current matrix omits visible working/failed/completed artifact states and exact archive coverage. A package tarball does not establish normal project retention.

**Required disposition before checkpoint**: add a canonical inventory of the existing PRISM input, output, diagnostic, and retained partial-failure locations; enumerate working/failed/completed and legacy states. Plan a normal project browser/download check and a real canonical archive/restore round trip, asserting expected member paths and byte preservation for generated climate and retained diagnostics. Reuse existing paths and archive behavior. The standalone EDDE adapter remains outside project/browser integration; its companion metadata and useful failure evidence must remain retained, without claiming application integration.

## Approved boundaries and continuing obligations

- Keep exactly the midpoint projection for finite PRISM-introduced crossings; no positive-range floor or repair of malformed source data.
- Keep valid same-writer output, precipitation, breakpoint records, auxiliary fields, public returns, NoDb keys, ownership, and finalization semantics unchanged.
- Preserve the paired Rust/Python rollback and prior EDDE rejection posture if implementation acceptance fails; record exact source/native identities. No live rollback or deployment is authorized here.
- After both independent reviews are dispositioned, commit the complete checkpoint as an ancestor before implementation. Final review must verify ancestry, actual rebuilt-module import, finite/ordered serialized extrema, unchanged valid cases, and fresh WEPP consumption.
- Scientific acceptance is bounded to the measured fixture matrix. The prototype's three successful WEPP runs do not establish final production conformance, all-dataset validity, or corrected future auxiliary weather.

## Re-review confirmation

Re-reviewed the amended canonical temperature-ordering contract, checkpoint, package, and ExecPlan on 2026-10-14 01:57 UTC. No implementation changes were present in either repository. The original findings above are retained as review history.

C1 is resolved by a visible, output-specific `<output-cli>.temperature-ordering.log` in the existing climate or retained attempt directory. The contract specifies source/output attribution, a working record, completion only after successful climate write/flush, scalar correction diagnostics including zero corrections, incomplete-failure retention, legacy-project compatibility, and occupied-log rejection for EDDE. This bounded record is a justified escalation from process-only logs after identifying the absent project-log capture. It adds no storage service, hidden directory, public return change, or global stdout interception. Existing publication must carry the log with its climate; implementation and tests must establish this delivery rather than infer it.

C2 is resolved by the canonical Artifact visibility and downstream scope section and matching execution-plan obligations. They inventory the existing source/normal paths, revised climate/log siblings, visible failed attempts and EDDE companion, require canonical project ZIP/restore payload-hash checks, and require actual browser/download handling under the configured service identity. Missing historical logs remain a valid legacy state. No archive exclusion or authorization exception is introduced. These are acceptance obligations, not claims that the tests have already run.

The downstream clarification correctly preserves Historic PRISM's existing dewpoint floor on final Tmin. Writer-level auxiliary invariance must not be misread as authority to freeze an earlier Tmin-dependent downstream value. The additional repaired-day regression verifies unchanged downstream policy rather than introducing a second scientific decision.

No unresolved medium/high control finding remains. The primary agent may include this approval and its dispositions in the standalone contract ancestor; implementation remains gated on that commit and the other independent review. Final correctness/consumer acceptance must verify the promised retention, archive/browser behavior, rebuilt native artifact, and rollback identities before closure. No production deployment or automatic project rebuild is approved.
