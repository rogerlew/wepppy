# CILogon implementation validation

## Source and environment

Task worktree `/home/workdir/wepppy-cilogon-oidc`, branch `work/cilogon-oidc-scaffold`; contract checkpoints `9eb2dfcf0` and `874de621c`. Implementation source commit: `679dc65d4`. These source bytes passed the final focused tests; subsequent evidence commits change documentation only. Implementation remains separate from production. Original checkout WIP was not modified.

The operator approved `/tmp/cilogon-test-compose.yml`: existing `wepppy-dev` image, exact task-worktree bind mount, no published ports or production secrets, no shared-container remount. All Python/frontend commands use `wctl --project-dir /home/workdir/wepppy-cilogon-oidc --compose-file /tmp/cilogon-test-compose.yml`. Disposable `/wc1` paths were created inside that container for existing test fixtures. Locked frontend dependencies were installed and the canonical controller builder generated ignored test assets in the task worktree.

## Executed evidence

- 64 lifecycle/OIDC checks passed: real Flask-Security/CSRF, production SQLAlchemy models on SQLite, actual signed RSA/Authlib validation, and generated mail-sink link redemption.
- 111 migration/Bootstrap/token/auth regressions passed.
- 88 expanded lifecycle/Bootstrap/configuration checks passed, including real detached ORM owner/collaborator/admin/revoked-access tests and actual FastAPI ID-adapter tests.
- Final expanded isolated auth/session/Bootstrap regression batch: **429 passed, 30 warnings in 32.47s**. This includes final JSON shape and owner-display fixes. Earlier counts overlap and must not be summed.
- Diagnostic sanitation plus generated-controller asset checks: **36 passed**.
- Frontend lint passed. Jest: 126 suites, 1,091 tests passed; Node: nine passed.
- Browser: nine synthetic-page combinations at 320/375/1280 CSS pixels; no horizontal page overflow; approved login wording and verification actions present. See `ui-layout-results.json` and screenshots. Includes role-gated API-token panels. These are rendered-template layout checks, not live authenticated provider/browser-action acceptance.
- ADR date inventory passed (149 ADRs). Broad-exception enforcement passed after mechanically updating existing allowlist line locations; no new broad exception handlers were introduced.
- Independent security and correctness artifacts record no unresolved medium/high source findings; low JSON-shape and owner-display findings were also fixed.

## Incomplete broader gates

The full `tests --maxfail=1` sweep stopped at `tests/culverts/test_culvert_batch_rq.py::test_culvert_batch_topo_sequence[False]`: Redis connection refused, after 332 passed and 29 skipped. The isolated container has no Redis service. A broad WEPPcloud attempt first needed the ignored controller bundle; the canonical builder supplied it. Pure-control rendering later stopped at the roads form's Redis dependency after 277 preceding checks passed. These are not full-suite passes.

The PostgreSQL catalog-reader suite was attempted and stopped because `postgres:5432` is unavailable in the isolated environment (54 preceding checks passed). Migration evidence here is SQLite, not populated PostgreSQL or simultaneous PostgreSQL transactions. No shared or production database was substituted. Additional rq token/fork regressions stopped after 98 passed at `test_fork_target_runid_refuses_overwrite_for_non_profile_run`, again because Redis was unavailable.

Before release: execute populated PostgreSQL upgrade/normalized uniqueness, simultaneous registration/link/redemption/resend/unlink, full-suite dependencies, registered nonproduction CILogon/Google/GitHub redirects, actual SMTP delivery, external-prefix/session-cookie browser flow, and protected-project access. Confirm the actual production web UID/GID can read the staged mode-0600 files through Compose mounts; host file existence is not proof. Keep mailbox links/tokens out of production diagnostics.

## Compatibility and review disposition

User IDs/hashes/roles/run memberships remain; existing local login is grandfathered without fabricated verification. New passwordless states cannot use stock reset/confirm/change to bypass mailbox setup. CILogon contacts cannot recover or merge shared accounts. Bootstrap and API access use stable IDs, not contacts; legacy signed email Bootstrap tokens remain compatible. Email-based collaboration lookup targets shared users; ID-based administration remains available for CILogon.

Cookie TTLs, heartbeat behavior, marker TTLs, and raw forwarded-origin policy are unchanged (N/A for normative changes); remember-cookie, session migration, and rq session tests are regression coverage. No queue dependency topology changed. No model-output format or calculation changed.

Production is held: no deployment, restart, live migration, credential activation, or image publication. The staged credentials remain inactive. New account states require compatible code across database consumers; do not roll back to old code or drop the additive fields after activation.

## Handoff checks

Individual absolute-path Markdown lint passed for 29 changed/current package documents; the final staged set of 22 Markdown documents also passed. Spelling preview differences were confined to preexisting vocabulary in PROJECT_TRACKER, the broad-exception allowlist, and tests/AGENTS; left unchanged. `git diff --check` passes. `wctl check-test-stubs` passed. No tests introduced collection-time module stubs. Existing dependency precedent: `email-validator==2.1.1` was already pinned in `docker/requirements-uv.txt`; no dependency addition.

## Final cleanup and code-quality observation

The isolated test container was stopped after checks. Temporary synthetic HTML previews were removed; retained screenshots and rendering/check scripts remain reproducible. Shared development containers and production were untouched.

Observe-only metrics were regenerated against checkpoint `874de621c` after the implementation commit. The existing OAuth callback grew from 116 to 154 logical lines because protocol validation, independent identity selection, and legacy-provider compatibility remain in one orchestration path. Identity persistence and mailbox logic are in the bounded new account module (301 logical lines, longest function 54). Retaining that layout avoided an unrelated provider refactor during the security change; the callback length is retained telemetry, not a hidden gate waiver. Python cyclomatic complexity was unavailable because the host lacks radon.
