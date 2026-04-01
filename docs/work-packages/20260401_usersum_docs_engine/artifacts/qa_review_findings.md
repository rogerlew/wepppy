# QA Review Findings - Usersum Docs Engine

Review date: 2026-04-01  
Reviewer: Codex (QA verification pass)  
Scope: functional + UX validation for usersum routes, templating, search behavior, and contract tooling.

## Findings (ordered by severity)

1. Medium - Header/search layout did not match target behavior.
Symptoms: usersum shell not full width; search appeared left of theme selector; search controls misaligned vertically with theme selector.  
Resolution: moved header search to the right of theme selector, removed label text, aligned controls, and switched to theme-aware control/button styling.

2. Medium - Sidebar visual tokens were hardcoded.
Symptoms: `wc-usersum-sidebar` background stayed white regardless of theme; overflow scrollbar was not theme-aware.  
Resolution: migrated sidebar/nav colors to theme CSS variables and added themed scrollbar styling.

3. Medium - Search snippets were escaped.
Symptoms: highlighted preview markup rendered as escaped HTML entities.  
Resolution: render snippet with `|safe` in search template, preserving intended highlight output.

4. Medium - Canonical doc links failed under prefixed deployment.
Symptoms: links like `/usersum/doc/<doc_id>` failed behind `/weppcloud` prefix, while legacy prefixed links resolved.  
Resolution: switched usersum route URL generation and template links to `url_for_run(...)`, added regression test for prefixed links.

## Final Disposition

- High findings: 0
- Medium findings: 4 (all resolved)
- Low findings: 0
- Unresolved medium/high: none

## Validation Evidence

- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate` -> PASS
- `PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate --require-vendor-files` -> PASS
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py --maxfail=1` -> PASS
- `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1` -> PASS
- `wctl run-npm lint` -> PASS
- `wctl run-npm test` -> PASS
- Broad-suite baseline run during package execution:
  - `wctl run-pytest tests --maxfail=1` -> `2971 passed, 36 skipped`
