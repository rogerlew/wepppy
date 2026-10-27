# Independent capacity assessment

Date: 2026-10-27 UTC. **HOLD for general fleet enablement. Recommend a bounded
shared-batch pilot after its admission/stop policy is approved and implemented.**
Correctness, security, full discovery and bounded recovery/tick canaries pass
their separate gates. This review does not authorize runtime/default changes.
The operator-excluded preexisting legacy read-only mount limitation is not a
release blocker here; project READONLY policy and all four namespaces remain.

## Finding and recommendation

**CAP-01 — Medium operational availability risk, open:** fleet-wide distinct-scope
admission can accumulate shared-batch work without a global outstanding-job bound.
Per-scope coalescing and 25 considerations per tick do not bound distinct jobs or
protect ordinary queue delay. Evidence does not prove the unchanged fleet will
overload, but it also supplies no defensible whole-job cost bound or measured daily
capacity budget.

The smallest useful next step is a **bounded pilot on the existing batch queue**,
using selected owned fixtures and normal compatible-fleet admission checks.
Further component-only sampling cannot measure publication, guarded verification,
whole-job service or interference with ordinary work. Before the pilot, require:

- An atomic bound on all outstanding catalog maintenance, **no more than one
  compatible worker cohort**: currently at most eight jobs, including inventory
  and refresh jobs across producer, scheduler and retry admission paths. Pending
  receipt intent remains durable when admission is deferred. Merely lowering
  the scheduler's candidate count does not cover direct producer admission.
- Pause **new catalog admission** when ordinary batch jobs are waiting, or an
  agreed ordinary-wait stop condition is crossed. Preserve receipts and let
  already-running work drain. Do not suspend the shared queue or discard jobs
  and receipts to satisfy the measurement.
- A finite pilot scope and duration, with per-job service, effective tick spacing,
  distinct admissions, outstanding maintenance, ordinary queue age and catalog
  artifact/receipt readback retained. Include slow samples and shared owners.

This guard is justified as a **pilot containment condition**, not as a proven
permanent default. At most eight outstanding jobs prevents thousands of distinct
maintenance jobs accumulating ahead of later ordinary arrivals. It does not
guarantee short waits: in-flight maintenance may occupy workers for a long time.
Contract/ADR updates and compatibility/recovery review must precede any admission
policy implementation. No new queue, service, mount, routing or worker identity
is proposed.

## Measured population and components

[Full discovery](20261027_full_inventory.md) and
[classification](20261027_scope_classification.md) account for **30,891 scopes**:
18,514 writable, 12,377 READONLY, zero classification errors/unwritable scopes.
These are observations over the probe window, not an atomic filesystem snapshot.

| Namespace | Writable | READONLY | Relevant owner concentration |
| --- | ---: | ---: | --- |
| Primary runs | 4,609 | 1,100 | Owner histogram includes READONLY |
| Batch | 1,756 | 0 | Eight owners; largest group 470 |
| Culverts | 2,727 | 0 | 55 owners; largest group 278 |
| Legacy runs | 9,422 | 11,277 | Separate top-level owners |

The 25,429 missing catalogs include READONLY and are not bootstrap write demand.
[Owner grouping](20261027_owner_concentration.json) means idle worker count alone
does not establish parallel throughput. Discovery cost was 2,000.714 seconds of
primary driver elapsed plus 4,032.650 cumulative legacy process-seconds across
fencing/restart. Their sum, 6,033.364 seconds, combines different timing boundaries
from separate probes; it is not combined-configuration runtime or CPU time.
Legacy recorded start-to-completion was 4,105.325 seconds including the gap.

The [final component profile](service-component-final-profile.md) attempted all
48 final selected digests: 26 reused and 22 new measurements. Independent readback
verified exact final membership, one source-hash set matching the relevant local
catalog-refresh source, and 46 matching paired entry digests. All 48 first
collections and 47 first verifications completed; 46 samples completed both
passes. Two children reached the 300-second whole-process bound; no application
error or blocked-mutation result was recorded. Cleanup reports no owned processes.

| Namespace | First collection mean, seconds (n) | First verification mean, seconds (n) | Complete first collection + one verification mean, seconds (n) |
| --- | ---: | ---: | ---: |
| Primary runs | 28.866 (12) | 5.906 (11) | 14.078 (11) |
| Batch | 35.817 (12) | 22.722 (12) | 58.539 (12) |
| Culverts | 3.974 (12) | 0.386 (12) | 4.360 (12) |
| Legacy runs | 6.251 (12) | 1.951 (12) | 8.202 (12) |

Do not add means from unequal cohorts. The primary censored sample collected
1,463 entries in 256.494 seconds, then entered verification at process elapsed
261.631 seconds; verification was unfinished at the deadline. The batch censored
sample completed first collection/verification in 165.079/112.512 seconds
(277.591 combined); its second verification began at process elapsed 298.577
seconds. Neither process deadline is a measured component duration or a production
timeout failure. All five earlier full 60-second censors completed under the
larger diagnostic bound; original attempts remain retained.

Source inspection confirms strict `refresh_catalog` performs **one collection
and two verifications**, the second under the lifecycle guard. Each measured pass
contains one collection and only one verification. Even `collection + 2 ×
verification` would be a conditional model, not measured strict service: the
second verification, source/cache state, guard wait, publication and receipts
differ. Pass 2 is cache-influenced; pass 1 is not guaranteed cold. Selection is
deterministic digest sampling, not workload weighting; missing-catalog batch and
existing-catalog legacy strata are absent. No complete sample-service mean,
tail percentile, fleet completion bound or safe admission rate follows.

## Scheduler and worker capacity are separate constraints

For stable observed eligibility, each READONLY scope consumes one candidate
consideration. Each writable cycle scope consumes its initial admission and at
least one later pending-empty retirement; the implementation unconditionally
re-appends the cycle item after initial admission. Therefore:

```text
12,377 + 2 × 18,514 = 49,405 minimum considerations
ceil(49,405 / 25) = 1,977 ticks
49,405 / 25 × 30 seconds ≈ 16.47 hours
```

That excludes extra active-job rechecks, dirty arrivals, failed admissions and
discovery gaps. First-to-last tick starts span 1,976 nominal intervals; final
execution adds time. The ideal daily budget is 72,000 consideration slots, leaving
22,595 beyond the minimum. Approximately 43.70-second average effective spacing
across the minimum ticks would exhaust 24 hours before additional work.

Cadence is **scheduler-loop-start based**: synchronous reconciliation runs before
`next_run = captured_now + 30`; this is not a fixed 30-second sleep after work.
Slow ticks/other due tasks extend spacing; there is no parallel catch-up. The
[independently reviewed tick canary](inventory-scheduler-tick-independent-review.md)
measured full 25-item admission at 11.668846/6.716834 seconds, queued recheck at
0.790840, completed retirement at 0.623231 and READONLY skip at 0.135262 seconds.
Those calls fit nominal cadence for the tiny scratch cohorts. They exclude worker
execution, ordinary scheduler interference and large-backlog processing: only
25 pending items / 3,375 bytes were measured.

The [eight-scope whole-job canary](capacity-canary.md) used two workers sharing
one owner and the same hardlinked source data. Its job-service mean was 19.49183
seconds (median 20.686201); cohort elapsed was 83.285920 seconds. It is real service
evidence for that fixture, not a fleet distribution. At a hypothetical sustained
25 distinct jobs per 30 seconds, that mean would demand 16.24 workers versus eight
available. Actual considerations include skips/coalescing, and producer admissions
are additional. This warns about an admission wave without proving overload.

Historical homogeneous-service arithmetic assigned that mean to all writable
scopes: 100.24 worker-hours, or 101.92 with separate discovery elapsed as a cost
proxy. Its ideal eight-idle-worker duration of 12.74 hours is **not a cycle
forecast**, especially given the 16.47-hour scheduler floor. Discovery, scheduling
and worker execution overlap; simply summing their durations is also invalid.

The 86,400-second cycle setting starts the next cycle after previous completion
plus that interval. Distinguish cycle duration from per-scope revisit time; a
24-hour-duration cycle does not prove a 24-hour freshness/revisit guarantee.

## Shared workload evidence

- The earlier 20-point window spans 570.26 seconds: all eight workers busy at
  every sample, queued jobs 80 to 54. Net decrease is not spare service capacity.
- The [later 40-point window](20261027_batch_capacity_extended_summary.json)
  spans 1,170.66 seconds: queue zero throughout; six samples show seven idle/one
  busy, then 34 show eight idle. This supports a quiet-window pilot, not a daily
  capacity guarantee or proof of no work between samples.
- Retained 24-hour job attempts record 71,928.47 worker-seconds (0.833 average
  occupied workers). They are a lower bound, not evidence of 7.17 spare workers.
- [Current worker accounting](20261027_worker_lifetime_accounting.json) totals
  46,184.18 working seconds across current lifetimes ranging approximately
  1.04–15.49 hours. Those lifetimes do not align with a full day and omit prior/dead
  workers. Source default result TTL is 604,800 seconds (seven days); that default
  does not reconstruct overridden TTLs, expired/removed jobs or earlier attempts.
  Do not add this counter total to retained-job totals, which can overlap.

## Concrete policy for operator decision

The [bounded-admission proposal](20261027_bounded_admission_proposal.md) supplies
a concrete decision: cap **seven** outstanding inventory/refresh jobs against
the current eight-consumer pool; pause new admission on any ordinary waiting job;
use owned validation scopes with at most 25 refresh jobs and their inventory work;
limit new admissions to 30 minutes; treat five minutes of ordinary queue wait as
pilot failure; resume only by explicit operator action. **Independent assessment:
reasonable to present for approval, not yet authority to execute.**

It correctly avoids claiming a universal reserved worker, a five-minute drain
guarantee or a 24-hour cycle certificate. Before implementation/execution, make
these contract details unambiguous:

1. Count all admitted nonterminal/reserved maintenance across every admission
   path, including queued, started, deferred and scheduled jobs. Reduced worker
   capacity cannot grant new permits. Count retries against the cumulative
   25-refresh-job budget by new admitted job ID; explicitly bound inventory
   attempts/work as well.
2. Thirty minutes is an **admission window**, not a completion deadline. Preserve
   and observe queued/in-flight work and receipt outcomes after admission stops.
   Agree the observation interval and response to the ordinary-wait trigger;
   pausing admission cannot preempt already-running maintenance.
3. Prove normal fleet compatibility and owned-scope isolation before any shared
   execution. Enabling a pilot must not silently release admission for unrelated
   real projects. Approve its fixture list, cumulative budget, success criteria
   and scoped pause/resume authority in the reviewed contract/ADR.

The proposal is an operational decision, not an approved permanent default. If
it is not accepted, retain disabled rollout and report capacity unproved.
Additional component measurements alone are not the recommended next step.
CAP-01 remains open until the approved bounded policy and pilot supply the
missing shared-load evidence, or explicit operational risk acceptance is
recorded. Correctness/security review dispositions are unchanged. Expansion to
fleet scopes and a claimed cycle target require the remaining rollout gates.

All earlier snapshots and arithmetic remain in
[capacity-independent-observations.json](capacity-independent-observations.json)
and their linked source artifacts. This final assessment consolidates them;
no further experiment, runtime edit or production action was performed here.
