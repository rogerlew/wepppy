# Culvert catalog contention tracker

## Progress

- 2026-11-09: Operator requested defect repair on forest. Serializer integration implemented; 122 focused tests pass.
- Real sibling-scope reproduction confirms errno 11 at lifecycle acquisition.
- Independent design review supports ordinary metadata participants joining the
  existing serializer, with strict missing-directory refusal for catalog callers.

## Decisions

Keep the batch-owner guard needed for whole-tree lifecycle operations. Do not
make RedisPrep wait on lifecycle ownership while holding downstream locks. Do not
retry model stages or change lock granularity as the first repair. Cover ordinary
catalog critical sections and the pilot receipt wrapper; preserve genuine
destructive lifecycle conflicts. Scientific state and schemas remain unchanged.

## Validation and outcomes

Failing regression reproduced exact EAGAIN; focused tests pass and independent
correctness/security review reports no code blocker. All 91 real-Redis peer tests
pass. Broad sanity and fresh parallel replay `dd79b0a7-9fb6-4ba2-97f2-7275fcbf0cd7` are running.
Artifact acceptance remains pending. The prior full suite has a confirmed
unchanged `runsTtlDeletionHelpUrl` template assertion failure.


## Stateless WBT follow-through

- First parallel replay: 32/33, no recorded EAGAIN; culvert2909 failed parsing
  WBT settings during constructor. Full suite caught HTTP catalog wait regression
  after 6,891 passes. Neither result is acceptance.
- Operator authorized general stateless WBT execution. Active plan includes
  immutable Rust invocation configuration, all three bindings, bundled plugin
  propagation and atomic explicit administrative settings saves.
- Catalog waiting correction: six HTTP races pass; 296 focused WEPPpy tests pass
  with one deliberately disabled live smoke. Real-Redis races all executed.
- Initial WBT validation: 206 Rust tests and 20 Python tests pass; old executable
  fails new regression. Review identified ownership/symlink preservation gaps;
  repaired with Linux ACL/xattr preservation and added executable regression.
- Added opt-in real admission/parallel-child/archive pytest; fresh acceptance
  remains pending rebuilt forest installation and replay.


- First rebuilt-runtime batch99ee4497 completed33/33 without retries. Live pytest
  uncovered its own Redis-recorder mismatch after model checks; fixed with
  StrictRedis. Fresh full gate733f8579 is running, with identity evidence persisted.
- First clean replay's daily/event outputs are exactly equal to the earlier
  successful replay; topology IDs/areas equal by ID (hillslope row order varies).
- Shared WBT settings bytes unchanged. First archive gate passed: authenticated
  browse/download HTTP 200 and all 2,877 members match source files. Full suite
  and second complete automated replay remain pending.


## Final live acceptance

Fresh second batch733f8579 passed the complete live pytest:33/33 success without
retries,2,364 hillslopes,858 Parquet files,2,877 archive members matching source,
authenticated browse/download. Independent review's added overlap assertion
confirms four simultaneous child executions in both clean replays. Settings hash
unchanged. Evidence retained under `artifacts/second-live-evidence.json` and
`artifacts/second-concurrency.json`. Broad-suite final disposition follows.


## Final disposition (2026-11-09)

Forest acceptance complete. Full sanity: 13,236 passed, 435 skipped, 15 passed
subtests; stopped at the known baseline failure
`tests/weppcloud/test_usersum_template_wiring.py::test_runs_template_uses_the_ttl_deletion_usersum_doc_id`
after 3,895.78 seconds. Both test and `templates/user/runs2.html` are unchanged;
HEAD already asserts `runsTtlDeletionHelpUrl` while the HEAD template lacks it.
The suite is not fully green, and maxfail=1 leaves the remaining tests unexecuted.
Focused real-Redis/HTTP/catalog/culvert checks: 296 passed, one opt-in live skip.
WBT: 207 Rust tests and 23 Python executable/binding tests passed. The separate
live gate passed, and both clean replays prove four overlapping child jobs.

Scope: forest batch-worker runtime reloaded and verified; other resident service
processes were not restarted. Production rollout/recovery and other-platform
validation are outside this completed task. Both repositories retain uncommitted
changes; the prior dirty WBT runtime is backed up. No model defaults changed.
