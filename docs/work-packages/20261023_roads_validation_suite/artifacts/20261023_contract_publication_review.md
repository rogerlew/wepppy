# Independent publication and isolation contract review

Date: 2026-10-23 UTC. Reviewer: integration_contract_review.
Baseline: `a7ea23927`. Preimplementation review; no runtime code was changed.

## Disposition

Approved for the contract checkpoint. No unresolved high or medium contract
finding remains. The proposed suite and publication fit the authorized additive
scope: scientific fixtures, tests, generated evidence and one curated user-readable
document. Existing numerical, route, role and lifecycle contracts remain in force.
This approval does not certify fixture contents, fresh model results or rendered
publication before they exist.

Final clarification reviewed: unrutted profiles use the production geometry
parity helper and select soil templates with `design=outslope_rutted`, matching
the existing replacement path, including paved surfaces. The precise OFE orders,
12 sensitivity controls, shortest-segment precision disclosure and nonzero
four-design execution requirements strengthen fidelity without changing
publication, access or isolation scope. Approval remains unchanged.

## Concrete implementation constraints

The existing vendor CLI has no vendor selector. Both `sync-vendors` and default
`build-index` call `sync_vendor_docs()` for every configured vendor; explicit sync
also cleans vendor roots by default. Honor the scoped contract using the existing
API with `dataclasses.replace(contracts, vendors={"wepppy-roads": ...})`, then
build the index with `--skip-vendor-sync`. No new CLI, endpoint or vendor subsystem
is necessary. Use the exact include `tests/roads/analysis_results_current.md` and
the separate target root `wepppy/weppcloud/routes/usersum/vendor/wepppy-roads`.
The self-repository source does not recurse with this exact include.

`source_ref` is stored configuration metadata: the sync implementation copies the
working-tree file and does not check out or verify that ref. Report/provenance
hashes and source/vendor byte equality must establish the reviewed identity.
Do not describe the ref field alone as a reproducibility guarantee.

`runtime_catalog.load_runtime_catalog()` prefers an existing generated index and
caches its result. Manifest/nav edits alone therefore do not prove publication.
Build through the ordinary index path, refresh the validation process/catalog,
and exercise the actual canonical and vendor routes plus the navigation link.
Keep incidental generated-index and unrelated vendor drift outside the task diff.

These are execution constraints under the proposed contract, not requests to
expand scope or change Usersum behavior.

## Isolation and scientific provenance

- Curate committed scientific inputs through an explicit file/field allowlist;
  inspect their contents and provenance for credentials, account/controller
  serialization and incidental private metadata. A whole-project copy is local
  execution material, never the portable repository fixture.
- Source and scratch paths must resolve to separate trees. Avoid write-through
  hardlinks or symlinks into the original project, and use fresh scratch roots.
  Read back source/baseline hashes after full-project execution. Reusing the
  controller without this filesystem evidence does not establish isolation.
- Bind matrix cases, selected source segments, actual climate dates, prescribed
  profile geometry, production builders, native reader, binary and analyzer to
  the retained provenance. Source hashes plus generated input/output hashes are
  needed; a successful process exit or an updated sidecar alone is insufficient.
- Validate the complete expected case set and calendars before replacing current
  report artifacts. Keep the reviewed report, machine summary and provenance
  mutually consistent; failed generation retains diagnostics and must not leave
  partial output presented as current.

## Valid and invalid states

| State | Required result |
| --- | --- |
| Fresh, complete canonical matrix and declared controls | Eligible for scientific review and report generation; full-project evidence remains separately required. |
| A valid zero-output day/year or signed deposition value | Preserve it in complete-calendar aggregates; do not drop, clip or require positive erosion. |
| Zero ratio denominator | Explicitly unavailable, never an invented zero or infinity. |
| Empty, incomplete, malformed, duplicate-calendar or nonfinite case | Reject current report generation and retain diagnostics. |
| Relevant source changed since report generation | Freshness check fails or report is explicitly stale; replacing hashes alone does not refresh evidence. |
| Optional local full-site fixture absent | Opt-in test may skip with a reason; package acceptance remains incomplete. |
| Historical beta output or previous scratch run exists | Preserve it as historical material; it cannot substitute for fresh evidence. |
| Current vendor file absent or different from the reviewed report | Publication validation fails; ordinary Usersum access does not certify content equality. |

## Acceptance evidence to retain

1. Curated fixture inventory and privacy inspection; direct prepared-file readback
   and native output/calendar validation for all 504 cases and declared controls.
2. Four isolated design executions, including persisted settings, prepared inputs,
   current receipt, profile summaries and aggregate accounting, with unchanged
   source/baseline evidence. Numerical interpretation belongs to the independent
   correctness review; profile comparisons alone do not certify watershed routing.
3. Repository-only freshness checks without scratch directories, incomplete-case
   rejection, report/summary/provenance consistency and exact source/vendor hashes.
4. Usersum contract/index validation and actual ordinary user-role rendering,
   Workflows and Modules navigation, the Roads guide link and canonical/vendor
   aliases under the deployment prefix. Check rendered body content and links,
   rather than treating any HTTP 200 as proof of the intended document.

The user-readable document is intentionally available under the existing Usersum
`user` visibility tier, including anonymous readers. Protected navigation sections
and existing role gates are untouched. No new authentication or publication API
is needed. Execution, numerical and browser evidence remain implementation gates;
this review makes no field-calibration or production-deployment claim.

## Reviewed document fingerprints

| Document | SHA-256 |
| --- | --- |
| roads-validation-suite-contract.md | `10a8b6bc977066e3c156c13566dfffbef7e9a97cb6c1e808f323e5a6acf05e4e` |
| package.md | `c6614d28019b8b791c2bc0d9186b2dc16260ab1104ecfb062b6842d184bf6a21` |
| validation_execplan.md | `6f3a6424915489b5589aa518762caf58a486410ff2876f8d922bde431949f42f` |
| 20261023_contract_decision.md | `7690a86576c9d44e41536d447aa564561400d4662ba7824dc46bed31cc48ed46` |
| Usersum specification.md | `6ba75663aef3fc4f8aee65d15290a3f9ecab52cf408072a27e0e48a0c4916685` |

Implementation references inspected: `tools/usersum_docs_tool.py`,
`wepppy/weppcloud/usersum_docs/{vendor_sync,docs_contracts,runtime_catalog}.py`,
and Usersum `AGENTS.md`, `vendors.yaml`, `docs_manifest.yaml` and `nav_tree.yaml`.
