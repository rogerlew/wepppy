# Make browse filesystem names inert in HTML and links

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, an authorized user can browse a directory containing unusual
or attacker-chosen filenames without those names becoming HTML, attributes, or
new URL structure. The visible name remains faithful to the filesystem, and
ordinary browse, download, preview, D-Tale, schema, CSV, and diff actions still
open the intended entry. A symlink target is displayed only as text.

The proof is deliberately narrow. Focused tests create real temporary files,
directories, and symlinks with HTML-sensitive and URL-sensitive characters,
serve them through the browse test application, and inspect the returned HTML
and link destinations. Per the operator's direction, do not run the full Python
or frontend suites.

## Progress

- [x] (2026-11-11 04:22 UTC) Confirm F3 source paths and the wepp1 production
      boundary.
- [x] (2026-11-11 04:22 UTC) Scaffold the package, contract decision,
      failure-class matrix, and review artifacts.
- [x] (2026-11-11 04:22 UTC) Record the operator's patch-scoped test decision.
- [x] M0: amend the canonical contract, obtain independent correctness/security
      review, and retain a pre-implementation checkpoint.
- [ ] M1: add focused failing tests for labels, links, breadcrumbs, symlink text,
      and action-bearing files.
- [ ] M2: implement one-segment URL encoding and context-aware HTML rendering.
- [ ] M3: run only the approved focused validation and close independent
      correctness, QA, and security findings.
- [ ] M4: perform a separately authorized wepp1-equivalent rollout and closeout.

## Surprises & Discoveries

- Observation: the primary defect is not only filename label interpolation.
  The same raw name is reused in browse, download, raster-info, CSV, annotated,
  D-Tale, schema, and diff URL attributes.
  Evidence: `wepppy/microservices/browse/listing.py:848-947`.

- Observation: the trust bypass occurs after assembly as well as in the row
  builder. `listing_html` is wrapped in `Markup`, and the template applies
  `safe`, so Jinja cannot correct a missed field.
  Evidence: `wepppy/microservices/browse/flow.py:580-589` and
  `wepppy/weppcloud/routes/browse/templates/browse/directory.htm`.

- Observation: filesystem-derived directory breadcrumb labels and links repeat
  the same assembly pattern and are part of the confirmed failure class.
  Evidence: `wepppy/microservices/browse/flow.py:410-457`.

- Observation: JSON files APIs serialize names as JSON data rather than HTML.
  They are not confirmed consumers and do not justify expanding the patch or
  focused tests unless implementation touches them.

## Decision Log

- Decision: fix the output boundary and preserve valid filenames.
  Rationale: a filename allowlist would change filesystem transparency, miss
  other artifact producers, and would not establish correct HTML/URL handling.
  Date/Author: 2026-11-11, operator scope interpreted by Codex.

- Decision: encode each filename as one URL path segment and independently
  escape the completed URL for its HTML attribute context.
  Rationale: HTML escaping alone does not stop `?`, `#`, or separator semantics,
  while URL quoting alone does not make an attribute safe.
  Date/Author: 2026-11-11, Codex; review pending.

- Decision: include stored directory breadcrumbs but defer site-wide CSP.
  Rationale: breadcrumbs are a confirmed consumer of the same unsafe trust
  assumption. CSP is a separate site-wide compatibility/rollout decision and is
  defense in depth, not a substitute for encoding.
  Date/Author: 2026-11-11, Codex; review pending.

- Decision: run only patch-scoped tests.
  Rationale: the operator explicitly requested scoped validation and no full
  suite. Exact test node IDs and affected existing controls will be retained.
  Date/Author: 2026-11-11, operator.

## Outcomes & Retrospective

The source diagnosis and implementation board exist. No production code, tests,
or runtime configuration changed in the scaffold milestone. M0-M4 remain open;
no local validation or production claim is made.

## Context and Orientation

Work from `/home/workdir/wepppy`. Read the root `AGENTS.md`,
`wepppy/microservices/browse/AGENTS.md`, and `tests/AGENTS.md` before editing.
The canonical behavior is in `docs/schemas/browse-filesystem-contract.md`.

The browse microservice reads a directory and formats each entry as a tuple.
`wepppy/microservices/browse/listing.py:html_dir_list()` turns those tuples into
HTML rows. A filesystem entry name is used both as visible text and as part of
several links. A symlink target is appended as visible text. These are different
output contexts: visible text needs HTML escaping; a name inside a route needs
URL path-segment encoding; the finished route inside an `href` or `data-*`
attribute also needs HTML attribute escaping.

`wepppy/microservices/browse/flow.py:_render_directory_response()` obtains the
listing and passes it to
`wepppy/weppcloud/routes/browse/templates/browse/directory.htm`. Today both the
Python handoff and template broadly declare the assembled strings safe. The same
flow module builds breadcrumbs from filesystem path components. The safe design
must keep intentional anchor/span markup while ensuring that every dynamic field
is encoded for its own context before any final trusted-markup object exists.

In this plan, a "path segment" means one filename between URL `/` separators.
Percent encoding turns bytes with URL syntax into `%HH` sequences. Use
`urllib.parse.quote(value, safe="")` for an entry name so no character in the
name is treated as path structure. Do not call `quote()` on an already encoded
name. Query values such as `diff` and `pqf` continue to use `urlencode`.

The primary route tests are in
`tests/microservices/test_browse_routes.py`. Its `load_run_browse` fixture maps a
run ID to a real `tmp_path` directory while stubbing only authorization. Keep
new tests in this module unless a small renderer is extracted into a module that
deserves direct unit tests. Do not add a browser, network, or external service
dependency.

## Plan of Work

### Milestone 0 - Ratify the boundary

Amend `docs/schemas/browse-filesystem-contract.md` with the normative rules from
`artifacts/20261110_contract_decision.md`: filesystem-derived labels and symlink
targets are text; entry names in routes are exactly one encoded segment; query
values are encoded separately; and intentional markup may be trusted only after
all untrusted fields are contextually encoded. State explicitly that valid names
are not filtered or renamed and JSON APIs remain JSON data.

Have independent correctness and security reviewers inspect the contract and
`artifacts/20261110_failure_class_matrix.md`. Record review identity, revision,
findings, and disposition. Retain a checkpoint revision containing the contract
and reviewed plan before production-code changes. Update `Progress`, `Decision
Log`, and `tracker.md`.

Milestone acceptance is a reviewed canonical rule and a clean checkpoint; no
runtime behavior changes yet.

### Milestone 1 - Retain focused red evidence

Add focused tests to `tests/microservices/test_browse_routes.py`. Use actual
files and directories under `tmp_path`. Use a compact corpus that jointly covers
`&`, `<`, `>`, both quote types, spaces, `#`, `?`, `%`, Unicode, and Unicode
slash/backslash lookalikes. Do not place a literal `/` in one filename. Create a
real symlink where `os.symlink` is available and use the existing skip style.

Add these behaviors with stable names:

- `test_browse_listing_escapes_filename_and_encodes_entry_links` proves an inert
  filename appears as text and the primary browse/download links contain one
  encoded segment, not a new element, attribute, fragment, or query.
- `test_browse_directory_breadcrumb_escapes_and_encodes_stored_name` enters a
  real directory and proves both its parent row and nested breadcrumb are inert
  and navigable.
- `test_browse_listing_escapes_symlink_target_text` proves the displayed target
  cannot form markup and that existing symlink navigation policy is unchanged.
- `test_browse_action_links_encode_filename_and_preserve_query` uses an
  action-bearing suffix, preferably Parquet with existing lightweight fixture
  patterns, and checks every action/data URL produced by the changed code.
- If the not-found renderer is changed, add one reflected-path regression for
  it; otherwise document source review and leave that separate path untouched.

Parse anchors with a standard-library `html.parser.HTMLParser` helper or another
already-installed parser. Do not add a dependency. Assert structure and decoded
attributes rather than relying only on the absence of one literal payload. Also
assert direct GETs for the ordinary and Unicode controls so encoding correctness
is proven, not merely string shape.

Run only the new node IDs. Before the fix, expect assertions showing an injected
element/attribute or unencoded link. Retain the concise failure output in a
validation artifact. A test that fails because of a fixture or URL construction
mistake is not red evidence; correct the test and rerun before implementation.

### Milestone 2 - Implement the narrow renderer

In `wepppy/microservices/browse/listing.py`, add one small URL-segment helper
using `urllib.parse.quote(name, safe="")`. Build each entry URL by appending that
encoded name to the current trusted route path. Ensure the current route path is
encoded once: Starlette exposes a decoded request path, so verify this fact with
the red tests before choosing whether to encode the whole existing path or to
rebuild its filesystem suffix from known path components. Never quote an
already-encoded segment, and never use `os.path.join` to grant filename data URL
separator semantics.

Build intentional HTML from literal markup and escaped dynamic values. The
preferred bounded implementation is a small `markupsafe.Markup` renderer whose
`format()` placeholders receive raw display strings and completed URLs, because
`Markup.format()` escapes placeholder values while retaining only the literal
format string as markup. Equivalent Jinja partials are acceptable if they keep
the patch smaller and all default autoescaping intact. Do not concatenate a raw
filesystem value into a `Markup` object. Keep alignment widths based on original
display strings, not escaped entity lengths.

Apply the helper to directory, primary file, download, raster/CSV, annotated,
D-Tale, schema/data, and diff links. Keep suffix dispatch based on the original
filename. Keep `urlencode` for `diff`, `pqf`, sort, and page values, then escape
the completed URL when it enters an HTML attribute.

In `wepppy/microservices/browse/flow.py`, render stored breadcrumb labels with
the same text rule and build breadcrumb routes from encoded path segments. Keep
the already escaped copy-path and filter attributes. Remove the broad
`env.Markup(listing_html)` trust conversion; instead pass the narrow renderer's
safe result or let Jinja render structured data. Remove the corresponding
template `safe` filter if the value no longer requires it. Do the same for
breadcrumbs. Intentional static pagination/showing markup may remain only after
review confirms it contains no untrusted raw field.

Inspect `wepppy/microservices/browse/browse.py:_path_not_found_response()` with
the focused red case. If it reproduces the same injection or shares the new
helper cleanly, repair it in the same patch. If it cannot reproduce and would
require unrelated refactoring, record that evidence in the failure matrix and
do not expand the implementation.

Update the canonical contract status and directly affected browse documentation.
Do not change Bootstrap, files JSON APIs, auth, containment, CSP, frontend
JavaScript, or dependencies.

Milestone acceptance is that the red tests pass, normal controls pass, and the
diff contains only the renderer, its template/handoff if needed, the focused
tests, and directly affected documentation.

### Milestone 3 - Focused validation and independent review

From `/home/workdir/wepppy`, run the exact new node IDs and affected controls.
The expected command shape is:

    wctl run-pytest \
      tests/microservices/test_browse_routes.py::test_browse_listing_escapes_filename_and_encodes_entry_links \
      tests/microservices/test_browse_routes.py::test_browse_directory_breadcrumb_escapes_and_encodes_stored_name \
      tests/microservices/test_browse_routes.py::test_browse_listing_escapes_symlink_target_text \
      tests/microservices/test_browse_routes.py::test_browse_action_links_encode_filename_and_preserve_query \
      tests/microservices/test_browse_routes.py::test_run_browse_directory_tree_uses_theme_assets_and_preserves_default_row_colors \
      tests/microservices/test_browse_routes.py::test_directory_includes_parquet_filter_builder_and_parquet_link_attrs

Adjust only for the exact test names retained by M1 and add a not-found node only
if that path changes. If an extracted renderer receives its own test module, run
that module plus the route node IDs. Do not run `tests/microservices` broadly,
the full Python suite, npm lint, or npm test.

Run scoped source and documentation checks:

    rg -n "Markup\(|\|safe|listing_html|breadcrumbs_html" \
      wepppy/microservices/browse/flow.py \
      wepppy/microservices/browse/listing.py \
      wepppy/weppcloud/routes/browse/templates/browse/directory.htm
    wctl doc-lint --path docs/schemas/browse-filesystem-contract.md \
      --path docs/work-packages/20261110_browse_listing_output_safety \
      --path PROJECT_TRACKER.md
    git diff --check

Record command, revision, exit status, test counts, red/green distinction, and
limitations in a validation artifact. Update every confirmed row in the
failure-class matrix with a test or source-review disposition.

Obtain independent correctness/UX, QA/code-quality, and security reviews. The
security reviewer must verify element/attribute/path/query separation and close
all High/Medium findings. The correctness reviewer must verify empty, ordinary,
Unicode, hostile, symlink, action-bearing, diff, and missing-path states as
applicable. Do not substitute security approval for valid-state approval.

Milestone acceptance is focused green evidence, scoped docs lint, a clean diff
check, and all review gates passing. The full suite remains waived and must be
reported as not run.

### Milestone 4 - Separately authorized rollout

This scaffold does not authorize deployment. If the operator later authorizes a
wepp1 rollout, first inspect `scripts/deploy-production.sh`, the current `wctl`
preset, and the nearest deployment documentation. Exercise the real service
identity, mounts, routing, and template artifact through the canonical deploy
flow. Use only ordinary and punctuation/Unicode controls in production; do not
create or browse a script-like payload on wepp1.

Verify an ordinary directory listing and action link, retain response headers
and rendered HTML evidence without private identifiers, and confirm rollback
will not knowingly restore unsafe output handling. Update the plan, tracker,
security review, and audit board only after production-equivalent evidence
exists.

## Concrete Steps

All commands run from `/home/workdir/wepppy`.

1. Re-read local instructions and establish the base:

       git status --short
       git rev-parse HEAD
       sed -n '1,240p' wepppy/microservices/browse/AGENTS.md
       sed -n '1,260p' tests/AGENTS.md

2. Complete and review M0. Lint only the changed contract/package docs and
   retain a checkpoint before code edits.

3. Add M1 tests with `apply_patch`, run only their node IDs, and retain valid red
   evidence.

4. Implement M2 with `apply_patch`. Preserve unrelated dirty worktree changes
   and never modify
   `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.

5. Run the M3 command set, update artifacts, and obtain independent reviews.

6. Stop before M4 unless deployment is explicitly authorized.

## Validation and Acceptance

Acceptance is behavioral:

- A response containing a filesystem name with HTML-sensitive characters has
  the same DOM structure as an ordinary row, with the characters only in text.
- An anchor for a name containing URL-sensitive characters has one encoded
  filename segment. Parsing its URL shows no attacker-created fragment, query
  key, authority, or extra path segment.
- Following the encoded link returns the intended file or directory.
- A nested directory's breadcrumb is inert and still navigates correctly.
- A symlink target is visible as text and cannot create an element or attribute.
- Every changed action link retains its route, query state, and current
  capability decision.
- Empty and ordinary directory presentation remain unchanged.
- Focused tests and scoped documentation checks pass. Full Python/frontend
  suites are explicitly not run.

Do not use browser script execution as validation. Structural assertions over
inert local strings are sufficient and safer.

## Idempotence and Recovery

Temporary test entries live under pytest's `tmp_path` and are deleted by the
test harness. Re-running focused tests is safe. The code change has no migration,
state mutation, or dependency installation.

If encoding breaks a valid link, first inspect whether the current path was
encoded twice; do not weaken HTML escaping or add a decode/retry fallback. If a
structured renderer proves incompatible with an existing action, revert only
the incomplete local patch and retain the red tests and contract checkpoint.
Do not hide the problem with a filename allowlist.

For a deployed regression, use the canonical production rollback only if the
restored revision retains equivalent output safety. Otherwise retain the
security patch and roll back unrelated changes separately. Record any temporary
containment and its owner/expiry.

## Artifacts and Notes

The starting implementation base is `c040d51d0`. The worktree also contains
unrelated user changes; preserve them and scope all diffs by path. The local
security audit board is gitignored and is not an approved public disclosure.

Required package artifacts at closeout are the contract decision and reviews,
updated failure-class matrix, focused validation receipt, correctness review,
QA review, security review, and optional separately authorized rollout receipt.

## Interfaces and Dependencies

Use only dependencies already present in the service:

- `urllib.parse.quote(value, safe="")` for one filename path segment;
- `urllib.parse.urlencode` for query values;
- Jinja autoescaping or `markupsafe.Markup.format()`/`markupsafe.escape()` for
  HTML contexts;
- standard-library `html.parser.HTMLParser` for structural test assertions if
  an existing installed parser is not already used nearby.

Do not introduce a sanitizer, URL builder package, browser harness, service,
queue, datastore, or CSP middleware. Keep `html_dir_list()`'s observable return
contract or change it only as needed to carry a narrowly safe markup result into
`_render_directory_response()`. Preserve current route layouts for runs, batch,
culverts, Omni scenarios, and supported virtual entries.

## Revision Note

2026-11-11: Initial ExecPlan created for F3. It records the confirmed breadcrumb
consumer, selects contextual output encoding instead of filename restriction,
defers CSP, and limits validation to patch-scoped browse tests per operator
direction.

2026-11-11 M0: canonical amendment reviewed by independent correctness and
security agents; missing-path consumer confirmed and included. Scoped doc lint
passed (8 files). Required standalone checkpoint follows before code edits.
