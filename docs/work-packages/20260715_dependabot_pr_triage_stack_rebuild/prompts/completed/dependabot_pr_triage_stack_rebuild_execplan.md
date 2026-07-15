# Review Dependabot PRs and validate a local integration candidate

This ExecPlan is a living document. Maintain `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, the maintainer has an exact, evidence-backed decision for every
open Dependabot PR rather than a backlog of unreviewed version bumps. The
recommended merge set is proven together in a clean rebuilt local stack with
npm and Python tests, while risky major upgrades are isolated into explicit
follow-up work instead of being mixed into a blind dependency batch.

## Progress

- [x] (2026-07-15 18:56 UTC) Opened the package, tracker, security review, and
  ExecPlan from an initial count of 36 open Dependabot PRs.
- [x] (2026-07-15 19:18 UTC) Reconciled the complete inventory to 37 open PRs;
  successful `npm-tests` checks are present only on PRs #540 and #541.
- [x] (2026-07-15 19:24 UTC) Froze each PR head SHA, changed files, current
  mergeability, checks, and version class.
- [x] (2026-07-15 19:24 UTC) Reviewed upstream and local compatibility evidence;
  published one disposition per PR.
- [x] (2026-07-15 19:25 UTC) Composed an isolated local candidate from the 35
  merge-ready PR intents.
- [x] (2026-07-15 19:44 UTC) Rebuilt and recreated the local stack, passed npm
  and focused CAO gates, and completed controlled aggregate pytest validation.
- [x] (2026-07-15 19:47 UTC) Completed security review, archived the plan, and
  closed the package.

## Surprises & Discoveries

- Observation: The open queue spans 37 PRs and five runtime surfaces, while only
  PRs #540 and #541 currently report successful GitHub check runs.
  Evidence: `gh pr list --author app/dependabot --state open` at
  2026-07-15 18:54 UTC.
- Observation: GDAL 3.13 cannot be treated as a Python-only version bump.
  Evidence: the no-cache Docker build reports that GDAL 3.13 bindings require
  libgdal 3.13 while Debian currently provides 3.10.3.
- Observation: The canonical full pytest command has a baseline collection
  defect independent of pytest 9. The Daymet test installs a synthetic `flask`
  module without `Request`; the same error reproduces with pytest 8.4.2.
  Evidence: canonical pytest-9 collection and a temporary in-container pytest
  8.4.2 reproduction.
- Observation: Detached worktrees omit the gitignored disturbed-matrix fixture
  expected by one unguarded test.
  Evidence: `test_ag_fields_management_corpus.py` stopped after 1,523 passes
  until the primary checkout fixture was mounted read-only.

## Decision Log

- Decision: Keep GitHub PR state read-only and test a reversible local candidate.
  Rationale: assessment and local validation are authorized, but shared merge or
  close mutations require owner confirmation of the final matrix.
  Date/Author: 2026-07-15, Codex.
- Decision: Treat dependency updates touching auth, parsing, networking,
  geospatial libraries, or container builds as high security impact.
  Rationale: version-only diffs can materially change internet-facing runtime
  behavior and supply-chain inputs.
  Date/Author: 2026-07-15, Codex.
- Decision: Recommend 35 merges, defer GDAL #570, and close/recreate stale
  Starlette #576.
  Rationale: the 35-update coherent candidate builds and passes focused gates;
  #570 has a proven native ABI failure and #576 targets an obsolete framework
  release.
  Date/Author: 2026-07-15, Codex.
- Decision: Preserve the canonical pytest failure as evidence and use only a
  real-Flask pre-import plus read-only fixture mount for diagnostic aggregate
  validation.
  Rationale: this distinguishes existing test infrastructure defects from
  dependency regressions without modifying application or test source in the
  candidate.
  Date/Author: 2026-07-15, Codex.

## Outcomes & Retrospective

All 37 open Dependabot PRs have a frozen, evidence-backed disposition: merge 35,
defer GDAL #570, and close/recreate stale Starlette #576. The coherent 35-update
candidate passed clean Node and CAO installs, 629 static frontend tests, UI lab
lint/build, CAO's 20 service tests, no-cache CAP/WEPPcloud image builds, complete
stack recreation, and service health checks.

The canonical full pytest invocation exposed an existing collection-order bug
in the Daymet test's synthetic Flask module. It reproduces under baseline pytest
8.4.2. With real Flask pre-imported, the full pytest-9 run produced 4,888 passes,
58 skips, and 9 failures caused solely by another detached-worktree limitation:
a required gitignored WEPP fixture was absent. Mounting that fixture read-only
made both affected files pass 31/31, accounting for all nine failures without a
source or dependency change.

The key operational lesson is that native geospatial updates must be validated
against system-library versions, and full-suite worktree validation needs a
documented fixture-materialization contract. The primary source mount and all
local services were restored while retaining the tested candidate images.

At owner direction after package closure, PRs #570 and #576 were closed at
20:03 UTC with comments carrying the validated native-library and stale-target
rationale. The 35 merge recommendations remain open.

## Context and Orientation

Dependabot opens independent branches for each ecosystem and directory declared
in `.github/dependabot.yml`. The main Docker Python environment is locked under
`docker/`; CAO uses `services/cao/pyproject.toml` plus `uv.lock`; the primary
WEPPcloud browser code uses `wepppy/weppcloud/static-src/package.json` and its
lockfile; CAP and `weppcloud-ui-lab` have separate Node locks. A pull request may
be clean relative to the base revision where it was opened yet stale relative to
today's `master`, so the review must compare its requested direct version and
transitive lock resolution to the current manifest rather than applying old
lockfiles mechanically.

The primary checkout stays on `master`. Candidate validation uses a detached
temporary worktree rooted at the exact current base. Pull-request commits may be
fetched into private local refs and cherry-picked or their direct version intent
may be regenerated with the repository's own package manager. The latter is
preferred when several PRs touch the same lock because it proves a coherent
current resolution rather than preserving obsolete lock state.

## Plan of Work

Milestone 1 freezes the queue. Record PR number, title, URL, head SHA, update
ecosystem/directory, changed files, direct before/after version, semver class,
mergeability, and check state. Detect PRs whose target version is already present
or whose branch is behind/conflicting with current master.

Milestone 2 assesses compatibility. Patch/minor updates with no contract or
dependency-source change may enter the candidate after upstream release-note and
local usage review. Major updates, framework contract changes, native/geospatial
ABI changes, or updates requiring application migration are deferred unless
focused evidence proves compatibility. Duplicate Docker/CAO updates are reviewed
as coordinated pairs but remain separately dispositioned.

Milestone 3 constructs the candidate in a detached worktree. Apply only direct
version intents marked `merge`, regenerate each affected lock with its canonical
tool, inspect new transitive dependencies and install hooks, and record the exact
candidate diff. Do not alter the primary checkout or GitHub PR state.

Milestone 4 rebuilds and validates. Stop the local development stack only after
confirming RQ has no active work. Build the candidate image without cache where
needed to prove dependency installation, recreate the local stack, and verify
service health. Run canonical npm lint/tests and
`wctl run-pytest tests --maxfail=1`. Restore/recreate the primary checkout stack
after candidate testing if the candidate is hosted outside the primary tree.

Milestone 5 records the final security verdict, recommendation matrix, exact
test results, residual migration packages, and owner actions. Archive this plan
and close the package only when every PR has one decision and all candidate gates
pass.

## Concrete Steps

From `/home/workdir/wepppy`, capture GitHub and local evidence with:

    gh pr list --repo rogerlew/wepppy --state open \
      --author app/dependabot --limit 100 --json number,title,url,headRefName
    gh pr view <number> --repo rogerlew/wepppy \
      --json headRefOid,mergeable,mergeStateStatus,statusCheckRollup,files
    git diff --stat master...<fetched-pr-ref>

Create the detached candidate with `git worktree add --detach` at the current
base. Use the package manager already authoritative for each changed lock:
`uv`/`pip-compile` according to repository scripts for Python and `npm` for Node.
Record commands in `artifacts/validation.md` as they become final.

Use the canonical local operational and test commands:

    wctl rq-info --detail
    wctl compose build --no-cache weppcloud
    wctl compose up -d --force-recreate
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1

## Validation and Acceptance

Acceptance requires a 37-row decision matrix with no missing or duplicate PR,
one coherent candidate diff composed only of `merge` recommendations, a clean
container build from those manifests, healthy recreated services, passing npm
lint/tests, and a passing full pytest suite. The security artifact must have no
unresolved high/medium findings for the candidate. A deferred PR is acceptable
when the matrix identifies the incompatible contract and the smallest follow-up
needed; deferral is not a test failure.

## Idempotence and Recovery

Inventory and detached-worktree construction are repeatable. Record the frozen
head SHAs so later Dependabot updates cannot silently change conclusions. Do not
delete or overwrite the primary checkout. Before stack replacement confirm RQ is
idle. If a candidate image fails, capture the first actionable error, restore
the primary compose stack, and keep the PR deferred until a focused package owns
the migration.

## Artifacts and Notes

The final PR matrix lives at `artifacts/pr_decisions.md`, security findings at
`artifacts/20260715_security_review.md`, and build/test evidence at
`artifacts/validation.md`. Large logs and temporary worktrees are not committed.

## Interfaces and Dependencies

No application API is intentionally changed. The candidate may modify only the
dependency manifests and lockfiles represented by reviewed PRs plus the work
package documentation. GitHub PR merge/close state is an owner action after this
package reports recommendations.

## Plan Revision Note

2026-07-15 18:56 UTC: Created from the owner's request to triage every open
Dependabot PR, rebuild the local stack, and run npm and Python tests. The plan
uses an isolated current-base candidate so validation does not imply unauthorized
GitHub merges or contaminate the primary checkout.

2026-07-15 19:47 UTC: Closed with 35 merge recommendations, two explicit
non-merge actions, candidate build/npm/pytest evidence, and two test-harness
follow-ups. The canonical pytest success criterion remains visibly unchecked
because the baseline Flask stub defect was documented rather than hidden.

2026-07-15 20:03 UTC: Recorded the owner-authorized closure of PRs #570 and
#576; no merge recommendation was closed or merged.
