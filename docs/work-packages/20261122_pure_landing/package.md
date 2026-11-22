# Pure CSS landing migration

Visitors can review a server-rendered, theme-aware landing page with the
same scientific, help, attribution and funding content as the UI Lab page.
Authors can update content through Jinja without a frontend build.

The target is faithful extraction of semantic content. The preview also
presents the Run Atlas as the visual hero and offers a keyboard-readable
table for project details. The human approval
gate covers layout, content and accessibility before switching home routes
and retiring UI Lab. The [canonical landing contract](../../ui-docs/contracts/pure-landing-contract.md)
defines the intended behavior.

Complexity budget: one additive Flask route, Jinja, scoped CSS and existing
public data and shell. Security impact is low. The preview reads the existing
public snapshot and renders escaped HTML and bounded numeric map markers with no project links or new
permissions. A dedicated security review artifact is unnecessary at this
scope. The cutover retains the separately used Forest Service renderer with
its existing security boundary.
