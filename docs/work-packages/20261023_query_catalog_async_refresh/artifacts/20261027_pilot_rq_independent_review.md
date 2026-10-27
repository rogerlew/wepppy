# Independent RQ pilot implementation review

Reviewer scope: `_query_catalog_admission.py`, `_query_catalog_pilot.py`, pilot paths in `query_catalog_rq.py` and `_query_catalog_inventory.py`, and their tests. The reviewer authored the operator CLI, so this artifact does **not** approve that CLI; it requires the separate implementation/security reviews. Production execution remains pending.

Status: **PASS for the bounded RQ implementation gate**, 2026-10-27 UTC. All three original review findings and the subsequent security cancellation finding are closed in the retained final source. This does not approve production deployment, the reviewer's own CLI, shared-queue acceptance, or general enablement.

## Findings and closure

1. **Admission queue scan must remain conservative under corrupt duplicates.** Inspecting only the first eight queue IDs assumes a unique maintenance entry per permit. Duplicate known IDs could pad that prefix and hide ordinary waiting work later in the list. Scan all raw IDs or validate the necessary invariant explicitly; reject duplicate/uncertain records and retain a real Redis regression proving no admission/counter debit. **Closed:** full raw queue scan, duplicate/status checks and ordinary-tail regression are present.
2. **Pilot reconciliation must not initialize scope identity.** Registered pilot fixtures already have an incarnation. Its reconciliation path should resolve with `create=False`, then revalidate authority/identity under the shared filesystem guard immediately before receipt creation. Keep ordinary non-pilot initialization behavior unchanged. **Closed:** pilot resolution uses `create=False`; receipt creation revalidates authority and scope inside the shared guard. General initialization is unchanged.

3. **Execution claim must watch its job-state precondition.** The claim initially read `started` without watching the job hash, allowing a concurrent cancellation before EXEC to escape CAS detection. **Closed:** the job hash is watched with the ledger. The real Redis regression cancels during scope validation, proves the retry rejects the canceled state, and verifies the authority remains unclaimed.

4. **Running cancellation must not free a live execution permit (security finding PILOT-SEC-04).** RQ `Job.cancel()` can mark a claimed running job canceled without stopping its process. **Closed, independently rechecked:** admission, pilot/global status and observation share the same cancellation-aware classification. A claimed canceled job remains outstanding and uncertain until its matching `execution_exited_at` is committed. Both refresh and inventory workers enter their exit-recording `finally` only after a successful execution claim; suspension, identity rejection after claim and exceptions are covered, while a rejected replay cannot mark the original execution exited. The exit marker follows catalog/inventory scope work, so it is evidence of leaving that execution boundary, not a claim that RQ finished all administrative cleanup.

The cancellation change is deliberately bounded. Unclaimed cancellation remains releasable under the watched claim/status race. Ordinary `finished`, `failed` and `stopped` transitions retain RQ death/timeout recovery semantics. A claimed cancellation without exit proof remains held for explicit recovery; neither vanished worker registration nor a canceled label proves scope work stopped. The retained actual-process regression holds refresh work, calls real `Job.cancel()`, observes seven outstanding and one uncertain job, denies an eighth admission, rejects replay without creating an exit marker, then releases the process and verifies the exit marker, catalog and zero pending receipts. This is stronger evidence than terminal labels or a simulated job-state-only test.

A separate parent finding identified host-local `st_dev` mismatch on the shared production filesystem. The final implementation binds pilot directory identity to inode plus namespace/incarnation/owned-marker binding, with different-device/same-inode acceptance and replacement-inode rejection tests. The operator CLI does not independently freeze `st_dev`.

## Confirmed design properties from current source

- Fixed `batch` queue and one global permit ledger; manifest/counter/permit writes join the RQ enqueue transaction. All eligible eight pilot participants are checked in the admission transaction.
- Scope allowlist, configuration, generation and job binding are explicit. General async remains false outside the tagged pilot exception. Claimed job authority cannot be reused by same-ID reexecution.
- Exact allowlist inventory seeds and worker-side scope validation prevent recursive discovery of unlisted child scopes. Pilot reconciliation does not consume ordinary dirty indexes.
- Controller ownership and observations have finite leases; already-admitted jobs may drain after pause/expiry. Cumulative job budgets and original deadline persist separately from controller lifetime.
- Missing accounting remains unavailable rather than implicitly resetting pilot budgets. Raw queue IDs and primitive fields drive policy; no arbitrary task deserialization is needed for admission.

The current real Redis tests exercise these implementation boundaries but use test worker registrations. They do not replace deployment parity or actual shared-queue acceptance on the eight existing consumers. Final post-cancellation author validation passed **72 tests in 35.90 seconds** (`pilot-rq-final-tests.log`). Independent security validation passed **86 RQ/disclosure tests in 37.06 seconds** (`pilot-security-rq-final-tests.log`), and its separate actual-process cancellation reproduction passed (`pilot-security-cancellation-after.log`). Earlier 68/20-test checkpoints are retained history; they did not cover the subsequently confirmed live-cancellation defect. I independently inspected the final classification, both worker boundaries, cancellation regression and retained results. No further rerun was necessary for this read-only closure. The independent CLI/security reviews and the parent's broader/deployment gates remain separate. Production capacity and ordinary-work delay cannot be approved from local tests.


## Reviewed source hashes

| File | SHA256 |
| --- | --- |
| `_query_catalog_admission.py` | `ccf94032d46ec7038017a4f219b13e1d288b59753412ea3b9fdcf60abfecaf80` |
| `_query_catalog_pilot.py` | `c85de18002b08dd5fc9d69f4bb597df0a03bb2b18f2e333d838f401881fbb0c5` |
| `query_catalog_rq.py` | `6de79801a17428df2caccd8fb7a449dfa1bf960b6b6bbd7dfa2fa397a4222ce9` |
| `_query_catalog_inventory.py` | `f023fc55743141705aa964baf9ded6a4d031319c8b247f90c95583daa31de1b4` |
