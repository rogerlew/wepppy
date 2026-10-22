# Independent Roads accounting integration contract review

Date: 2026-10-22 20:59 UTC. Reviewer: Codex integration_contract_review.
Disposition: **Approved for the pre-implementation contract checkpoint.**
No unresolved high or medium findings remain in the reviewed contract.
This approval covers intended behavior and integration boundaries, not
implementation correctness, scientific calibration, deployment or historical repair.
The reviewer authored no contract or runtime changes; this review is the only
file written by the reviewer.

## Reviewed authority and evidence

Reviewed the [canonical contract](../../../schemas/roads-water-accounting-contract.md),
[ADR-0102](../../../adrs/ADR-0102-roads-modeled-area-accounting.md),
[contract decision](20261022_contract_decision.md), package and active ExecPlan,
and amendments to output-scope, hillslope-water aggregation and Roads specification.
Starting revisions remain WEPPpy `38df23fbf5696b9cc5b5cdbbd6f15fa297a5286e`
and wepppyo3 `3b630643ba06bd40262285f206112c9d3ee32b21`.

Review included existing Roads source assembly, manifest timing, native weighted
PASS combination, native TotalWatSed reduction, average-report mapping/cache
logic, and raw dashboard/export joins. Earlier geographic analysis is superseded
by the operator's explicit modeled-MOFE direction and is not a dependency.

Reviewed document SHA-256 values:

| Document | SHA-256 |
| --- | --- |
| roads-water-accounting-contract.md | `2d8b71db7586a2cc39257bd351111d7469fb119794fb63de28a8b043190589ec` |
| ADR-0102-roads-modeled-area-accounting.md | `802354dd80715d1b89b0f8330e809efed9a19f60982ec3cc49192762351f2ddc` |
| 20261022_contract_decision.md | `d0eb6a522c0c783c07c606e81dd3e360f3e1381028cf3c98f60ab1b20ff6b976` |

## Prior findings and disposition

| Finding | Disposition |
| --- | --- |
| Area authority and zero-road parity unspecified | Resolved: stationary source WAT OFE area governs continuous runs; PASS headers govern single storms; product-specific response scales reconcile serialized areas; untouched PASS bytes and zero-road baseline parity are explicit. |
| Equivalent OFE would change TotalWatSed Q diagnostics | Resolved: TotalWatSed directly aggregates original weighted source profiles. Dedicated equivalent H.accounting.wat serves only average-hillslope reporting with physical terminal Q. |
| Optional SOIL/ELEMENT support denominators lost during collapse | Resolved: native joins remain source-qualified and retain valid supporting areas before aggregation. Absent, empty, partial and malformed optional sources have explicit policies. |
| Geographic requirements and negative-remainder rejection conflicted with latest direction | Resolved: contract, decision, ADR, package and plan consistently use B=max(A-C,0), retain all contributors and record model-space expansion. |
| Accounting artifact/readiness and stale caches unspecified | Resolved: corrected readiness requires ledger/source/PASS provenance and marked accounting products; average-report cache binds accounting-source hashes. Historical raw-backed results cannot silently become corrected. |
| Failed contributors could imply partial success | Resolved: execution failures still fail the whole run; only intentional skips permit a reduced successful contributor set. |
| Native particle-header admission could regress existing Roads workflows | Resolved: explicit Roads strategy preserves first-source particle-header semantics; AgFields retains strict validation. |

## Required implementation evidence and residual risks

The planned interfaces are compatible with existing consumers: canonical target
IDs remain the PASS population; raw H.wat, GL Dashboard and feature exports stay
diagnostic; original source topology survives until terminal selection. Retained
baseline Parquet supports raw-WAT cleanup. Baseline APIs, schemas and AgFields
behavior remain protected by explicit regression requirements.

Implementation must still prove the following obligations:

- Direct native tests for C<A, C=A, C>A, zero remainder, zero contributors,
  replacement remainders and mixed replacement precedence; serialize and reparse
  the exact canonical PASS consumed by fresh watershed execution.
- Unequal multiple-OFE sources, independent native terminals, preserved literal
  TotalWatSed Q/QOFE versus physical average-report Q, and partial optional
  observations across unequal source/target areas.
- Missing/empty/malformed sources, stationary geometry, complete date/topology
  validation, intentional skips versus failed execution, and original source isolation.
- Accounting cache refresh for equal-timestamp byte changes, rejection of stale
  raw-backed caches for corrected reports, and historical-result availability.
- Dedicated security review of source selection, aliases, publication failures,
  permissions and real worker-equivalent execution; contract review does not
  substitute for those unmocked boundary tests.
- Full UM1 reconstruction, fresh routing and daily/yearly/average report readback,
  plus baseline and existing AgFields regression gates.

The mixture approximates residual baseline response and retains existing Roads
first-header sediment-class interpretation. Model-space area closure does not
establish geographic overlap removal or full hydrologic closure. Raw diagnostic
views intentionally remain different from corrected aggregate views and must
be described as such. Build/runtime provenance and all implementation tests are
pending; this review provides no production-conformance claim.

The independent checkpoint must be committed as an ancestor before runtime
implementation, with the second required review and final disposition retained.
