# Dependabot PR Triage and Local Stack Rebuild

**Status**: Complete (2026-07-15)
**Timezone**: UTC

## Overview

WEPPpy has accumulated 37 open Dependabot pull requests across four dependency
manifests and five runtime surfaces. This package determines which updates are
safe to merge now, which require coordinated migration work, and which are stale
or superseded, then validates the selected candidate set through a clean local
container rebuild and the canonical npm and Python gates.

## Objectives

- Freeze an exact inventory of all open Dependabot PRs and their current diffs,
  mergeability, checks, release class, and affected runtime.
- Produce one evidence-backed recommendation for every PR: `merge`, `defer`, or
  `close/superseded`.
- Evaluate authentication, cryptography, parser, geospatial, framework, and
  build-tool upgrades as supply-chain/security changes rather than routine
  lockfile churn.
- Build an isolated local integration candidate for the `merge` set without
  changing GitHub PR state or switching the primary checkout branch.
- Rebuild the local development stack from the candidate and pass npm lint,
  npm tests, and the full WEPPpy pytest suite.

## Scope

### Included

- All open PRs authored by `app/dependabot` against `rogerlew/wepppy:master` at
  the inventory timestamp.
- Docker Python requirements, `services/cao` uv dependencies, WEPPcloud
  `static-src`, CAP, and `weppcloud-ui-lab` npm dependencies.
- Upstream changelog/security review proportional to version jump and runtime
  criticality.
- A PR decision matrix, security review, candidate composition record, container
  rebuild evidence, npm results, and full pytest results.

### Explicitly Out of Scope

- GitHub mutations until explicit owner direction after review. The owner later
  authorized the selected merges and evidence-backed closures; those actions
  are recorded in the package artifacts.
- Unrelated dependency modernization not represented by an open Dependabot PR.
- Production, forest1, or remote-host deployment.
- Redesigning application code solely to make a major dependency update fit; a
  required migration becomes a deferred follow-up package.

## Stakeholders

- **Decision owner**: Roger Lew, WEPPpy maintainer.
- **Implementer/reviewer**: Codex.
- **Security reviewer**: Codex supply-chain and changed-surface review.
- **Informed**: WEPPpy, CAO, CAP, and frontend maintainers.

## Success Criteria

- [x] Every open Dependabot PR is represented exactly once in the decision
  matrix with evidence and rationale.
- [x] Duplicate, stale, superseded, and breaking-major PRs are distinguished
  from merge-ready patch/minor updates.
- [x] The local candidate contains only the recommended `merge` set and has no
  unresolved dependency-file conflicts.
- [x] A clean local container image/stack rebuild completes from the candidate
  after excluding the incompatible GDAL update.
- [x] Canonical npm lint and test gates pass.
- [ ] `wctl run-pytest tests --maxfail=1` passes on the rebuilt candidate stack.
  It was run and exposed a preexisting collection-order defect that reproduces
  under baseline pytest 8.4.2; controlled aggregate validation accounted for
  every test outcome without candidate source changes.
- [x] Dedicated security review has no unresolved high/medium findings for the
  recommended merge set.

## Parameterization ADR Gate

- **Parameterization change present**: `no`.
- **ADR required**: `no`.
- **Decision provenance captured**: `yes`; Codex API request from Roger Lew,
  2026-07-15, with Codex as implementer.

## Dependencies

### Prerequisites

- Authenticated read access to `rogerlew/wepppy` PR metadata and diffs.
- A clean primary checkout aside from known unrelated user files.
- Docker, Docker Compose, and `wctl` available locally.

### Blocks

- None. All 35 reviewed dependency intents are incorporated into `master`; 34
  PRs report `MERGED`, and auto-superseded #564 is present through exact merge
  ancestry at the reviewed Mistune 3.2.1 head.

## Timeline Estimate

- **Expected duration**: one focused review/build session.
- **Complexity**: high because the PRs span multiple independent runtimes.
- **Risk level**: high for supply-chain, auth, parser, and geospatial upgrades.

## Security Impact and Review Gate

- **Security impact triage**: `high`.
- **Dedicated security review required**: `yes`.
- **Triage rationale**: the candidate may change authentication, JWT,
  cryptography, multipart parsing, XML/HTML parsing, HTTP clients, and build
  tooling in internet-facing services and production containers.
- **Security review artifact**:
  [artifacts/20260715_security_review.md](artifacts/20260715_security_review.md).

## References

- `.github/dependabot.yml` - update ecosystems and directory grouping.
- `docker/requirements*.txt` - primary container Python dependencies.
- `services/cao/pyproject.toml` and `services/cao/uv.lock` - CAO runtime.
- `wepppy/weppcloud/static-src/package*.json` - primary frontend tests/build.
- `services/cap/package*.json` and `weppcloud-ui-lab/package*.json` - auxiliary
  Node applications.

## Deliverables

- [PR decision matrix](artifacts/pr_decisions.md): 35 merge, one defer, and one
  close/recreate recommendation across all 37 frozen heads; both non-merge PRs
  are now closed.
- [Validation evidence](artifacts/validation.md): clean installs, npm/CAO gates,
  no-cache image builds, local stack recreation/health, and pytest results.
- [Security review](artifacts/20260715_security_review.md): pass for the
  35-update merge candidate with security fixes prioritized.
- Completed ExecPlan under `prompts/completed/`.

## Follow-up Work

- Migrate the base image and native libgdal stack before adopting GDAL 3.13 in
  #570.
- Close/recreate #576 as a current coordinated Docker FastAPI/Starlette update.
- Repair the Daymet test's incomplete synthetic Flask stub so canonical full
  collection does not depend on test order.
- Materialize required ignored WEPP fixtures for detached-worktree test runs.

## Merge and Local Rollout

At 2026-07-15 20:07 UTC, the owner authorized merging all 35 reviewed merge
recommendations, rebuilding/redeploying the local development stack, and
rerunning the npm, CAO, health, and Python gates. The completed rollout is
archived at
`prompts/completed/dependabot_merge_local_rollout_execplan.md`; #570, recreated
#586, and #576 remain excluded and closed.

The rollout incorporated every reviewed intent. GitHub reports 34 reviewed PRs
as merged. Dependabot auto-closed #564 as superseded by unreviewed #587 during
the merge sequence, so the exact reviewed #564 head was retained as a merge
parent and `master` contains Mistune 3.2.1. Newly opened #587-#589 were not
substituted into the frozen review set.

The merged `master` produced no-cache WEPPcloud and CAP images, recreated all 26
long-running local services, and passed health and idle-worker checks. Static
npm lint and all 629 tests passed; UI lab lint/build, CAP smoke, and all 20 CAO
tests passed. The full controlled Python run passed 4,897 tests with 58 skips.
The canonical wrapper still stops during collection on the preexisting Daymet
synthetic-Flask defect documented in `artifacts/validation.md`.
