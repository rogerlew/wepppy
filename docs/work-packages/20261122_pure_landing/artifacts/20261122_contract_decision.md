# Pure CSS landing contract decision

Starting revision `dcf1ab785c86b500573d709156e6c35217ec570e`.

On 2026-11-22 the operator requested a contract-first migration to Pure CSS,
semantic content parity, existing theme support, Section 508 conformance,
design consistency with Interfaces, Runs and reports, a review route, and
full UI Lab removal gated on human approval with no environment switch.
The preview route and atlas table layout are implementation decisions for
review. Production cutover approval remains pending.

The [landing contract](../../../ui-docs/contracts/pure-landing-contract.md)
adds those requirements and the data, input, session, failure and theme
states. [FSBASE-01 and FSBASE-03](../../../ui-docs/contracts/forest-service-basemap-contract.md)
govern attribution and current delivery. The [controller contract](../../../ui-docs/controller-contract.md)
governs presentation reuse. The [table overflow contract](../../../ui-docs/contracts/table-overflow-discoverability-contract.md)
applies to the atlas table. The shared theme and accessibility documents
guide evidence collection. No controller, authorization, CSRF, queue,
scientific or persistence behavior changes.

Discrepancy classification is intended additive behavior. A Jinja page
and native filter remove the landing build and allow keyboard access to
project data. Rendering only summary data would lose atlas information.
A second map build would preserve the dependency and interaction burden.

Compatibility impact is additive during review. Keep both existing landing
variants and their API and assets. The public snapshot boundary stays the
same, with autoescaped HTML, no client identity payload, read-only input
and no direct project links. No security-sensitive state or filesystem
write is added. Exercise a real snapshot fixture and hostile values in
served output. Verify legacy routes, anonymous and authenticated branch
behavior, links and acknowledgments, theme persistence, keyboard focus,
reflow and axe. Confirm the Forest Service renderer independently before
removing exports.

## Independent reviews

Read-only correctness and accessibility review on 2026-11-22 UTC found
two medium issues and no high issues. The contract now requires keyboard
access to overflow with scripts disabled and a results anchor for native
GET navigation. It also identifies the year as last-access year and
distinguishes empty snapshots from all-invalid records. Keep the existing
about and map anchors for cutover review.

Read-only compatibility review on 2026-11-22 UTC found two medium issues
and no high issues. The contract now specifies explicit data failure
states and legacy response compatibility. Tests cover real invalid UTF-8,
invalid JSON shape, mixed and all-invalid rows, and mounted URLs for links,
form and pagination. Cutover inventories root and variant aliases and
preserves the locked renderer byte-for-byte. The atlas uses only the
specified public fields, with a fixture to confirm unknown fields
stay out of the response.
