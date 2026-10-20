# Explain water outputs and make the explanation discoverable

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Users comparing multiple overland flow elements (OFEs, sequential sections of a hillslope) need to know which depths refer to a section and which represent the entire hillslope. After this change, Results links to a user guide and column reference; Usersum search finds both. The run-specific README explains what its previews and metadata can establish.

## Progress

- [x] (2026-10-20 UTC) Audit and scope captured.
- [x] (2026-10-20 UTC) Canonical amendment and two reviews committed as `14c7eebb1`.
- [x] (2026-10-20 UTC) Interpretation/reference guides, description metadata, and interface corrections implemented; native release `3b63064`.
- [ ] Generated artifact, discovery, regression and independent correctness evidence.
- [ ] Close package and update project tracker.

## Surprises & Discoveries

The generated Usersum index was dirty before work began and must not be overwritten. Python and native Arrow schemas independently contain misleading Q/QOFE/Area descriptions. Updating only the prose would leave misleading downloaded metadata.

## Decision Log

On 2026-10-20 the operator authorized executing the audited documentation corrections. Preserve scientific calculations and field identities; describe their current contract instead. Use existing Usersum Technical Reference navigation and existing prefix-safe link helpers. Do not sync historical vendor sources as part of this work.

## Outcomes & Retrospective

Implementation and generated Parquet metadata parity are established. Runtime index publication awaits an explicit operator exception. Completion requires evidence from rendered documents and generated files, not merely source edits.

## Context and Orientation

The audit at `docs/dev-notes/20261020_water_output_documentation_audit.md` lists twelve defects and source locations. `docs/schemas/hillslope-water-aggregation-contract.md` and ADR-0099 govern science. Local ET and deep percolation are area weighted per day; terminal Q already represents physical hillslope depth; terminal latqcc requires terminal area divided by full hill area. PASS runoff is threshold-filtered delivery. Internal transfers and storage cannot be indiscriminately summed for closure.

Usersum content lives in `wepppy/weppcloud/routes/usersum/weppcloud/`, registration in `docs_manifest.yaml` and `nav_tree.yaml`, and generated discovery in `generated/docs_index.json`. Results templates live in `wepppy/weppcloud/templates/controls/wepp_reports.htm` and report templates in `templates/reports/wepp/`. `wepppy/wepp/interchange/interchange_documentation.py` produces README previews from Arrow metadata. Python hill schemas and `/workdir/wepppyo3/wepp_interchange/src/schema.rs` must agree.

## Plan of Work

First amend the Usersum specification with the bounded publication contract and record the decision and valid-state matrix. Obtain two independent read-only reviews required by the contract-first standard; disposition findings and commit this checkpoint before template changes.

Next publish `water-balance-and-runoff.md` and `water-pass-variables.md`, register both for user visibility under Technical Reference, and link them from existing guides, Results and water report descriptions. Include a two-OFE example (areas 250/750 square meters, ET 2/6 mm gives 5 mm; terminal lateral 6 mm gives 4.5 mm; terminal Q 8 mm stays 8 mm). Explain daily versus hourly, PASS events, denominators, signs, stocks, missing records, version provenance and known limitations. Verify uncertain variable meanings against native writers rather than inventing definitions.

Correct misleading metadata in Python and native schemas without altering names, types or numeric data. Rebuild and validate the paired native artifact according to its repository instructions. Improve generated README guidance while preserving its three-row streaming preview. Fix broken links and stale conformance status in current docs; leave historical packages/vendor copies intact.

Finally validate fresh catalog/search and rendered links using existing tests and actual generated README/Parquet artifacts in scratch space. Preserve existing run files and unrelated dirty work. Obtain independent correctness review and close every medium/high finding before closure.

## Concrete Steps

From `/workdir/wepppy`, run `wctl run-pytest` on the affected interchange documentation/schema and Usersum/report tests. Run `wctl doc-lint --path <changed markdown>` and preview `uk2us` spelling diffs. Validate manifests with `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate --require-vendor-files`. Build a fresh index with vendor sync disabled into temporary storage to check user-role discovery without clobbering the dirty index. Record exact executed checks and outcomes in `artifacts/20261020_validation.md`.

## Validation and Acceptance

Both guides must render for normal user role and be found for latqcc, QOFE, SUBEVENT, ET and deep percolation. Results keeps run-specific README conditional on existence but provides interpretation help without it. Single-storm and continuous, baseline and Roads links retain scope. The existing numerical aggregation suite remains green. Metadata must be read from Parquet generated by the rebuilt native artifact, not only mocked Python schemas. Generated README must work with missing manifests and old metadata without implying historical results are corrected. Test existing prefix handling and route gates unchanged.

## Idempotence and Recovery

All documentation additions are reversible. Save the initial dirty index separately before any isolated comparisons; never restore over someone else's new changes. Generate artifacts only in scratch directories. Native release restoration uses the recorded original revision/artifact, without changing unrelated model binaries. No production writes or deployment.

## Artifacts and Notes

Retain checkpoint reviews, disposition, validation and final correctness review under this package's artifacts directory. Record checkpoint ancestry and the native release provenance in tracker. Closed prior packages are evidence only.

## Interfaces and Dependencies

Use existing Usersum helpers, Arrow schemas, Markdown renderer, wctl and native release tools. No signatures, file columns, authorization policies, network services or dependencies change. Metadata descriptions are compatible descriptive corrections, and existing old-file metadata is not silently rewritten.

## Checkpoint review refinements (2026-10-20 UTC)

Review identified the stale generated index as a publication blocker. Explicit operator permission to edit the dirty index is pending. If granted, back it up and merge only the package's affected entries from a fresh build without vendor sync, then validate the actual newly loaded catalog; otherwise record discovery publication as incomplete. A deployment must reload process catalog caches. Temporary index validation is not active-runtime discovery evidence.

Machine-readable unit edits can change downstream values and names. Restrict this package to description metadata; document verified physical units and explicitly identify inherited machine-label defects. Correcting those labels requires separately scoped conversion/suffix/cache compatibility evidence. Usersum AGENTS now explicitly names specification.md as canonical.

The final discovery check found that the existing in-memory search matches ET
inside unrelated words such as parameters and getting. The reference title now
adds the descriptive subtitle “ET, Dp and runoff” so it appears on the first
results page for ET without altering the search engine. This is document-authoring
within the approved publication scope; no ranking or authorization logic changes.
