# NFMS-01 contract decision

Date: 2026-10-31 UTC. Starting revision:
`2f2bd0ef49f7521f0b888c94d4cdd16e473de416`, branch `master`.
Checkpoint status: independently accepted after revisions; no ancestor commit yet.
Reviews and dispositions: `20261031_review_disposition.md`.

## Authority and classification

Operator request: execute the retained `prompts/active/operator_prompt.md`.
It explicitly authorizes clean reusable state after failed mutation, confirmed
peer consumers, tests, contract amendments and independent reviews. It explicitly
does not grant commit authority. Preserve unrelated roads-program dirty files
and ignore generated `docs_index.json`.

Classification: normative behavior extension. Prior persistence contract requires
disk authority, lock fencing and signature freshness, but does not define immediate
held-reference repair or quarantine. Its Batch receipt precedent promises next-read
invalidation only. MRS-01 explicitly makes no rollback promise for later storage
errors; this amendment does not undo commits and leaves that statement intact.

## Applicable canonical authority

- `docs/schemas/nodb-persistence-concurrency-contract.md`: storage, ownership,
  cache, coherent reads, atomic commit, retries, Batch receipt; add NFMS-01 section.
- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`: preserve scoped
  invalidation placement, not a substitute for recovery.
- `docs/schemas/wepp-run-input-contract.md`: WAM-01 admission, leases, replay,
  no-prep prepared files and omission policy unchanged.
- `docs/schemas/request-payload-contract.md`: MRS-01 early rejection and valid
  defaults unchanged. Do not weaken validation to manufacture a reproduction.
- `docs/schemas/rq-response-contract.md` and `rq-webhook-contract.md`: unchanged
  error envelopes/publication outcome; no queue or callback mutation proposed.
- `docs/schemas/single-user-defined-inputs-contract.md`, Source state, publication
  and recovery: amend ambiguous disk-failure wording to distinguish metadata
  precommit rejection from postcommit accepted source retention; cross-link NFMS.
- `wepppy/nodb/mods/postfire_debris_flow/docs/production_m1.md`, Durable state and
  immutable artifacts; Observable intermediate artifacts and migration; Attempt
  receipts and migration exclusion; Fixed completed-file access: preserve
  accepted pointers, receipts, explicit recovery, admission and publication.
  The domain specification Artifact observability section delegates here.
- `docs/schemas/climate-parquet-lineage-contract.md`, Daymet source preservation:
  retain original attempts/backups and independently finalized stages. Later
  PRISM failure cannot roll back a finalized Daymet generation.
- Grouped Soils/Watershed compensation remains bounded by existing ownership and
  generation checks. NFMS adds no new distributed rollback; after existing
  compensation, memory must reflect actual durable state or be unusable.
  No domain value or external rollback is authorized.

## Normative delta and rationale

The new canonical NFMS-01 section specifies acquired abort, acquire failure,
pre/post-commit distinction, failed recovery, aliases, resource lifecycle,
initialization, direct persistence retries and composite state. Successful recovery
preserves controller identity; unsafe recovery makes the failed instance unusable.
First initialization with no prior disk preserves its original failure and requires
a fresh initialization object. Optional absent reads retain None behavior.

Preferred implementation direction: eager disk-only coherent in-place recovery
on failed owned high-level mutations, with enforced unusability only when safe
recovery is impossible. Existing hydration can initialize logging and mirrors;
do not naively reuse it without lifecycle analysis. Use local staging for options
mutated before lock acquisition. Reject shallow snapshots/global eviction because
they miss nested values and held references. Reject healthy-path serialization
snapshots absent measured necessity. Exact implementation remains subject to
boundary tests and review; a changed normative outcome needs a new checkpoint.

## Compatibility, security and evidence

No payload schema change, scientific/default change or external API expansion.
Direct low-level dump retries survive; stale dumps must still refresh/reapply.
Shared failed-state recovery does not roll back commits or cross-owner state;
existing domain compensation remains separately bounded as stated above. Security impact high:
shared ownership/state enforcement, requiring a dedicated final security artifact.
Valid states: absent initialization/optional feature, present-empty, populated,
supported legacy, detached/readonly; malformed durable state must fail explicitly.
Operational storage/Redis errors preserve primary exceptions and safe retry
instructions; no private recovery context in HTTP output.

The full required regression matrix is retained in the operator prompt and active
ExecPlan. Baseline probe proves contamination through real jsonpickle/filesystem
state. Follow-up must include real controllers, ownership interleavings, serialization,
write/fsync/replace and postcommit faults, recovery faults, held/nested references,
manual producers, resource/performance observations and exact prepared input parse.
Existing WAM/MRS, NoDb suite and full suite remain gates. No implementation or
closure claim is made by this checkpoint.
