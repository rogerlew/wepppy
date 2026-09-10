# Independent QA review

Reviewer: `deval_identity_qa`, September 10, 2026 UTC.

## Disposition

Code quality and the scoped production permission-boundary evidence are
accepted. No blocking maintainability or test-quality findings remain. This
review follows [the primary correctness review](correctness-review.md).
The generated-input, queued-render, and both-host canaries have now passed.
Broad-suite completion, source publication, and final package records remain
closure tasks in [the active plan](../prompts/active/execplan.md).

## Findings and disposition

- **Minimal implementation: accepted.**
  `wepppy/rq/weppcloudr_backends.py`, `DockerExecBackend.render`, adds only the
  Docker execution user argument and its rationale. Effective UID/GID come from
  the worker process. No configuration, permission migration, retry loop, new
  dependency, or alternate execution path is introduced. Existing transport,
  errors, timeout, logging, and publication remain cohesive.
- **Regression tests: accepted.**
  `tests/rq/test_weppcloudr_backends.py` tests two distinct UID/GID pairs and
  the complete argv, guarding against hardcoded deployment identity. It also
  preserves request, fencing, timeout, and result expectations. The updated
  orchestration test in `tests/rq/test_weppcloudr_rq.py` retains completion and
  log assertions. Fixtures use scoped monkeypatching and existing unit markers;
  no new global stub pollution is introduced.
- **Permission-boundary coverage: accepted with separate workflow evidence.**
  `docker/validate-weppcloudr-runtime-contract.sh` creates real parquet under
  umask 0077, invokes R/Arrow using the worker identity, writes output, and
  verifies worker readback and unchanged input mode. This is stronger evidence
  than mocked command construction alone. The probe passes the identity itself;
  it verifies image/filesystem compatibility, not execution of the Python
  backend. The full queued canary is therefore a required complementary check.
- **Documentation and scope: accepted.**
  `weppcloudR/README.md`, One-shot renderer, explains the supported RQ workflow,
  identity source, stderr location, and fresh-render requirement. Keeping the
  legacy direct Plumber lifecycle outside this patch avoids unrelated migration
  work. The fix must not be described as repairing that separate ingress.

## Evidence reviewed

- Reviewer inspected the scoped diff, surrounding RQ publication code, Compose
  identity declarations, deployment invocation, tests, and primary review.
- Reviewer ran shell syntax validation, scoped `git diff --check`, and review
  document lint: passed.
- `/tmp/deval-identity-focused.log`: 52 focused tests passed in 9.11 seconds.
  Reviewer inspected the result rather than repeating that run.
- `/tmp/deval-live-runtime-probe.log`: real image preflight passed as 1002:130.
- `/tmp/deval-identity-canary.log`: fresh wepp1 candidate render produced
  13,494,027 bytes with input mode 0600 and unchanged input bytes. The inspected
  driver asserts effective identity 1002:130, `skip_cache=True`, SHA-256 parity,
  and unchanged mode after rendering.
- `/tmp/deval-regenerated-canary.log`: deployed soils writer preserved DataFrame
  contents, published 0644, and rendering recreated the absent export directory,
  producing 13,494,033 bytes. The driver asserts controller and soils paths stay
  inside the isolated canary despite the copied NoDb working-directory warning.
- `/tmp/deval-queued-canary.log` and `/tmp/deval-queued-completed.log`: ordinary
  default-queue job `deb10627-1fbd-48d7-87e3-55fcc3ab1283` finished at
  2026-09-10 04:22:21.694667 UTC with the expected report result. Its inspected
  enqueue driver requires an existing report, sets soils mode 0600, and requests
  `skip_cache=True`. Later wepp2 rendering superseded the artifact modification
  time, so current modification time is not claimed as evidence for this job.
- `/tmp/deval-route-readback.log`: authenticated Flask application route returned
  status 200 and 13,494,023 bytes with SHA-256 matching the published report:
  `a2e5361a5ae3c42ffe0796453e42b1a3633f0d7c5a6ebc8e5c61f5dd17aa75f5`.
  The inspected driver uses the deployed app test client and an existing Root
  session; this proves application-route delivery, not a browser/proxy roundtrip.
- `/tmp/deval-wepp2-canary.log`: installed backend on the second host produced
  13,494,036 bytes as 1002:130, preserving mode-0600 input bytes and SHA-256.
  Its inspected driver imports the installed backend and forces fresh rendering.
- These are independently inspected operator-run logs and drivers; the reviewer
  did not launch separate production mutations. Broad validation was still
  running when this acceptance update was written.

## Residual debt and non-blocking follow-ups

The existing preflight uses image defaults and a local temporary bind mount;
it cannot establish production Compose overrides, NFS behavior, or full
R Markdown publication by itself. Its existing deploy hook runs when the
renderer is in the build set. Operators changing worker identity or mounts must
also run the explicit preflight and fresh workflow check documented in the
README, including worker-only rollouts. No additional framework or deployment
mode is warranted for this repair.

Owner-only files belonging to a different historical UID and legacy direct
Plumber output ownership are outside the stated worker-owned-input contract.
No speculative permissions migration is recommended. Preserve these limits in
the final handoff and complete the package's outstanding validation records.
