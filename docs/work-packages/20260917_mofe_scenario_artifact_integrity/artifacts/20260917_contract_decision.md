# MOFE management artifact contract decision checkpoint

**Status**: simplified contract accepted for execution; both independent reviews
passed; standalone checkpoint committed before implementation.
**Starting local revision**: `714693a00c1ce47def86ba0b984065262b9f49bd`
**Observed wepp1 revision**: `97800607c` (abbreviated host revision captured
during diagnosis; record the full revision at the next preflight)
**Prepared**: 2026-09-17 22:39 UTC
**Simplified contract SHA-256**:
`aab2b182422f900a5a4d8ce96d09b475bc77bdee3ac904e580e2fecb5361e896`

## Operator Direction

The takeover instruction to complete this package authorizes execution of the
bounded three-fix plan and its required checkpoint commit. No additional runtime
mechanism is approved. The separately recorded operator-owned production
deployment boundary remains in force. The reviewed contract hash below is
unchanged; its proposed label is historical checkpoint metadata, with acceptance
recorded here.

The operator requested a work package to fix the failed MOFE behavior, required
actual validation on Forest before deployment, reserved the WEPPcloud deployment
to himself, and directed Codex to manually repair all Abdisa runs after that
deployment. This approves the outcome and sequencing. The exact canonical
contract text, independent reviews, and standalone checkpoint commit remain
pending; no implementation file may be edited under this checkpoint yet.

On 2026-09-18, the operator rejected an expanded draft because its attempt
storage, publication ledger, recovery, retention, event-deduplication, and
full-workflow fencing would make this bounded fix fragile. Those mechanisms and
their proposed ADR were removed. The replacement contract is limited to the
three confirmed propagation defects, existing failure behavior, direct artifact
tests, and Forest acceptance.

## Classification

This is a bounded incident remediation spanning NoDb landuse generation and an
existing UI-coupled RQ mutation. It is not a parameterization change. The current
`docs/schemas/disturbed-mofe-mapping-contract.md` governs a later remap method,
and `docs/schemas/landuse-modification-contract.md` explicitly excludes global
class-to-class mapping. A new canonical artifact contract is needed rather than
using implementation or this work package as normative authority.

Stable remediation ID: `MOFE-ARTIFACT-20260917-01`.

## Applicable Current Contracts

- `docs/schemas/disturbed-mofe-mapping-contract.md` - effective mapping lookup and
  later Disturbed severity remap.
- `docs/schemas/landuse-modification-contract.md` - separate selected-hillslope
  edit behavior and explicit-assignment regeneration precedent.
- `docs/schemas/nodb-persistence-concurrency-contract.md` - locking, refresh,
  mutation, and persistence behavior.
- `docs/schemas/rq-response-contract.md` - worker completion and error envelope.
- `docs/standards/artifact-observability-standard.md` - visible and archivable
  project records.
- Proposed `docs/schemas/mofe-management-artifact-contract.md` - new current
  authority for the obligations below.

## Proposed Normative Delta

1. A `SoilBurnSeverityMap.build_lcgrid()` result is already in the classified
   130-to-133 namespace. The MOFE management builder consumes that value once and
   does not translate it again through the raw-pixel `class_pixel_map`.
2. The final `domlc_mofe_d` assignment map is the source of truth for combined
   MOFE management generation. A successful global class-to-class mutation must
   regenerate `landuse/hill_*.mofe.man` from the final assignments before it
   publishes completion.
3. A persisted `ManagementSummary.cancov_override` applies to MOFE segment
   synthesis when present. If RAP is active, its existing segment-specific cover
   calculation retains precedence. No cover value, formula, or threshold changes.
4. Later WEPP preparation continues to copy the corrected landuse artifacts
   through the existing workflow. Forest acceptance requires agreement among
   persisted intent, combined managements, prepared managements, and summaries;
   the landuse mapping event does not claim WEPP preparation or execution.
5. Writer failure follows the existing RQ exception path and cannot publish a
   completion event. No new staging, rollback, retry, or recovery subsystem is
   authorized.
6. Single-OFE projects, no-SBS projects, unburned/nodata SBS areas, configured
   buffer precedence, supported legacy assignments, request/response shape,
   authentication, run paths, locks, caches, and queue topology remain unchanged.

## Rationale and Rejected Alternatives

The current state lets user intent stop at NoDb while WEPP consumes stale or
baseline files. Correctness therefore belongs at the artifact-generation boundary.

Rejected alternatives are direct production file edits, rewriting NoDb to match
the wrong files, forcing result values to differ, applying `class_pixel_map` a
second time with more fallback keys, and adding a repair queue/service. Also
rejected are a new attempt store, publication ledger, event protocol, retention
policy, and cross-workflow transaction fence. These would hide the producer
defect, change scientific intent, or add unnecessary failure modes and
operational mechanisms.

## Compatibility and Data Impact

No user-visible key, NoDb field, route payload, response field, parquet column,
directory, filename, or archive member is added, renamed, or removed. Corrected
generated file bytes change only where persisted scenario intent differs from the
previous generated content. Downstream propagation must be validated in
`wepp/runs/*` and completed outputs.

No migration is required. Existing affected projects require supported rebuild
and rerun after deployment; silently treating their old outputs as current is not
compatible.

## Security Impact

Impact is low under the proposed boundary. Existing authorized routes, run access,
NoDb locks, cache guards, RQ workers, paths, and writers are reused. There is no
new upload, download, auth, secret, shell, subprocess, egress, queue edge, or path
authority. Any such expansion changes triage to high and requires a dedicated
security review.

## Parameterization Impact

No parameterization change is authorized. The correction propagates values that
already exist: severity code, effective class, and explicit cover override. RAP's
current precedence is preserved. A proposed change to a formula, lookup row,
default, threshold, unit conversion, or fallback requires an ADR before code.

## Required State Matrix

| Runtime state | Required behavior |
| --- | --- |
| Single-OFE project | Preserve existing build and mapping behavior; no MOFE state required. |
| MOFE never built or assignment absent | Explicit existing-contract build-first failure where a segment mutation needs assignments. |
| Empty MOFE assignments | Preserve valid empty semantics only where the current operation permits them; never claim generated treatment files. |
| Populated valid assignments | Regenerate from the final assignment map and summarize the result. |
| Supported legacy key representation | Normalize through existing loaders without schema migration. |
| Malformed/incomplete assignments | Fail before success publication and retain diagnostics. |
| SBS absent | No burn remap; ordinary assignment generation remains. |
| SBS present with unburned/nodata | Preserve classified 130 and existing nodata behavior. |
| SBS present with 131/132/133 | Apply the effective low/moderate/high class once. |
| Explicit canopy override absent | Use existing source/RAP behavior. |
| Explicit canopy override present, RAP absent | Write the stored override to applicable MOFE managements. |
| Explicit canopy override present, RAP present | Preserve current RAP segment-specific precedence. |
| Writer working | Request remains pending; file existence is not completion. |
| Writer failed | Explicit failure, no completion event, visible partial artifacts and diagnostics. |
| Writer completed | NoDb, combined managements, and summaries agree; prepared-input agreement is checked later after normal WEPP preparation. |
| Archived/restored project | Preserve artifact and diagnostic bytes; restoration does not certify failed artifacts as complete. |

## Regression Evidence Required

- A failing-before/fixed-after real or production-faithful SBS classification
  test that cannot pass by returning raw fake pixels.
- Content assertions for low, moderate, high, unburned, and nodata SBS cases.
- Real combined management generation after global class-to-class RQ mutation.
- Explicit failure/no-completion and retry behavior at the writer boundary.
- 0.30 and 0.50 management summary cover cases through combined and prepared
  WEPP management files.
- RAP precedence, buffers, single-OFE, supported legacy, stale-job, invalid-class,
  missing/empty/malformed assignment, archive/restore, and normal authorization
  behavior.
- Actual-project Forest evidence through completed WEPP outputs.

## Review and Checkpoint Status

- Independent governance review: PASS on the simplified exact hash; no unresolved
  High or Medium findings.
- Independent correctness review: PASS on the simplified exact hash; no
  unresolved High or Medium findings.
- Initial compact review: correctness PASS; governance HOLD on missing proposed
  status and a writer/preparation boundary wording conflict. Both wording issues
  are corrected and independently confirmed in the simplified hash above.
- Finding disposition: complete for the contract checkpoint.
- Operator approval: takeover instruction to complete the bounded package.
- Canonical contract amendment/addition: included in this checkpoint.
- Standalone ancestor commit: this documentation-only checkpoint; revision will
  be recorded in the tracker immediately after commit.
- Implementation authorization: effective after this checkpoint commit.
