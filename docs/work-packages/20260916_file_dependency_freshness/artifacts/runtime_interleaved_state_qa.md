# Independent QA: interleaved full-state observation

**PASS for the measured warm digest-read and bounded working-set clause.**
Reviewed actual `runtime_interleaved_state.py`, its completed log and JSON after
the coordinated service restart. This review ran no additional workload and
changed no runtime/test code.

The script calls the actual production `get_state(..., model='M3',
frequency='cli', reconcile=False)` under the service identity. Two independent
ordinary copies of the same geography on `/wc1` alternate30 settled calls each
in one process. The first calls and one-second admission/warm-up calls precede
the measured cache interval.

| Observation | Recovered root copy | Omni parent copy |
| --- | --- | --- |
| Initial observed freshness | current | stale |
| First full-state call |2.2249s |2.6478s |
| Settled sample count |30 |30 |
| Settled mean |739.48ms |862.19ms |
| Settled observed range |591.19–887.56ms |651.19–1109.95ms |

The digest cache remains395/512 entries. Hits increase66→12,906; misses remain395,
and the direct uncached-digest recorder remains empty. Both the cache-miss
counter and uncached path are checked by the harness assertion. Together these
establish zero full payload reads through this production digest path for the
60 settled calls. They do not count every filesystem/NoDb/JSON/footer access.
Initial freshness is retained honestly; the script does not assert or retain
the state of every later call. Other live M3/browser records independently prove
the recovered root's current state.

These are local production-function timings, not HTTP roundtrip latency. No
whole-state numerical deadline was ratified; the historical approximately695ms
measurement predates the final lineage/source checks and is not a comparable
service-level target. Component limits cannot be summed or repurposed into that
deadline. The means and individual samples are retained as observations without
calling them a latency-budget pass or hiding samples above one second.

This run establishes coexistence below the existing capacity, not512-entry
eviction behavior. Actual eviction and repeated admission costs are covered by
the separately retained component acceptance probes. Prior copies and reads
warm filesystem pages; first process/helper calls do not establish storage-cold
latency. One host/process and one geography do not establish cross-host NFS
coherence or all-project size bounds. No new cache size, latency threshold or
freshness policy is introduced by this acceptance.
