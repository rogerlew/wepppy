# Independent correctness review: per-run stream selection contract

Review date: 2026-11-16 UTC. Reviewer: `per_run_contract_correctness`.
Scope: read-only review of the proposed stream-selection contract, ADR-0144,
contract checkpoint, integration-spec transition, and relevant existing RQ/NoDb
selection behavior. No implementation or normative-document edits made.

Verdict after re-review: approve the contract checkpoint. The two medium findings
below are resolved by the updated normative contract; implementation and runtime
acceptance remain pending.

## Findings

### C1 — Medium, resolved: configured-count precedence could disable map mode

`docs/schemas/culvert-stream-selection-contract.md:31` says both a configured
fixed count and an explicit payload count take precedence over map mode. Every
`CulvertsRunner` already has a configured `_order_reduction_passes` value
(`wepppy/nodb/culverts_runner.py:89`), including map-mode runners. Existing
`run_culvert_batch_rq` instead starts with that value, applies the mapped value
when mode is map and mapping is available, then applies a payload override.
The proposed wording permits an implementation to always choose the configured
count and never use the new 4/3/2/1 bins.

Required clarification: explicit valid payload override wins; otherwise map mode
uses its valid mapping; otherwise fixed/configured count is used. Explicitly
retain the existing missing/nonpositive-cellsize mapping behavior and define
whether the existing invalid-override behavior changes. Add precedence and
missing-resolution cases to the regression list. Update ADR/checkpoint wording
as needed so it does not imply configured count overrides active map mode.

### C2 — Medium, resolved: incomplete preparation and legacy absence needed distinct states

`docs/schemas/culvert-stream-selection-contract.md:68` identifies legacy batches
by manifest absence, while line72 requires partial new generation to fail.
A new batch interrupted before the final manifest is written also has no
manifest. Without a durable distinction, an interrupted new-policy preparation
or missing-manifest new-policy resume can silently enter the legacy path and
bypass the per-run intersection contract. Conversely, treating every missing
manifest as failure would break the promised retained-batch compatibility.

Required clarification: bind new-policy intent/version durably before generating
its candidates, independently of the final ready manifest. Define the first-bind
rule for already-admitted but never-prepared batches, and state that only truly
unbound retained legacy state follows the old path. Publish readiness atomically
after all candidates validate; interrupted preparation must resume under the
bound version or fail explicitly, never downgrade. Test interruption before
manifest publication, missing ready manifest after policy binding, and parent
retry with already-consumed immutable candidates.

## Supported direction and residual risk

The descending ladder, original-stream pass zero, point intersection plus
watershed coverage, explicit rejection versus infrastructure errors, additive
selection receipts, and actual RQ/artifact gates are appropriate to the operator's
request. The proposed nominal starts are bounded heuristics; the contract
correctly retains the unresolved 4 m TOPAZ failure and avoids claiming universal
calibration. Keeping the existing outlet-finding algorithm means acceptance must
still verify its resolved outlet and connected generated network, not merely the
candidate's point sample. Existing legacy paths may retain their old mismatch
behavior intentionally; this is compatibility, not new-policy acceptance.

No implementation, live replay, or final scientific acceptance is approved by
this document. The checkpoint may proceed once the other independent review and
operator commit-authority requirements are satisfied.

## Re-review and disposition — 2026-11-16 UTC

C1 is resolved in the contract's Starting pass count section: explicit payload
count, valid active map-mode result, then configured count; missing/nonpositive
cell size preserves the configured-count behavior. Existing upload validation
continues to reject negative/malformed overrides; this checkpoint does not
change the client payload contract. Include precedence/missing-resolution
regressions during implementation.

C2 is resolved in Persistence and compatibility and Artifact lifecycle and
observability: new admission durably writes a separate versioned policy-intent
marker; retained batches without that marker stay legacy. A marker with an
absent/not-ready manifest is explicitly incomplete, never legacy. Atomic
preparing/ready/failed publication, no child execution against incomplete
candidates, immutable referenced ready sets, and identity-verifying resume
provide the required state distinction. The checkpoint explicitly includes the
narrow admission-marker write, while keeping external API/auth/queue contracts
unchanged. Existing admitted batches without a marker therefore remain legacy.

Archive/restore obligations now retain the marker, manifest, candidate topology,
and receipts together, with resolvable references and actual readback evidence.
This is consistent with the promised resume/retention behavior rather than a
new standalone-archive guarantee.

No remaining medium/high correctness finding in the contract checkpoint.
Residual implementation gates: invalid/unknown policy markers must fail
explicitly; test interruptions before readiness and parent retries after child
consumption; verify both VRT and symlink consumers use the selected immutable
network and matching per-run regenerated junctions; retain the unresolved
4 m terrain-tool failure without treating it as zero cardinality or successful
calibration. No universal scientific calibration or production deployment is
implied by this approval.
