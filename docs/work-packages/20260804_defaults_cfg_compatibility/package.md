# Defaults CFG Compatibility (WP01)

**Status**: Closed (2026-08-26)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate

## Overview

WP01 moves the shared NoDb defaults source to its canonical `_defaults.cfg`
name without breaking legacy projects, archives, deployed readers, or rollback
revisions that still open `_defaults.toml`. It adds the ratified project-local
and shared four-name precedence before any project-owned config writer exists.

## Objectives

- Move the tracked shared defaults content to `_defaults.cfg` and retain
  `_defaults.toml` only as a relative compatibility symlink.
- Implement project-local `_defaults.cfg`, project-local `_defaults.toml`,
  shared `_defaults.cfg`, shared `_defaults.toml` precedence.
- Update direct consumers and normalization checks to use the canonical source.
- Prove effective-value parity, explicit missing-file failure, older-reader
  compatibility, config-token persistence, and development-stack operation.

## Scope

### Included

- `wepppy/nodb/base.py` defaults-name resolution and public helper behavior.
- The shared defaults rename/symlink under `wepppy/nodb/configs/`.
- Direct consumers in setup discovery, profile recording, and the root-resource
  migration utility.
- Focused compatibility tests, documentation, and local Forest-gate evidence
  for later consumption by WP11.

### Explicitly Out of Scope

- Flattened project-config detection, manifests, and nested/PUP authority
  (WP02).
- Registry composition and serialization beyond preserving WP00B behavior
  (WP03).
- Any project-owned config writer or feature-flag enablement (WP04+).
- Forest deployment or production promotion (WP11/WP12).

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful migration of current defaults-plus-preset
  behavior.
- **Authoritative source paths**: `wepppy/nodb/base.py` and
  `wepppy/nodb/configs/_defaults.toml` at starting revision `c45726072`.
- **Cutover proof required**: current readers select the canonical shared file,
  legacy readers open the symlink, and the restarted dev stack loads configs.
- **Acceptance evidence type**: both fixture and development-stack evidence.

## Owned Requirements

- PC-02 and PC-03.
- `WP01-PC02-N017`, `WP01-PC02-N018`, `WP01-PC02-N019`,
  `WP01-PC02-N020`.
- `WP01-PC03-N099`, `WP01-PC03-N100`.
- `WP01-PC02-R004` through `WP01-PC02-R008`.
- `WP01-PC03-R009` and `WP01-PC02-R010`.

## Compatibility and Regression Plan

This is a project configuration schema-path mutation, not a value mutation.
Existing config tokens and serialized NoDb payloads remain unchanged. The
reader will select the first existing path from the ratified four-name order;
opening the selected file retains the existing explicit `FileNotFoundError` or
parser error rather than masking it. Tests will exercise each precedence row,
defaults-plus-local layering, shared fallback, a missing-both-shared failure,
the relative symlink through a deliberately old hard-coded reader, and JSON
payload inspection showing no defaults basename. WP00B typed parsing will prove
the renamed shared bytes remain semantically and lexically identical. Direct
consumer tests and a restarted development stack provide downstream evidence;
no generated `wepp/runs/*` artifact changes are expected because this package
changes configuration discovery only and does not alter parameter values.

## Success Criteria

- [x] Canonical `_defaults.cfg` and relative `_defaults.toml` symlink are
  present with byte-identical content through either path.
- [x] The full four-name precedence and legacy layering matrix passes.
- [x] Missing/malformed defaults retain explicit failures.
- [x] Direct consumers use canonical resolution without embedding a defaults
  basename in persisted NoDb state.
- [x] Focused, NoDb, full-suite, docs, and development-stack checks pass.
- [x] WP11 receives exact defaults compatibility evidence; no writer is
  enabled.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes
- **Rationale**: only file naming and resolution precedence change; the shared
  defaults bytes and effective parameter values remain unchanged.

## Dependencies

- **Depends on**: WP00R contract ratification.
- **Available prerequisites**: WP00A secret sanitization and WP00B canonical
  source normalization are complete on the initiative branch.
- **Blocks**: WP02 reader foundation and the later WP11 acceptance gate.

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: no auth, secret, route, queue, upload, subprocess, or
  external-input boundary changes; missing files continue to fail explicitly.

## References

- `docs/schemas/project-owned-config-contract.md` sections 6.2, 6.3, 14.1-14.3,
  and 15.
- `docs/schemas/project-owned-config-implementation-roadmap.md` WP01.
- `docs/work-packages/20260804_project_config_contract_ratification/artifacts/normative_requirement_checklist.md`.

## Deliverables

- Canonical shared defaults file and compatibility symlink.
- Dual-name resolver and updated direct consumers.
- Defaults compatibility regression suite and dev-stack evidence.
- Completed tracker and archived ExecPlan.

## Follow-up Work

- WP02 consumes PC-02/PC-03 and WP11 evidence but owns flattened-reader and
  manifest behavior.

## Closure Notes

**Closed**: 2026-08-26

**Summary**: WP01 faithfully moved the canonical shared defaults source to
`_defaults.cfg`, retained the old name as one relative symlink, and implemented
the contract's permanent project-local and compatibility-period shared
precedence. Direct consumers and WP00B tooling now use canonical resolution.
The package also prevented `_defaults` from entering the named-preset catalog,
closed the touched stub surface, and passed the full repository suite.

**Evidence**:
`artifacts/2026-08-26_defaults_compatibility_evidence.md` and
`artifacts/2026-08-26_correctness_review.md`.

**Implementation revision**: `a5d0367d7`.

**Promotion state**: implemented on `feature/project-owned-config`; not Forest
accepted and not promoted to `master`. WP11 owns deployed Forest and rollback
evidence.

**Lessons Learned**: suffix migrations can affect discovery globs even when
file bytes are unchanged. Reserved infrastructure basenames need an explicit
catalog boundary test.

**Archive Status**: package, evidence, and completed ExecPlan retained.
