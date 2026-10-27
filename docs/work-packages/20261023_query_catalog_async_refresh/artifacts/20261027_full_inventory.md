# Full discovery and restart acceptance

**PASS for complete discovery; not a fleet reconciliation or capacity certificate.**
Both retained inventories completed under the existing production batch identity
(uid1002/gid130). No production project was modified. Independent terminal
[readback](20261027_full_inventory_terminal.json) verifies empty frontiers,
zero errors, unique emitted paths and exact equality between each discovery
stream and its scope set. Raw project path lists remain private in expiring
validation Redis keys.

| Inventory | Directories visited | Scopes | Execution |
| --- | ---: | ---: | --- |
| Three primary roots | 15,399 | 10,192 | Normal forking RQ worker; 2,000.714 s driver elapsed |
| Legacy root | 21,262 | 20,699 | Read-only helper, deliberately fenced and resumed |
| Total | 36,661 | 30,891 | Discovery only |

Legacy first attempt ran 1,391.382 s before deliberate job-token supersession.
It retained 62,200 entry observations, 18,834 frontier nodes and 18,833 seen
children while still listing the root. The old writer raised
`InventorySuperseded`; its successor completed in 2,641.268 s. Cumulative
process elapsed is 4,032.650 s, while recorded discovery start-to-completion is
4,105.325 s including the gap between attempts. The final 138,922 entry counter
includes prefix replay and must not be described as unique entries. Retained
scope/stream equality proves that replay did not duplicate emitted scopes.

This deliberate helper restart is not an RQ timeout test. The separately retained
normal-worker timeout/retry canary exercises that boundary with shortened,
process-local test timing; production timeout settings remain unchanged.

## Provenance and harness limitations

The [provenance comparison](20261027_inventory_probe_provenance.json) verifies
identical ASTs for discovery, checkpoint, completion and path-validation functions
between the initial helper snapshot and final reviewed helper. Later admission
validation changes are covered by final-source regressions and reconciliation
canaries; do not imply every original probe used the final whole-file hash.

The primary driver incorrectly assumed `get_status()` returned an enum on the
production RQ version. The actual job had already finished successfully. The
corrected harness and independent [terminal job readback](20261027_primary_inventory_readback.json)
verify success, stream completeness and sanitized public job-tree output without
rerunning the full inventory. The original [log](streaming-primary-rq.log)
retains its post-completion assertion failure.

The restart controller's `before` mapping referenced the subsequently mutated
state, so its recorded job ID shows the successor. The controller asserted the
old token before changing it; do not use that mislabeled field as independent
proof of the prior ID. The old process's fenced exit is retained in the
[initial log](streaming-legacy-initial.log), with completion in the
[resume log](streaming-legacy-resume.log).

Owned inventory keys have seven-day retention. Discovery streams were not fed
into production reconciliation. Writable/READONLY classification and service
measurements are separate capacity evidence.
