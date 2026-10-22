# Independent accounting contract review

## Verdict and scope

**APPROVED for the standalone contract checkpoint.** No unresolved high or
medium accounting findings remain. This approves intended behavior before
implementation, not a native build, generated result, release or deployment.

Reviewer: independent `accounting_contract_review` agent. Reviewed at
2026-10-22 20:59 UTC. Runtime files were read only; this review artifact is the
reviewer's sole edit. The reviewer did not author the canonical amendments.

Starting WEPPpy revision: `38df23fbf5696b9cc5b5cdbbd6f15fa297a5286e`.
Starting native revision: `3b630643ba06bd40262285f206112c9d3ee32b21`.
Those revisions still identify HEAD at review time. Unrelated native
calendar/HBP edits remain outside this review's implementation scope.

Reviewed the [canonical accounting contract](../../../schemas/roads-water-accounting-contract.md),
[ADR-0102](../../../adrs/ADR-0102-roads-modeled-area-accounting.md),
[checkpoint decision](20261022_contract_decision.md), package, tracker, active
ExecPlan, and amendments to output-scope, hillslope-water aggregation and Roads
specification. Their modeled-area rules agree; geographic ownership is no longer
a required input.

## Accounting and authority conclusions

The operator's full-MOFE and expanded-model-domain choices support
`B=max(A-C,0)` and `T=B+C`. Saturation removes exhausted baseline response while
retaining complete contributor areas. Expansion is explicitly modeled area,
not a determination of exterior geographic land. This remains a mixture of
existing responses, not a rerun of a physically changed residual hillslope.

Continuous WAT geometry and single-storm PASS geometry are now explicit ledger
authorities. Product-specific serialized source areas determine scaling against
the same represented-area ledger. Untouched PASS bytes and zero-road continuous
named water results retain their stated compatibility. Replacement target area
is the complete strip/remainder sum, with baseline excluded and existing
replacement precedence retained.

Native terminal reduction precedes target mapping. TotalWatSed retains original
source profiles for literal Q/QOFE and optional support-area joins. Dedicated
marked accounting WAT supplies physical Q/lateral and target area to the average
hillslope report. This resolves the earlier conflict between equivalent-profile
reporting and native diagnostic semantics.

## Disposition of earlier findings

| Finding | Severity | Final disposition |
| --- | --- | --- |
| Additive local-flux policy was unspecified | High | Resolved by operator-selected modeled-area mixture and ADR-0102; complete contributor local terms participate. |
| Replacement area and remainder accounting were undefined | High | Resolved: summed replacement MOFE areas define target area; no baseline or second subtraction. |
| Existing weighted PASS rejects valid Roads particle diameters | High | Resolved in intended contract: explicit Roads first-source header compatibility; AgFields remains strict. Actual UM1 baseline H27 class-4 diameter is 0.30600E-03 versus road H900001 0.40000E-03. |
| WAT/PASS precision could produce inconsistent weights | Medium | Resolved: continuous WAT authority, single-storm PASS authority, recorded product-specific areas/scales and existing native serialization readback budgets. |
| Equivalent WAT could change TotalWatSed diagnostics/support weights | High | Resolved: TotalWatSed reads original weighted profiles; the separate derived WAT is restricted to corrected aggregate reporting. |
| Earlier checkpoint still required geographic allocation | Medium | Resolved in current package, tracker, ExecPlan, decision artifact and ADR. Geographic audit remains historical evidence only. |
| Old/raw report cache could masquerade as corrected accounting | Medium | Resolved in intended contract: corrected readiness requires ledger/provenance/markers; cache fingerprints bind the accounting source hash. |

## State and input coverage required during implementation

The following are acceptance obligations, not claims of completed tests.

| Runtime state | Contracted outcome and required evidence |
| --- | --- |
| Roads never executed; no accounting artifacts | Existing workflow creates ledger and derived products during execution; no fabricated corrected-ready state. |
| Valid empty contributor manifest | Baseline-equivalent continuous named water quantities and unchanged canonical PASS. |
| Populated additive sources | Exercise C<A, C=A and C>A independently of OFE count; prove once-only PASS and consistent WAT weights. |
| Replacement strips/remainder; mixed designs | Exclude baseline and superseded additive sources; retain every contributing native terminal. |
| Optional absent, empty or partial diagnostics | Preserve admitted absence/null and valid-support semantics; no required-source fallback. |
| Supported historical outputs | Remain historical; corrected certification requires reconstruction and fresh routing. |
| Failed segment execution | Existing whole-run failure remains; intentional skips are distinct. |
| Malformed IDs, dates, geometry, terminal values or schemas | Explicit failure without corrected readiness; validate the actual native/filesystem boundary. |
| Corrected outputs followed by source or ledger drift | Reject stale corrected selection/cache even if timestamps match. |
| Generation in progress or failed | Preserve established working/failed visibility and inspectable retained evidence under normal project authorization. |
| Archived/restored corrected run | Existing archive/restore must retain ledger, source/provenance and derived products with byte equality; verify normal freshness/selection after restoration. |

Separate input dimensions include native OFE topology, particle-header
differences, optional columns versus partial observations, continuous versus
single-storm execution, target occupancy, replacement precedence, duplicate
source identity and output aliasing. No exhaustive implementation coverage is
claimed at this checkpoint.

## Remaining evidence and residual risks

Require native tests, WEPPpy consumer/cache tests, actual UM1 PASS reconstruction,
fresh watershed execution, complete daily/yearly and average-report readback,
and unchanged original hashes. Compare modeled-area propagation into the exact
PASS files consumed by watershed routing, not just ledger values or job success.

File selection and publication are security-sensitive. Dedicated security and
final correctness reviews remain required, including production-equivalent
identity, permissions and mounts at changed boundaries. Checkpoint approval does
not replace those reviews or the artifact-observability/archive obligations above.

Residual scientific limits are explicit: response mixing does not recompute
remaining-hillslope geometry, channel physics or geographic overlap. PASS Runoff
and physical WAT Q retain distinct meanings. Raw views intentionally remain raw
and must not be presented as corrected aggregate results.

The ancestor commit is not yet created. The parent must commit the approved
checkpoint and record its revision before editing covered runtime code. Final
review must verify that ancestry and the completed implementation evidence.

## Reviewed document fingerprints

These SHA-256 values bind approval to the reviewed numerical and compatibility
rules. Later substantive changes require renewed review.

| Document | SHA-256 |
| --- | --- |
| roads-water-accounting-contract.md | `2d8b71db7586a2cc39257bd351111d7469fb119794fb63de28a8b043190589ec` |
| ADR-0102-roads-modeled-area-accounting.md | `802354dd80715d1b89b0f8330e809efed9a19f60982ec3cc49192762351f2ddc` |
| output-scope-contract.md | `c960b25011f53b9d436ab1c4ecfac7bd5561892105cd16d4648c1b2c0e665c21` |
| hillslope-water-aggregation-contract.md | `fff7edba9629e13d7a93ceaabb8eb7f3a8525f9dc28119896a788d742021fe77` |
| Roads specification.md | `4455c104180c9571d6c31c35e278ea41c8dd0c7f1624570e5c783f7565d2f8f0` |
| 20261022_contract_decision.md | `d0eb6a522c0c783c07c606e81dd3e360f3e1381028cf3c98f60ab1b20ff6b976` |
