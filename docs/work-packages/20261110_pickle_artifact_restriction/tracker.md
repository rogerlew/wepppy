# Tracker - Pickle artifact restriction

> Living status, decisions, risks, and handoff record for F2/SEC-02.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-11-11 03:50 UTC  
**Current phase**: M1 focused failing regressions  
**Last updated**: 2026-11-11 03:50 UTC  
**Next milestone**: ratify and checkpoint the restriction contract  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `artifacts/20261110_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Amend Bootstrap and browse canonical contracts with the approved rule.
- [ ] Obtain two independent contract reviews and commit the ancestor checkpoint.
- [ ] Add focused Bootstrap suffix rejection tests.
- [ ] Add browse preview/listing/files API/D-Tale bridge restriction tests.
- [ ] Add direct D-Tale loader/dispatch restriction tests.
- [ ] Remove pickle readers and capability advertisements.
- [ ] Update browse and D-Tale docs plus D-Tale stubs.
- [ ] Run only the approved focused tests, stub checks, and docs lint.
- [ ] Complete independent correctness, QA/code, and security reviews.
- [ ] Perform a scoped deployment smoke when rollout is authorized.

### In Progress

- [ ] Contract decision and failure-class matrix are ready for review.

### Blocked

- [ ] Implementation is gated, not externally blocked: the contract-first
      checkpoint has not yet been reviewed and committed.

### Done

- [x] Operator selected suffix restriction, raw legacy download preservation, and
      focused validation without the full suite (2026-11-11 03:50 UTC).
- [x] Confirmed two request-time pickle readers and their advertised browse/D-Tale
      entry points (2026-11-11 03:50 UTC).
- [x] Scaffolded package, ExecPlan, decision, matrices, and review gates
      (2026-11-11 03:50 UTC).

## Timeline

- **2026-11-11 03:50 UTC** - Package opened for the operator-requested F2 fix.
- **2026-11-11 04:08 UTC** - Contract checkpoint ancestor `aeab3c3e1`; both independent reviews approved.
- **Pending** - Focused implementation and validation.
- **Pending** - Scoped rollout and closeout.

## Decisions Log

### 2026-11-11 03:50 UTC: Restrict rather than convert

**Context**: Request-time pickle parsing can execute code. The operator sees no
need for a migration or broad artifact redesign.

**Decision**: Reject `.pkl`/`.pickle` in Bootstrap and remove their interactive
parsers. Existing files remain listable and downloadable as bytes.

**Impact**: No legacy deletion, conversion, content scanner, or replacement
format enters this package.

### 2026-11-11 03:50 UTC: Focused validation only

**Context**: The implementation affects small suffix-dispatch surfaces and has
direct tests.

**Decision**: Run changed-surface Bootstrap, browse, D-Tale, stub, documentation,
and source-search checks. Do not run the full Python or frontend suites.

**Impact**: Package closure must not list a full-suite pass, and reviewers must
assess the focused matrix rather than request broad testing without new evidence.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| One pickle reader remains reachable | High | Medium | Failure-class search and zero-call assertions | Open |
| Mixed-case suffix bypass | High | Low | Lowercase suffix tests at each boundary | Open |
| Legacy raw download breaks | Medium | Medium | Byte-equality download test | Open |
| D-Tale bridge forwards before reject | High | Low | Reject before materialization/HTTP spy | Open |
| Allowed tabular formats regress | Medium | Low | CSV/Feather/Parquet controls | Open |
| Documentation advertises pickle | Low | Medium | Scoped capability search and docs lint | Open |

## Hardening Signal Log

- **Baseline health signal**: allowed previews and Bootstrap inputs work.
- **Baseline danger signal**: two request-time `read_pickle` call paths exist.
- **Post-change signals**: pending focused validation.
- **Temporary callus register**: none.
- **Recurrence trigger**: any request-time pickle reader or advertised pickle
  preview/D-Tale capability creates a new incident record.

## Verification Checklist

### Contract and Security

- [ ] Contract checkpoint precedes implementation edits.
- [ ] Every request-time pickle consumer has a disposition.
- [ ] No unsafe deserialization or hidden fallback remains.
- [ ] Raw download behavior is explicitly preserved.
- [ ] Security and correctness artifacts have no unresolved medium/high findings.

### Approved Focused Validation

- [ ] `wctl run-pytest tests/weppcloud/bootstrap/test_pre_receive.py --maxfail=1`
- [ ] `wctl run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_files_routes.py --maxfail=1`
- [ ] `wctl run-pytest tests/microservices/test_browse_dtale.py tests/microservices/test_dtale_freshness.py --maxfail=1`
- [ ] Applicable `wctl run-stubtest` and `wctl check-test-stubs` checks.
- [ ] Scoped docs lint and spelling preview.
- [ ] Source/capability search shows no request-time pickle support.
- [ ] Full Python suite intentionally not run per operator decision.
- [ ] Frontend suite intentionally not run unless frontend source changes.

### Deployment

- [ ] Exact candidate revision and changed services are recorded.
- [ ] Scoped wepp1 Bootstrap rejection, 415, listing, and download controls pass.
- [ ] Rollback does not restore request-time pickle loading.

## Progress Notes

### 2026-11-11 03:50 UTC: Source review and scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Confirmed Bootstrap's NUL check does not establish pickle safety.
- Confirmed browse preview and D-Tale are the two request-time pickle readers.
- Identified preview metadata, directory links, bridge admission, D-Tale dispatch,
  documentation, and stub surfaces that must stay consistent.
- Created the work package without changing runtime code or production systems.

**Blockers encountered**: none for scaffolding. Implementation awaits the
contract-first ancestor checkpoint.

**Next steps**:

1. Amend and review canonical contracts.
2. Commit the contract checkpoint.
3. Implement tests first, then the smallest suffix restriction.

**Test results**: docs validation only for this scaffold; runtime tests were not
warranted before implementation.

## Handoff Summary

**From**: Codex  
**To**: implementation owner after checkpoint  
**Date**: 2026-11-11 03:50 UTC

The approved behavior and validation scope are fixed. Do not expand into pickle
migration, generic content scanning, internal serialization, or the full test
suite without new evidence and an explicit scope decision.
