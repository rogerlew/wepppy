# CI runner migration tracker

Updated: 2026-11-19 UTC. Branch: task/ci-runner-migration. PR: #684.

## Progress

- [x] Audit live runner labels and retained workflows/runs.
- [x] Migrate three active checks, eight nightly suites and Cloc; regenerate YAML.
- [x] Retire 21 Forest profile schedules and CI Samurai Nightly with explicit approval.
- [x] Validate isolated runtimes, meaningful reports and independent source security review.
- [x] Integrate PR; retain fresh ancestry receipt and final queue/runner readback.
- [ ] Observe deferred broad baseline and full pytest coverage after integration.

## Decisions

Use remote-ci for general jobs; preserve ghcr-builder isolation. Remove Forest host
configuration and shared Redis cleanup. Retire only the explicitly approved profile
and Samurai schedules; keep CLI tooling and archived catalogs. No production deploy.

Preserve all assertions and report failures. Keep Features Export/PATH findings
separate from this runner migration. Broad coverage/baseline validation is deferred
until after integration in accordance with the operator's earlier instruction.

## Validation and limits

Executable candidate: 97a82588310dc91a9e3dd2b11547200db0a6dd3a. Later evidence-only
changes do not change tested workflow/runtime sources.

| Surface | Evidence/outcome |
| --- | --- |
| Artifact Observability | Supported-runner pass, 44425293294 |
| Shape-Converter Gates | Focused and full unit/integration passes, 44425293369 |
| NPM tests | Supported-runner pass, 44425293043 |
| Accessibility | Supported-runner pass, 44425329684; 11 passed, one opt-in canary skipped; all seven page reports present |
| Controller checks | Supported-runner 44425333040 matches local: 16 passed, two failures, zero skipped; report upload and cleanup completed |
| NPM coverage | Pass, 44423384936; verified 1,192,148-byte LCOV |
| Theme Metrics | Pass, 44423392936; 14 themes, 1,568 measurements |
| Status / Preflight / Status2 smoke | Passes, 44422206052 / 44422210831 / 44422215161 |
| Cloc / exception guard / governance | Passed on candidate; retained final run readback identifies exact revisions |
| RQ contract guards / docs / code quality | Passed: 44425293131 / 44425293295 / 44425293013 |
| Local regression | 295 focused Python checks; final nine helper/generator checks; clean receipts retained compressed |
| Broad coverage / baseline | Explicitly deferred; canceled pre-merge runs are not passing evidence |

See [remaining controller findings](artifacts/remaining-controller-findings.md).
Accessibility passes existing suite rules, not full conformance: retained axe and
non-enforced contrast findings remain. No checks, thresholds or permissions were
weakened to obtain passing migration evidence.

## Runtime repairs and cleanup

The remote preflight initially found missing native parsers and browser assets.
The test image now builds candidate parsers with provenance; explicit preparation
requires candidate-matching image-owned browser assets. The same shared assumption
is repaired in existing stubtest, isolation and RQ guard consumers. RQ preparation
also initializes its disposable account schema before broad preflight.

[Browser runtime evidence](artifacts/header-conformance-repair.md) explains the
shared header alias repair, actual CAP/password/CSRF login, private RQ API, exact
Host forwarding, browser outbound bridge for existing CDN scripts, fixture OpenET
grant and early accessibility project provisioning. Other services stay internal;
there are no published ports or production credentials/mounts.

All 22 retired workflows are disabled and their queued runs cleared. Additional
obsolete homelab runs and superseded task-PR runs are separately recorded; unrelated
runs were not canceled. Local containers, volumes, networks and job-owned images
were removed. The canceled remote coverage project's resources were also absent
on readback. Final readback verifies all 26 workflow jobs target supported labels, all 22
retired workflow files are absent, and queued homelab jobs are zero.

## Integration receipt

PR #684 merged at ef935e559a1cca71ce0862215d80b5074d1aefe0 on 2026-11-19
00:27:03 UTC. The fresh receipt proves accepted candidate
350b565ed501d4533b5f1d60499e30092ddf9c88 is an ancestor of remote master.
This is remote integration, not a full-suite pass or deployment approval.

Full coverage dispatched on master: 44429119454. Automatic Stubtest/baseline:
44429094546. Results remain pending. No production deployment was performed.
Post-integration receipts and readback are retained in a subsequent audit commit
on the task branch, separately from the accepted source they identify.
