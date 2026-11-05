# User notifications tracker

Status: design scaffold; implementation and forest deployment pending.
Last updated: 2026-11-05 19:58 UTC.

## Task board

- [x] Inspect TTL, scheduler, database and shared headers.
- [x] Record conversation-derived behavior in the canonical notification contract.
- [x] Scaffold complete implementation/testing/forest deployment ExecPlan.
- [x] Obtain two independent contract reviews, correct findings and obtain post-fix confirmation.
- [ ] Record operator decision checkpoint and standalone ancestor commit.
- [ ] Add parameterization ADR and additive schema/migration.
- [ ] Implement task, Flask surfaces and header/list UI.
- [ ] Complete local regression and independent implementation reviews.
- [ ] Deploy to forest, verify artifacts/browser/job tree, observe nightly execution.
- [ ] Verify rollback, finish documentation and close package.

## Decisions

- 2026-11-05 19:58 UTC — Nightly RQ producer; Flask inbox/API; PostgreSQL read state.
  Reuses existing mechanisms and avoids a second account API or delivery service.
- 2026-11-05 19:58 UTC — Bell with unread count, direct listing, no attention popup.
  Explicit read/unread actions preserve user control and eliminate repeat alerts.
- 2026-11-05 19:58 UTC — 100 rows per page; select-all is current page; unread-first,
  read-first and newest sorts. Page-bound selection limits accidental bulk changes.
- 2026-11-05 19:58 UTC — Start with background non-mutating TTL reads; catalog
  projection deployment is not assumed. Preserve its separate owner and cutover.
- 2026-11-05 19:58 UTC — Test deployment targets forest, not forest1; do not infer
  authorization to deploy production from the work-package scaffold request.

## Contract checkpoint

Starting revision: `5fb446744d1e5d0e193c3d3aa2cf2dc040e22823`.
Checkpoint: [contract decision](artifacts/20261105_contract_decision.md).
Ancestor revision: pending. No implementation edits authorized by this scaffold.
Reviews: [correctness/UX](artifacts/20261105_correctness_review.md),
[security](artifacts/20261105_security_review.md), and
[disposition](artifacts/20261105_review_disposition.md). Both reviewers confirmed
closure; no open medium/high design findings. Runtime approval remains pending.

## Validation and evidence

Documentation lint: contract, seven package documents and PROJECT_TRACKER passed
with zero errors/warnings. Spelling preview is clean for contract/package files.
Runtime tests: not run (documentation-only).
Implementation tests, real PostgreSQL boundaries and forest acceptance remain
required by the ExecPlan; no implementation/deployment success is claimed.

## Surprises and risks

The worktree already has unrelated controller-input-validation documentation
and a modified PROJECT_TRACKER. Preserve those edits; ignore generated docs_index.
Daily access compilation and GC use different queues; do not promise immediate
expiration refresh. Existing header overrides require an explicit coverage map.

## Next action

Ratify the reviewed proposal, author the workflow-default ADR and record the
standalone ancestor checkpoint when implementation is requested. Preserve this
package as an executable scaffold; keep plan/tracker current thereafter.
