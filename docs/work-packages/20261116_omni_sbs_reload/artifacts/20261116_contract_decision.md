# OSR-01 / UFS-01 contract decision

Date: 2026-11-16 UTC. Starting revision:
`65fa0c0bd008b16157a82191a766a0bdb9453173`.

## Authority and intended delta

The operator requested fixing saved Omni SBS reload/resubmission and canonical
filename display; required contract-first execution and scoped tests; selected
`_limbo` or the corresponding scenario project's map with no legacy migration;
approved an independent staging contract; and then instructed “proceed with
contract-first execution”. This authorizes the plan's checkpoint commit and
bounded implementation, not deployment. No branch change is authorized.

Create UFS-01 in `docs/schemas/user-file-staging-contract.md` and OSR-01 in
`docs/ui-docs/contracts/omni-sbs-control-contract.md`. Amend
`docs/schemas/omni-sbs-freshness-contract.md` to permit admission-time restoration
before execution and `docs/schemas/upload-endpoint-contract.md` for adoption.
Shared controller, request-payload, RQ-response, NoDb persistence, and canonical
Disturbed SBS contracts remain unchanged; the new domain contract explicitly
links them. Existing unrelated working-tree amendments to shared contracts are
excluded from this checkpoint.

## Discrepancy and implementation boundary

UI serialization drops the saved file; admission selects by request row and
requires a temporary file consumed by execution. The old freshness rule forbids
missing-source execution, so this is an intended admission extension, not just
conformance repair. Restaging before dispatch resolves that conflict without
changing direct execution's failure or content-proof requirements.

Bounded files: Omni controller and tests, rq-engine Omni admission and tests,
paired template only if required, generated controller bundle, affected user and
developer docs, and this package. Existing raster helpers, NoDb commit validator,
and scenario-name/child-source helpers are reused. Worker queue wiring, model
parameters, new storage/services/locks and unrelated upload consumers are excluded.

## Compatibility and replacement plan

Preserve `sbs_file_path`, saved scenario names, receipt schema and upload field
names. Match a submitted saved reference to server-owned definitions, then use
its local staging suffix or associated child. Numeric legacy staging remains
readable. New files occupy unique directories so failed replacements cannot
clobber accepted files. Restore missing input before a destructive rerun, retaining
its path where possible. Old readers can consume these staged paths, though the
old positional admission remains broken on rollback. No data migration, bulk
cleanup, output rollback promise, or historical receipt fabrication.

## State and regression matrix

| State/action | Expected outcome |
| --- | --- |
| Never-used/empty row, no map | Actionable missing-input error; no accepted mutation |
| Saved staged map, no replacement | Display basename, preserve reference, use exact associated file |
| Consumed map, associated child present | Validate/copy to staging before reset; no re-upload |
| Legacy child without receipt | Same input resolution; normal freshness decides rerun |
| Dependency change | Staged source survives reset; generated input uses intended bytes |
| Valid replacement, same or new basename | New isolated input accepted; normal content freshness applies |
| Invalid replacement/later invalid row | Previous accepted association/file remains usable |
| Multiple rows, blank/deleted row, type switch | Submitted indexes align; no association transfer |
| Fork/restored old prefix | Resolve only current project's corresponding locations |
| Missing/invalid/hostile/symlink/unknown reference | Explicit 4xx, no guess, no escape or accepted mutation |
| Distinct saved paths sharing one basename/child | Exact staged selection allowed; consumed-child recovery rejects ambiguity |
| Enqueue error/timeout after state commit | Reconcile accepted definitions; do not claim rollback |
| Selection/content changes before commit | Reject under existing commit validator |
| Active/failed execution or archived roots | Preserve existing job and archive rules; no claim of new locking |

## Security and validation

Security impact high: file resolution/upload admission. Two independent contract
reviews precede the checkpoint commit. Final correctness/UX and security reviews
must close medium/high findings. Scope tests to Omni JS, route, filesystem/copy,
and implicated NoDb/RQ modules; no full suites. Retain actual browser and generated
artifact readbacks with candidate identity before environment-validation claims.
Review disposition and checkpoint revision are recorded in tracker.md.
