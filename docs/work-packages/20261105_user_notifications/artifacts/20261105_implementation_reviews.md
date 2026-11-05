# Independent implementation reviews

Date: 2026-11-05 UTC. Contract ancestor: `ceeaa5960`.
Scope: notification schema/migration, repository, producer, RQ entry/schedule,
Flask routes, shared headers, inbox JS/CSS and tests. Reviewers were independent
read-only agents; the primary agent applied fixes and retained these responses.

## Correctness and UX

Reviewer: `notification_impl_correctness` (reviewer).

- COR-I01, medium: malformed TTL policy/delete-state containers could stop a
  whole sweep. Closed by explicit type validation and real malformed-first,
  healthy-second project coverage.
- COR-I02, medium: legacy dark navigation inherited dark bell text. Closed with
  explicit white normal/hover/focus color. Reviewer verified Chromium computed
  styles and focus outline.
- Low: historical notice wording clarified with “Earlier notice”.

Final code-review verdict: pass, no open medium/high findings. Reviewer confirmed
the blueprint availability flag prevents mixed-version source-mounted header
failures. Valid-state and deployed acceptance evidence remains a separate gate.

## Security

Reviewer: `notification_impl_security` (security_reviewer).

SEC-IMPL-01, medium: same malformed-TTL boundary; closed with direct file checks
and regression tests. Verified recipient scope/current membership, atomic mixed-ID
rejection, strict IDs/booleans, CSRF precedence, private responses, escaping,
descriptor-bound reads, empty-scope no-op, episode uniqueness, sweep locking and
durable read state. Later availability-context and episode-metadata additions were
re-reviewed with no new medium/high concerns.

Final security code-review verdict: pass, pending runtime evidence. Real hostile
and valid API/database tests, forest job/browser acceptance and rollback remain
required; this does not replace those results.

## QA

Reviewer: `notification_impl_qa` (qa_reviewer).

QA-01, medium: isolated test schemas initially shared the production advisory
lock. Closed by per-fixture randomized lock keys and module-constant references.
Low findings addressed: run identity added to operator warning; targeted ESLint
run for standalone script/tests because the normal lint glob covers controllers.
Browser acceptance must prove successful read/unread, reload and navigation
selection clearing, in addition to Jest failure-path coverage.

Final QA verdict: pass, no open medium/high findings.

## Operational review and disposition

Reviewer: `notification_forest_rollout_review` (ops_security_control_agent).
Verified forest dev preset, UID:GID 1000:993, groups 993, umask 0022, source mounts,
local batch consumer identity, and existing migration head. Required preserving
source snapshots, not only image IDs, and explicit isolated restore URIs.
Restored database rehearsal and fixture-scoped RQ preflight passed afterward.

Canonical targeted-web recreates only web/rq-engine; canonical full mode would
recreate 25 services. Operator explicitly approved scheduler-only recreation with
`wctl docker compose up -d --no-deps --force-recreate scheduler` for activation
and rollback. No full-stack or production rollout is included.
