# F7 implementation validation (2026-11-12 UTC)

Status: source/component checks pass; runtime acceptance and combined readiness
remain open. No service restart or deployment occurred.

## Revision and environment

Contract ancestor: `21a75b794` (full revision in tracker). Implementation is the
subsequent scoped working diff; final implementation revision will be recorded
at commit. Host is forest, running development Compose. Tests use the existing
WEPPcloud container, UID 1000/GID 993, and its real mounts. `/wc1` is NFS4.
The existing container has support enabled and no profile; no service environment
was changed. New Python processes explicitly selected test or production.

`wctl run-pytest` cannot inject per-exec environment settings into that existing
container. Its initial focused run correctly failed the new production-default
guard. Subsequent commands use the same wctl/container boundary with
`wctl exec -T weppcloud env WEPPCLOUD_DEPLOYMENT_PROFILE=test /opt/venv/bin/pytest`.
Configuration unit fixtures clear inherited profile/flag values for isolation.

## Component gates

- Focused configuration, test routes and registration: 74 passed, 8 warnings,
  10.65 seconds before final malformed-number vector refinement; final rerun
  recorded below.
- `PYTHONPATH=/home/workdir/wepppy .venv/bin/pytest tools/wctl2/tests/test_playwright_command.py -q`:
  27 passed, 1.75 seconds. Actual local HTTP redirect/proxy boundaries, captured
  mint failures, child-only injection, viewer exclusion and output suppression.
- `node --test wepppy/weppcloud/static-src/tests/node/support-request.test.mjs`:
  3 passed. Real HTTP server, prefix/origin/method/redirect confinement, startup
  proxy environment and self-signed HTTPS despite insecure ambient TLS override.
  Native tests are now included in `wctl run-npm test` after Jest.
- `wctl run-npm lint`: passed.
- `wctl run-npm test`: 126 Jest suites, 1,076 tests passed; three native tests
  passed. No browser lifecycle acceptance is implied.
- Broad-exception enforcement against the contract ancestor: PASS, net zero.
- Code-quality observability: generated local observe-only report; no gate.
- Unsegmented broad Python run: in progress at documentation update. This is a
  local sanity receipt, not M6: F6 M4 and an exact combined freeze are absent.

## Rendered configuration and actual application inventory

`wctl docker compose config --format json`, filtered in memory to the two public
fields, produced development/true for dev. With attempted host overrides
`TEST_SUPPORT_ENABLED=true WEPPCLOUD_DEPLOYMENT_PROFILE=development`,
`wctl --compose-file docker/docker-compose.prod.yml docker compose config --format json`
produced production/false. Adding `docker/docker-compose.prod.wepp1.yml` also
produced production/false. No full environment dump was retained.

A fresh process imported the actual `wepppy.weppcloud.app` with explicit
production/false: 484 URL rules total, zero `/tests/api/*` rules. This is the full
application, not the isolated registration unit fixture. Unknown/production-true
startup rejection before secret lookup is covered by the configuration matrix.

HPC remains unsupported for support smoke and defaults production; canary does
not enable support; forest1 uses the production family and receives no implicit
non-production exception. No live host override audit or activation is claimed.

## Unmocked filesystem acceptance: failure retained

A process-local Flask test client used the actual app, signing configuration,
Ron constructor, run resolver and filesystem. It minted a one-hour support token
in memory and used the existing `disturbed9002_wbt` configuration. The old
`dev_unit_1` example is absent from this checkout and returned 400; it was not
substituted as a passing case. The ordinary config produced:

| Observation | Result |
| --- | --- |
| Create | 201; actual run directory exists |
| Returned page (with Caddy's prefix stripping represented) | 200; run ID present |
| Invalid bearer delete | 401; directory preserved |
| Authorized delete | 200, but path still exists: FAIL |
| Generated run files contain exact minted token | false |
| Captured stdout/stderr contain exact minted token | false |

Direct cleanup during the originating process reproduced `OSError` errno 16
(`EBUSY`) on NFS. After that process exited, the remaining directory was empty
and a separately scoped cleanup removed it; direct absence readback passed for
each identified disposable fixture. This is evidence consistent with open-file
NFS cleanup, not proof that every outstanding handle has been identified.
No retained/user run was deleted. No blanket directory cleanup was attempted.

The support helper still uses existing `shutil.rmtree(ignore_errors=True)`;
changing general cleanup or the deletion worker is explicitly excluded by M2.
The confirmed false-success is therefore retained as an M4 acceptance blocker,
not hidden behind the 200 or the passing local-filesystem component test.
Existing `NoDbBase.cleanup_run_instances` is a precedent (ordinary project
route uses it), but directly constructed initialization objects are not all
covered by its cached-instance lookup; a separate bounded lifecycle repair must
prove all relevant handles and consumers before claiming resolution.

Automatic `wctl run-playwright` against a configured live backend and exact-token
scans of its browser trace/report/log artifacts remain outstanding. The running
forest service was not restarted or deployed to manufacture that evidence.
The file/output scans above are narrower and do not substitute for it.

## Review and readiness

Independent correctness, QA and security reviewers cleared source findings after
fixes; all retain the M4 hold. No production readiness or deployment is claimed.
F6 remains below M4, so M6 combined owner gates, image/advisory evidence, final
candidate freeze and M7 final runbook acceptance cannot complete here.

## Final focused and draft-review updates

- Final configuration/routes/registration selection: 77 passed, 8 warnings in
  10.88 seconds, including all source-defined Flask consumers in dev/prod/worker
  Compose and the fractional-issued-time/huge-expiration regression.
- Entire `tools/wctl2/tests` selection: 59 passed in 2.54 seconds.
- Rendered all eight Flask consumers in dev: development/true under intentional
  support enablement. All eight production consumers: production/false despite
  hostile environment inputs. Both worker-only Flask consumers: production/false.
  Worker render used a nonsecret dummy Redis URL solely for interpolation; no
  connection or service action occurred.
- Independent deployment source review found the shared dev environment omission;
  moving the profile to the common anchor fixed it. Production and worker common
  anchors now pin production/false for lazy Flask import consumers too.
- Operations/security approved the deployment draft only as a HOLD document after
  mandatory no-prune, frozen-source and cross-host RQ recovery corrections.
  Required F6/F7 blocking preflights do not yet exist in the deploy script; no
  execution approval is implied.
- Scoped markdown lint passed all package/canonical/workflow docs, root AGENTS
  size passed (160 lines), and diff whitespace checks passed. Spelling previews
  were inspected; brand/code terms such as axe were deliberately preserved.
