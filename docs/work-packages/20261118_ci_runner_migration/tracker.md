# CI runner migration tracker

Updated: 2026-11-18 UTC. Branch: task/ci-runner-migration.

## Progress

- [x] Audit live runner labels, workflow state and retained runs.
- [x] Operator approved migrating nightly checks and retiring 21 profile schedules.
- [x] Migrate active checks, nightly checks and telemetry; regenerate workflows.
- [ ] Validate generated workflows and real isolated executions; review boundaries.
- [ ] Integrate through PR and retain receipt; clean obsolete queued runs.

## Decisions

Preserve coverage; remove dependence on Forest host setup. Profile schedule retirement
is explicit operator authorization, not inferred from lack of recent successful runs.

## Evidence

[Runner audit](artifacts/runner-audit.json) records 33 enabled homelab workflows;
32 latest executions were queued and Cloc's latest was canceled. There is no
registered homelab runner. Both supported runners are online; only runner-02
is eligible for general remote-ci workloads.

## Implementation observations

Status2 isolated smoke built the actual service/client and delivered all five
samples successfully; cleanup removed its own project. Browser image construction
and direct browser validation are in progress. Existing already-relabeled docs,
quality and broad-exception jobs also inherited unused Forest bootstrap; their
explicit standalone setup removes that same host dependency. Cloc retains optional
repository behavior but now explicitly anchors its base directory to the checkout.
The CI Samurai SSH/restart schedule is a separate discovered consumer; the operator explicitly approved retiring it as well. It is disabled on GitHub,
and the source is archived alongside the profile catalog.

## Validation update

PR #684 is draft. NPM tests, Cloc, docs, quality, exception guards and both
required governance checks passed on b53395d36. Manual supported-runner executions
also passed: Status Tests 44422206052, Preflight Tests 44422210831 and Status2
Smoke 44422215161. All 22 retired workflows are disabled and their queues cleared.

Initial Artifact Observability and Shape Gates runs failed preflight because the
common CI image lacked native shape parsers and the checkout could not see locked
browser assets. Candidate-native builds and explicit asset preparation repair this
shared assumption, including existing stubtest/RQ/isolation consumers. Local broad
preflight now passes all five readiness checks; remote reruns remain pending.

Local NPM V8 coverage produced the verified 1.2 MiB LCOV artifact. The earlier
relative output path passed tests but failed artifact-location validation; the
workflow now uses the absolute workspace path. Browser login passes real CAPTCHA,
CSRF and password validation; controller and accessibility acceptance remain open.

The real controller path required the existing RQ session API and public CDN
scripts. The fixture now preserves Host/origin checks through a private RQ socket;
only the browser/app container has outbound access. Earlier controller failures
are retained as fixture diagnostics, not claimed as accepted application tests.
Focused generator/helper/header validation: 295 passed, 3 deselected, clean source
receipt 49895803660d498f8af012d5b6d81aa0. Independent source security review has no
unresolved findings before the final egress amendment (review requested).

## Browser and artifact acceptance update

Local accessibility fixture: 11 passed, one intentionally opt-in mixed-version
activation canary skipped; all seven required pages are present in the retained
axe report. Five supporting Python checks and 44 Jest checks also pass. Source
security review covers the final fixture grants and early project provisioning.
Theme Metrics passed remotely (44423392936); NPM coverage passed remotely
(44423384936) with verified 1,192,148-byte LCOV. Eight obsolete homelab runs for
accepted replacements were canceled, separate from retired profile cleanup.

The controller run before the OpenET fixture grant was 15 passed/3 failed. A final
run is checking that grant. Features Export selection on an empty run and PATH's
missing second error-detail line remain visible assertions; no skip or weaker
expectation has been added. These are follow-up findings outside runner migration.
Pytest Coverage and remaining PR checks are still running/queued remotely.
