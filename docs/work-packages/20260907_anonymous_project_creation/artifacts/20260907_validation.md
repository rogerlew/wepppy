# Creation Policy Validation

Implementation checkpoint: `fb67f32fc`; implementation commit: `935d96220` plus the subsequent OpenAPI description-budget fix. Validation ran on 2026-09-07 UTC against the development Compose stack.

## Automated Gates

Focused tests: **296 passed**, including API, Flask configuration, route context, create index, and actual Jinja rendering. Frontend lint passed; **108 suites / 835 tests passed**. Stub completeness passed. Broad exception changed-file enforcement passed with zero new broad catches. Documentation lint passed for affected guides and contracts. Code quality observability ran; see `20260907_quality_delta.json`. The creation route's existing large function grows modestly for the access gate; a broad auth refactor was deliberately avoided. The existing large template-test module gains one four-state test; no new large function is introduced.

Baseline focused run had 57 passes and one preexisting unit-test DB lookup failure in the migration-aware cookie-selector test. That test now stubs role lookup while retaining the real selector/identity path under test. The new restricted-CAPTCHA regression failed against old code before implementation. The first full suite reached 1,314 passes and 27 skips before rejecting the new OpenAPI description's 418 characters against the 280-character budget. The description was shortened without changing the budget; all 12 OpenAPI tests then passed. Final full-suite rerun passed: **7,721 passed, 72 skipped**, in 779.85 seconds.

## Runtime and Browser Evidence

`runtime_canary.py` ran through the public development HTTPS proxy and the actual Compose Flask/rq-engine processes, using real CAPTCHA challenge/redeem/verification, password login, Redis sessions and revocation, PostgreSQL actor/ownership lookup, and NAS-backed run artifacts. Containers ran as UID 1000 / GID 993 with their existing mounts, groups, entrypoints, and configuration. No auth, allocation, or persistence boundary was mocked.

`20260907_runtime_default.json` proves default anonymous creation and logged-in cookie creation with expected ownership and NoDb/config artifacts. `20260907_runtime_restricted.json` proves solved-CAPTCHA denial through both aliases without consuming the CAPTCHA or reserving creation idempotency; real cookie-plus-stale-CAPTCHA success; cross-origin rejection; and real signed-token rejection for both transports with session/uppercase classes and deleted/inactive/conflicting accounts. The temporary inactive account was removed in the canary's finally block.

`20260907_browser_default.json` and `20260907_browser_restricted.json` come from headless Chromium using `browser_canary.cjs`. Default anonymous and authenticated pages each expose 15 creation forms. Restricted anonymous pages expose zero forms, no CAPTCHA widget/assets or context-menu actions, and a working sign-in link. After real login, all 15 authorized forms remain; no page exceptions occurred.

## Configuration and Operational Checks

Development and production `wctl config --format json` renders were inspected in memory (secrets were not printed). Both `weppcloud` and `rq-engine` received true, false, and explicit empty values consistently. Supported host overrides inherit these values; unsupported legacy HPC configuration and worker-only topologies are unchanged.

Only the development web/API containers were recreated, using `WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION=false wctl up -d --no-deps --force-recreate weppcloud rq-engine`; both actual container environments were verified false. After restricted checks, the same command with true restored both services; both actual values were verified true. No production deployment or secret-file changes occurred. `20260907_runtime_restored.json` proves default behavior after restoring both containers to true. `20260907_runtime_identity.json` records their real UID/GID/groups, umask 0022, mounts, and restored values. `20260907_cleanup.json` records removal of the initial seven disposable runs and the one remaining completed canary idempotency key. The security-review follow-up passed all 16 before/after run-directory and Run-row snapshots in `20260907_runtime_denial_snapshots.json`, including logged-in missing-origin requests. It also proves real signed service/MCP creation and retained cookie ownership. `20260907_browser_final.json` repeats the restricted browser checks after sanitizing the failure logger. `20260907_cleanup_final.json` confirms all ten recorded canary runs are absent, with no remaining ownership records; `20260907_restoration_final.json` verifies both services restored to true and the default anonymous UI/API behavior.

## Limitations and Scope

This policy covers `/rq-engine/create/`, its alias, and `/interfaces/`; it does not disable anonymous fork or excluded builder/test-support allocation paths. Location pages retain their controls but their submissions to the restricted endpoint fail. The strengthened denied-request snapshots and final independent correctness/UX and security reviews passed with no unresolved findings. No claim is made that all possible request/runtime states are covered.

## Cleanup Notes

Immediate removal of the first disposable run (`numeral-workmate`) encountered an NFS open-log-handle directory-not-empty error. Subsequent canaries retained their exact run directories for removal after service recreation releases those handles. Cleanup succeeded after the serving process released the handles; see `20260907_cleanup.json`. This is a canary lifecycle issue, not a creation-policy fallback.
