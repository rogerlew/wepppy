# Final broad validation disposition

**Broad acceptance remains incomplete.** All 15,104 collected test nodes are
accounted for in a qualified composite: **14,582 passed, 505 runtime skipped,
nine failed and eight setup errors**. One collection skip is separate. This is
not an uninterrupted full-suite pass, and the broad gate does not close M5.

The exact ordered per-node evidence is retained as
[compressed machine data](broad_evidence/broad_final_node_evidence.json.gz).
[Reconciliation](broad_final_reconciliation.json) records source hashes, evidence
origins, the complete remaining failure list and all qualifications. The
[packaging receipt](broad_evidence/packaging_receipt.json) maps original runtime
bytes to deterministic gzip files and verifies every decompressed hash. Failed
attempts remain preserved; normalized console copies are not the originals used
in this package.

## Successful complete-module replacement

The final guarded replay selected 17 complete modules, 391 nodes, from the same
ordered 15,104-item collection. It passed all 391 tests in 55.79 seconds, with
1,173 complete phases and no runtime skips. Both exit statuses are zero. Source,
environment, runtime inputs, script, selection specification and pinned evidence
were unchanged. The before/after 2,836-file source manifest SHA-256 is
`4c58acdf39d0ffef185b86b14c0d8d15b60520e902f67bc5ce0cf2e450412100`.

The replay replaces all 391 prior module results: 192 passes and 199 failures.
The resolved failures comprise 194 shape-parser cases, four ordinary-retention
fixture cases and one AF_UNIX pathname-length case. Existing parser binaries and
their provenance sidecars were mounted read-only at canonical paths. Both source
manifests match the baseline and candidate; no native build, dependency install,
service change or shape source edit was made. The GeoParquet artifact came from
an existing local image, inspected through a stopped container that was never
started. Its [identity receipt](geoparquet_existing_artifact_check.json) binds
image, binary, sidecar and source hashes. A short isolated basetemp avoids the
socket-path limit; this is an explicit environment change.

QA accepts the two source changes at `5812caa02`: three added lines each in
`tests/rq/test_batch_rq_retry_selection.py` and
`tests/rq/test_project_rq_delete_run.py` clear inherited retention ID/root only for
ordinary temporary workspaces. Baseline reproduces all four affected failures.
Dedicated retention cases and assertions remain unchanged. Their complete
50-test scoped run and the subsequent complete-module replay both pass. No
medium/high quality finding remains in these bounded fixture changes.

## Remaining failures and errors

| Class | Nodes | Disposition |
| --- | ---: | --- |
| Missing generated `controllers-gl.js` | 1 failure | Reproduced on baseline; no unrelated bundle generated or mounted. |
| Missing Jinja fixture global `account_display_email` | 4 failures | Reproduced on baseline; unrelated fixture expansion deferred. |
| Missing Playwright dependencies | 3 failures | Reproduced on baseline; no packages installed or mounted. |
| Catalog notification latency | 1 failure | Isolated baseline passed; full-suite load behavior remains inconclusive. |
| PostgreSQL `user.account_kind` schema mismatch | 8 setup errors | Representative baseline setup reproduces the same error; no shared schema changed. |

The [non-shape assessment](nonshape_failure_class_assessment.md) and
[receipt](nonshape_failure_class_receipt.json) retain attribution and commands.
Baseline attribution explains scope; it does not convert these outcomes into
passes. No threshold was relaxed and no failing test was skipped to close the gate.

## Source drift and composite limits

v5 changed only `wepppy/wepp/management/scripts/man42_5.man.json`, adding
`_pmet_plant_names: null`. The existing import-triggered writer reproduced the
changed bytes exactly on copied input. QA independently verified the captured
before/after hashes, sole semantic delta, copied-input reproduction and exact
HEAD restoration. The [drift receipt](management_sidecar_drift_receipt.json)
retains that evidence. Restoration explains the current clean source state; it
does not make v5's source-integrity gate pass.

The composite retains 2,947 original-prefix outcomes reconstructed from quiet
progress and stable later collection; those original per-node reports were not
captured. Those tests used the driver's global `/tmp` retention root. Canonical
replays use `/wc1`; the native-parser mounts and shorter basetemp add further
explicit variance. Continuations and replacements run in separate processes, so
cross-boundary session state is not revalidated. Original-prefix and v5 subtest
reports remain separate from unique-node counts.

Roads source-quality, focused validation, native output identity and five-project
parity evidence remain independent accepted gates. This broader result supplies
complete qualified accounting with unresolved failures, not broad acceptance.
