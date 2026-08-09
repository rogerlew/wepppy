# Security Review - Durable Topanga Peak-Flow Census Preparation

## Metadata

- **Package**: `docs/work-packages/20260808_peakflow_topanga_census_prep/`
- **Reviewer**: Codex implementation security review
- **Date**: 2026-08-09
- **Scope reviewed**: implemented manifest, filesystem, artifact, terminal
  recovery, and subprocess surfaces
- **Commit/branch context**: current `master` worktree
- **Related artifacts**:
  - Code review: `artifacts/20260809_code_review.md`
  - QA review: `artifacts/20260809_qa_review.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the planned reusable CLI accepts source/evidence paths,
  creates run trees, and invokes a selected WEPP binary.
- **Threat model assumptions**:
  - The tool is a local developer/operator CLI, not a public service.
  - Scenario authorities and approved binary roots are explicitly declared.
  - Study manifests may be malformed and must not expand filesystem or process
    authority.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Review gate | Implementation was unavailable in the initial review | Generated implementation and tests | Complete all surface checks before GO | Resolved |
| SEC-02 | High | Recovery | Early failures initially lacked a stopped terminal | Retry-binding regression test | Persist stopped records and preserve prior attempts | Resolved |
| SEC-03 | Medium | Executable | First plan named an unresolved binary locator | Accepted build hash and existing clean worktree | Generate a new content-bound plan with the verified locator | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: preparation GO is permitted after remaining QA
  and documentation gates pass

## Required Surface Checks

- [x] Canonicalized source reads stay within declared read-only authorities.
- [x] Evidence writes stay within the declared evidence root.
- [x] Symlink traversal cannot escape either root.
- [x] Executable identity is pinned by path and SHA-256.
- [x] Subprocess execution uses an argument vector with `shell=False`.
- [x] Manifests cannot inject environment variables, shell text, or arbitrary
  commands.
- [x] Partial failures leave explicit terminal records and do not authorize
  completeness.
- [x] Logs and committed artifacts contain no secrets or unrelated file data.
- [x] No network, queue, auth, session, CSRF, secret, or public route surface is
  introduced.
- [x] No new external dependency is introduced.

## Validation Evidence

- Automated checks: focused suite passes path escape, symlink escape, content
  identity, executable binding, terminal retry binding, and explicit-selection
  behavior.
- Manual checks: generated plan contains no routing concepts; bounded execution
  used the pinned binary through direct `subprocess.run` with no shell; the
  full-census evidence root has no terminal or outcome artifact.

## Residual Risk

- **Accepted residual risks**: the tool is a local operator CLI and trusts an
  authorized user to choose manifest and output file locations. Model evidence
  writes remain constrained by the manifest evidence root.
- **Follow-up packages/issues**: the execution package inherits all unresolved
  findings and may not start with a failed preparation review.

## Sign-off

- **Security reviewer**: Codex, 2026-08-09
- **Package owner**: requesting operator, decision recorded 2026-08-09
