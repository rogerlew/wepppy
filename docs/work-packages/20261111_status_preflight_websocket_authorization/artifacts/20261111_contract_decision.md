# F4 WebSocket authorization contract decision

Status: operator-ratified; both independent final reviews approved.
Date: 2026-11-11 UTC.
Starting revision: `b7c2e44d5947aabeda22f19e55b0b91d7f0baca1`.
Remediation: F4 / SEC-04, bounded status/preflight authorization and disclosure.

## Authority and approved delta

The operator requested execution of the active plan, then explicitly stated:
“i approve the policy. please proceed with ratification and implementation.”
This approves ownerless no-cookie inspection after authoritative resolution,
job/channel-bound admin run-sync status before registration, and selected-project
WebSocket diagnostics. The plan also authorizes the standalone checkpoint commit
and forest-only deployment after validation. No production deployment is granted.

The [canonical contract](../../../schemas/weppcloud-websocket-auth-contract.md)
contains the full claim, transport, state, lifetime, error, Origin, session,
message and lifecycle matrix. It supersedes the initial combined-audience draft.
Each token names exactly one service; config is resolved at issuance and carried
as nonsecret query data. SID markers/fences use DB 11; JTI fences use DB 0.
No existing RQ marker lifetime is shortened. No generic RQ token is issued.

## Applicable authority and compatibility

Affected canonical contracts: `weppcloud-websocket-auth-contract.md`,
`weppcloud-session-contract.md`, `weppcloud-csrf-contract.md`; related token
specification `docs/dev-notes/auth-token.spec.md`; ADR-0141 for thresholds.
Canonical RQ error envelopes and feature inspect policy remain unchanged.
The package composes those boundaries without advancing unrelated owner work.

New client transport is required across StatusStream, preflight, command-bar
and diagnostic probes, plus generated outputs. Fork retains source-run scope;
archive/restore uses canonical archived identity. Run-sync uses retained job
arguments and current admin authority without altering queues or enqueue edges.
No run-scoped CSV/parquet/NoDb schema mutation occurs. Stream issuance adds only
short-lived session markers compatible with existing readers.

Security impact is high: new credential issuance/verification and run read
boundary. Required independent reviews are retained in `20261111_m0_reviews.md`.
Dependency evaluation approves jwt/v5 v5.3.1 for the owned shared Go validator;
ADR-0141 records five-minute lifetime, zero skew, early refresh and input bounds.

## Regression and acceptance

The canonical valid-state matrix and failure inventory require positive private,
public, ownerless, composite, archived, working/failed/completed and run-sync
states; hostile claims, Origin, protocol, config, revocation and Redis outages
must deny before upgrade/run Redis access. Message fixtures preserve progress,
triggers, structured failure consumers and command output while removing the
confirmed disclosures. Focused Python/Go/Jest, full pytest/npm gates, independent
reviews, forest service redeploy and sanitized real-browser evidence are all
mandatory. Implementation alone cannot close SEC-04.

## Checkpoint

Commit only this package, affected contract amendments, dependency record and
ADR after both independent reviewers confirm the ratified matrix. Record the
ancestor hash in tracker and ExecPlan. Preserve unrelated dirty work.
