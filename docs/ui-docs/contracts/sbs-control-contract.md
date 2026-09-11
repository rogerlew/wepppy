# Soil Burn Severity upload result and error contract

Implemented by `sbs_error.js`, Disturbed and BAER. Applies to the shared Disturbed/BAER SBS control for
upload, result-summary fetch and their failure paths. Shared controller, CSRF,
run-access and RQ response contracts remain authoritative.

- Status shows concise progress, success or failure text.
- Hint elements MUST NOT display success/error bodies or gateway HTML. They are
  reserved for job-link metadata under the shared controller contract.
- Summary contains successful SBS classification HTML from the existing
  `view/modify_burn_class` endpoint, rendered as markup, never escaped source.
  Transport errors MUST NOT overwrite Summary with an error body. Preserve the
  last accepted Summary while replacing an SBS map; a failed replacement retains
  it until a successful result refresh. Initial absent Summary remains empty.
- Details contains errors. An HTML gateway response MUST render as readable
  formatted HTML, not escaped source text. JSON errors and stacktraces retain
  their normal text treatment. Automatically reveal Details on failure.
- Gateway HTML is untrusted: retain only inert formatting (headings, paragraphs,
  lists, tables, pre/code, emphasis, line breaks and generic text containers),
  strip all attributes, and remove active/resource-loading content entirely.
  The complete allowed tag set is h1–h6, p, div, span, br, pre, code, strong,
  em, b, i, ul, ol, li, blockquote, table, thead, tbody, tr, th and td.
  No script, event handler, style, link, image, iframe, SVG, form, custom element
  or navigation may be introduced into the parent document. Parse in a detached
  HTML template (inert during parsing), then construct fresh HTML elements and
  text nodes. Never import/clone source nodes or insert raw error HTML into live
  DOM. Discard foreign/custom/active/resource subtrees, not just their wrappers.
  Apply HTML formatting only to a raw string HTTP failure body with a text/html
  Content-Type; JSON error messages containing markup remain escaped text.
- Upload success updates accepted filename, classification summary and map.
  Follow-up summary/map requests must settle before the browser smoke declares
  success. Summary/map errors are tracked separately: a successful sibling
  request cannot hide an unresolved error. Successful retry clears that
  request’s error; a new upload clears the prior attempt’s errors. Legacy
  HTTP200 JSON error envelopes are failures, never successful HTML summaries.
- Timeout reports failure without claiming that the backend stopped or that a
  map was not saved. Reload/state queries remain authoritative.

The SBS-specific Details renderer is a bounded exception to the shared default
of escaping error-message strings; other controllers keep their behavior.
No general HTTP helper or shared error-rendering redesign is authorized.

Rationale: the operator explicitly requests rendered HTML gateway errors in
Details, not hints; Summary remains model results. The old upload handler placed
the raw gateway document in hints and shared error handling copied it into
Summary and escaped it in Details.
