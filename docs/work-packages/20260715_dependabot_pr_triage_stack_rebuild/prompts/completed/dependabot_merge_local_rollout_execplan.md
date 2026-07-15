# Merge the approved Dependabot set and validate the local rollout

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current throughout execution.

## Purpose / Big Picture

The prior review proved a coherent 35-PR dependency candidate and excluded two
incompatible PRs. This rollout merges those 35 approved PRs into
`rogerlew/wepppy:master`, synchronizes the local checkout without disturbing
unrelated working files, rebuilds the affected container images from the merged
manifests, recreates the full local stack, and reruns the same npm, CAO, health,
and Python gates. Success is observable when all 35 PRs report merged, the
running services mount the updated local `master`, candidate dependency versions
are present, health endpoints return `OK`, and validation results are recorded.

## Progress

- [x] (2026-07-15 20:07 UTC) Reopened the work package at local and
  `origin/master` commit `cc31c121f`; verified exactly 35 approved Dependabot PRs
  remain open and currently report mergeable/clean.
- [x] (2026-07-15 20:20 UTC) Incorporated all 35 frozen approved heads: 34 PRs
  report `MERGED`; Dependabot auto-closed #564 as superseded during rollout, so
  its exact reviewed head was incorporated as a merge parent with Mistune 3.2.1.
- [x] (2026-07-15 20:21 UTC) Fast-forwarded local `master` to merged remote
  commit `1c4fd3c50` while preserving the
  unrelated NASA report and uncommitted work-package records.
- [x] (2026-07-15 20:23 UTC) Validated all merged locks with clean installs;
  static lint/85 suites/629 tests, UI Vite 8 lint/build, CAP smoke, and 20 CAO
  tests passed.
- [x] (2026-07-15 20:32 UTC) Rebuilt WEPPcloud and CAP without cache from merged
  `master`, force-recreated the complete local compose stack, and verified image
  IDs, installed versions, health, primary source mount, and native WEPPpyo3.
- [x] (2026-07-15 20:45 UTC) Re-ran canonical npm and Python gates, recorded the
  baseline Flask-stub distinction, verified 4,897 controlled full-suite passes,
  ten idle workers, and zero jobs, then closed the package.

## Surprises & Discoveries

- Observation: Only static frontend PRs #540 and #541 publish GitHub checks;
  local aggregate validation remains the acceptance authority for the rest.
  Evidence: frozen GitHub metadata refreshed at 2026-07-15 20:07 UTC.
- Observation: Dependabot auto-closed reviewed #564 and opened #587 for Mistune
  3.3.0 while merges were in flight. It also recreated excluded GDAL as #586 and
  opened unrelated #588/#589.
  Evidence: #564 comment `Superseded by #587`; #586-#589 creation timestamps
  between 20:11 and 20:12 UTC.
- Observation: GitHub conflict detection rejected several shared-lock PRs even
  though their reviewed intents were independent.
  Evidence: #580 and later Docker heads reported `DIRTY` or merge conflicts
  after narrow updates landed.
- Observation: Immediately after force recreation, RQ's registry still listed
  ten dead pre-recreate workers alongside the ten live workers.
  Evidence: the first post-restart `wctl rq-info --detail` reported 20 workers;
  after normal worker TTL expiry it reported exactly ten idle workers and zero
  jobs without intervention.
- Observation: The canonical pytest command still stops on the Daymet test's
  partial synthetic Flask module, while primary-checkout fixtures remove the
  detached candidate's secondary fixture failures.
  Evidence: canonical collection failed at `from flask import Request`; the
  controlled merged-primary run passed 4,897 tests with 58 skips and exit 0.

## Decision Log

- Decision: Merge via GitHub PR merge commits rather than pushing an aggregate
  dependency commit directly to `master`.
  Rationale: each reviewed PR must retain its individual audit trail and final
  `MERGED` state.
  Date/Author: 2026-07-15, Codex.
- Decision: Merge narrow lock updates before broad framework/bundler updates
  within each ecosystem.
  Rationale: later broad resolutions can incorporate already-merged security and
  patch updates; if a head becomes stale, refresh that PR rather than silently
  replacing its reviewed intent.
  Date/Author: 2026-07-15, Codex.
- Decision: Preserve all current uncommitted documentation and the unrelated
  NASA report while synchronizing `master`.
  Rationale: those files belong to the current work package/user and are outside
  the Dependabot PR commits.
  Date/Author: 2026-07-15, Codex.
- Decision: For shared-lock conflicts, create local merge commits whose second
  parent is the exact reviewed PR head, preserve already-merged lock state, and
  regenerate/apply only the reviewed dependency intent.
  Rationale: this retains auditable ancestry without allowing stale branches to
  revert earlier merges. UI locks were regenerated with npm; Docker pins were
  applied as exact one-line resolutions.
  Date/Author: 2026-07-15, Codex.
- Decision: Do not substitute newly opened #587-#589 into the reviewed set;
  close replacement GDAL #586 under the existing native-library finding.
  Rationale: those heads were not part of the frozen/tested candidate, and
  Mistune 3.3.0 exceeds the approved 3.2.1 target.
  Date/Author: 2026-07-15, Codex.
- Decision: Preserve the canonical pytest failure as a visible test-isolation
  defect and use only a real-Flask preload for the aggregate compatibility run.
  Rationale: the same failure was reproduced under baseline pytest 8.4.2; the
  preload changes collection order, not application or dependency source.
  Date/Author: 2026-07-15, Codex.

## Outcomes & Retrospective

All 35 reviewed dependency intents are incorporated into `master`. GitHub marks
34 reviewed PRs `MERGED`; Dependabot auto-closed #564 before its merge call, so
its exact reviewed head remains auditable as a merge parent and the approved
Mistune 3.2.1 pin is installed. The incompatible GDAL and stale Starlette heads
remain excluded; newly opened #587-#589 were not silently substituted.

No-cache images `wepppy-dev@18e7a4a4b094` and
`wepppy-cap-dev@c6b4a62b98f0` were built and deployed locally. Twenty-six
long-running services are active, both build helpers exited 0, health endpoints
return `OK`, native WEPPpyo3 is loaded, ten RQ workers are idle, and no jobs are
queued or executing. Static npm lint and 629 tests, UI lab lint/build, CAP
smoke, and all 20 CAO tests passed. The merged-primary controlled Python suite
passed 4,897 tests with 58 skips. The only non-green required command is the
preexisting canonical collection-order defect, now isolated with direct
baseline evidence and retained as follow-up work.

The principal process lesson is that Dependabot's automatic supersession can
change PR state during a large merge batch. Freezing exact heads and retaining
them as merge parents preserved auditability without allowing stale shared
locks to revert already merged updates.

## Context and Orientation

The authoritative PR inventory and original compatibility evidence live in
`artifacts/pr_decisions.md` and `artifacts/validation.md`. PRs #570 and #576 are
closed and must remain excluded. The remaining 35 PRs span Docker Python pins in
`docker/requirements-uv.txt`, CAO's resolved `services/cao/uv.lock`, CAP and UI
lab npm locks, and the primary frontend lock. Several PRs touch the same lockfile
at distinct package entries, so GitHub may temporarily report a later PR stale
after an earlier merge. A stale PR is refreshed and rechecked; a conflicting
lock is never force-merged.

The local checkout is `/home/workdir/wepppy` on `master`. Its work-package docs
are intentionally uncommitted, and
`docs/projects/nasa-roses-utility-watersheds/july2026-nasa-roses-weppcloud-summary-report.md`
is an unrelated untracked user file that must remain untouched. The development
stack is defined by `docker/docker-compose.dev.yml`, with local environment and
secrets already present under `docker/`.

## Plan of Work

First, merge security patches, then narrow CAP/static/UI updates, Docker patches
and majors, and finally CAO's broader framework/MCP resolutions. After each
merge, verify GitHub reports `MERGED`; if another reviewed head becomes dirty,
use GitHub's branch-update mechanism and confirm its head diff still represents
the approved version intent before merging.

Next, fetch `origin/master` and fast-forward the local branch. Inspect every
merged manifest and run `npm ci` in the three Node workspaces plus `uv sync
--locked --all-groups` in CAO. Run static frontend lint/tests, UI lab lint/build,
CAP import/syntax smoke, and CAO's declared `test/` suite.

Then confirm RQ has no queued or executing work. Build `weppcloud` and `cap`
without cache from the merged primary checkout and recreate the complete compose
stack. Verify the primary source mount, installed dependency versions, native
WEPPpyo3 import, status/preflight health endpoints, running services, and worker
state.

Finally, run `wctl run-npm lint`, `wctl run-npm test`, and
`wctl run-pytest tests --maxfail=1`. The prior baseline had a collection-order
defect in the Daymet test's synthetic Flask stub. Preserve the canonical result;
if it recurs, reproduce the same narrow controlled aggregate run so dependency
compatibility is still measurable without hiding the defect.

## Concrete Steps

From `/home/workdir/wepppy`, merge and verify each PR with `gh pr merge <number>
--repo rogerlew/wepppy --merge` followed by `gh pr view`. Synchronize with `git
fetch origin` and `git merge --ff-only origin/master`, stopping if the dirty docs
overlap an incoming path.

Use clean package-manager installs in each affected workspace. Use canonical
`wctl run-npm` and `wctl run-pytest` wrappers for primary gates. Build and deploy
with the primary compose file and existing local environment:

    docker compose -p docker --env-file docker/.env \
      -f docker/docker-compose.dev.yml build --no-cache weppcloud cap
    docker compose -p docker --env-file docker/.env \
      -f docker/docker-compose.dev.yml up -d --force-recreate

## Validation and Acceptance

Acceptance requires all 35 approved PR numbers to report `MERGED`, #570/#576 to
remain `CLOSED`, and no unexpected open Dependabot PR to be silently included.
Every merged lock must install cleanly. Static npm lint and 629-test gates, UI
lab lint/build, CAP smoke, CAO tests, image builds, stack health, native WEPPpyo3
import, and post-restart RQ idle state must be recorded. The canonical full
pytest result is reported exactly; any baseline harness exception is separated
from dependency regressions with controlled evidence.

## Idempotence and Recovery

GitHub merge calls are state-checked before retrying; already merged PRs are not
merged twice. A stale branch is refreshed and re-inspected. Local synchronization
uses only fast-forward merge and never resets or discards working files. Compose
build/recreate commands are repeatable and preserve named/bind data volumes.
Before any restart, RQ must be idle. If a build fails, keep the current running
stack, record the exact dependency boundary, repair only the reviewed lock
resolution when authorized by the existing merge intent, and rebuild.

## Artifacts and Notes

Append merge commit/state evidence and final rollout results to
`artifacts/validation.md`. Update `artifacts/pr_decisions.md`, `tracker.md`, and
the security review with the actual merged state. Large build and test logs are
not committed.

## Interfaces and Dependencies

No application API or parameterization is intentionally changed. This rollout
changes only dependency versions represented by the 35 approved PRs plus the
work-package records. GitHub CLI performs the authorized PR merges; npm, uv,
Docker Compose, and `wctl` remain the canonical install, build, deployment, and
test interfaces.

## Plan Revision Note

2026-07-15 20:07 UTC: Created when the owner authorized merging all 35 approved
Dependabot PRs, rebuilding/redeploying the local stack, and rerunning tests.

2026-07-15 20:21 UTC: Updated after merge execution to record Dependabot's
mid-rollout supersession, shared-lock conflict resolution, exact #564 head
integration, new unreviewed PR exclusions, and local master synchronization.

2026-07-15 20:45 UTC: Completed the no-cache merged-master rebuild, local stack
recreation, focused and full validation, final health/worker checks, and package
closure evidence.
