# Generative Inputs Fuzzing Milestone 1: Wrapper Property Suite

**Status**: Implemented, pending review (2026-04-21 UTC)
**Timezone**: UTC

## Overview

Milestone 0 established binary-lane contracts, a canonical signature schema, and
historical replay validation for trap classification in `wepp-forest`.

This package defines and executes Milestone 1: property-based tests for wrapper
parse/validate/serialize contracts so binary-level fuzzing failures are
attributable to modeled state boundaries rather than wrapper corruption.

## Objectives

- Add Hypothesis-style property tests for wrapper boundaries that generate WEPP
  run artifacts.
- Enforce deterministic serialization for canonicalized wrapper inputs.
- Enforce explicit-failure behavior for malformed/unsupported wrapper states.
- Align wrapper contract checks with Milestone 0 signature schema assumptions.

## Scope

### Included

- Wrapper contract inventory for parse/validate/serialize pathways used by
  generated runs.
- Property-test suite design and implementation for canonical wrapper surfaces.
- Determinism assertions (same canonical input yields stable output payloads).
- Explicit-failure assertions (no silent coercions/fallbacks on invalid states).
- Documentation updates in this package and
  `generative-inputs-fuzzing/specs/parameter_contracts.md` (or equivalent).

### Explicitly Out of Scope

- Fortran routine guard changes.
- High-scale binary fuzz campaign execution (Milestone 3).
- Scientific parity adjudication.
- Climate-generator redesign.

## Stakeholders

- **Primary**: WEPP maintainers and WEPPcloud wrapper maintainers.
- **Reviewers**: Roger.
- **Informed**: Operators and maintainers running Milestone 2-4 campaigns.

## Success Criteria

- [x] Wrapper contract inventory completed with owner/source references.
- [x] Property test suite added for the selected wrapper surfaces.
- [x] Deterministic serialization contract validated in tests.
- [x] Explicit-failure contract validated in tests.
- [x] Milestone 0 replay validation remains green after wrapper-suite merge.
- [x] Work-package evidence and notes are complete for handoff.

## Dependencies

### Prerequisites

- Milestone 0 artifacts:
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/specs/milestone0_binary_lanes.md`
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/specs/canonical_result_schema.md`
  - `/home/workdir/wepp-forest/generative-inputs-fuzzing/scripts/classify_signatures.py`
- Access to wrapper implementation and tests in `wepppy` (cross-repo dependency).

### Blocks

- If wrapper entry points in `wepppy` are ambiguous, contract inventory cannot be
  finalized.

## Related Packages

- **Depends on**: Milestone 0 completion in this repo.
- **Related**: `docs/work-packages/20260421-wshpas-campaign-closeout/`.
- **Follow-up**: Milestone 2 (soil/landuse constrained generators) and Milestone 3
  (scale campaign + clustering).

## Timeline Estimate

- **Expected duration**: 1-3 days.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: test/invariant coverage for wrapper contracts only; no
  auth or network-surface changes.
- **Security review artifact**: `N/A`

## References

- `/home/workdir/wepp-forest/generative-inputs-fuzzing/README.md`
- `/home/workdir/wepp-forest/generative-inputs-fuzzing/specs/canonical_result_schema.md`
- `/home/workdir/wepp-forest/generative-inputs-fuzzing/specs/milestone0_binary_lanes.md`
- `/home/workdir/wepp-forest/tests/test_generative_signature_classifier.py`

## Deliverables

- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone1-wrapper-properties/tracker.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone1-wrapper-properties/prompts/active/milestone1_wrapper_property_execplan.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone1-wrapper-properties/artifacts/command_log.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone1-wrapper-properties/artifacts/property_inventory.md`
- `/home/workdir/wepp-forest/docs/work-packages/20260421-generative-fuzzing-milestone1-wrapper-properties/notes/review_*.md`

## Follow-up Work

- Milestone 2: constrained soil/landuse generator implementation.
- Milestone 3: campaign sharding, signature clustering, and minimization at
  scale.

## Closure Notes

To be completed when package is closed.
