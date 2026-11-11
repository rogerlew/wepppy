# Focused browse output validation

## Boundary and revisions

Base `c040d51d09530dee7f1562c467b98d74c8d6c5a4`; reviewed contract checkpoint
`5e6de201b`. Validation on 2026-11-11 UTC through the existing development
container with `wctl run-pytest`; no deployment. Final implementation revision:
`73d219877` (the exact source/test candidate observed by independent reviewers).

## Red evidence

Command: `wctl run-pytest tests/microservices/test_browse_routes.py -k 'test_browse_listing_escapes or test_browse_directory_breadcrumb or test_browse_action_links or test_browse_not_found_breadcrumb'`.

Exit 1: 8 failed, 27 deselected. Every failure was the structural assertion
`assert not any(tag == 'x-probe' for tag, _ in self.tags)`: actual response HTML
contained the inert test element. HTTP statuses before parsing were expected.
No browser or script execution was used.

## Green evidence

Command (all node IDs share `tests/microservices/test_browse_routes.py::`):

    wctl run-pytest \
      tests/microservices/test_browse_routes.py::test_browse_listing_escapes_filename_and_encodes_entry_links \
      tests/microservices/test_browse_routes.py::test_browse_directory_breadcrumb_escapes_and_encodes_stored_name \
      tests/microservices/test_browse_routes.py::test_browse_listing_escapes_symlink_target_text \
      tests/microservices/test_browse_routes.py::test_browse_action_links_encode_filename_and_preserve_query \
      tests/microservices/test_browse_routes.py::test_browse_not_found_breadcrumb_escapes_reflected_path \
      tests/microservices/test_browse_routes.py::test_run_browse_directory_tree_uses_theme_assets_and_preserves_default_row_colors \
      tests/microservices/test_browse_routes.py::test_directory_includes_parquet_filter_builder_and_parquet_link_attrs

Exit 0: **10 passed**, six existing dependency deprecation warnings, 1.29 seconds
pytest execution. Four suffix variants cover Parquet, raster, annotated and diff
links. Real temporary entries prove labels, parsed href/data attributes, query
preservation, empty child presentation and copy-path attributes. Direct GETs
prove ASCII, Unicode and hostile-name browse/download bytes, nested literal
percent-name bytes, allowed symlink bytes, and Parquet schema output.

## Discoveries and limits

The first green attempt exposed a download fixture omission (its handler has a
separate authorization/context binding), corrected with fixture-scoped patches.
It also demonstrated that URL.path truncates decoded `#`/`?`; the listing now
reads the complete ASGI scope path. Starlette TestClient additionally unquotes
HTTPX's decoded path, so a literal `%23` filename GET uses installed HTTPX
ASGITransport, which preserves exactly-once decoding. These intermediate runs
were not counted as successful validation.

Action hrefs are parsed locally; D-Tale's external service and GDAL execution are
not invoked. Authentication/run-root bindings are fixtures; actual output
renderers, filesystem entries and local byte/schema readers execute unchanged.
Manifest and virtual entries share the tested tuple renderer; archive workflows
were not restored or exercised. JSON APIs and preview-body rendering are outside
this output boundary. Full Python/frontend suites were explicitly not run.
Production-equivalent identity/mount/routing evidence remains the separate M4 gate.

## Source and document checks

`rg -n 'Markup\(|\|safe|listing_html|breadcrumbs_html'` over flow.py, listing.py
and directory.htm confirms literal renderer trust and removal of listing and
breadcrumb handoff casts/filters. Pagination has only urlencode-generated query
values and integer labels; showing text has integer counts and a static note.
The missing-path message already escaped its path; repaired breadcrumbs now
encode diff separately. No JSON, authorization, containment or dependency changes.

`wctl doc-lint --path docs/schemas/browse-filesystem-contract.md --path docs/work-packages/20261110_browse_listing_output_safety --path PROJECT_TRACKER.md`:
11 files validated, zero errors/warnings, exit 0. Final `git diff --check` passed
after removing one trailing Markdown hard-break space on the updated status line.
Spelling-normalization preview used `uk2us`; no prose replacements were needed.
