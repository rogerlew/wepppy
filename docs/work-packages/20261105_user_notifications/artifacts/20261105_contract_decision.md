# Notification contract decision checkpoint

Amendment: NOTIFY-01. Recorded: 2026-11-05 19:58 UTC.
Starting implementation revision: `5fb446744d1e5d0e193c3d3aa2cf2dc040e22823`.
Classification: new intended behavior; no conformance-fix exception.
Status: operator ratified the reviewed proposal on 2026-11-05 by requesting execution; independent reviews passed; ancestor checkpoint being recorded before runtime implementation.

## Operator intent and rationale

The operator requested a generic notification schema, upcoming two-week deletion
warnings, a nightly RQ population task, server-side state, a bell/unread count,
direct paginated listing, individual/current-page selection, read/unread actions,
read-state sorting and approximately 100 records per page. They accepted Flask
ownership and requested this contract, complete execution scaffold and agent
reviews. This records conversation provenance, not approval of every newly
specified edge-case or permission to execute the deployment during scaffolding.

## Contract and source matrix

| Canonical authority | Intended delta / preserved boundary | Source boundary |
| --- | --- | --- |
| `docs/schemas/user-notifications-contract.md` | New account inbox, producer, schema, UI/API | New notifications module/routes/template/task/tests and additive migration |
| `docs/schemas/weppcloud-session-contract.md` | Preserve session/account identity | Flask route decorators and header identity |
| `docs/schemas/weppcloud-csrf-contract.md` | Apply CSRF to bulk mutation; no exemption | New POST route and frontend request helper |
| `docs/schemas/request-payload-contract.md` | Validate JSON before mutation | New request parser only |
| `docs/schemas/rq-response-contract.md` | Reuse success/error envelopes | Count/read-state JSON; no rq-engine API addition |
| `docs/ui-docs/controller-contract.md` | Preserve shared UI, escaping, accessibility | Base/legacy/report/dashboard header inclusion and new listing |
| `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md` | Preserve read-only metadata and existing catalog behavior | Membership selection and TTL reader reuse |
| `docs/ui-docs/contracts/project-ttl-control-contract.md` | Preserve protection/access controls | TTL/protection read only; no mutation |
| `docs/schemas/run-catalog-projection-contract.md` | No projection change or rollout dependency | Projection not used in first implementation |

Only the notification contract introduces normative behavior. Other rows are
unchanged constraints; implementation must not change their owner scope or claim
their package milestones complete. If review discovers an actual conflicting
requirement, amend the affected current contract and re-review before code.

## Compatibility, security and evidence

Two additive account tables and indexes; old application versions ignore them.
No run data/schema mutation, deletion schedule/formula change, auth widening or
new queue. Security impact high because account endpoints, project metadata and
queue wiring are involved. Real PostgreSQL, real TTL bytes, authorization/CSRF,
concurrent retry and browser evidence are required; see the ExecPlan matrix.

## Checkpoint completion

Two independent read-only reviews must assess authority, scope, compatibility,
security and regression evidence. Record every finding and post-fix confirmation
for medium/high findings. Clarifications in the proposed contract must be included
in operator ratification before implementation. Commit the approved contract,
this checkpoint, ADR and review disposition together as a standalone ancestor;
record the resulting SHA in tracker.md. This scaffold intentionally does not
manufacture that commit or claim the contract is implemented.

## Execution authorization

On 2026-11-05 the operator instructed “execute the work-package”, ratifying the
reviewed contract and authorizing its forest delivery scope. ADR-0137 records the
reviewed defaults without expanding scope. Runtime implementation follows this
standalone checkpoint commit. Unrelated controller-validation worktree edits
remain outside this checkpoint.
