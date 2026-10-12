# PCV-01 — Portland collection read access (checkpoint draft)

**Prepared**: 2026-10-12 08:21 UTC  
**Starting local revision**: `dc6f3879e3372fa35062708b2c2f0caeb7eba18e`  
**Status**: intent recorded; canonical amendments, independent reviews, and ancestor commit pending

## Authority and normative delta

The operator stated that the Portland group is supposed to see these runs and requested this work-package scaffold. This is authority for the intended group-access correction, not publication, a new membership system, broader private-run access, or production mutation. Existing source uses `PortlandGroup` for the Portland landing page.

Proposed correction: current PortlandGroup membership admits reads of server-associated Portland collection runs through viewer, generator, and the downstream data surfaces actually consumed. Validate every run; never trust submitted prefix/configuration/group claims as proof. Existing independently valid access must remain available. Reject mixed collections when any run lacks authorization; do not silently omit unauthorized runs.

## Discrepancy and source boundaries

The `Ron.ispublic()`-only combined-viewer gate conflicts with the operator's stated group workflow. Ordinary authorization and combined authorization also disagree about ownerless legacy resources. This second discrepancy needs an explicit compatibility disposition; the scaffold does not authorize general lockdown.

Boundaries: `wepppy/weppcloud/routes/combined_watershed_viewer.py`, `routes/locations.py`, `utils/helpers.py`, `combined_watershed_viewer_generator.py`, combined templates, existing GL dashboard modules, and consumed query-engine/resource/report/file authorization. Inventory exact downstream handlers before committing the checkpoint.

## Canonical checkpoint work remaining

Create `docs/ui-docs/contracts/combined-watershed-viewer-contract.md` with the bounded resource association, admission matrix, transport, errors, optional/missing state, old-link compatibility, and data/display semantics. Review the feature-access, browse-auth, CSRF, output-scope, NoDb, and controller contracts named in package.md; amend affected obligations and record justified non-applicability for others. Reconcile the public-only endpoint security note. Record production and local starting revisions, exact amendments, two independent review dispositions, and the standalone ancestor commit before runtime edits.

Do not invent a Portland feature entitlement: feature access governance distinguishes feature actions from ordinary resource reads. Existing PortlandGroup is the starting mechanism. If no trusted resource association exists, prepare a finite server-owned association using the existing location catalog, document maintenance/revocation behavior, and review it before implementation.

## Compatibility, security, and regression evidence

High security impact. Matrix: member, removed member, nonmember, anonymous, existing owner/admin, public run, unrelated private run, mixed collection, missing run, malformed IDs/configs, and stale credentials. Pair transport tests with current membership and real resource authorization tests. Test geometry, value queries, popups, and consumed file/catalog paths directly, not just page admission.

Legacy artifacts are additive, generated from retained output, and compared semantically before cutover. Existing URLs preserve display settings and actual run configuration. No new model formulas, defaults, or unit conversions are authorized. Roles/membership records and PUBLIC markers remain unchanged by artifact preparation or UI repair.

## Reviews and approval status

Operator behavior intent: recorded above. Exact canonical amendment reviews: not started. Commit authority: not supplied by scaffold request. Accepted ancestor: none. No implementation conformance or deployment claim.

## Execution authorization and resolved matrix — 2026-10-12

Operator authorized carrying out forest work through rollout readiness, including forest restarts and dev-agent permissions. Required local checkpoint/implementation commits are included in execution of the plan; production writes/deployment are not.

Fresh inventory: production revision 84337c967136c6bc50f357fb600c0a44534edf2f, 63 existing runs, all ownerless, no PUBLIC markers, all loss text present and loss Parquet absent. Evidence: `evidence/production-inventory.jsonl`. Preserve existing anonymous ordinary resource access; collection entry gains the bounded PortlandGroup/owner/admin admission specified in the new canonical contract. No general authorization or query-engine policy edits are needed for these ownerless resources.

Canonical matrix: new combined-viewer contract owns admission/input/data/UI behavior; feature-access contract gains explicit cross-link distinguishing resource reads from feature actions; endpoint security note is reconciled. Browse-auth, CSRF, NoDb persistence and output-scope contracts remain unchanged: existing transports/permissions, no new persistence mutations, baseline loss products and preserved original output. Controller shared safe rendering, HTTP/CSRF and accessibility conventions apply unchanged. Generated-artifact and observability standards apply to offline preparation and direct consumer validation.

Source boundary: combined routes/generator/templates, explicit Portland catalog, focused Deck.gl collection controller reusing existing map/key/color components, offline artifact preparation tooling, tests and documentation. Read-only existing geometry/report/query consumers require no general auth grants. Existing popup/report dependency failures must be handled visibly, or replaced by numeric feature details and a run-specific navigation link. No queue, model, membership migration, or unrelated dashboard changes. Two independent reviews remain required before checkpoint commit.

## Review disposition

Both independent contract reviews pass: `2026-10-12_contract_security_review.md` and `2026-10-12_contract_correctness_review.md`. Security documentation wording was reconciled to current forest authority and preserved downstream ownerless access. Correctness's exact native field/area mapping was added to the canonical contract. Actual native area positivity, READONLY staged publication, complete geometry joins, current membership and full browser/artifact evidence remain implementation gates, not review findings silently waived. No unresolved medium/high contract findings remain.
