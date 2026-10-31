# MRS-01 final QA review

Reviewer: independent `implementation_qa` agent. Scope: task-owned implementation
and regression tests in the working tree after contract checkpoint `ca28085ac`.
Unrelated Roads, Usersum, binary-release and research changes are excluded.

Verdict: **no open high or medium QA findings**. The earlier findings are closed
by the implementation and evidence below. Required full-suite and final
documentation gates were still running or being consolidated at review time;
this verdict does not assert their completion or production deployment.

## Findings and closure

| Finding | Closure evidence |
| --- | --- |
| Valid Treatments upload lacked evidence at the changed raster/promotion boundary | `tests/microservices/test_treatments_upload_persistence.py` uses actual GDAL rasters, real HTTP and NoDb reload. Invalid raster preserves the existing source/settings; valid follow-up produces readable derived raster pixels and persisted treatment assignments. |
| Dynamic route matrix omitted batch and culvert routes through its `/runs/` filter | `test_malformed_route_matrix.py` now includes every POST in its named route modules, including batch/culvert operations and batch uploads. The tested boundary suite passes. |
| Percent-encoded invalid UTF-8 was accepted differently by Flask and rq-engine | Shared `validate_form_encoding` rejects decoded invalid bytes; actual HTTP conformance includes `name=%FF` in both frameworks. |
| Equivalent blank/false form duplicates were configured only for RHEM | Domain `blank_false_fields` now covers the documented false-sentinel consumers, including landuse, soils, SWAT, OpenET, fork, DSS, migration, run-sync, RAP and the applicable WEPP flags. No blanket change to sparse no-override fields. |
| Flask URL form validation read an oversize body before enforcing its memory limit | `StrictFormDataParser` now checks declared size before reading and bounds unknown-length reads to limit plus one byte. Read-counting regressions prove both paths. Independently rerun: two passed. |

## Evidence assessed

- Inspected `/tmp/mrs-final-boundaries.log`: **220 passed**, including real
  Treatments apply/readback, relative-VRT staging, route matrix, upload cleanup,
  shared conformance and batch directive coverage.
- Inspected `/tmp/mrs-followup-tests.log`: **175 passed**, including Flask
  optional-controller persistence, agent routes, project mutations, batch
  directives and shared conformance.
- Independently executed
  `wctl run-pytest tests/microservices/test_request_payload_conformance.py -k url_form_limit_precedes_encoding_buffer -q`:
  **2 passed, 79 deselected**. Log: `/tmp/mrs-qa-url-limit.log`.
- Reviewed URL form adapter SHA-256:
  `f496f1f01f075a957b8a647a28ccd93bc2d1c8cd4762416fb06f68041948e1b8`.

The route matrix controls authorization and business boundaries; it proves error
translation/order for its enumerated routes, not complete persistence behavior
for each route. Real persistence/filesystem suites supply representative direct
evidence. No claim is made about unenumerated consumers or live deployment.

Residual non-blocking debt: several new tests use dense formatting and retain
unused imports; a later formatting pass would improve scanning. Keep framework
private-cache/stream integration covered when upgrading Werkzeug or Starlette.
No production or test files were edited by this reviewer.

## Gate inventory and session-test addendum

Independently reviewed the final broad-exception inventory update against
checkpoint `3ab204e9c`: all 985 prior entry IDs remain, and 34 existing entries
change only their source line. Owner, rationale, handler type and expiration
cells are unchanged. The retained `allowlist-line-refresh.json` contains exactly
those 34 relocations. Thirty-three match identical handler ASTs and enclosing
scopes automatically. The remaining export handler is independently verified by
an unchanged whole-function AST and corresponding handler order: lines 147/151
became 149/153. This does not renew expired historical approvals.

Approved the two explicit new entries, `BEA-20261030-MRS-0001` and
`BEA-20261030-MRS-0002`, at `payloads.py:65` and `request.py:48`. These deliberate
transport resource boundaries close temporary streams and re-raise failures;
they do not turn cancellation, disconnection or operational errors into empty
payloads. Both have accountable owners, bounded rationales and a 2027-04-30
revisit date. No other new suppression is included. Inspected the latest
`/tmp/mrs-exceptions-final.log`: default changed-file enforcement **PASS**, net
broad-handler delta -37. This approves the concrete inventory change, not an
exception to the gate.

The session-token no-Content-Length regression now spies both token issuance
and marker storage. Its malformed request asserts neither occurs; the valid
follow-up asserts both occur. This closes the earlier evidence gap between
marker-only observation and actual token minting.

## AgFields stub correction and broad route evidence

Reviewed the test-only correction in `test_rq_engine_ag_fields_routes.py`.
The dummy validator now asserts a sibling staging path with the expected suffix,
correct destination parent, exact uploaded bytes and unchanged original filename.
The real `validate_field_boundary_geojson` accepts the supplied path, reads and
validates a staged copy, and then replaces its canonical artifacts; it does not
require the old final upload basename. The revised assertions accurately model
that path contract and strengthen content checking. The accompanying upload
callback docstring clarifies the existing repaired behavior without changing it.

Inspected `/tmp/mrs-agfields-final.log`: **58 passed**. Inspected
`/tmp/mrs-routes-final.log`: **4,017 passed, 74 skipped** across microservices and
WEPPcloud. These results close the obsolete stub assertion; they do not represent
a completed full repository gate or additional unmocked AgFields geometry evidence.
No new blocking QA finding. Full repository gate remains separately pending.

## Full-gate environmental collision and continuation

The plain full-suite command in `validation/full-attempt-3.log` **failed** after
4,117 passes and 125 skips: the unchanged postfire M3 case could not acquire a
NoDb lock owned by container PID 1001876. Independent read-only process inspection
confirmed that owner was the concurrent `out/261029-r2-isolated` pytest worker.
No foreign lock was cleared or bypassed. Both affected parameter cases passed
with unique temporary-directory basenames: two passed, 66 deselected in
`validation/postfire-isolated.log`.

Reviewed `validation/isolated_tmp_plugin.py` and confirmed it matches the executed
cache copy. It changes only the default `tmp_path` basename and selects the
collection suffix beginning at the exact failed node, inclusive. It raises if
that node is absent or ambiguous; it does not mock persistence, native execution,
locking, or assertions. Continuation collects the same 12,819 items and explicitly
deselects 4,241 prior items, consistent with 4,117 prior passes and 124 executed
skips, plus one collection skip. This is a reasonable collision-isolated
continuation, with its final result still pending at this review.

Report the failed plain command and any continuation result separately. Their
combined evidence must not be described as one uninterrupted full-suite pass.
The shared basename-based test lock namespace is an environment/test-harness
limitation; this review does not authorize a production locking change.

## Treatments controller stub fidelity

Reviewed the two `_DummyDs` updates in
`tests/nodb/mods/test_treatments_build.py`: they add only the newly exercised
`GetRasterBand(1).Checksum()` interface, assert band 1, and return a valid checksum.
Existing valid-pixel, nodata and tie-breaking assertions are unchanged. These
algorithm tests still use controlled raster doubles; they do not claim native
GDAL evidence. The separate real-GDAL HTTP/persistence test supplies that boundary
evidence. Inspected `/tmp/mrs-treatment-final.log`: **8 passed** across both suites.

The first isolated continuation stopped after 502 passes on this fixture omission.
Record that result separately from the resumed suffix; the production code was
unchanged by this correction. QA finding closed, with final full-collection
continuation results still pending.

## Final local validation disposition

Independently checked the final remainder log and reconciled its collection and
selection counts with the two preceding attempts:

| Segment | Passes retained | Executed skips retained | Disposition |
| --- | ---: | ---: | --- |
| Plain full command before postfire lock collision | 4,117 | 124 | Command failed environmentally; one additional collection skip |
| Isolated continuation before Treatments stub failure | 502 | 0 | Fixture omission corrected and reviewed; one repeated collection skip |
| Final remainder from the failed Treatments node, inclusive | 7,832 | 244 | Passed with 4,743 prior items deselected; one repeated collection skip |

The retained segments account for all **12,819 collected tests: 12,451 passes and
368 executed skips**, plus **one distinct collection skip**. Diagnostic and focused
reruns are not added to these totals. The unchanged collection size, exact pivot
nodes and prefix counts (4,241 then 4,743) reconcile. Final remainder evidence:
`/tmp/mrs-full-remainder.log`, 7,832 passed, 245 skips including the collection skip,
4,743 deselected, with no failures.

**Final QA disposition: no open high or medium findings; local repair closeout is
supported by the recorded evidence and limitations.** The original plain full
command remains a failed command. The split runs use separate processes and
unique temporary-directory basenames, so they do not prove uninterrupted suite
execution or cross-segment process-state isolation. Retain this limitation in the
handoff; no production behavior, deployment or implementation commit is claimed.
