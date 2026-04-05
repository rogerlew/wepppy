# usersum/AGENTS.md
> Agent guide for `wepppy/weppcloud/routes/usersum/`.

## Purpose
- Keep Usersum docs/routes behavior predictable for end users and for in-repo markdown references.
- Capture the canonical link-resolution contract for Usersum markdown pages.

## Scope
- Applies to:
  - `wepppy/weppcloud/routes/usersum/usersum.py`
  - `wepppy/weppcloud/routes/usersum/templates/usersum/*`
  - developer authoring guides:
    - `wepppy/weppcloud/routes/usersum/weppcloud/enduser-authoring-guide.md`
    - `wepppy/weppcloud/routes/usersum/weppcloud/enduser_stub_authoring_guide.md`
  - Usersum markdown content roots:
    - `wepppy/weppcloud/routes/usersum/db/`
    - `wepppy/weppcloud/routes/usersum/input-file-specifications/`
    - `wepppy/weppcloud/routes/usersum/weppcloud/`

## Link Resolution Contract (Required)
- Usersum renders markdown via `cmarkgfm`, then rewrites markdown anchor `href` values for in-repo `.md` links.
- Canonical source-doc route:
  - `GET /usersum/src/<path:rel_path>`
- Legacy compatibility route:
  - `GET /usersum/src//<path:rel_path>` -> permanent redirect (`308`) to canonical `/usersum/src/<path:rel_path>`.
- Rewriter behavior:
  - External links (`http`, `https`, other schemes) are unchanged.
  - Non-markdown links are unchanged.
  - In-repo markdown links are resolved relative to the source markdown file (or repo root for `/...` paths).
  - If target is under a Usersum category root, link is rewritten to:
    - `/usersum/view/<category>/<filename>`
  - Otherwise, in-repo markdown targets are rewritten to:
    - `/usersum/src/<repo-relative-path>`

## Authoring Rules For Usersum Markdown
- Prefer normal repo-relative markdown links (for example `../../../../nodb/mods/openet/README.md`).
- Do not hardcode `/nodb/...` or other non-usersum absolute app paths for markdown docs.
- Do not hand-author `/usersum/src//...` links; canonical route is single-slash `/usersum/src/...`.
- Keep links as `.md` targets when you want usersum rendering; rewriter only promotes markdown links.

## Validation
- Route-level regression tests:
  - `tests/weppcloud/routes/test_usersum_bp.py`
- Template/shell wiring tests:
  - `tests/weppcloud/test_usersum_template_wiring.py`
- Run after usersum route/template/link logic edits:
  - `wctl run-pytest tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py`
