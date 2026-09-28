# SUDI-03 preimplementation correctness review

Reviewer: independent correctness agent. Date: 2026-09-28.
Scope: canonical SUDI-03 contract/ADR, package decision and active plan; no
production implementation edits reviewed or made.

## Finding and disposition

One documentation clarification was identified before implementation. The original
contract rejected “inputs invoking silent numeric repair,” but the supplied
`/tmp/boulderck_mica_1_7777.sol` includes a 2400 mm bottom horizon. Native
`input.for` caps depth at 1800 mm and performs its existing deepest-layer
processing. Clarify that forbidden repair means WEPPcloud parser repair; native
format calculations/clamps remain active. Preserve 2400 in prepared input and
retain native behavior. Do not reject the operator's otherwise valid fixture or
promise unchanged native internal state.

Resolved: the canonical contract now explicitly distinguishes WEPPcloud parser
repair from native calculations and its 1800 mm depth cap, admitting deeper valid
sources without rewriting generated input. The checkpoint records that decision
and acceptance of the exact supplied source.

Verdict: approved. No unresolved preimplementation findings.

## Evidence and acceptance expectations

- `/home/workdir/wepp-forest/src/input.for:479` reads eight header fields for
  superuser formats; line 541 reads exactly ten 7777 layer fields; line 638
  reads restrictive flag, profile anisotropy and conductivity. Version 7777
  has neither per-layer anisotropy nor avke.
- Existing WSU parsing uses the same shape and restrictive semantics. Its
  preserving serializer currently groups versions below 7778 with six-field
  layers, so explicit version branching is necessary. Default catalog paths
  must remain unchanged.
- The supplied 243-byte CRLF file contains one OFE, two increasing horizons,
  nondefault explicit hydraulics and restrictive record `1 10 0.46`. It is a
  suitable real regression fixture, including its 2400 mm authored depth.
- Additive admission reuses existing upload state/error, auth, immutable-source,
  modifier and synthesis contracts; no schema or queue changes are needed.
- Approval of implementation requires exact generated ten-field comparisons and
  profile anisotropy preservation, source hash checks, real upload publication,
  native 1/2/12/32-OFE execution, and compatible modifier cases. Include malformed
  widths, bounds, layer counts and existing-version regression coverage. Native
  success alone does not prove supplied fields reached the generated file.
