# FDC-01 implementation security review

## Findings

| ID | Severity | Surface and evidence | Remediation and validation | Status |
| --- | --- | --- | --- | --- |
| FDC-SEC-01 | Medium | A child source can exist while `catalog.root` or its entry `fs_path` selects another run's data. Query results do not expose physical provenance. | `_source_status` binds catalog root and effective entry to the canonical owned daily file. Direct filesystem tests reject foreign roots, pointers and source/catalog symlinks. | Resolved |
| FDC-SEC-02 | Medium | A Roads dashboard must not silently display baseline FDC output. | `flow_duration_context` returns explicit unavailability outside baseline scope; direct Roads test passes. | Resolved |
| FDC-SEC-03 | Medium | Resolving a scenario-directory symlink before binding its identity could label baseline or sibling outputs as the selected scenario. | Nonempty scenario paths must equal their resolved canonical location beneath the authorized project. Direct base/sibling directory-alias tests pass. | Resolved |
| FDC-SEC-04 | Medium | `_outlet_ids` initially loaded `watershed.nodb` and translator Parquets before checking shared topology containment. External metadata could be read before the `network.txt` guard. | Project containment now precedes NoDb loading and translator invocation for the NoDb file, watershed directory and both translator Parquets. Direct external NoDb and temporary-file Parquet tests reject before deserialization. Normal parent topology remains valid. | Resolved |
| FDC-SEC-05 | Medium | A later smoke-test edit exported authenticated browser storage to fixed `/tmp/fdc-browser-auth.json`, setting restrictive permissions only after writing. The test did not itself consume this session export. | Unconditional export removed from test source. After the authorized regression run, the owner removed the temporary private session and configuration; independent existence/symlink checks confirmed cleanup. | Resolved |
| FDC-SEC-06 | Medium | In a directly opened Omni child dashboard, treating the child as the topology project rejected its normal parent-shared metadata. The safety control interfered with a valid child view. | Only exact `_pups/omni/scenarios/<child>` lineage establishes the shared parent topology boundary. Daily/catalog ownership remains child-specific. The `?pup` transport receives its verified scenario selector, while composite child endpoints retain their own run identity. Two direct child-view tests pass. | Resolved |

No unresolved high or medium findings.
Explicit nullable catalog pointers retain Query Engine's normal logical-path behavior.

## Metadata and gate status

Reviewer: `/root/fdc_contract_security`, dedicated security reviewer.
Inspection and independent tests: 2026-10-10 21:30 UTC; child-view follow-up 21:36 UTC.
Final sign-off: 2026-10-10 21:39 UTC, after correctness/QA addenda and session cleanup.
Implementation checkpoint: `c63f2cc5218aed52822c20f36e77698fea3382a1`, an ancestor
of the reviewed working tree. Starting implementation revision:
`189d10649793f0be1bdae5aeb90e8af9a810d977`.

Scope: `routes/gl_dashboard_flow_duration.py`, its existing authorized route
integration, the three new flow-duration JS modules, graph loader/controller/
renderer/state/mode changes, template bootstrap, and focused route/Jest/browser
tests. No production code was edited by this reviewer.

Security impact: **high**, because the package adds public-route filesystem
inspection and dataset consumption. Dedicated review is required. This does not
mean the patch adds a new authorization endpoint or privilege.

The independent correctness gate passed in
[its implementation review](20261010_implementation_correctness.md).
The independent [QA gate](20261010_implementation_qa.md) also passed. Both
standalone-child addenda were read, then the final query marker, source ownership
and output sinks were rechecked. Temporary session cleanup is independently
verified. **Security gate: PASS.** No security finding blocks package closeout.
Final delivery, deployment and broad-test claims remain owned by the orchestrator.

## Threat model and surface checks

- The existing dashboard route still invokes `authorize` before computing run
  context and FDC metadata. The patch introduces no new route, token, session,
  CSRF exemption, upload, export, file writer or cross-service authorization rule.
  Query Engine admission and scenario transport remain unchanged.
- Daily source names are fixed server/client constants. Source ownership uses
  actual resolved paths and catalog effective paths. Scenario identity is
  checked separately from project containment, preventing same-project aliases
  from becoming false scenario curves. Absolute physical paths are not added to
  browser bootstrap metadata.
- Topology is legitimately shared with the baseline project in normal Omni
  runs. Its permitted boundary is the authorized project, while daily outputs
  and catalogs remain scenario-owned. The checks precede metadata loading;
  ambiguity, missing metadata and malformed Parquets receive an explicit outlet
  unavailable state without discarding valid hillslope curves. Standalone child
  views identify that parent only through the exact established Omni lineage;
  no arbitrary ancestor is admitted.
- Bootstrap uses Jinja `tojson`. New controls, legends, errors and hover output
  use `textContent`, text nodes or canvas text. No scenario/error text is inserted
  as HTML, SQL, executable code or a new network URL. Query dataset/column choices
  are fixed; verified outlet identifiers are supplied as existing query filters.
- Raw queries request complete daily populations, verify returned row counts,
  and do not interpret null values as zero. Failed requests leave the cache;
  raw promises are reused for display/filter changes. Queries are sequential
  within each load. Controller generation checks prevent obsolete results from
  replacing the active graph; correctness review owns full interaction coverage.
- Credentials in the smoke test are read from the existing gitignored
  `docker/secrets/dev-agent.env`. The new test records graph summaries and request
  counts, not password/token contents. No literal credentials were introduced.
  The incidental session export identified by QA is removed from test source;
  temporary state from that export and its regression configuration were removed.
- No queue, worker, shell, dependency, package registry, CI permission, external
  network destination or deployment topology is added. Existing CDN references
  are unchanged. The requested forest restart is a separately recorded operator
  action, not evidence for the data-reader boundary.
- Expected reader errors return a named unavailable state and are logged on the
  server. There are no new broad production exception catches or silent security
  fallbacks in the reviewed patch.

## Valid-state noninterference

No Omni means the baseline remains available. Missing daily files are unavailable
without placeholder curves; absent catalogs can follow existing activation.
Present malformed or mismatched catalogs cannot masquerade as absence. A valid
readonly source and a catalog with `fs_path: null` remain usable. Parent-shared
topology is accepted, but parent-shared daily flow files are rejected. One
invalid source leaves the other source and independent valid scenario curves
usable. Roads receives an explicit unsupported state. No READONLY completion
gate was introduced.

The preimplementation security findings and valid-state commitments are recorded
in [the contract review](20261010_contract_security.md). Security containment
approval does not replace the independent correctness/UX obligations.

## Validation evidence

- Independently ran `wctl run-pytest tests/weppcloud/routes/test_gl_dashboard_flow_duration.py -q`:
  **8 passed** after updating the expected earlier containment error. The first
  run had 7 passes and one message-regex mismatch; the path was correctly denied
  in both runs.
- Repeated that focused command after the standalone-child conformance change:
  **10 passed**. Both `?pup` and composite child metadata selectors retain owned
  daily output with normal parent-shared topology.
- Direct on-disk tests exercise absent/valid catalog state, foreign catalog root
  and pointer, parent-pointing daily/catalog symlinks, base/sibling scenario
  aliases, valid parent network sharing, external topology and NoDb rejection,
  malformed translator Parquets, and Roads behavior. Only unrelated NoDb object
  construction is stubbed in the network parser test; path resolution and actual
  network-file reads are real.
- Independently ran a temporary-directory probe through `wctl exec weppcloud
  python`: missing source is unavailable; a READONLY owned source remains ready;
  a nullable catalog pointer remains ready; each of `hillslopes.parquet` and
  `channels.parquet` symlinked outside the project is rejected before the guarded
  NoDb loader can run. All assertions passed. Temporary files were removed.
- Inspected fixed query construction and safe DOM/template sinks, and verified
  the preimplementation checkpoint's git ancestry. `git diff --check` passed for
  the changed route/template/dashboard scope.
- Correctness/QA reviews and child-view addenda passed; final changes were
  rechecked after those reviews. Direct existence and symlink checks confirm the temporary
  browser session and named regression configurations are absent. No credential
  file contents were printed during this review.
- The orchestrator reports 32 targeted pytest cases, 951 full Jest tests and two
  feature browser tests passed, including both standalone child URL forms. The
  retained [parent browser evidence](browser_evidence.json) contains graph
  summaries for both sources and no application errors. This reviewer inspected
  that evidence but did not independently rerun the browser. Three legacy smoke
  failures were reproduced by the orchestrator with pre-feature checkpoint
  assets; those broader regression dispositions are not security certification.

## Residual risk and boundaries

Readiness and page caches are snapshots. Regeneration or malicious filesystem
replacement during an open page is not transactionally pinned by this feature;
reload after regeneration. This is the explicit existing dashboard limitation,
not a newly claimed query-time race guarantee. Existing Query Engine and NoDb
authorization, activation and trusted metadata serialization are retained, not
certified wholesale by this review.

Source data remains visible through the established authorized project/query
tools. This feature consumes existing artifacts and persists no new model/report
artifact; it introduces no new archive/restore writer. Rain-on-snow exclusion is
visibly disabled rather than applying an unverified classifier. No unresolved
medium/high finding is accepted as residual risk.
