# Native SBS upload contract security review

## Findings

| ID | Severity | Surface and evidence | Required action and disposition |
| --- | --- | --- | --- |
| SNU-C01 | Medium | Untrusted gateway HTML crosses into the authenticated run-page DOM. Merely saying "off-document parse" does not establish that parsing cannot load resources or that source nodes cannot later become active. | Resolved in the SBS control contract: parse in a detached inert HTML template; construct only fresh allowlisted HTML elements/text nodes; copy no attributes or source nodes; discard active/resource, foreign-namespace and custom-element subtrees. |
| SNU-C02 | Low | `disturbed.js` and `baer.js` normalize raw HTTP bodies into `error.message`. Formatting every message that resembles markup would also reinterpret ordinary JSON diagnostics. | Resolved in the contract: formatting applies only to a raw string HTTP failure body with `text/html` Content-Type. JSON messages and stacktraces remain text. The existing HttpError retains the response and raw body, so no shared HTTP redesign is necessary. |

No unresolved medium/high contract findings. No risk acceptance is requested.

## Verdict and review context

**Pre-implementation security contract gate: pass.** Independent reviewer:
Codex `contract_security`, 2026-09-10. Starting revision: `f59d18942`.
Reviewed the [checkpoint](20260910_contract_decision.md),
[SBS raster contract](../../../schemas/sbs-raster-contract.md),
[SBS control contract](../../../ui-docs/contracts/sbs-control-contract.md),
linked shared controller exception, ADR-0065 and active ExecPlan.

This is contract approval, not implementation acceptance. The independent
correctness review and standalone ancestor checkpoint remain required before
native-required/UI implementation. The tracker explicitly identifies the
preexisting experimental NoData-union change; this approval does not turn that
experiment into validated parity evidence. Only this review artifact was edited.

## Security triage and boundaries

Security impact is **high**, requiring dedicated final security review. A
malicious or reflected response body must not execute script, read session data,
initiate requests, submit forms, navigate, instantiate custom elements, clobber
DOM IDs, or change page styling. Attribute removal and rebuilding native HTML
nodes address those threats; removing dangerous wrappers while retaining their
subtrees would not meet the contract.

The finite allowed tags are h1 through h6, p, div, span, br, pre, code, strong,
em, b, i, ul, ol, li, blockquote, table, thead, tbody, tr, th and td. Parsed source
nodes must never be inserted, imported or cloned into the live page. Inertness
must hold during parsing as well as insertion. Error formatting is limited to
Details in the two SBS controllers. The existing successful
`view/modify_burn_class` HTML remains a separate result path.

Actual source boundaries inspected:

- `disturbed.js`: `uploadSbs`, `toResponsePayload` and `handleResponseError`.
- `baer.js`: upload handlers, `toResponsePayload` and `loadModifyClass`.
- `http.js`: `parseBody` and `buildError` retain response/body information.
- `control_base.js`: shared stacktrace rendering also writes Summary; the SBS
  path must bypass that side effect without changing other controllers.
- `sbs_map.py`: all five native wrappers, summary cache, default/custom color
  handling, sanity checks and four-class export.
- Owned `wepppyo3/sbs_map/src/lib.rs`: native exports and NoData classification.

Native-required execution adds no external dependency, input path, subprocess,
network destination, authorization scope or queue edge. Missing APIs and native
exceptions must remain explicit, never successful cache entries. A valid raster
without a color table remains valid where already supported; absence of palette
metadata must not be mistaken for a missing native dependency. Scalar custom
color-map interpretation and existing GDAL display processing remain in scope.

## Required final evidence

1. Exercise the actual Details renderer in a real browser with benign gateway
   headings/tables and hostile scripts, event attributes, styles/resource URLs,
   base/meta navigation, iframe/srcdoc, SVG/MathML, forms and custom elements.
   Observe both script/custom-element execution and network requests from before
   parsing until after insertion. Include malformed/deeply nested markup.
2. Run actual Disturbed/BAER failure handlers: HTML upload failure, summary-fetch
   failure, JSON messages containing literal markup, prior successful Summary
   during failure, and subsequent success clearing Details. Assert no error body
   is copied into hints or Summary through shared callbacks.
3. Inject missing module/function and native execution failures through every
   wrapper and public operation. Assert explicit error/no success caching, then
   restore the dependency and prove recovery. Preserve valid no-palette and
   custom-color-map cases rather than treating optional metadata as corruption.
4. Use real installed native code and actual Wallow output plus analytical
   rasters to prove orientation, class/palette, projection and source/display
   NoData-mask parity. Native NoData comparisons cast to integers; distinguish
   already-invalid non-integer uploads from the public helper surface when
   checking fractional/NaN edge cases. Do not broaden accepted input semantics.
5. Complete the real authenticated development upload through the proxy and wait
   for summary/map requests to settle. Test timeout followed by authoritative
   reload; a client failure must not claim backend cancellation or no saved map.

Focused Python/Jest tests, lint, browser evidence and final independent reviews
remain required. The full suite is explicitly excluded by the operator.
