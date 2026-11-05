# User notifications

Status: Closed — implemented and verified on forest, 2026-11-05. Timezone: UTC.

## Overview

Give signed-in users a quiet inbox for projects approaching automatic deletion.
A nightly RQ task creates notices, a header bell shows active unread count, and
a paginated Jinja page supports sorting and explicit bulk read/unread changes.
The generic schema accommodates future maintenance notices.

## Authority and deliverables

The [canonical contract](../../schemas/user-notifications-contract.md) owns durable
behavior. The [ExecPlan](prompts/completed/implementation_execplan.md) covers delivery
through a forest test deployment. The [tracker](tracker.md) records evidence.
The operator requested the contract, scaffold and independent reviews, then
authorized execution through forest acceptance. Implementation is committed;
live migration, scoped worker preflight, browser acceptance and application rollback
passed. Actual scheduled execution, fixture cleanup and post-cleanup browser
acceptance also passed.

Deliver two additive PostgreSQL tables, migrations, a repeatable nightly task,
three Flask routes, shared bell integration, a 100-row listing, tests and updated
user/operator/developer documentation. No maintenance authoring UI, email,
popups, dismissal controls, new service, new queue, or deletion-policy changes.
Target forest (`forest.tail305ec9.ts.net`, dev Compose); forest1 and production
hosts are outside this package's deployment scope.

## Complexity budget

Reuse Flask sessions/CSRF, SQLAlchemy/Alembic, PostgreSQL, RQ and its scheduler,
existing queues, Jinja and established frontend utilities. Permit two notification
tables, one task, bounded background TTL reads and a database sweep lock. Start
without a catalog-projection dependency or streaming notification delivery.
Measure a complete forest sweep and inspect the consumed browser results before
considering optimization. Any additional infrastructure requires retained evidence
that this approach fails the acceptance condition and an explicit scope decision.

## Security impact

High: new authenticated routes, bulk account mutations, project metadata exposure,
and queue wiring. Dedicated independent security review is required alongside
correctness/UX review; no unresolved medium/high findings at closeout. Design
reviews do not replace implementation and deployed-boundary reviews. Use
`docs/prompt_templates/security_review_template.md` and
`docs/prompt_templates/correctness_review_template.md` for final artifacts.

## Compatibility and parameterization

Additive account tables only; no run-scoped data/schema changes or model artifact
changes. Preserve all current run access and TTL behavior. Record an ADR before
implementation/merge for new workflow defaults: 14-day window, daily cadence,
100-row page/bulk bound, and default unread-first order. No existing TTL duration
or formula changes. Operator decisions and rationale are in the contract;
implementation-derived clarifications remain proposed until checkpoint review.

## Success criteria and generated evidence

- [x] Contract checkpoint has two independent reviews, disposition and an ancestor revision.
- [x] Nightly task is wired and retry-safe, with reconciliation and persistent read state.
- [x] Ordinary users see only their notices; empty, stale, revoked and hostile cases behave as contracted.
- [x] All header families, three sorts, 100-row pagination and bulk updates pass browser acceptance.
- [x] Focused, broad, frontend, graph, migration and documentation gates pass or retain explicit blockers.
- [x] Independent correctness, security and QA reviews have no open medium/high findings.
- [x] Forest runtime identity/mount parity, scheduler execution and full browser workflow are evidenced.
- [x] Rollback is verified and user/operator/developer docs are updated before closure.

Generated evidence applies to TTL observations transformed into database inbox
rows and browser output. Retain fixture intent, exact TTL bytes and protections,
unmocked worker reads, reloaded database rows, actual route responses and rendered
browser results under a named candidate revision. Model-run output generation is
not changed and is N/A. Do not add private inbox records to project archives:
these are account records, observable through the authorized inbox and operator
job telemetry, not new project artifacts. Highest supported claim: implemented and verified on forest, including actual
scheduled execution, application rollback and final fixture cleanup.

## Risks

Daily access compilation can lag visits; notices must describe recorded dates.
Missing metadata must not produce false protection claims or silently close an
episode. Concurrent tasks must not reset read state. Revoked membership must not
leak project information. Header exceptions must not break unrelated pages.
Large history grows independently of the page limit; retention is deferred.
Forest has separate identity/configuration from forest1; verify the actual target.

## Stakeholders and next step

Decision owner: requesting operator. Implementer: executing agent. Reviewers:
independent correctness/UX and security agents, followed by implementation QA.
Delivery is complete. Retained evidence and final review dispositions are linked
from the tracker; no additional deployment is authorized by closure.
