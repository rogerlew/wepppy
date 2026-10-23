# Independent publication, isolation and maintainability review

Date: 2026-10-23 UTC. Reviewer: integration_contract_review.
Disposition: approved for publication, isolation and scoped implementation.
No unresolved high or medium finding remains. Final report/provenance and live
Usersum evidence were inspected at the hashes below. The package's broad
regression gate remains separate and pending. No runtime edits were made by
this reviewer.

## Corrected findings

| ID | Severity | Finding and disposition |
| --- | --- | --- |
| PUB-01 | Medium | Publication trusted saved project evidence after limited readback. Resolved: publisher reruns the collector; collector compares prepared inputs, summary/accounting/total/input hashes and selection against saved execution identities before writing. It also reconstructs the expected upload from the pinned source and rechecks source/baseline bytes. |
| PUB-02 | Medium | Negative verification equated unavailability with receipt absence. Resolved: verifier checks the actual canonical receipt before and after validation and checks explicit unrutted controls in the retained full upload. The observed negative project genuinely has no receipt. |
| EVID-01 | Medium | Emitted management semantics were not inspected. Resolved: matrix and project collection use `read_management` to compare all original plant sections, selected initial/yearly section data and every rotation's assignment/order. The verified 516-case matrix completed with these checks. |

Publication now completes scientific reads, serializes/renders all three current
artifacts and checks source stability before staging and replacing them. This
resolves the earlier render-failure partial-write path. Individual file replacements
are atomic; this is an offline reviewed publication workflow, not a multi-file
transaction service. Final repository freshness and vendor equality passed.

## Reviewed behavior and scope

- The management writer diff matches the approved reference-integrity repair;
  both original management templates retain their checkpoint SHA-256 values.
  The soil diff removes only the trailing `k` token from `3psand10.sol`.
- The Usersum guide's relative link resolves to the intended vendor report.
  The manifest uses `source: vendor`, `vendor_id: wepppy-roads` and `min_role: user`.
  Navigation is adjacent to disturbed results under Workflows and Modules.
  There are no route, role, authorization or protected-section changes.
- The vendor includes exactly the source report; its self-repository source
  cannot recurse with this include. The scoped sync populated only this vendor;
  contract validation reports 79 documents/leaves and three vendors. Existing
  vendor files are unchanged in the reviewed task diff.
- Committed fixture candidates contain selected geometry/climate/shared model
  inputs and provenance, without serialized controllers or account metadata.
  Content inspection and a credential-keyword scan found no apparent secrets.
- Clone setup now rebases serialized source-root paths before controller loading
  and copies file contents rather than retaining source symlinks. The documented
  early exploratory log append remains a historical side effect, not a claim
  that every exploratory action was read-only.

## Independent source isolation evidence

Read-only SHA-256 verification against each retained before-inventory passed for
`/wc1/runs/ro/roads-validation-oct23-v2-{bd,rd,rutted,unrutted}`. Each project
matches all 2,383 recorded original-source files and 911 copied baseline files.
No recorded-file drift was found. The original source is
`/wc1/runs/cl/clogging-starch`. This audit establishes the retained inventory's
byte equality; it does not prove the absence of arbitrary unrecorded files or
erase the earlier logging incident.

The separate negative-fixture review independently confirmed two expected failed
crossings, one identified source feature and absent current receipt. The positive
root `/wc1/runs/ro/roads-validation-oct23-unrutted-positive` was independently
rehashed against its retained before-inventories: all 2,383 source files and 911
baseline files match. Its published evidence identifies the exact one-feature
exclusion, 54 selected inputs, one road replacement and one remainder on one
target. The report prominently discloses this limited integration coverage.

An independent management probe read 14 emitted files from the verified matrix:
all seven arrangements for traffic-present and no-traffic templates passed.
Three altered copies were each rejected: wrong initial residue, wrong yearly
plant reference and a missing yearly assignment. Probe artifacts remain in the
weppcloud container at `/tmp/roads-management-review-ze1199wz`; source matrix
artifacts were read-only. The inspected verified-matrix log reports 516 passed
in 361.05 seconds.

## Final publication evidence

The completed report, 516-case compact result and provenance were inspected.
All 94 recorded source hashes match current bytes; report and result hashes match
the provenance, and the vendor report is byte-identical to the source. The final
interpretation refresh was explicitly limited to `analysis_context.md`, verified
the prior report/result hashes and retained the preceding report/context identity.
It changed no numerical results or model evidence.

The [live Usersum receipt](20261023_usersum_http_validation.json) and
[script](validate_usersum_http.py) exercise forest HTTPS through its ordinary
reverse proxy with no authentication override. Canonical report, vendor alias,
navigation and Roads guide all return 200. Both rendered report routes contain
tables, the 516-case statement, the reviewed extreme-ratio explanation and
unrutted limitation. Navigation/guide links retain the `/weppcloud` prefix and
their followed responses contain the report body. This does not mistake a login
or CAP challenge's 200 for the requested content.

The inspected publication/Usersum test log reports **68 passed** in 12.07 seconds.
The separate correctness review confirms native numerical reconciliation and
scientific scope; its approval does not substitute for this publication evidence.

## Reviewed identities

The provenance hash binds the full 94-file model/harness/fixture source inventory.
Additional publication configuration hashes bind the additive Usersum wiring.

| Artifact or source | SHA-256 |
| --- | --- |
| analysis_results_current.md and vendor copy | `69ac12140d779b92ed06c383adeb671a0ab4ab5f81b1dfd23541040d59bdc32b` |
| matrix_results_current.json | `f8fed5c145c507548db0c331e1d7e603a9f54cd72e399db5bef930b6203dab11` |
| analysis_provenance_current.json | `eec985dfbc4d2bec1f6ad03fc384b0206666a4bccf0a632c7a7847ceab53a5a7` |
| roads.py | `c902e86fd2c2cef162deef7231da159939458b137c7498c6054f7e6e96517aec` |
| 3psand10.sol | `c37870ab65aa917be188d2e591323bf4973292cd26f066b30c1337dcc277954b` |
| Usersum vendors.yaml | `3d363124dbba1800326b2aac015a9aa5240ccd3cd991f8ea5f6d60650e91eda8` |
| Usersum docs_manifest.yaml | `1c6444b33174f95c9e538e9f9212b1da4e705e237f05695a8d0fab1056c02334` |
| Usersum nav_tree.yaml | `25a8ac9b8b4a835b326fb35d629d11930dd4c3a078ddad3aa46285740475ebd7` |
| Usersum Roads ENDUSER.md | `9497eeea769c8603d62a00821a56cfd77c54653b66701a195df9fce89c4ae2aa` |

## Remaining acceptance and maintainability limits

The broad regression result remains a package closure requirement. This review
supports local forest publication and isolated scientific execution; it does not
certify production deployment, repair of historical results, field calibration or
general whole-site unrutted applicability. The source-isolation audit covers
recorded files, and the early exploratory logging side effect remains disclosed.

The changes reuse existing builders, native readers, the controller and vendor
machinery. The mechanical production edits remain small. Keep evidence collection
and verification shared rather than duplicating checks in report generation;
otherwise freshness assertions can diverge. Numerical interpretation and formula
validation remain the independent correctness review's responsibility.
