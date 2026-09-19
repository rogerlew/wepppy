# Correctness and user-experience review

Reviewer: `/root/ground_correctness`, independent read-only review, 2026-09-19 UTC.
Scope: MOFE cover propagation, regression tests, and validation evidence.
Base `8dbf8f037`; reviewed standalone contract ancestor `824457074` and
implementation `0fd1a6eca`. Canonical authority:
`docs/schemas/mofe-management-artifact-contract.md`, Ground-cover propagation;
NoDb persistence contract unchanged. Security low; no new access boundary,
dedicated security artifact not required.

## User outcome and state/error matrix

Users' saved ground selections must reach generated and prepared managements.
Input dimensions: independent interrill/rill/canopy fields, zero/one/interior
fractions, RAP/no RAP, serializable/preloaded managements and process workers.

| State | Required outcome | Direct evidence |
| --- | --- | --- |
| Missing/empty MOFE assignments | Expected unbuilt state, actionable build-first error before mutation | Parameterized unbuilt-assignment regression |
| Populated assignments and saved cover | Apply to assigned segments; preserve other class/cover values | Real combined/prepared parsing and Forest 455-hillslope readback |
| Legacy absent/None overrides | Existing source cover unchanged | Legacy real-parser regression |
| Retained summary classes | Preserve all three selections, including zero | Summary tests and normal Forest identity-mapping job |
| Malformed populated assignment | Existing explicit incomplete-segment failure | Nonsequential-segment regression |
| Writer failure | Existing error, partial files not success; supported retry | Writer injection/retry regression; archive tests retain diagnostics |
| Single-OFE | No MOFE assignments/build required | Three explicit coverage regressions |

No new hostile-input surface or exception translation; existing value validation,
run authorization, locks and filesystem boundaries remain unchanged. No claim
of exhaustive unrelated field/flag combinations.

## Generated-artifact evidence chain

Exact requests and evidence are in [Forest validation](20260919_validation.md).
Saved intent, combined managements, prepared inputs and downloads pass. Model
output and final live archive/restore acceptance pass. Real Management
load/synthesis/write/read and WEPP preparation exercise the corrected boundary;
soil/slope mocks in fixture tests isolate unrelated work. Forest checks use real
controllers, service identities and project data.

## Findings and disposition

No production-code blockers. Low validator finding: assignment-map iteration
could miss a parquet hillslope while reporting the full count. Resolved by exact
key-set equality plus 455-hillslope/1,065-segment assertions. Source generated and
prepared management manifests and expected covers supplement pinned NoDb hashes.

Contract-review medium artifact-acceptance gap was resolved before checkpoint:
canonical inventory/status rules, browser/download and archive/restore tests
were added. Configured cover-default ordering remains explicitly excluded;
Forest fixture has no configured defaults.

## Verdict

Source correctness and Forest artifact acceptance: pass. Final reviewer
independently reran the post-restore validator: 455 hillslopes, 1,065 segments,
910 management files, expected covers, checked prepared hillslope input parity,
archive-byte matches, fresh outputs and unchanged source NoDb all pass.
Production code remains unchanged from reviewed candidate `0fd1a6eca`.
No remaining correctness or Forest artifact-acceptance blockers. No production
deployment or production-project repair is claimed.
