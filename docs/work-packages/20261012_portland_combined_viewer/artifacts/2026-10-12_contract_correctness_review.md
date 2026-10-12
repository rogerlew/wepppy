# PCV-01 contract correctness review

## Metadata and verdict

- Reviewer: independent `contract_correctness` agent; read-only review of implementation and proposed contracts, with this review artifact as the only authored file.
- Reviewed: 2026-10-12 16:32 UTC; starting implementation `dc6f3879e3372fa35062708b2c2f0caeb7eba18e`.
- Scope: [canonical PCV-01 contract](../../../ui-docs/contracts/combined-watershed-viewer-contract.md), [decision checkpoint](2026-10-12_contract_decision.md), package/ExecPlan, production inventory, feature-access PCV-01 cross-link, and endpoint security note.
- Canonical contract SHA-256 at review: `481a29931e29d1b74b1264644fa61bc91b0cf16220b914a648a9327b1e91e1db`.
- Gate: **pass for the pre-implementation contract checkpoint**. Unresolved high: 0; medium: 0. This is not implementation or release approval. Commit the reviewed checkpoint before runtime edits.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| PCV-C01 | Medium | The initial data section named annual depths/densities but did not fix the exact native fields, denominator, or average table. Reusing the GL data manager would produce soil loss in t/ha with watershed area, while legacy collection ranges use kg/ha. | Resolved before sign-off: the canonical contract now names `loss_pw0.hill.parquet`, native `Hillslope Area` in ha, native volume/mass columns, exact preserved normalization, complete WEPP-to-Topaz joins, and valid phosphorus options. The reviewer re-read the amendment and verified it against native schema/report source. |

No additional high/medium contract finding. The independent security review and final runtime correctness review remain required.

## Authority, compatibility, and source evidence

The operator authorized the forest work described by the package, forest restarts, and development account permission changes. The boundary excludes production writes/deployment, model reruns, membership migration, PUBLIC-marker changes, and general authorization rewrites. Read admission is an existing-role correction for a finite catalog, not feature-action entitlement.

The reviewer independently parsed the local Portland template and retained production inventory: 63 unique IDs, nine scenario titles, identical run-ID sets. The inventory records all runs as existing and ownerless, none PUBLIC, all retaining loss text and all missing loss Parquet. The reviewer did not independently execute the remote inventory or treat these flags as numerical validation.

Source checks support the proposed compatibility disposition:

- `wepppy/weppcloud/routes/locations.py:62` uses the existing PortlandGroup role.
- `wepppy/weppcloud/routes/combined_watershed_viewer.py:60` checks only PUBLIC status; `utils/helpers.py:848` separately admits ordinary ownerless runs. Preserving ordinary access while bounding collection admission is explicit and does not imply confidentiality of historical artifacts.
- `combined_watershed_viewer_generator.py` confirms empty-input, role-assignment, URL encoding and extent-union repair targets. These are bounded changes; no general authorization helper change is needed for the inventoried runs.
- `templates/combined_ws_viewer.htm:235` establishes winter/jet2/viridis, kg/ha loss, and the existing phosphorus normalization. `static/js/gl-dashboard/data/wepp-data.js:76` uses different soil-loss display normalization, which must not be copied into this workflow.
- `wepppy/wepp/interchange/watershed_loss_interchange.py` produces average and annual tables through the required native writer. `tests/wepp/interchange/test_watershed_loss_interchange.py:52` establishes average field names and native `Total Pollutant`; current annual data can contain area while older annual rows do not. Selecting the already averaged table avoids that annual compatibility trap.
- `wepppy/wepp/reports/loss_hill_report.py:156` and `wepppy/wepp/interchange/watershed_loss.py:107` substantiate the prescribed depth/density formulas. Native total pollutant fields must not be confused with old augmented `Total Phosphorus` labels.

## Valid-state and error matrix

This is a reviewed obligation matrix, not a claim that runtime tests already pass.

| Stored/resource state | Required outcome | Contract coverage |
| --- | --- | --- |
| No collection / empty generator entry | Explanatory viewer state or usable generator form | Inputs, errors, and generator |
| Run or required artifact absent | Authorized caller receives explicit readiness failure; no successful empty map | Inputs and data sections |
| Geometry/value collection present but empty or incomplete | Explicit incomplete/error state; no silent watershed exclusion | Data and artifact sections |
| Populated supported artifacts | Complete composite joins and correct per-run values/links | Data and display |
| Ownerless legacy output without Parquet | Offline additive preparation; preserve original files and ordinary access | Existing resource visibility; artifact compatibility |
| READONLY legacy run | Explicit offline staging and manifest-owned publishing; marker and source bytes unchanged | Offline maintenance amendment |
| Optional phosphorus absent or invalid | Disable only phosphorus; explicit unavailable selection state | Data and display |
| Valid zero modeled value | Preserve zero rather than dropping feature or substituting missing data | Data and display |
| Malformed/hostile input or resource content | Safe 400, 403, or explicit readiness error as applicable | Input and data sections |

Identity/input combinations are separately required: current/revoked member, anonymous/nonmember, independent public/owner/admin grants, unrelated private and mixed lists, duplicate IDs, stale config aliases, special-character titles, variables/units/ranges, and share/reload. Membership removal ends group-derived collection entry; it must not be misreported as revocation of already independent ownerless resource visibility.

Expected optional absence is distinguished from invalid required content. Source/converter/query failures require retained diagnostics and a visible error. The reviewed policy explicitly prohibits partial success and credentials in share URLs. Exact user-facing error text and retry behavior require implementation review against these obligations.

## Evidence chain and residual risk

Only contract readiness is approved. Writer, query-engine, browser, and archive/restore evidence are pending; current files and source inspection cannot establish numerical parity or rollout readiness.

- Verify the actual native writer against one copied run, then all nine collections. Validate exact consumed paths/catalog entries, field units, complete ID joins, row counts, finite values, and source hashes. Native writer success alone is insufficient.
- The existing legacy adapter substitutes watershed area when native `Hillslope Area` is zero (`watershed_loss.py:94`). The new contract rejects zero/nonfinite native area. Check the real collection areas; if actual supported records require that existing fallback, amend its exact compatibility policy before implementing it. This is an acceptance risk, not evidence that current Portland records fail.
- Confirm valid all-zero phosphorus output remains available when configured; column existence alone cannot establish pollutant meaning, and nonzero totals must not be used as the availability test.
- Prove READONLY preparation and interrupted retry refuse unrelated preexisting outputs/catalogs and retain visible staging/provenance/failure records. Final correctness review must verify canonical archive members and byte-preserving restore, normal browse/download, production-equivalent identities/mounts, and rollback ownership.
- Browser evidence must exercise the non-admin member, revoked member, and independent grants directly, plus old/new generated links, all units/variables, actual map values, and no hidden partial collections.

Forest validation and later production deployment/repair remain separate milestones. No existing query-engine containment issue or unrelated feature-governance milestone is closed by this checkpoint.
