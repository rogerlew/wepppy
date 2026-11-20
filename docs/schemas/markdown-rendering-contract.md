# WEPPpy Markdown rendering contract

Implementation conformance is pending.

The Usersum viewer and search snippets, Usersum vendor and link tools,
project README preview and viewer, and Browse Markdown previews use one
Python rendering adapter backed by Comrak. The runtime and Docs Quality
use the same pinned Python binding. A missing parser is an installation
error. Existing route authorization, README size limits and template
processing, and Browse response behavior remain in effect.

The default profile supports CommonMark, GFM tables, task lists,
strikethrough and autolinks. Code fences retain the language on the
`pre` element for existing styles. The renderer omits source-supplied
raw HTML and suppresses unsafe URL schemes for both links and images.
Comrak formatting differences are acceptable where content, accessibility,
navigation and security semantics are preserved.

The Python adapter allows trusted callers to opt into reviewed Comrak
extensions per render. The initial options are alerts, description lists
and footnotes. Request parameters and document content cannot
enable options or supply rendering callbacks. The adapter owns render options and does not accept native render options
or arbitrary AST mutations. It supports structured link inspection and
a narrow destination callback on parsed link nodes. No callback or
extension can return raw markup. Browse and project README use direct
rendering without a Python AST round trip. Link URL rewrites run before
Comrak applies its URL rendering policy. A rewrite changes the
destination while retaining the parsed link label and title. Images
and literal code retain their existing treatment.

Usersum keeps its published heading ID algorithm and computes lint IDs
with that same rule. Runtime URL resolution and build-time discovery
use the same parsed link semantics. Existing manifest access, canonical
links, source routes, fragment handling, query strings, vendor
provenance and missing-target warnings continue to apply.

Dependency evaluation must identify the native Comrak crate bundled in
the wheel. The Rust crate and Python distribution have independent
versions. Maintain one mandatory renderer so fixes and safe defaults
apply consistently across entry points.
