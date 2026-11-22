# WEPPcloud landing page

The preview is implemented for local review. Public cutover requires human
acceptance of the rendered replacement and its accessibility evidence.

## Delivery

During review, GET `/landing/preview/` renders the replacement for anonymous
and authenticated users. Normal WEPPcloud mount-prefix handling applies.
The response uses the site's no-store policy for personalized content.
The home page, `/landing/`, and both explicit UI Lab variants continue to
follow [FSBASE-03](forest-service-basemap-contract.md#landing-delivery-and-navigation-fsbase-0203)
during this phase. The preview is unlinked from existing navigation and
requests exclusion from search indexing. It is accessible by URL and
requires no environment configuration.

Use server-rendered Jinja and the existing Pure CSS WEPPcloud shell. Reuse
its theme initializer, theme selector, tokens, typography, page width,
buttons, focus treatment, and responsive conventions from Interfaces,
Runs, and reports. Keep page-specific CSS scoped. The site theme preference
continues across pages. Landing content, navigation and the Atlas text equivalent work without
JavaScript. The theme selector and Atlas map use the existing browser
runtime. The preview adds no npm package, separate frontend build or
configuration.

## Content and rationale

The current light landing supplies the baseline for content and section
order. Keep introduction, About, full-width Run Atlas, help and resources,
points of contact, affiliations and collaborators, sponsors, contributors,
attributions and data sources, legal disclaimer, and the accessibility
footer in that order. Preserve
the WEPP and watershed modeling overview, Interfaces, Help, Research, Login
or My Runs, model and FAQ links, Run Atlas, help resources, contacts,
collaborators, sponsors, contributors, data and mapping attributions, legal
disclaimer, and accessibility statement. Preserve names, contact details,
acknowledgments and disclaimer wording. Organization names and links
identify collaborators and sponsors independently of any graphics.
Retain cartography and hydrography credits in a section that describes where
they apply, including the separate Forest Service credit and use limitations
required by FSBASE-01. Preserve the four regional data documentation links.

Edit prose in the [landing template](../../../wepppy/weppcloud/templates/landing/preview.htm)
and names and acknowledgments in the [landing content partial](../../../wepppy/weppcloud/templates/landing/_content.htm).
Use existing shared table and button conventions. A landing-local macro is
appropriate for repeated organization cards shared by collaborators and
sponsors. Keep one-off content in semantic HTML and keep the shared macro API
unchanged. This lets maintainers update text without rebuilding frontend assets.

## Run Atlas

The Run Atlas is the landing's main visual and follows About as it did
on the original light landing. Reuse the existing Deck.gl 9 runtime and
WEPPcloud Deck.gl map and tile helpers. Keep the light Atlas's CARTO
basemap provider and the Deck.gl centroid and label layers, general initial
view, map navigation and marker semantics. Use CARTO raster tiles with the
existing Deck tile helper, including a theme-appropriate map palette. This
allows retirement of the UI Lab package without adding a React mount, a
MapLibre runtime to this page, or a separate map implementation.
Credit CARTO and OpenStreetMap for this map. The fixed HTTPS tile templates
are `https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png` and its
`dark_nolabels` counterpart. Allow only bounded integer XYZ indexes.
Cross-origin requests omit application credentials and preview referrers.
No proxy or CSP relaxation is required. Theme changes retain the camera
and overlays. Use the current palette's tile status only.

Use the full existing compiled public snapshot via its existing path resolver.
Keep unique runs, total hillslopes and latest recorded access. The Atlas
provides no access-year selector. Previously entered preview `year`
parameters have no effect. Pagination moves through the accessible project
table without changing the displayed map.

Keep the text equivalent in a native disclosure next to the map. List
geographic quadrant totals, project locations, soil burn severity presence,
run name and ID, config, hill count, access count and last access. Keep a
recent-first table with at most 25 rows per page. A page link returns to the
results heading and keeps the disclosure open, including page one. Map
tooltips use plain text and repeat information available in the disclosure.
Native zoom and reset controls and a named focusable map region with
arrow-key panning provide keyboard access. Tab exits normally. The canvas
has no separate tab stop. Wheel scrolling remains page scrolling.
Marker size shows access count, with a visual key and a text equivalent for
soil burn severity and other marker attributes.

The HTML fallback remains readable if scripts fail. Loading is announced
after initialization starts and cleared only when the current visible tiles
are ready. A renderer or tile failure produces a readable status and keeps
the native details available. For Web Mercator, coordinates above the
projection's latitude limit remain in the table and are omitted from the
plot. Both antimeridian coordinates retain the same dateline location.

The existing project authorization, public snapshot, and cache generation
continue to apply. Render only the named public fields and derive coordinates
from validated numbers. Serialize values with Jinja's JSON encoding and put
only plain text into tooltips. Use fixed provider URLs. No project links,
raw access log, identity data, or user-controlled tile URLs are part of
this surface.

| Input or runtime state | Required outcome |
| --- | --- |
| Anonymous or authenticated session | Shared header and relevant Login or My Runs action |
| Fresh or stored theme | Existing shared theme behavior with light or dark CARTO basemap and themed layout |
| Missing, empty, invalid or out-of-range page | First table page. Invalid input leaves the disclosure collapsed |
| Valid page request | Keep the disclosure open and preserve the same full map snapshot |
| Missing, empty or invalid snapshot | Readable Atlas status and usable landing |
| Populated snapshot | Full Deck.gl map, overall totals and accessible project details |
| Script, renderer or tile failure | Readable status and working text equivalent when project data is available |
| Supported row with missing optional text or counters | Keep valid coordinates and identify missing details |
| Invalid coordinates or hostile text | Skip invalid rows. No executable tooltip content or provider URL construction from data |
| Archived, removed or restored runs | Reflect the compiled snapshot and retain existing access rules |

## Accessibility acceptance

Apply the Revised Section 508 web baseline, including WCAG 2.0 A and AA,
and the repository's existing AA theme baseline. Include a skip link, one
main landmark and H1, logical headings, labeled controls, table headers,
descriptive links, visible keyboard focus, readable text at 200% zoom,
usable narrow layouts with and without scripts, and no reliance on color or mouse hover.
Verify desktop and narrow screenshots show the map as the main visual after About.
Check the real Deck.gl canvas and visible tiles, keyboard map navigation,
pagination and disclosure focus
in served output. Verify with keyboard and axe across default,
light-high-contrast, ayu-mirage, ayu-mirage-bordered and cursor-dark-midnight.
Keep any horizontal table overflow contained, with a named focusable
scroll region and keyboard guidance when scripts are disabled. Verify the
shared overflow disclosure and keyboard behavior when scripts are enabled.
Review text and non-text contrast and perform manual assistive technology
checks against the [Access Board web testing baseline](https://ictbaseline.access-board.gov/web-baselines/)
before claiming conformance or approving cutover.

## Approved cutover

After human approval, make home and `/landing/` serve the Jinja page.
Apply the approved compatibility disposition to explicit variant URLs,
preview, root and variant JSON/asset aliases, and old fragment bookmarks
such as `#about` and `#map`. Inventory and remove UI Lab source,
exports, Vite-only routes, state injection, build/test/deploy wiring, and
live operator instructions. The optional Forest Service map on Runs and
dashboards must keep its approved locked MapLibre assets and license
byte-for-byte in a WEPPcloud-owned static vendor path with no UI Lab dependency.
Verify lazy loading and provider switching in both consumers and update the Forest Service delivery contract
with the approved cutover. No environment switch or runtime choice between
implementations is required.
