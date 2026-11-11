# Tracker - Query-engine run access boundary

> Living status, decision, risk, and handoff record for F1/SEC-01.

## Quick Status

**Timezone**: UTC

**Started**: 2026-11-11 01:03 UTC

**Current phase**: M2/M3 implemented; M4 review fixes and validation

**Last updated**: 2026-11-11 02:12 UTC

**Next milestone**: close local reviews and validate browser/ingress

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**: `artifacts/20261110_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Decide whether wepp1 needs immediate Caddy containment before the code fix.
- [x] Ratify the access/state matrix and explicit activation behavior.
- [x] Amend canonical query-engine, session-token, and browser-mutation contracts.
- [x] Obtain two independent contract reviews and commit the ancestor checkpoint.
- [x] Add failing route, resolver, token, side-effect, and valid-state regressions.
- [x] Implement strict identifier resolution and pre-side-effect authorization.
- [x] Add the query-engine-scoped HttpOnly browser token path.
- [x] Restrict activation method/authority and query-engine CORS.
- [ ] Run focused, broad, browser, Compose/Caddy, and artifact readback gates.
- [ ] Complete independent correctness, QA, code, and security reviews.
- [ ] Validate on forest/equivalent and deploy to wepp1 only when authorized.

### In Progress

- [ ] Independent review fixes, expanded compatibility tests, broad gates and
      browser/environment evidence.

### Blocked

- [ ] Production deployment requires separate operator authorization after
      candidate validation; no production action has been taken.

### Done

- [x] Fetched GitHub `origin`; `origin/master` advanced to `ef5b4e289`
      (2026-11-11 00:59 UTC).
- [x] Confirmed F1 source evidence and direct wepp1 ingress
      (2026-11-11 01:03 UTC).
- [x] Scaffolded package, ExecPlan, matrices, and initial review gates
      (2026-11-11 01:03 UTC).

## Timeline

- **2026-11-11 00:59 UTC** - `git fetch --prune origin`; no merge, checkout, or
  branch creation.
- **2026-11-11 01:03 UTC** - Package opened for the operator-requested F1 fix.
- **2026-11-11** - Operator approved revised contract; checkpoint `2f9401f93`.
- **Pending** - Local implementation and validation.
- **Pending** - Forest/equivalent acceptance and wepp1 rollout.

## Decisions Log

### 2026-11-11 01:03 UTC: Interpret F1 as SEC-01

**Context**: The local audit ranked finding 1 as the query-engine ordinary-run
authorization and filesystem-path bypass.

**Decision**: This package fixes only that finding and restates its evidence in
tracked artifacts.

**Impact**: F2-F8 remain out of scope and cannot be bundled into this patch.

### 2026-11-11 01:03 UTC: Preserve direct query-engine calls

**Context**: The nearest WEPPcloud instructions prohibit a Flask response proxy.
Private browser queries currently call Starlette directly, while the existing
HttpOnly run cookie is path-scoped under `/weppcloud/runs/`.

**Decision**: Reuse the existing JWT/session-marker protocol and add a dedicated,
least-privilege query-engine cookie path. Do not expose tokens to JavaScript and
do not add a proxy or identity service.

**Impact**: Browser compatibility is a first-class acceptance gate, not an
afterthought to route denial tests.

### 2026-11-11 01:03 UTC: Fetch without integrating

**Context**: The user requested a GitHub fetch, not a pull, merge, rebase, or new
branch.

**Decision**: Record fetched `origin/master` at `ef5b4e289`; leave local `master`
at its existing revision and require implementation to reconcile deliberately.

**Impact**: The scaffold does not claim to include the two fetched commits.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Private data remains reachable before rollout | Critical | High | Decide immediate Caddy containment | Open |
| Valid owner queries fail after guard | High | Medium | Query-scoped cookie and browser matrix | Open |
| Composite or playback runs regress | High | Medium | Direct failure-class matrix coverage | Open |
| Denied requests still write catalog/log files | High | Medium | Assert hashes/absence before and after denial | Open |
| Token audience/path widens authority | High | Low | Exact audience, scope, path, SameSite, HttpOnly | Open |
| Application rollback restores exposure | Critical | Medium | Keep containment through rollback | Open |

## Hardening Signal Log

- **Baseline health signals**: authorized query behavior is operational, but
  private-denial evidence is absent and ordinary routes do not enforce it.
- **Post-change health signals**: pending.
- **Danger signals observed**: current resolver accepts filesystem forms; current
  ordinary guard is a no-op; direct browser token is not sent to query-engine.
- **Temporary callus register**: none. Record any Caddy block here with owner,
  introduction revision, and removal gate.
- **Softening experiments**: none until a temporary containment exists.

## Verification Checklist

### Contract and Scope

- [ ] Canonical contract decision approved and checkpointed before code edits.
- [ ] Feature-access package overlap is dispositioned without changing policy.
- [ ] Failure-class matrix covers every route and documented run form.

### Security and Correctness

- [ ] Security artifact has no unresolved medium/high findings.
- [ ] Correctness artifact has no unresolved medium/high findings.
- [ ] Unauthorized requests perform no catalog, dataset, or exception-log access.
- [ ] Valid public/owner/Admin/Root/service cases remain functional.
- [ ] Explicit activation cannot be triggered by GET or cross-origin cookie use.
- [ ] Exact CORS origins and token audience/scope/path are verified.

### Tests and Documentation

- [ ] `wctl run-pytest tests/query_engine --maxfail=1` passes.
- [ ] Focused WEPPcloud auth/cookie tests pass.
- [ ] Relevant browser tests pass through the real Caddy/Compose route.
- [ ] `wctl run-pytest tests --maxfail=1` passes or blockers are retained.
- [ ] Canonical docs and operator guidance are updated and lint clean.
- [ ] Code quality and broad-exception changed-file gates are recorded.

### Deployment

- [ ] Rendered wepp1 Compose and Caddy configuration match the reviewed candidate.
- [ ] Forest/equivalent public/private HTTP and artifact checks pass.
- [ ] Exact wepp1 candidate revision and deployment receipt are retained.
- [ ] Rollback preserves containment.
- [ ] Fourteen-day health/danger signal observation owner is named.

## Progress Notes

### 2026-11-11 02:12 UTC: Execute M0 contract preparation

Prepared `docs/schemas/query-engine-http-access-contract.md` and proposed
amendments to session, JWT, CSRF, composite IDs, feature governance, PCV and query
README. Two independent read-only reviewers identified pre-auth Omni writes,
parent-cookie transport failure, missing direct-entry minting, ownerless/PCV
compatibility, scenario symlinks and shared MCP parsing. The exact proposal
addresses these; implementation evidence remains pending.

The operator's execution request authorizes this work. The revised exact matrix
needs ratification because the scaffold left scope/activation choices open and
its path/cookie assumptions conflict with existing valid behavior. Next: finish
reviews and doc validation, present the concrete decision, then checkpoint it
before M1 source/test edits. Production containment/rollout remains separately
unauthorized. Fetched origin commits were inspected and do not overlap the
query boundary; no merge, checkout or branch change was performed.


### 2026-11-11 01:03 UTC: GitHub fetch and scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Fetched the authorized GitHub origin and recorded the two new remote commits.
- Re-read work-package, ExecPlan, security, correctness, contract-first,
  hardening, test, WEPPcloud, and Docker guidance.
- Confirmed the source path and documented the direct-browser token compatibility
  requirement.
- Created a tracked, self-contained scaffold. No production code, branch,
  production service, or live data was changed.

**Blockers encountered**: none for scaffolding. Implementation intentionally
awaits the contract-first checkpoint.

**Next steps**:

1. Review `artifacts/20261110_contract_decision.md` with the operator.
2. Amend canonical contracts and obtain two independent read-only reviews.
3. Commit that checkpoint as a standalone ancestor before implementation.

**Test results**: documentation validation only; runtime tests are not evidence
for a scaffold and were not run.

## Watch List

- Query-engine HTTP routes and MCP routes have different authentication layers;
  the fix must not regress the already-scoped MCP surface.
- `get_wd` supports legacy, playback, batch, culvert, and Omni layouts; an
  allowed-root shortcut can become either a compatibility bug or a tenant escape.
- Query reads can generate catalog state. "Read-only datasets" must not be used
  to justify authorization after activation.

## Handoff Summary

**From**: Codex

**To**: implementation owner after contract checkpoint

**Date**: 2026-11-11 01:03 UTC

**What's complete**: source diagnosis, exact M0 contract proposal, affected
canonical amendments and two passing independent contract reviews.

**What's next**: ratify the exact access contract; do not edit implementation
until the ancestor checkpoint required by the active ExecPlan exists.

**Open question**: should the wepp1 operator apply immediate Caddy containment
while the compatible application fix is prepared?

## M0 review result, 2026-11-11 01:26 UTC

Both independent reviewers approved the proposal for ratification/checkpoint,
with no open medium/high contract findings. See
`artifacts/20261110_contract_reviews.md` for reviewed digest and dispositions.
Runtime correctness/security findings remain open. Next action is exact operator
ratification of the revised decision, then the standalone ancestor commit.

M0 validation, 2026-11-11 01:29 UTC: package doc lint (8 Markdown files)
and all eight affected canonical/reference documents passed with zero errors
or warnings; `git diff --check` passed. Spelling preview found only existing
CSRF-contract differences, left untouched. Evidence: `artifacts/20261110_m0_doc_validation.txt`
(package-relative). No runtime tests were run because source/tests are unchanged.

Operator ratification, 2026-11-11 UTC: "I approve the revised contract. please
commit and proceed". Exact contract approved; checkpoint commit follows before
implementation. Production deployment is not authorized.

M0 complete: accepted standalone checkpoint ancestor `2f9401f93` committed
2026-11-11 UTC before implementation/test edits. M1 execution begins.


## Implementation and validation update (2026-11-11 UTC)

- Checkpoint ancestor `2f9401f93` precedes all source/test edits.
- M1/M2 implemented; direct browser cookie, exact CORS and POST activation paths
  implemented. Independent correctness/code/security and local QA findings closed.
- Focused release gate: 478 passed, 2 skipped; npm:124 suites/1069 tests passed;
  helper stubtest, stub hygiene and changed broad-exception gate passed.
- Full Python sanity gate is still running; do not infer completion from the
  focused suite. Final browser/environment gate remains in progress.
- Real forest login/direct-page cookie, owner query, public query, private denial
  and activation origin checks passed.100-run acceptance exposed existing URL
  and H11 incomplete-header buffering limits. Bounded, independently reviewed
  corrections and retained failure evidence are recorded in the ExecPlan Decision
  Log and the canonical HTTP operations guide. No production changes performed.
- Observe-only quality report lacks Radon and changed-file analysis; no complexity
  threshold conclusion is claimed.
