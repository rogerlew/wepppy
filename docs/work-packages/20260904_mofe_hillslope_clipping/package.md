# Multiple-OFE Hillslope Clipping

**Status**: Open (2026-09-04)
**Timezone**: UTC

## Overview

Make the WEPP hillslope clipping option effective for multiple-OFE hillslopes.
The configured clip length will cap each OFE independently while preserving
the representative area of the complete hillslope.

## Objectives

- Apply `clip_hillslope_length` per OFE when `clip_hillslopes` is true.
- Preserve total representative hillslope area by scaling shared width.
- Explain per-OFE semantics in the WEPP advanced options and user docs.
- Deploy to development host `forest` and run local `dainty-signature` through
  rq-engine with a 60 m clip length.

## Scope

### Included

- Slope-file clipping utility and multi-OFE WEPP preparation wiring.
- Regression tests for generated slope files and preparation behavior.
- Canonical contract, ADR, UI copy, user/developer documentation.
- Local gates, Forest deployment, rq-engine submission, and generated-output
  inspection.

### Explicitly Out of Scope

- Changing the default clip length.
- Renaming request or persistence fields.
- Changing OFE segmentation or management/soil generation.
- Deploying to forest1 or WEPPcloud production.

## Stakeholders

- **Primary**: WEPPcloud model operators and users of multiple-OFE projects.
- **Reviewers**: two contract reviewers and one final correctness reviewer.
- **Security Reviewer**: required for the transformed run-tree file boundary.
- **Informed**: WEPPpy maintainers.

## Success Criteria

- [ ] Mixed-length multi-OFE fixtures cap every long OFE at the configured value.
- [ ] Generated width preserves original total area.
- [ ] Disabled clipping leaves source geometry unchanged.
- [ ] UI and user documentation state that the limit is per OFE.
- [ ] Focused and broad quality gates pass.
- [ ] Forest rq-engine run of `dainty-signature` at 60 m finishes successfully.
- [ ] Every generated hillslope `p*.slp` OFE is at most 60 m; every source and
      generated pair preserves OFE count, profile/header fields, and area within
      the documented tolerance.

## Parameterization ADR Gate

- **Parameterization change present**: yes
- **ADR required**: yes
- **ADR link**: `docs/adrs/ADR-0048-mofe-per-ofe-hillslope-clipping.md`
- **Decision provenance captured**: yes

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: authorization and source-path selection remain
  unchanged, but the multi-OFE worker changes a directory-backed input copy
  into a transformed filesystem write and therefore crosses the default
  high-impact file/path threshold.
- **Security review artifact**: `artifacts/2026-09-04_security_review.md`

## Compatibility and Regression Plan

The existing persisted keys and rq-engine aliases remain unchanged. The change
is additive for multiple-OFE execution: enabled runs intentionally receive
clipped generated inputs; disabled runs retain copy behavior. Unit tests cover
the parser/transform boundary, integration tests cover multi-OFE prep wiring,
and Forest acceptance compares every source/generated slope pair before result
acceptance. Direct unmocked tests cover directory-backed success, archive-only
and mixed-root rejection, malformed input, injected write/replace failures,
prior-destination preservation, and hardlink de-aliasing/source immutability.

## References

- `docs/ui-docs/contracts/wepp-hillslope-clipping-contract.md`
- `docs/adrs/ADR-0048-mofe-per-ofe-hillslope-clipping.md`
- `wepppy/topo/watershed_abstraction/slope_file.py`
- `wepppy/nodb/core/wepp.py`
- `wepppy/weppcloud/templates/controls/wepp_pure_advanced_options/clip_hillslopes.htm`

## Deliverables

To be completed at closure.

## Closure Notes

To be completed after Forest generated-output acceptance.
