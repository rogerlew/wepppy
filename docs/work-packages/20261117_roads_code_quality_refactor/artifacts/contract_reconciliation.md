# RUPC-02 acceptance reconciliation

Date: 2026-11-17 UTC. Base: `96555f2f95326350d2d7007c19327378ea831ab0`.

## Authority and scope

The operator answered “Yes—use RUPC-02 as authority” to the explicit proposal to
reconcile the older validation-suite contract and test guidance, preserving
rejection when road plus fill exceeds hillslope length. The current
`docs/schemas/roads-unrutted-strip-contract.md` remains the scientific authority.
The stale `docs/schemas/roads-validation-suite-contract.md` negative-control
section and `tests/roads/README.md` are reconciled to that existing behavior.

No production behavior, defaults, geometry formula, queue, schema, security
boundary or parameterization changes are authorized by this reconciliation.
Historical published artifacts stay unchanged. Current-policy project harness
updates and fresh native output evidence are still required; no prior report is
recertified by replacing hashes or wording.

## Compatibility and regression plan

Preserve historical inspectability and source fixtures. A current-policy baseline
must declare exact geometry/membership before native execution, verify top-placed
and exact-fit successes, and preserve explicit road/fill fit failures with no
current receipt. Validate manifest role order, placement marker, area readback,
PASS/watershed output and retry/publication semantics. Do not assume historical
OSUNUM6 exclusion yields a valid current positive control.

## Reviews

Independent read-only reviewers `roads_explore` and `roads_contract_review`
accepted the reconciliation on 2026-11-17, with no medium/high findings. The
second review requested that the README also name the opt-in pytest suite as
pending reconciliation; that clarification is included. Reviews cover the
contract/documentation checkpoint only, not implementation or native evidence.
The standalone checkpoint commit is identified in the tracker after creation.
