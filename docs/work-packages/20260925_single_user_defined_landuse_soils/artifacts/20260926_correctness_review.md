# Runtime correctness and UX review

Independent reviewer: `review_upload_work_package`. Scope: current uncommitted
SUDI-01 implementation, with focused readback of UI corrections, independent input
modes, generated artifacts, reports and lifecycle acceptance. Review date:
2026-09-26. Runtime files were not edited by this reviewer.

## Findings

| ID | Severity | Evidence and user impact | Required correction | Status |
| --- | --- | --- | --- | --- |
| COR-R01 | Medium | `wepppy/weppcloud/templates/reports/landuse.htm:58-67` rendered only static `landuseoptions` in the mapping select. The new `single-user-defined` summary key had no option, so the browser selected an unrelated first catalog entry. `controllers_js/landuse.js:556-565` recorded that value as the current mapping, both misrepresenting the source and preventing an intentional change to that first option from being staged. | Render a selected current-source option for the uploaded summary while retaining catalog alternatives. Verify the selected value and staging a remap to the first catalog choice. | Closed: selected escaped source option confirmed; independent render test and controller staging regression passed |
| COR-R02 | Medium | `wepppy/weppcloud/routes/nodb_api/wepp_bp.py:624-680` obtained a retained Disturbed controller and rendered disturbance-adjusted management without checking the upload policy. `routes/nodb_api/landuse_bp.py:653` advertised the preview based only on module IDs. The canonical exclusion covers reports and retained controllers as well as the main page. | Reject the excluded effective-management preview before Disturbed lookup and suppress its report links under the immutable policy. Preserve ordinary management viewing and legacy previews. | Closed by readback: endpoint, landuse report and all three hill/preparation report call sites enforce policy; independent endpoint rejection test passed |

No remaining correctness or UX blocker was found in the bounded reviewed paths.
This verdict closes the reported code findings; it does not substitute for the
remaining repository gates or authorize deployment. The preexisting fork
limitation below remains explicitly unresolved. The subsequent
[QA review](20260926_qa_review.md) also closes numeric-underflow admission,
contractual boundary coverage and native contour/drainage reference findings.

## Previously reported findings

Source readback confirms corrections for these earlier findings:

- Restored landuse/soil controllers now retain their numeric mode before Build,
  preserving mode-5 file transport and legacy mode-4 raster uploads after reload.
- Initial run sections, header options and bootstrap controller flags enforce
  exclusions, including the load-all override.
- The Disturbed-only Rosetta override checkbox is hidden for opted-in projects;
  independent soil depth and saturation controls remain.
- MOFE guidance no longer claims that every supported mode requires a raster.
- Core corrections retain ordinary Forest2006/Tenerife soil handling, numeric OFE
  ordering, active management initial-condition references and strict policy
  token parsing.
- Uploaded and opted-in catalog managements now preserve native contour/drainage
  references through summary reload, segment materialization, synthesis, year
  expansion and preparation. The explicit reference flag is independent of
  strict source validation, preserving later catalog remaps and legacy parser
  defaults. Both synthesis remappers follow each reference's actual section.

Accepted-file feedback uses the existing Pure/SBS label, display and code macros,
escapes the filename, and remains outside the hidden read-only upload wrapper.
The landuse and soil modes use separate form fields and source metadata.

## Evidence and limits

The reviewer inspected the retained [upload/job evidence](20260926_upload_job_acceptance.json)
and [native execution evidence](20260926_native_acceptance.json), plus the focused
artifact tests. The native evidence covers two and twelve OFEs, generated-input
hashes, nonempty outputs and the service identity. The topology and climate are
controlled fixtures. These records do not prove a complete browser workflow or
every supported management section boundary.

The implementation owner reports passing focused route/render and controller
tests, broader Jest coverage and archive round-trip acceptance. This reviewer
independently ran the two new report-source/preview pytest regressions: **2 passed**,
with four existing deprecation warnings. The landuse controller suite also
independently passed **25 tests**, including remap staging and restored upload
modes 4 and 5. These targeted checks do not repeat the broader owner-run suites.
The reviewer subsequently added asymmetric contour-only, drain-only and distinct
mixed-reference regressions, then independently ran
`tests/wepp/test_single_input.py` and `tests/wepp/test_single_input_references.py`:
**52 passed**, including all 13 new reference cases and three native executions.
These check referenced scenario values after preparation, not only parse success.

Full pytest and closeout remain in progress; this review does not claim an overall
repository pass. Browser coverage and its limits are recorded in the QA review.
The owner reports the independent security findings closed; that status is
governed by the [security artifact](20260925_runtime_security_review.md). Complete
the remaining required gates, retain regression evidence and re-review any
subsequent material source changes before overall release approval.

## Preexisting fork limitation found during acceptance

The first fork target appended `-fork` to the source run ID. The existing
`wepppy/rq/project_rq_fork.py:1220` performs successive working-directory and
run-ID string replacements. The second replacement rewrites the already replaced
destination when it contains the source ID, producing `-fork-fork` paths.

Independent inspection of that fork's persisted landuse and soils summaries found
both generated-file paths pointing to the nonexistent doubled destination; the
files exist at the actual single-suffix destination. NoDb hydration repairs only
the controller's top-level working directory. Relative raw-source hashes passing
therefore does not establish functional management or soil summary access.

This generic relocation defect predates SUDI-01. The implementation owner elected
to preserve scope, retain this limitation and rerun acceptance with an unrelated
destination ID, including actual management loading and soil summary path checks.
The first target must not count as a successful functional fork. This review does
not claim that the preexisting prefix-target defect has been repaired.

The [rerun](20260926_fork_acceptance.json) targeted `single-input-copy-20260925`
and recorded a finished fork job.
The reviewer independently confirmed that both persisted summary directories now
match the actual destination and their generated files exist. The acceptance script
also loads each copied management and checks soil summary file paths, in addition
to checking immutable source bytes and policy. This establishes the ordinary
unrelated-target path; it does not remove the prefix-target limitation.
