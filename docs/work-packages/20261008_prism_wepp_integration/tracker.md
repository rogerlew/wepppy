# Tracker

Completed (code/forest acceptance), 2026-10-08 UTC. Both live methods passed;
target remains nearest-cell. Aggregate reader floor: 6781de988. Implementation
working changes are not pushed; wider deployment is not claimed.

2026-10-08 UTC: started from 199fa5b1e. Independent contract reviews resolved; ratified checkpoint d3b5958c5 and reader floor e25299022 committed before writer exposure. Catalog, menu, staged adapter/build and raw-dewpoint revision implemented.

Focused Python gates and full frontend lint/925 tests pass. Correctness review's same-cell scaling collision, postcommit diagnostic failure and observed-year schema findings fixed; focused follow-up regressions pass.

Forest: original 788-file snapshot retained. Multiple/PRISM revision climate job 39c3b430-dc37-48e4-a0c5-b3e67366a70c and WEPP tree fdf0cc21-b061-4d9f-aea6-41b74afb70c7 completed. Nearest-cell climate job 9beebbd6-5d77-42b7-aa29-c0163e302508 and WEPP tree 12e17b21-7611-419c-9869-46646a21040d completed. Both methods passed prepared CLI and actual WEPP precipitation readback across 104 hillslopes/1,096 days. Both cases archived; run left nearest-cell. Mode2 sampled 24 native cells and retained 24 distinct wet-day calendars.

Authenticated browser/download, 993-file portable climate restoration and committed-reader-floor reopening passed. Correctness review initially closed all findings. The full suite then found a missing single-input CONUS reader structure after 4,964 passes. Two independent correction reviews approved the climate-only variant; checkpoint 5b97490e7 precedes aggregate reader floor 6781de988. 94 Builder/capability and 14 creation/explicit-refresh tests passed after the append-only correction; final reader inventory 75-test run passed. All four ordinary/single-input × OFE representation configs reopened byte-unchanged with that exact committed reader. Both original multiple-method model results remain valid; no numerical code changed.

Broad coverage completed: 4,964 passes before the corrected catalog defect;
5,219 passes in the continuation before an unrelated Redis-auth test failure;
301 passes in the final tail, including the entire previously failing module.
Counts overlap and do not represent one clean full-suite invocation. Current
preset/registry expectations were corrected while frozen historical fixtures
were preserved. All four independent correctness findings are closed. PRISM
broad-exception enforcement passes; concurrent RQ notification edits retain a
separate line-based allowlist warning outside this package. Final evidence and
documentation are complete.

See [forest results](artifacts/forest-results.md), [validation ledger](artifacts/validation.md), and [review](artifacts/correctness-review.md). The existing silent-pass CLIGEN convergence warning remains a scientific limitation; OpenET/AgFields mode 16 integration is outside this package. The unrelated user commit 0e331f5e2 was preserved.
