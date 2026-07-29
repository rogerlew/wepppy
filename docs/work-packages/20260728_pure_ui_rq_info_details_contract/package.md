# SURF-17 Pure UI RQ Info Details Contract

**Status**: Active
**Package ID**: SURF-17
**Security impact**: `high`
**Dedicated security review**: required for any production patch

## Purpose

Verify the privileged RQ Info Details surface from authorization through its
read-only Redis/RQ snapshot and rendered tables. Make active workload easier to
scan by presenting the default and batch queues in separate panels without
changing queue execution, filtering, or job metadata.

## Concise Intent Contract

Only authenticated Admin or Root users may view the page. The route reads a
static snapshot of recently completed, active, and failed jobs from the
requested queues and never mutates, enqueues, cancels, retries, or deletes a
job. Job, run, worker, state, timestamp, function, and submitter values are
rendered as escaped text with existing protected navigation targets.

Active jobs are grouped server-side into one ordered panel per requested queue.
The default view renders the `default` panel before the `batch` panel. Each
panel has its own explicit empty state. Requested queue tokens retain their
spelling and order after surrounding whitespace is trimmed; repeated names
produce only the first panel. A job belongs to a panel only when the producer's
stripped `queue` value equals the panel name case-sensitively. The existing
`queues` query parameter controls both collection and panel order; unknown,
case-different, unrequested, or missing job queue values must not leak into a
different requested queue. Recently completed and failed jobs remain combined
tables with their Queue column unchanged.

Errors remain explicit and logged at the existing route boundary. The change
does not alter RQ queue wiring, Redis topology, authorization roles, job
listing payloads, polling, or retention/lookback policy.

## Scope

- `wepppy/weppcloud/routes/rq/info_details/routes.py`;
- `wepppy/weppcloud/routes/rq/info_details/templates/info_details.htm`;
- `wepppy/rq/job_listings.py` as an inspected retained producer;
- direct rendered-template and focused route tests;
- Admin/Root authorization and metadata-exposure review; and
- parent tracker, package register, and audit register reconciliation.

## Exclusions

No queue mutation, enqueue-site or dependency-edge change, Redis schema change,
new role, public exposure, polling, job payload expansion, lookback change,
completed/failed queue split, or RQ dashboard redesign is authorized.

## Acceptance

Direct route and render evidence proves the Admin/Root-only, read-only page;
ordered queue panels; queue isolation; per-queue empty states; escaped
metadata; job/run navigation; combined completed/failed tables; query-filter
behavior; and explicit failure handling. Focused tests, broad tests, frontend
lint/tests, documentation lint, security review, and `git diff --check` are
recorded before closeout.
