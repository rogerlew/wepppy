# Proposed bounded admission before a shared-batch pilot

Status: **operator authorized execution; implementation and acceptance pending**. The October 27 inventory
and HTTP remediation is validated. General enablement remains disabled. The
operator has excluded the unrelated legacy read-only mount limitation.

## Why this is the next step

The fleet contains 18,514 writable scopes. Current settings bound candidate
considerations per tick, but not the number of queued/running maintenance jobs
across distinct scopes. Measured component costs have a substantial tail, and
one verification remains censored. More read-only scans cannot establish a bound
on maintenance queue accumulation or ordinary-job delay. The reviewed
[capacity assessment](capacity-independent-assessment.md) supports a bounded
shared-batch pilot rather than general enablement or further component-only loops.

## Concrete policy proposed for operator decision

- At most **seven outstanding catalog-maintenance jobs** on the current eight-
  consumer production batch pool, including inventory and refresh jobs in queued,
  started, deferred, scheduled or reserved states. Count all admission paths; a
  disappearing worker does not itself free a permit. Cap
  admission by the compatible live consumer count as well; reduced capacity
  cannot create additional permits. Seven leaves one consumer outside catalog
  work when all eight are healthy; it is not a universal reserved-worker guarantee.
- Pause new catalog admission whenever ordinary batch jobs are waiting. Preserve
  durable receipts and discovery progress; let already-running work drain. A cap
  bounds job count, not elapsed delay, and does not preempt scientific jobs.
- Apply the same admission decision atomically to producer requests, recurring
  reconciliation, inventory admission and retries. Per-scope coalescing remains;
  no new queue, service, worker identity, filesystem permission or datastore.
- Include an operator pause/resume control for catalog admission using existing
  coordination infrastructure, so stopping a pilot does not suspend ordinary
  queues or discard pending intent. Specify recovery/authority in the reviewed
  contract before implementation.
- First shared-queue pilot: owned validation scopes, at most 25 new refresh job
  IDs and two inventory job IDs, including retries in both cumulative budgets;
  at most 30 minutes of new admissions. The window is not a completion deadline:
  queued/in-flight work must drain and artifact readback may finish later. Stop further
  admissions on any ordinary backlog, configuration mismatch, artifact failure
  or unexpected job-count growth. A five-minute ordinary queue wait is a pilot
  failure trigger, not a guarantee that in-flight maintenance can finish in five
  minutes. Resume only through an explicit operator action.

Independent capacity review supports presenting this proposal without a latency
or capacity guarantee. Before implementation, prove that owned-scope isolation
and matching participant configuration do not globally release unrelated
project admissions. Budgets must survive a controller restart and must not reset
merely because an attempt failed.

The operator instructed “execute the bounded pilot.” This authorizes the
contract/ADR clarification, independent reviews, implementation and bounded
acceptance. It would not itself authorize broad
fleet enablement or deployment of unrelated workspace changes. Pilot participant
configuration, isolation of owned scopes, cumulative-work enforcement and pause
recovery must be concrete and reviewed before any shared-queue execution.

## Scope boundaries

Do not change the 25-candidate scheduler budget, 30-second cadence, 3,600-second
job timeout or 86,400-second cycle spacing simply to make a model pass. Retain
all four namespaces and READONLY behavior. The proposed cap cannot certify the
24-hour target: measure complete-cycle progress, actual oldest pending age and
ordinary-work delay under the agreed conditions before general enablement.
