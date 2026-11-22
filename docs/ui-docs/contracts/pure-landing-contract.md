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
continues across pages. Landing content, navigation and atlas controls work
without JavaScript. The existing theme switcher uses the shell's scripts.
The preview adds no client package, remote map request, animation, or build
step.

## Content and rationale

The current light landing supplies the baseline for section content. Preserve
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

The Run Atlas map is the landing hero's focal point. Place it in the first
visual section with the headline and project entry action. It should read as
a map at a glance, retain geographic context on narrow screens, and inherit
the selected theme. The map is a world overview of project locations on a
bundled Natural Earth land silhouette. Server-rendered CSS markers group
coordinates into fixed geographic cells. The map and markers share an
equirectangular 2:1 extent at longitude −180 to 180 and latitude −90 to 90.
Edge points use the nearest in-bounds cell. Keep the full extent at every
viewport and use a visible key that explains larger markers represent more
runs. The overview has no pan, zoom, pointer-only content, external tile
requests, client renderer, or animation. The hero still shows the basemap and
a readable status for missing, malformed or empty data.

Read the existing compiled public snapshot through its existing path resolver.
Use the full selected set for the map and keep markers stable across table
pagination. Show overall run count, total hillslopes and latest recorded access.
The native GET filter applies last-access year to both the map and table. A new
year starts on page one and returns to the Atlas heading. Pagination retains the
year, returns to the results heading and keeps project details expanded.

Keep the text equivalent in a clearly labeled native disclosure next to the
map. The summary describes the map and marker size. The disclosure lists
selected run counts for four quadrants divided by the equator and Greenwich
meridian. Pagination leaves the distribution unchanged. It also includes the
selected run count, filtered hillslopes and a recent-first
table with at most 25 rows per page. Coordinates, soil burn severity presence,
run name and ID, config, hill count, access count and last access remain
available as text. The visual itself is decorative to assistive technology.
Project authorization, snapshot generation and the public data boundary are
unchanged. Render only the named fields, escape all text, derive marker positions
from validated numeric coordinates and render no direct links to individual
runs. The raw access log is outside this boundary.

The map restores the visual overview that the initial table-only preview
omitted. The bundled silhouette and bounded server-rendered markers keep the
hero themeable and avoid the old rendering and tile dependencies. Native text
details supply the data independently of the visual.

| Input or runtime state | Required outcome |
| --- | --- |
| Anonymous or authenticated session | Shared header and relevant Login or My Runs action |
| Fresh, stored, absent or unsupported theme selection | Existing shared theme behavior |
| Missing or empty year and page | All years, first page |
| Available year and valid page | Matching rows with the requested page and current filter retained |
| Unknown year or invalid, oversized or out-of-range page | All years for unknown year, first page for invalid page |
| No snapshot or valid empty snapshot | Map silhouette with unavailable or empty status respectively, and the page remains usable |
| Populated snapshot | Hero markers for the selected year, overall totals, and paged project information in a native disclosure |
| Supported record with absent optional text or counters | Render remaining information and identify missing values |
| Malformed snapshot, row or hostile text | Report unavailable for unreadable or invalid snapshot or a nonempty snapshot with no valid rows. Skip structurally invalid rows in mixed snapshots. Escape text and use only validated coordinates for markers |
| Archived, removed or restored runs | Reflect the current compiled snapshot and retain existing project access rules |

Missing and empty snapshots are anticipated conditions. An unreadable or
malformed snapshot is a data-source failure isolated to the Atlas and logged
for operators. The landing remains usable in these cases.

## Accessibility acceptance

Apply the Revised Section 508 web baseline, including WCAG 2.0 A and AA,
and the repository's existing AA theme baseline. Include a skip link, one
main landmark and H1, logical headings, labeled controls, table headers,
descriptive links, visible keyboard focus, readable text at 200% zoom,
usable narrow layouts with and without scripts, and no reliance on color or mouse hover.
Verify desktop and narrow screenshots show the map as the dominant hero.
Check marker alignment and separability from land and water,
filter and pagination behavior, and disclosure focus
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
