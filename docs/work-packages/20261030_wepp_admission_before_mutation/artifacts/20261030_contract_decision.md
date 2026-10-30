# WAM-01 contract decision

Prepared 2026-10-30 22:00 UTC on `master` at
`29716c1bd9a24dacf1cb45e05a11b2aa44a5378e`. Ratification commit: pending authority.
Implementation: not started.

## Classification and authority

Intended behavior amendment closing a confirmed static ordering defect. The
unchanged RQ response contract's Error responses section says conflict does not
enqueue a second workflow; it does not state that proposed inputs remain unchanged.
NoDb atomic writer rules do not imply execution admission ordering. Do not use the
conformance-fix exception to invent that missing obligation.

Operator authorization: execute `/tmp/wepp-admission-before-mutation-prompt.md`,
retained as `operator-prompt.md`. Exact requested outcome: “an execution submission
rejected by WEPP admission must not persist its proposed input changes or change
the inputs consumed by already-admitted work. Preserve valid configuration-only
batch/base behavior.” Confirmed equivalent consumers are explicitly in assessment
scope. No additional outcome approval is required. Commit authority is absent.

## Applicable contracts and exact delta

| Contract / section | Disposition |
| --- | --- |
| `docs/schemas/wepp-run-input-contract.md`, WAM-01 | Add admission-before-input rule for five named endpoints, configuration-only exception, failure limits and direct evidence obligation |
| `docs/schemas/rq-response-contract.md`, Error responses and new WEPP ordering section | Extend existing no-duplicate rule through cross-link; retain canonical errors, deferred recovery and descendant checks |
| `docs/schemas/rq-webhook-contract.md`, Admission and recovery matrix and new WEPP input ordering | Cross-link new input rule; preserve callback reservation, replay and uncertainty contracts |
| `docs/schemas/nodb-persistence-concurrency-contract.md`, Writer Ownership / Locks / Hydration | Unchanged; payload remains under real controller persistence locks |
| `docs/schemas/rq-engine-agent-api-contract.md`, HTTP request admission isolation | Unchanged; outer request lifecycle lease and nested ownership retained |

The normative text is in current schemas, not this package. No conflict with
existing no-prep behavior: accepted controller metadata can change but checked-out
prepared files must not regenerate. Batch/base exception belongs only to the
shared preparation handler. Existing authorization, capability and prerequisite
rules continue to apply.

## Rationale and compatibility

Workers load by runid and reload controllers; persisting B before rejecting B
allows admitted A to consume B. Keep reconciliation, admission, application and
enqueue under the existing submission lease; a released precheck is insufficient.
Do not introduce immutable snapshots or distributed transactions. Payload
validation errors keep their existing shape when admission passes; simultaneous
admission and payload errors may now return the admission conflict first.
No parameterization, schema, queue topology, permissions or auth change.
Security impact low; requests retain existing access checks and ownership fences.

Reconciliation and webhook reservation/cleanup may write prior orchestration or
callback metadata. They are not proposed model inputs or replacement active-job
receipts. No rollback guarantee after application begins, including lease loss.

## Proposed regression evidence and gate

The assessment matrix and ExecPlan define separate state/payload dimensions and
all eight operator acceptance groups. Real NoDb persisted bytes/reload and real
Redis/file lifecycle coordination are mandatory. Parse a real prepared soil or
slope parameter after A accepted/B rejected; no-prep prepared files stay unchanged.
Run focused regressions, full substantive pytest gate, docs lint and independent
correctness/QA review after implementation. Graph/live-tree checks apply only if
actual queue wiring changes; no such changes are planned.

Two independent read-only checkpoint reviews and disposition must precede the
standalone ancestor commit. The only planned approval request is authority to
commit the exact reviewed checkpoint files, excluding unrelated dirty work.

## Commit authorization

2026-10-30 UTC: operator replied “yes” to committing only the reviewed checkpoint
and continuing implementation/validation. Standalone checkpoint commit authorized.
