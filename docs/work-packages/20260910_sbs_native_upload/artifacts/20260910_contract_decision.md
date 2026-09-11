# Contract checkpoint

Base f59d18942; intended native-required failure policy and bounded HTML error
presentation changes. Operator explicitly requested removal, UI fix and work
package execution; this includes required checkpoint commit, not pushing.

Affected canonical contracts: SBS raster contract, SBS control contract, shared
controller contract's linked SBS exception, ADR-0065. NoDb/CSRF/access/RQ response
contracts remain unchanged. Rationale and exact deltas are in those contracts.

Compatibility/regression plan: delete silent native fallback and duplicate raster
loops, preserve public operation signatures and native numerical output; compare
actual Wallow and analytical class/NoData rasters. Test missing module/API and
native failure explicitly, never hide errors or cache failures. Validate absent,
empty, populated, replaced and malformed rasters; normal/custom palettes.

UI states: initial/no map, uploading, success, JSON validation error, HTML gateway
timeout, summary-fetch failure, prior results during failed replacement and later
success. Details must render inert formatting only. Malicious scripts, resource
URLs, attributes, SVG, forms and custom elements must not enter live DOM.
No errors in hints/Summary. Preserve valid SBS result markup and filename reload.
Dedicated security review required. Focused Python/Jest tests and actual browser
Wallow upload through existing identities/proxy are acceptance; full suite
explicitly excluded. Independent reviews pending.

Security review refinement: finite tag list, detached inert template parse, fresh
attribute-free HTML elements/text only, subtree discard; raw HTTP text/html string
body selects HTML rendering, never a JSON message string. No network-capable
source nodes are inserted/imported/cloned.

Correctness review refinement: retain last accepted Summary during failed
replacement. Audit run/HUC/batch/Flask native failure boundaries. Batch summary
currently logs and returns success; include narrow explicit-error translation
there, with unchanged access/limits/cleanup. Fractional/NaN source NoData needs
real native parity tests; do not assume integer casts preserve those masks.

Both independent contract reviews approve after the documented HTML parsing,
batch failure-boundary and prior-Summary retention amendments. No unresolved
medium/high findings. Native-required/UI runtime implementation has not started.
