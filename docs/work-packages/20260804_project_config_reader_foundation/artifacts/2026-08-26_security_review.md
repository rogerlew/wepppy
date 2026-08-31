# Security Review - WP02 Reader Foundation

## Metadata

- **Package**: `docs/work-packages/20260804_project_config_reader_foundation/`
- **Reviewer**: Codex, dedicated post-implementation security pass
- **Date**: 2026-08-26
- **Scope reviewed**: config/manifest reads, parent containment, symlinks,
  sanitization, structured logging, and persistence noninterference
- **Commit/branch context**: uncommitted WP02 tree on
  `feature/project-owned-config` after `ceb10fc96`
- **Related artifact**: `artifacts/2026-08-26_correctness_review.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: this package changes which run-scoped files become
  configuration authority and handles potentially hostile paths/manifests.
- **Threat model assumptions**: run artifacts may be damaged or replaced; a
  nested persisted parent may be stale/hostile; logs may be accessible beyond
  the project owner; shared source files remain deployment-managed.
- **Valid states controls must preserve**: absent/default-off, valid legacy,
  valid flattened, missing/invalid manifest degradation, digest mismatch, and
  contained parent inheritance.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Config path | A direct-child filename can be a symlink to a config outside the authority root. | adversarial fixture | Resolve the flattened candidate and require its parent to equal the authority root. | Resolved |
| SEC-02 | High | Manifest path | A manifest symlink could read provenance outside the authority root. | adversarial fixture | Treat an escaping manifest as invalid without reading it as authority. | Resolved |
| SEC-03 | High | Nested containment | Legacy string-prefix containment accepts sibling `/run2` under `/run`. | prefix-collision fixture | Use `Path.resolve().relative_to()` and reject non-ancestors. | Resolved |
| SEC-04 | Medium | Logging | Digest/config contents could leak through warnings or repeated access. | structured-warning test | Allowlist code/run/filename/digests and deduplicate per controller. | Resolved |
| SEC-05 | Medium | Manifest secrets | Unknown forward-compatible fields could carry credentials. | secret-bearing manifest fixture + WP00A scanner | Run the redacted recursive scanner before accepting schema fields. | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship dormant; no writer or production activation

## Surface Checks

### Valid-state and user experience

- [x] Correctness review separates absent, populated, legacy, and hostile states.
- [x] Containment controls preserve child-local legacy and valid parent inheritance.
- [x] New exceptions are limited to malformed/unsupported/hostile authority states.
- [x] Direct real-file tests cover accepted and rejected boundaries.

### Auth, secrets, and input/output safety

- [x] No route/auth/session surface changes.
- [x] No secret defaults, argv, queries, or raw artifact values enter logs.
- [x] Manifest scanning rejects secret-bearing and runtime-host-bound material.
- [x] Schema, booleans, versions, filenames, timestamps, collections, and digests are validated.
- [x] Traversal through parent context and direct artifact symlinks is rejected/degraded.

### Filesystem, workers, dependencies, and integrity

- [x] The implementation contains no write, temporary artifact, cleanup, or permission path.
- [x] Config authority is a direct child of one validated root.
- [x] No queue, subprocess, network, agent-tool, CI/CD, or dependency change exists.
- [x] NoDb locking/dump/Redis behavior is unchanged; status fields are transient.
- [x] Failures are explicit and no broad exception handler was added.

### Logging and rollback

- [x] Warning fields are sufficient for triage without config contents/secrets.
- [x] Equivalent per-controller warnings are deduplicated.
- [x] The absent reader flag is a rollback/containment boundary; WP11 owns deployed proof.

## Validation Evidence

- Focused WP02: 38 passed.
- NoDb: 1,699 passed, 26 skipped.
- Stubtest and stub completeness: passed.
- Broad-exception enforcement and diff check: passed.
- Full suite and docs lint are recorded in the main evidence artifact at closure.

## Residual Risk

- Deployed mixed-version behavior and rollback are intentionally unproven in
  WP02 and remain a blocking WP11 gate before flag activation.
- Authenticated header disclosure/deduplication is not implemented here; WP09
  must expose only the immutable allowlisted status.

## Sign-off

- **Security reviewer**: Codex, 2026-08-26
- **Package owner**: Codex, 2026-08-26
