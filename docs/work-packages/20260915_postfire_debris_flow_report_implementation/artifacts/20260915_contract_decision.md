# PFR-I01: saved likelihood report checkpoint

Date: 2026-09-15 UTC. Starting implementation revision:
`e6c821cdd844e1cde360bd76d3ce500f389b3f15`.

## Authority and classification

Owner: “execute docs/work-packages/20260915_postfire_debris_flow_report”, then
“yes” to successor implementation package and required checkpoint/implementation
commits, excluding push, deployment and reruns. Intended additive behavior,
not a conformance repair. Review and standalone ancestor are still required.

## Exact normative delta and rationale

Ratify the five-section report and the exact read-interface section in
`docs/ui-docs/contracts/postfire-debris-flow-report-contract.md`: GET page/query/
detail/fixed artifact reads, accepted identity pinning, sanitized summary,
bounded query, read-only currentness, no-store, browser displayed-row CSV and
one existing-control entry link. Use Pure shell, existing helper/Unitizer patterns
and no new dependencies. Browser CSV removes unnecessary server surface; fixed
session-authorized attachments avoid bearer-token handling in links.

Amend `wepppy/nodb/mods/postfire_debris_flow/docs/rainfall_results.md` to retain
already-validated design/inverse tables in ResultCatalog while preserving
two-argument callers and every persisted schema. Amend the control contract and
feature registry specification for the single link and retained-result access.
Module specification/roadmap link the accepted current contract.

## Applicable authority and compatibility

In addition to those amended contracts, preserve production_m1.md,
production_m3.md, production_m3_runtime.md, model_selection.md, the shared
controller contract, NoDb persistence/concurrency, CSRF and canonical error
contracts, report conventions, and artifact observability. No changes to their
scientific, mutation, auth, enqueue or artifact-retention obligations.

M1 assessment ID is accepted dNBR ID, M3 assessment ID is model attempt ID.
Never confuse either with the transport pin. Currentness dependency errors must
not discard valid accepted values: show unknown, never current. Existing engine
identity can mark results stale after reader source changes; do not override it.
No run-schema migration or generated WEPP input mutation; prove accepted-file
hashes unchanged after reads. Preserve shared pup context across all URLs.

## State/input and security regression plan

Use the current contract's runtime-state table and field/input definitions as
the finite matrix: absent, empty, M1/M3 v1/v2 populated/partial, unavailable rows,
stale/currentness unknown, new running/failed attempt with prior acceptance,
replaced, corrupt, hostile, archive/restore. Preserve valid authorized public,
private-owner and read-only access; deny unauthorized private access on every
endpoint. Test duplicate/unknown/invalid/nonfinite keys and bounded paging.
Read actual temporary files for hash, symlink, missing artifact and replacement
checks. Verify no scientific/project writes, original raster decoding, model
tasks or published-file changes. Existing session/read-through Redis handling
and bounded currentness metadata/stat reads remain unchanged; explicit shared
Unitizer actions may persist presentation preferences, not model selections.

Security impact high: dedicated independent review required. No secrets in
seeds/errors/screenshots; escaped text/JSON, formula-safe CSV, validated opened
download descriptor, no arbitrary paths/SQL/remote URLs or persistent browser
cache. Auth failures also receive no-store. Review implementation separately.

## Checkpoint status

Contract amendments prepared; independent correctness/security/UX reviews pass
with all findings resolved in [contract_reviews.md](contract_reviews.md).
Ancestor commit is the next step.
Implementation conformance pending. No implementation edits authorized before
the reviewed checkpoint is committed.
