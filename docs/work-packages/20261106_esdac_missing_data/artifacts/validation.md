# Validation disposition

## Completed

- Focused ESDAC + NoDb disturbed runtime: 122 passed; final real-writer divergent-key/reordered-retry regression: 1 passed (123 distinct tests).
- Native disturbed matrix: 99 passed in 403.81 seconds.
- Paired actual-data study: 1,000 baseline and 1,000 final builds; 733 final accepted files parsed and independently hash-verified; 287 recovered, zero regressions, all 446 previous successes numerically identical.
- Incident batch: all 35 original locations, two unique base soils, 35 disturbed outputs; same-input retry preserves bytes and mappings.
- Independent correctness review: pass, no unresolved high/medium findings.
- ADR dates, targeted documentation lint, spelling preview, changed broad-exception enforcement and test-stub checks: pass.
- Cached legacy raster-table sampler: direct installed-data lookup passed.
- Updated Europe help section: local application returned HTTP 200 with the new text at `/usersum/view/weppcloud/getting-started.md`; existing navigation is unchanged.

## Broad regression

The initial `wctl run-pytest tests --maxfail=1` run was interrupted at 532 passed,
28 skipped when study evidence required a further production-code change. It
is not counted as final-candidate evidence.

The final source is exercised in two partitions: `tests/disturbed/test_disturbed_matrix.py`
(99 passed) and `tests --maxfail=1 --ignore=tests/disturbed/test_disturbed_matrix.py`
(13,118 passed, 424 skipped, one pre-existing template assertion failure). The last additive collision test was run separately after broad
collection; production source remained unchanged throughout the final runs.

The broad run stopped at `test_runs_template_uses_the_ttl_deletion_usersum_doc_id`:
the Runs template lacks `runsTtlDeletionHelpUrl`. Both that template and its test
are byte-identical to HEAD, and isolation reproduces the failure (10 other tests
pass). This is an unrelated existing template/test mismatch; it was not changed
under the ESDAC scope. Evidence: `broad-tests.log`, `baseline-template-failure.log`
and `baseline-template-verification.txt`.

Continuation through the remaining two watershed test modules and
`tests/weppcloud/utils` passes all 66 tests (`broad-tail-tests.log`). The isolated
template module also exercised its six tests after the failure. Across the final
partitions, 13,289 distinct collected tests passed, 424 skipped and one baseline
test failed; the additional late collision regression passed separately. The
repository-wide gate is therefore not fully green. ESDAC implementation and
generated-artifact acceptance pass; baseline UI maintenance is a separate follow-up.

## Limits and release boundary

These are local code-delivery and generated-soil results, not deployment or
original-project recovery. No production process or run artifact was modified.
The sample is spatially balanced across valid anchor cells, not an area-weighted
coverage estimate. Physical-source failures remain documented in the availability
report. Non-string categorical short codes are outside the real provider contract.
The observe-only code-quality tool lacked Radon and returned no changed-file
analysis; it provides no complexity-delta conclusion for this change. No dependency
was added to obtain that optional telemetry.
