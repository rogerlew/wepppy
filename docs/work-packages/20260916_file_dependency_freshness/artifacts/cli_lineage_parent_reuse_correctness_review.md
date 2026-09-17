# CLI parent reuse and corrected latency budget: correctness review

**Scoped implementation PASS.** No unresolved correctness finding in the
same-call directory-descriptor reuse. The proposed readiness mean limits of
10 ms settled and 50 ms cold/evicted are a justified, explicit measurement-scope
correction, subject to canonical amendment and final independent QA evidence.
They do not retroactively pass the original 5/40-ms gate or approve runtime
acceptance. Export limits remain unchanged.

Reviewed `rainfall_io._local_parent`, `_verify_parent`, `open_local`,
`production.cached_digest` and `_cli_lineage_current`. No production/test edits
were made by this reviewer. Retained source hashes match the post-reuse profile:
`production.py` starts `8c66a2f8c29b`, `rainfall_io.py` starts `f61f0c76caee`,
and `cli_parquet.py` starts `ef48004ff552`.

## Authority and coherent observations

The parent descriptor is created by an `O_RDONLY | O_DIRECTORY | O_NOFOLLOW`
traversal for this call and is closed on exit. Reuse is limited to the identical
immediate parent of the Parquet and selected CLI; a different source parent uses
the existing independent traversal. There is no process-global or cross-request
descriptor cache and no change to the 512-entry/one-second digest admission
policy. Cold digest computation still uses its separately guarded ordinary path.

Each reused leaf receives the regular/path checks and an actual no-follow read
open. `_verify_parent` compares the current directory type/device/inode to the
held descriptor before reuse and again at the outer context's normal exit.
Thus matching file hashes, inode and timestamps cannot hide replacement of the
immediate directory with another directory containing hardlinked leaves. The
exit check runs even when the function returns from inside the context. Errors
close owned descriptors; `ESTALE` at this readiness boundary becomes the existing
`changed_source` response. This preserves point-in-time checks, not isolation
from arbitrary subsequent writers or immediate revocation of an already opened
descriptor's authority.

The final Parquet descriptor/path version and both source signature checks remain.
Strict post-fire no-symlink admission makes the selected and resolved source names
equal, so direct comparison of both proof names to the validated relative path
is appropriate here. Generic export's supported source/output aliases still use
their own resolver. Proof paths are compared, not opened as new authority.

Independent additional probes:

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/cli_lineage_parent_reuse_correctness_probe.py -q
```

Adjacent retained log: **5 passed in 18.01 seconds**. Both content modes reject
an actual parent replacement with hardlinked CLI/Parquet leaves performed after
the final CLI signature has already been read. This specifically exercises the
outer exit check. Two real atomic lineage publications verify a selected CLI in
a different directory, with and without a previously supplied hash. One probe
verifies descriptor closure after an early return. The different-parent probe
uses an explicit one-row frame; it tests publication/path association rather than
claiming another scientific parser execution.

[Independent security probes](cli_lineage_parent_reuse_security_review.md)
retain nine passing cases for earlier parent replacement, default opener cleanup,
mode 0111/0000 directory denial, leaf read denial and ancestor/parent/leaf links.
The parent retained 42 passing affected tests in
`cli_lineage_parent_reuse_tests.log`. The new private optional argument expands
the shared opener's implementation surface; continued affected-module coverage
is appropriate. No persistent-state format or artifact-retention change occurs.

## Why the proposed budget correction is bounded

The original [prototype](benchmark_cli_lineage.py) measured
`composed_readiness`, which directly opened metadata and used the ordinary file
digest helper. It omitted the actual strict post-fire directory traversal and
full predicate association checks. Its 1.25–1.44-ms settled result was therefore
not an accurate full implementation baseline. The original failure is retained
in `cli_lineage_implementation_performance_final.json` and the
[QA review](cli_lineage_implementation_qa.md): actual settled 8.28/10.78 ms,
and the 120-year three-eviction mean about 43.85 ms. Those measurements fail
5/40 ms and remain failures of that earlier criterion.

The response first targets the measured repeated traversal without weakening it:
opens drop from 14 to 8 per settled call. The post-reuse profile retains unprofiled
100-call means of **5.82/6.98 ms**; separate instrumentation attributes 39–42% of
remaining time to required opens. The same source hashes identify the code
reviewed here. This supports a finite 10/50-ms local mean gate for the complete
predicate while preserving access and coherence behavior. It does not prove no
further optimization is possible, require a new persistent cache, or permit
discarding final signatures to reach the old microbenchmark number.

Final acceptance must record the revised numbers and rationale in the canonical
contract/decision, retain the miss, and measure the complete implemented lineage
predicate on both representative sources. Include the actual cold, admission,
settled and 512-entry eviction paths and byte counters; zero settled CLI payload
reads and bounded footer reads remain mandatory. Do not subtract mandatory
directory checks, select only a favorable sample, or compare the isolated
component budget to a wrapper containing additional existing inventory work.
Whole-state acceptance remains separate and must retain that work.

The 120-year full export limit stays 1.5 seconds with at most 200 ms added lineage
overhead. No source mutation, scientific change, relaxed proof validation,
cross-request authority cache or greater digest working set is authorized by
this correction. The local means do not establish cold-storage/NFS tail latency,
browser/RQ acceptance or package completion. Final post-reuse QA measurements
are still required; the quick profile alone cannot close that gate.
