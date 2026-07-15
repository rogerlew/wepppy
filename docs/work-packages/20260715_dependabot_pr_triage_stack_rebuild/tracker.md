# Tracker - Dependabot PR Triage and Local Stack Rebuild

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-15 18:56 UTC
**Current phase**: Complete
**Last updated**: 2026-07-15 20:45 UTC
**Next milestone**: None; follow-ups are separately scoped
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/20260715_security_review.md`

## Task Board

### Ready / Backlog

None.

### In Progress

None.

### Blocked

None.

### Done

- [x] Owner requested a work package, PR assessment, local rebuild, npm gates,
  and pytest gate (2026-07-15 18:56 UTC).
- [x] Confirmed the primary checkout is on `master` at `cc31c121f` with only the
  unrelated NASA report untracked (2026-07-15 18:56 UTC).
- [x] Froze and classified all 37 heads: 35 merge, #570 defer, and #576
  close/recreate (2026-07-15 19:24 UTC).
- [x] Regenerated a coherent 35-update detached candidate and passed all clean
  Node/CAO install and focused gates (2026-07-15 19:25 UTC).
- [x] Rebuilt the CAP and WEPPcloud images without cache and recreated the full
  local stack from the candidate (2026-07-15 19:30 UTC).
- [x] Completed aggregate pytest assessment: 4,888 full-run passes, all 9
  missing-fixture failures passed in a 31-test fixture-complete rerun, and the
  canonical collection defect reproduced under baseline pytest (2026-07-15
  19:44 UTC).
- [x] Restored the full local stack to the primary source mount using the tested
  candidate images; all services run and health endpoints pass (2026-07-15
  19:46 UTC).
- [x] Completed security review, validation evidence, and package closure
  (2026-07-15 19:47 UTC).
- [x] Closed PRs #570 and #576 with their validated native-library/stale-target
  rationale; verified 35 Dependabot PRs remain open (2026-07-15 20:03 UTC).
- [x] Owner authorized merging the remaining 35 PRs and rerunning the local
  rollout/test sequence; package reopened (2026-07-15 20:07 UTC).
- [x] Incorporated all 35 reviewed heads into master; 34 PRs report merged and
  auto-superseded #564 is present through exact merge ancestry at Mistune 3.2.1
  (2026-07-15 20:20 UTC).
- [x] Closed recreated incompatible GDAL #586, excluded unreviewed #587-#589,
  and fast-forwarded local master to `1c4fd3c50` without disturbing user files
  (2026-07-15 20:21 UTC).
- [x] Clean static/UI/CAP npm installs and CAO locked sync passed; static lint
  plus 629 tests, UI lint/build, CAP smoke, and 20 CAO tests passed
  (2026-07-15 20:23 UTC).
- [x] Rebuilt WEPPcloud and CAP without cache from merged `master`, then
  force-recreated the complete local stack (2026-07-15 20:32 UTC).
- [x] Verified 26 long-running services, two successful one-shot builders,
  primary source mount, native WEPPpyo3 import, both health endpoints, zero RQ
  jobs, and all 10 workers idle (2026-07-15 20:45 UTC).
- [x] Re-ran Python validation: the canonical command reproduced the baseline
  Flask-stub collection defect, while the controlled complete run passed 4,897
  tests with 58 skips and exit 0 (2026-07-15 20:44 UTC).
- [x] Updated validation/security/decision artifacts, archived the rollout
  ExecPlan, and closed the work package (2026-07-15 20:45 UTC).

## Timeline

- **2026-07-15 18:56 UTC** - Package opened with an initial count of 36 open
  Dependabot PRs.
- **2026-07-15 19:18 UTC** - Reconciled the complete inventory to 37 PRs. Only
  PRs #540 and #541 currently publish a successful `npm-tests` check; the
  remaining open PRs have no visible checks on their latest head revisions.
- **2026-07-15 19:24 UTC** - No-cache build proved #570 incompatible: GDAL
  3.13 bindings require libgdal 3.13 while the image supplies 3.10.3. Excluded
  it and completed the no-cache build with GDAL 3.10.2.
- **2026-07-15 19:30 UTC** - Recreated the full candidate stack; status and
  preflight health endpoints returned `OK`, and WEPPpyo3 imported natively.
- **2026-07-15 19:32 UTC** - Canonical pytest stopped at a preexisting Daymet
  test stub that shadows installed Flask without defining `Request`; the same
  failure reproduced under baseline pytest 8.4.2. Began controlled full-suite
  validation with real Flask pre-imported.
- **2026-07-15 19:44 UTC** - Controlled full run completed with 4,888 passed,
  58 skipped, and 9 missing-fixture failures. Both affected files then passed
  31/31 after the primary ignored fixture was mounted read-only.
- **2026-07-15 19:46 UTC** - Restored primary source mounts while retaining the
  rebuilt candidate images; all 26 long-running compose services are active,
  both one-shot build helpers completed, and both health endpoints return `OK`.
- **2026-07-15 20:03 UTC** - At owner direction, closed GDAL #570 and stale
  Starlette #576 with evidence-based GitHub comments. Verified both are closed
  and the 35 merge recommendations remain open.
- **2026-07-15 20:07 UTC** - Owner authorized all 35 merges plus local
  rebuild/redeploy and repeated npm/Python validation. Opened a rollout ExecPlan.
- **2026-07-15 20:20 UTC** - Finished merge execution. GitHub reports 34 reviewed
  PRs merged; Dependabot auto-closed #564 as superseded, so its exact head was
  manually merged with Mistune 3.2.1. Shared-lock conflicts retained all prior
  updates through audited merge commits.
- **2026-07-15 20:21 UTC** - Fast-forwarded the primary checkout to merged
  `origin/master` at `1c4fd3c50`; work-package docs and NASA report preserved.
- **2026-07-15 20:23 UTC** - All merged locks installed cleanly. Focused gates
  passed with exact reviewed versions, including Vite 8.0.16, FastMCP 3.2.0,
  Starlette 1.3.1, Express 4.22.2, and CAP path-to-regexp 0.1.13.
- **2026-07-15 20:32 UTC** - Built no-cache images
  `wepppy-dev@18e7a4a4b094` and `wepppy-cap-dev@c6b4a62b98f0`, then
  force-recreated the full primary compose stack.
- **2026-07-15 20:44 UTC** - Canonical pytest reproduced the known Daymet
  synthetic-Flask collection defect. The controlled primary-checkout run then
  completed with 4,897 passed, 58 skipped, and exit 0 in 620.49 seconds.
- **2026-07-15 20:45 UTC** - Final health and RQ verification passed: 26 running
  services, two successful one-shot builders, ten idle workers, and no queued
  or executing jobs.

## Decisions Log

### 2026-07-15 18:56 UTC: GitHub PR state remains read-only during assessment

**Context**: The request is to determine what should merge and validate the
result, while merge/close actions change shared repository state.

**Decision**: Fetch PR commits and build an isolated local candidate, but do not
merge or close GitHub PRs and do not switch the primary checkout branch without
explicit owner direction after the recommendation matrix is complete.

**Impact**: Test evidence is representative and reversible; the owner retains
the final shared-state decision.

### 2026-07-15 19:24 UTC: Exclude two Docker framework/native PRs

**Context**: PR #570 fails the container build at the native ABI boundary, and
PR #576 targets Starlette 1.0.1 even though the queue already contains 1.3.1.

**Decision**: Defer #570 to a GDAL base-image migration and close/recreate #576
as a current coordinated Docker FastAPI/Starlette update. Test the remaining 35
PR intents together.

**Impact**: The aggregate candidate remains buildable without silently masking
either incompatibility.

### 2026-07-15 20:20 UTC: Preserve reviewed intent through shared-lock conflicts

**Context**: Dependabot auto-superseded #564 and GitHub rejected several stale
shared-lock heads after earlier compatible updates merged.

**Decision**: Preserve each exact reviewed head as merge ancestry, retain
already-merged lock state, and apply only the reviewed dependency intent. Do not
substitute newly opened #587-#589 into the frozen candidate.

**Impact**: All 35 reviewed dependency intents are auditable on `master`; 34 PRs
report `MERGED`, and #564 remains closed only because Dependabot superseded it.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Major framework update breaks service contracts | High | Medium | Tested Vite/FastMCP/Starlette majors with focused gates | Mitigated |
| Stale PR overwrites newer lockfile resolution | High | High | Regenerated coherent locks; #576 classified stale | Mitigated |
| Batch hides the dependency causing a regression | Medium | Medium | Focused gates precede aggregate suite | Mitigated |
| Security update is deferred without rationale | High | Low | Security fixes #548/#549/#562 prioritized; exclusions documented | Mitigated |
| Existing test harness defects obscure dependency results | Medium | High | Reproduced under baseline and accounted for with narrow diagnostic setup; follow-up recorded | Accepted follow-up |

## Verification Checklist

### Code Quality

- [ ] Canonical full Python command passes; existing Flask stub collection defect
  is documented and reproduces under baseline pytest.
- [x] Controlled aggregate Python validation accounts for every observed
  failure without candidate source changes.
- [x] Merged-primary controlled full suite passes: 4,897 passed and 58 skipped.
- [x] Frontend lint and tests pass.
- [x] Dependency manifests remain internally consistent.

### Security

- [x] High security impact and dedicated review requirement recorded.
- [x] Every auth/parser/network/supply-chain update is dispositioned.
- [x] No unresolved high/medium findings remain in the merge candidate.

### Documentation

- [x] Decision matrix complete.
- [x] Validation artifact complete.
- [x] Work package, tracker, security review, and root board are current.

### Deployment

- [x] Local development images rebuild from scratch after excluding #570.
- [x] Recreated local services are healthy.
- [x] Rollback to the primary checkout source mount is verified after isolated
  candidate is used.
- [x] Merged-primary no-cache images are deployed locally; 26 services are
  running, build helpers exited 0, and all 10 workers are idle.

## Watch List

- Dependabot may update or supersede PRs while the frozen inventory is under
  review; all conclusions cite the inventory timestamp and head SHA.
