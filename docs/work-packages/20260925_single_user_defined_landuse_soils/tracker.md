# Tracker — Single User-Defined landuse and soils

## Status

**Closed**: 2026-09-26 UTC. Implemented and validated; not deployed.
**Security impact**: high; independent runtime review approved with no unresolved findings.
**Completed plan**: [ExecPlan](prompts/completed/single_user_defined_landuse_soils_execplan.md).
**Contract**: [SUDI-01](../../schemas/single-user-defined-inputs-contract.md).

## Completed work

- [x] Trace dependencies and independently review the work-package design.
- [x] Resolve Builder policy, formats, source lifecycle, bounds and buffer exclusion.
- [x] Ratify canonical contract and ADR before runtime implementation.
- [x] Implement Builder serialization, capability resolution and refresh preservation.
- [x] Implement secure independent source uploads, modes, builders and preparation.
- [x] Add themed controls, guidance, escaped accepted filenames and reload transport.
- [x] Enforce Disturbed/SBS/dependent-feature and buffer exclusions at relevant boundaries.
- [x] Validate native inputs, real upload/RQ/source lifecycle and compatible legacy paths.
- [x] Close independent correctness, QA and security findings.
- [x] Complete repository coverage, correction runs and documentation closeout.

## Decision record

The operator selected a creation-time Builder checkbox instead of disturbed-class
selectors or legacy-config-only support. Landuse and soil mode selection remain
independent, while the checked project excludes Disturbed/SBS and dependent
features. Compatible modifiers remain available. The operator explicitly disabled
both buffer OFE geometry and buffer management overrides.

Initial support is management 98.4 and soil 7778, exactly one source OFE,
replicated to all hillslopes and up to 32 non-buffer OFEs with `wepp_260803`.
The pinned native reader does not preserve modern management 2016.3 fields, so
those inputs are rejected. Sources remain immutable; generated artifacts receive
compatible modifiers. Later deliberate class edits work; rebuilding mode 5
restores uniform assignment. Full rationale is in SUDI-01 and ADR-0075.

## Commits and evidence

- `cb09ab422`: complete initial worktree snapshot authorized by the operator.
- `0efd7ea46`: standalone contract and design-security checkpoint before code.
- `c1d02d73f`: implementation checkpoint; follow-up closeout contains final
  regression corrections and completed evidence.
- [Validation summary](artifacts/20260926_validation_summary.md): 353 passing tests
  across fourteen corrected modules, 919 Jest tests, native execution through 32
  OFEs, and exact broader-sweep outcomes.
- [Correctness review](artifacts/20260926_correctness_review.md),
  [QA review](artifacts/20260926_qa_review.md), and
  [security review](artifacts/20260925_runtime_security_review.md).
- Real accepted uploads/jobs, boundary conflicts, publication recovery,
  archive/restore, fork and authenticated download hashes are retained in the
  adjacent acceptance JSON/log artifacts.
- Chromium verifies rendered controls, filename feedback, chooser selection and
  Tab reachability across three themes.

## Retained limits

No uninterrupted full-suite pass or production deployment is claimed. Existing
management stub debt and two optional real-WBT diagnostics failures are recorded
separately. A preexisting generic fork defect affects destinations containing the
source run name; an unrelated destination passed functional summary reads.

Environment acceptance uses real NoDb/Redis/filesystem and worker identities with
controlled topology/climate. Browser checks use real rendered control partials,
not a full authenticated Build session. The validation summary distinguishes
these boundaries from API, controller and generated-file evidence.
