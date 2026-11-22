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
the WEPP and watershed modeling overview, Interfaces, Docs, Research, Login
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
Use existing shared button conventions. A landing-local macro is
appropriate for repeated organization links. Keep one-off content in semantic HTML and keep the shared macro API
unchanged. This lets maintainers update text without rebuilding frontend assets.

## Reviewed presentation

Inherit the standard site masthead from `base_pure.htm`, including its
text brand, notification and theme controls, and responsive layout. Place
the landing destinations and account link in the header navigation slot
using the same `wc-nav__link` treatment as Interfaces. Expose Interfaces,
Docs, Research, then Login or My Runs directly on desktop. On mobile
provide those same links in order under a keyboard-operable hamburger
labeled Menu. Keep the skip link and shared header tools. Use a text-only introduction with WEPPcloud as H1, Water Erosion Prediction
Project as its subtitle, the original data-driven watershed modeling statement
as H2 and a short explanation of the online WEPP interface. Omit hero artwork
and action links; the header provides navigation. Restore the light landing's original About paragraph, model and FAQ labels,
resource labels, descriptions and destinations, and section introductions.
Use existing source wording for content updates unless a specific change
has been approved. Use plain link labels without decorative arrows. Follow the
same shared link color and decoration across landing destinations, including
resource and organization links, with no persistent underline and visible hover and
keyboard focus. Distinguish links in running text by weight. Include the original lightning, YouTube and GitHub marks beside their respective
resource labels. Keep the marks decorative so each card retains one named link.
Under the resource cards, show a WEPPcloud Stack subsection with a linked name and
short role description for wepppy, wepppyo3, weppcloud-wbt, peridot, jimf-cligen532,
rosetta, soil-data-access, and wepp-forest. Identify wepp-forest as private and
requiring collaborator access. Include topaz and oxidized-rasterstats for their
terrain delineation and raster analysis roles. Link the upstream devalc/WEPPcloudR
reporting project and jackson-nakae/PATH-cost-effective treatment optimizer.
Display the Stack as a two-column table with one repository per row. Stack each
description beneath its repository on phones. Prefix every full owner/repo link
with the decorative GitHub mark to identify the destination. Include
wepp-in-the-woods/wepp-forest-revegetation alongside wepp-forest and associate
both links with the visible note “Private repository. Collaborator access required.”
Present resources as action links, contacts as a
directory and affiliates as individual themed cards with a linked logo and visible name.
Display the nine original light landing captions, including mottos, verbatim
and in source order. A shared card surface groups each logo with its attribution.
Retain every contact and funding acknowledgment, keep sponsor roles distinct
and display each funding acknowledgment beside its sponsor. Show map credits,
Forest Service use limitations, regional documentation and all legal paragraphs
in normal document flow. Stack reference columns on narrow screens. Provide footer
shortcuts, hosting credit and a consistent mobile gutter. Use the shared
theme palette for UI surfaces and readable text.

Keep the interactive Atlas and metric group above it, formatted with clear
numeric hierarchy and a human-readable date. Open on the contiguous US at
a responsive zoom and level pitch. Bound marker size to reduce overlap
while retaining hillslope-area encoding. Keep the blue standard marker and
use ember with the existing thicker outline for SBS. Keep the requested
two legend chips and persistent desktop wheel instruction. A touch-only
screen omits the Ctrl instruction and permits one-finger vertical page scrolling. Run ID eligibility follows the build
rollover publication rule below.

## Run Atlas

The Run Atlas is the landing's main visual and follows About as it did
on the original light landing. Reuse the existing Deck.gl 9 runtime and
WEPPcloud map helper. Use the live light landing's CARTO Positron
vector style with the existing MapLibre runtime under the Deck.gl
centroids and labels. Use
`https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json`
and its versioned vector tiles, fonts and sprites from
`tiles.basemaps.cartocdn.com`. Accept only the style URL and the versioned
`vectortiles/carto.streets/v2`, `fonts`, and `gl/positron-gl-style/sprite`
resources used by that style. Disallow arbitrary style resource origins
and provider attribution markup. Reuse the local locked MapLibre assets
already shipped with WEPPcloud. When UI Lab is retired, preserve those
shared assets under the WEPPcloud-owned static vendor path. The preview
needs no new configuration, proxy or CSP relaxation. Cross-origin
requests omit application credentials and preview referrers. Credit
OpenStreetMap and CARTO for the preview map. The shell follows the selected
theme and the basemap uses the same palette as the original light landing.

Use the existing compiled snapshot. Keep unique runs, total
hillslopes and latest recorded access in shared `wc-landing__card` cards
above the map. Restore the original compact lower-left zoom-in, zoom-out
and reset map buttons with accessible names and focus indicators. The Atlas has no access-year
controls or browse-project disclosure and table. Former year and page
parameters have no effect.

Provide a concise nonvisual geographic summary and a readable failure
message in the rendered HTML. Keep the marker legend, named keyboard
panning, native zoom and reset controls, and a normal Tab exit. Render
run ID labels directly on the map, with the original zoom-dependent
label size. Keep the inspection paragraph and project-cycle controls out
of the page. Plain-text hover tooltips retain the existing project fields.
Marker area represents each run's hillslope count, with a minimum visible
marker and maximum radius to keep the map legible, and both an outline and fill distinguish
soil burn severity data. The canvas has no separate tab stop. Unmodified wheel input scrolls the page. Holding Ctrl while scrolling over
the map zooms it through the existing Deck.gl controller. On devices with a fine pointer, show “Hold Ctrl
while scrolling to zoom the map.” at the lower right and separate “Standard
runs” and “Runs with SBS” legend chips at the upper left, as in the original
Atlas. The overlays use theme colors and allow pointer input to reach the
map. Keep the tip clear of the zoom buttons at narrow widths.

Synchronize Deck.gl overlays and the vector basemap through the Atlas
camera for pan, zoom, reset and resize. Loading starts after the map
initializes and clears on visible tile readiness. Script, renderer or tile failure leaves readable status,
summary and metrics. Geodetically valid polar locations remain in the
summary and metrics. Web Mercator only plots eligible coordinates and
uses the same dateline location for +180 and −180.

At normal snapshot compilation, include a project's Atlas row only if its
run directory has the existing explicit public designation (NoDb PUBLIC
marker). If multiple input directories contribute to one run ID, each must
qualify for that merged row to be published. A change of visibility takes effect in the next successful
generation. The preview and all four JSON aliases use this same published
snapshot regardless of session. Only its eligible rows contribute labels,
tooltips, metrics and geographic summaries. Never ship a second unfiltered
snapshot as a static asset. Project access and internal statistics keep
their existing rules. Serialize only public marker fields with Jinja JSON
encoding. No project links, raw access log, identity data, or user-controlled
tile URLs are part of this surface.

| Input or runtime state | Required outcome |
| --- | --- |
| Anonymous or authenticated session | Shared header and relevant Login or My Runs action |
| Fresh or stored theme | Shared themed shell and controls with the existing Positron vector basemap |
| Former year or page parameters | Full Atlas uses the same snapshot |
| Missing, empty or invalid snapshot | Readable Atlas status and usable landing |
| Populated snapshot | Deck.gl map, overall metrics and geographic summary |
| Script, renderer or tile failure | Readable status, geographic summary and metrics when data is available |
| Supported row with absent optional text or counters | Keep valid coordinates, identify unknown details |
| Invalid coordinates or hostile text | Skip invalid rows and keep tooltip values inert |
| Archived, removed or restored runs | Reflect the compiled snapshot and retain existing access rules |

## Accessibility acceptance

Apply the Revised Section 508 web baseline, including WCAG 2.0 A and AA,
and the repository's existing AA theme baseline. Include a skip link, one
main landmark and H1, logical headings, labeled controls,
descriptive links, visible keyboard focus, readable text at 200% zoom,
and usable narrow layouts with and without scripts. Keep the requested
visual-only presentation of individual run IDs and hover details during
review. Their keyboard and nonvisual equivalence remains an open
manual Section 508 acceptance item before cutover.
Verify desktop and narrow screenshots show the map as the main visual after About.
Check rendered geographic features, run ID labels and keyboard navigation
in served output. Verify with keyboard and axe across default,
light-high-contrast, ayu-mirage, ayu-mirage-bordered and cursor-dark-midnight.
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
