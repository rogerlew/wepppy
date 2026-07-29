# SURF-18 Security Review

**Risk**: high
**Reviewer**: independent security reviewer
**Status**: passed; no unresolved findings

## Scope

The review covers DEVAL run authorization and CAP ordering, PUP-scoped job
tracking, tracked-job ownership, polling and error rendering, report and log
path confinement, worker execution, and generated artifact access.

## Findings and Disposition

The first review found one high and two medium issues:

- PUP job tracking used the active directory basename as its Redis identity,
  allowing equal PUP leaf names under different parent runs to collide. Tracking
  now uses the unique parent-run `RedisPrep`, a lossless config/PUP field key,
  and exact function/run/config/active-root validation before reuse.
- the shared blueprint preprocessor resolved filesystem context before the
  DEVAL CAP and authorization gates. WEPPcloudR routes already resolve their own
  contexts, so that blueprint was removed from eager preprocessing. PUP 404
  messages no longer disclose absolute paths.
- symlinked report directories, artifacts, or logs could escape the active run
  root. Route and worker paths now reject symlinked components and artifacts
  before read, write, unlink, or subprocess execution.

Regression tests cover two parent runs with the same PUP path, lossless keys,
function/run/config/active-root ownership mismatches, real registered-route CAP
ordering, non-sensitive PUP errors, and route/worker export, report, stdout, and
stderr symlink rejection.

## Final Gate

Independent post-fix review confirmed all original high and medium findings
closed. Its remaining low evidence observation was resolved by expanding the
ownership, PUP disclosure, and symlink parametrizations. Focused validation
passes 157 Python tests and 5 Jest tests. No unresolved security finding remains.
