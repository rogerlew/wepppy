# Forest Preflight — Blocked by Shared Dirty Checkout

## Result

**BLOCKED before backup, service quiescence, migration mutation, or canary.**

The reviewed Forest runbook requires a clean bind-mounted checkout before any
backup or service mutation. Read-only preflight found unrelated Command Bar and
Pure UI work in the same checkout, so the cleanliness assertion cannot pass.
Those changes were preserved and not staged, stashed, committed, reset, or
otherwise modified by SURF-14A.

## Exact identity

- Hostname from the active workspace: `forest`.
- Hostname through `ssh forest`: `forest`.
- Repository path on both sides: `/home/workdir/wepppy`.
- Local and SSH-visible `.git/index` device/inode:
  `66305:89260104`.
- Current branch: `master`.
- Current release commit:
  `363ab8ac391bdb2f2afee6284c7e297bd4efbfb1`.
- Reviewed rollback commit:
  `0517bb8de9b0343a64ab4102f35f4ae242fffa53`.
- Verified immutable rollback ref:
  `refs/heads/rollback/surf-14a-363ab8ac3-0517bb8de`.

This proves the earlier local acceptance and the Forest target share the same
host and bind-mounted checkout; they are not independent Git worktrees.

## Read-only runtime evidence

- PostgreSQL Alembic current:
  `c91f6b2a4d7e (head) (mergepoint)`.
- Compose services `weppcloud`, `rq-engine`, `scheduler`, `rq-worker`,
  `rq-worker-batch`, `postgres`, and `postgres-backup` were running.
- PostgreSQL and PostgreSQL backup services were healthy.
- RQ default: zero queued, zero executing.
- RQ batch: zero queued, zero executing.
- Ten registered workers were idle.

The schema was already at the reviewed additive merge head before this
preflight. No migration command was applied.

## Dirty-scope disposition

The checkout included unrelated unstaged or untracked work under:

- `docs/work-packages/20260716_pure_ui_contract_standardization_c/`;
- `docs/work-packages/20260729_pure_ui_command_bar_contract/`;
- Command Bar routes, JavaScript, tests, and documentation;
- Pure UI project-route/render tests and project route code;
- generated Usersum index and code-quality reports; and
- the SURF-14A rollback review artifacts being prepared for a follow-up
  evidence commit.

The SURF-14A implementation commit itself was cleanly committed and pushed.
The unrelated files prevent the exact runbook assertion
`test -z "$(git status --porcelain)"`.

## Required unblock

The owner of the unrelated work must first commit it, move it to another
worktree, or explicitly authorize a reviewed alternative deployment method.
SURF-14A may then restart from the beginning of Forest preflight. It must not
resume midway or infer that an already-current schema waives checkout,
backup, quiescence, rollback, or canary controls.

Production/wepp1 remains untouched and unauthorized.
