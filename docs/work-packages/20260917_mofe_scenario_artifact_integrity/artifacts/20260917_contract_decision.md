# MOFE management artifact contract decision checkpoint

**Status**: draft; implementation is blocked
**Starting local revision**: `714693a00c1ce47def86ba0b984065262b9f49bd`
**Observed wepp1 revision**: `97800607c` (abbreviated host revision captured
during diagnosis; record the full revision at the next preflight)
**Prepared**: 2026-09-17 22:39 UTC

## Operator Direction

The operator requested a work package to fix the failed MOFE behavior, required
actual validation on Forest before deployment, reserved the WEPPcloud deployment
to himself, and directed Codex to manually repair all Abdisa runs after that
deployment. This approves the outcome and sequencing. The exact canonical
contract text, independent reviews, and standalone checkpoint commit remain
pending; no implementation file may be edited under this checkpoint yet.

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
4. Prepared `wepp/runs/*.man` files must be generated from the corrected landuse
   artifacts. Success requires agreement among persisted intent, combined
   managements, prepared managements, and summaries.
5. Writer failure is explicit and cannot publish a completion event. Partial or
   mixed-generation artifacts remain visible with diagnostics and are not treated
   as complete. Retry uses the persisted final assignment through the same
   supported writer.
6. Single-OFE projects, no-SBS projects, unburned/nodata SBS areas, configured
   buffer precedence, supported legacy assignments, request/response shape,
   authentication, run paths, locks, caches, and queue topology remain unchanged.

## Rationale and Rejected Alternatives

The current state lets user intent stop at NoDb while WEPP consumes stale or
baseline files. Correctness therefore belongs at the artifact-generation boundary.

Rejected alternatives are direct production file edits, rewriting NoDb to match
the wrong files, forcing result values to differ, applying `class_pixel_map` a
second time with more fallback keys, and adding a repair queue/service. These
would hide the producer defect, change scientific intent, or add unnecessary
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
| Writer completed | NoDb, combined managements, summaries, and prepared WEPP inputs agree. |
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

- Independent contract review 1: pending.
- Independent contract review 2: pending.
- Finding disposition: pending.
- Operator approval of exact contract text: pending.
- Canonical contract amendment/addition: pending.
- Standalone ancestor commit: pending.
- Implementation authorization: blocked until all items above are complete.
