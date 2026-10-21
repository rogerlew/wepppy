# Water output documentation tracker

Status: Closed 2026-10-21 UTC. No production deployment or push.

## Revisions and deliverables

Starting WEPPpy `1ecf04735`; contract checkpoint `14c7eebb1` with two independent
reviews; source implementation `b47b768d7`; paired native release `3b63064`.
Two user guides, native/Python descriptions, Results/Roads/report/dashboard/export
help, current-doc corrections, and Usersum catalog publication are complete.
Plan: [water_output_documentation_execplan.md](prompts/completed/water_output_documentation_execplan.md).

## Publication decision and evidence

The operator explicitly authorized the dirty-index update and commit. Four
package-owned entries were added/refreshed; all 74 other entries and their order
were preserved. Existing index changes are included in the commit, with a
byte-for-byte prepublication backup. No vendor sync occurred. The current
scheduled task sets write_index:false; the origin of earlier index dirt remains
unverified. A fresh process using the unmodified runtime loader rendered both
guides and all seven searches successfully from the published repository index.

## Validation and review

Independent scientific and UX reviews closed all medium/high findings; the
publication reviewer separately confirmed preservation, source hashes and nav.
Focused publication suite: 66 passed. Native: 163 Python, 107 Rust unit and 17
integration passed. Frontend: 987 passed. Broad validation completed in resumed
chunks: 499 completed-file passes before the initial hash-test failure, 10,299
passes in the next chunk, and final 186 + 60 passes. The corrected startup test
and dashboard fixture passed on resumption. The final browser test required the
installed Chromium path in its environment; no application change was needed.
Three extra discovery cases added after broad collection also pass in the focused
suite. See [validation](artifacts/20261020_validation.md) and
[review](artifacts/20261020_correctness_review.md) for boundaries and caveats.

## Remaining operational boundaries

Production publication uses the normal deployment/reload workflow. Old output
files and report caches are not rewritten. Machine-unit metadata compatibility
work remains separate: the variable reference documents correct physical units
and inherited label defects. No scientific formulas or numerical behavior changed.
