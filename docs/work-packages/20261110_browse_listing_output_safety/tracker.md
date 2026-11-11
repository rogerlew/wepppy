# Tracker - Browse listing output safety

## Quick Status

**Timezone**: UTC  
**Last updated**: 2026-11-11 04:22 UTC  
**Current phase**: scaffolded; M0 contract checkpoint is next  
**Security impact**: high  
**Dedicated security review**: `artifacts/20261110_security_review.md`  
**Starting revision**: `c040d51d0`

## Task Board

- [x] Confirm F3 source evidence and production boundary (`wepp1`).
- [x] Scaffold package, active ExecPlan, failure-class inventory, and review gates.
- [x] Record the operator's focused-test decision and full-suite waiver.
- [x] M0: amend the canonical browse contract; obtain correctness and security
      review; retain a checkpoint before production-code edits.
- [ ] M1: add focused failing renderer/route regressions using real temporary
      filenames, directories, and symlinks.
- [ ] M2: implement contextual escaping and one-segment URL encoding; update
      directly affected documentation.
- [ ] M3: run only the approved focused tests and close correctness, QA, and
      security findings.
- [ ] M4: perform a separately authorized wepp1-equivalent rollout smoke and
      closeout. No production action is authorized by this scaffold.

## Decisions and Discoveries

- F3 is a stored same-origin XSS risk: `html_dir_list()` inserts filesystem names
  and symlink targets into HTML and URL attributes, and `_render_directory_response()`
  marks the assembled listing trusted.
- Filesystem-derived directory breadcrumbs repeat the same unsafe trust pattern
  and are included in the failure class. Query-encoded pagination and JSON APIs
  are not confirmed consumers and remain out of implementation scope unless a
  focused red test proves otherwise.
- The repair preserves valid names. It escapes display text and percent-encodes
  each name as one path segment; it does not add a Bootstrap filename allowlist.
- CSP is deferred to a separate package because it has site-wide compatibility
  and rollout concerns and cannot replace output encoding.
- The operator requires patch-scoped tests. The full Python and frontend suites
  are waived and must not be claimed as passing evidence for this package.

## Validation and Review

No runtime tests have been run because this turn only scaffolds the package. The
future validation receipt must list exact node IDs, red/green behavior, and the
implementation revision. At minimum it must retain direct route output for an
ordinary Unicode control and inert hostile filename, directory, action-link, and
symlink-target cases.

## Timeline

- 2026-11-11 04:22 UTC: source diagnosis and package scaffold.
- Pending: M0 contract amendment and independent review checkpoint.
- Pending: focused red/green implementation and validation.
- Pending: separately authorized rollout; no production change performed.

## Handoff

Begin with M0 in the active ExecPlan. Do not edit production code until the
canonical output-context rules and failure-class dispositions are reviewed. Keep
all tests limited to changed renderer/route surfaces. Preserve authorization,
containment, raw file access, actual filenames, and existing action behavior.

2026-11-11 M0: canonical amendment reviewed by independent correctness and
security agents; missing-path consumer confirmed and included. Scoped doc lint
passed (8 files). Required standalone checkpoint follows before code edits.
