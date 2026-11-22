# Pure CSS landing preview review

The independent correctness review on 2026-11-22 UTC covered the preview
route, landing templates, scoped CSS, snapshot handling and rendered-page
tests on `task/pure-landing`. The [delivery and atlas sections of the landing
contract](../../../ui-docs/contracts/pure-landing-contract.md) and the
[Forest Service delivery and credit requirements](../../../ui-docs/contracts/forest-service-basemap-contract.md)
govern this release.

| Surface | Finding | Disposition |
| --- | --- | --- |
| Swansea affiliation | Medium. The Welsh motto needs a language change for assistive technology. | Render the motto in `lang="cy"` alongside its English translation and assert the output. |
| Atlas row header | Medium. Chromium's accessibility tree included disclosure text in the row header name and repeated it in context. | Label the row header from the project-name span and retain the disclosure as its own control. |
| Snapshot parsing | Low. A deeply nested malformed snapshot could bypass the atlas-only failure message. | Catch the decoder's recursion error at file read and exercise a malformed fixture. |
| Text links and theme label | Browser validation found contrast failures and links signaled by color alone. | Use underlined links, contrast-tested theme tokens and scoped form and label styles. |

## Direct evidence

Focused Flask tests used real temporary snapshot files to exercise absent,
empty, populated, mixed, invalid shape, invalid encoding, deeply nested
and hostile input. Tests checked mounted URLs, supported numeric counters,
escaping, and aggregate and filtered values in rendered HTML. Expected
absence and exceptional source failures show a readable atlas status with
the rest of the page available. There are no new persisted settings or
project artifacts from the preview. Project archive and authorization
remain outside the atlas reader and its read-only trust boundary.

The isolated review instance served the full Flask application under
`/weppcloud` with a synthetic snapshot. It served both legacy variants and
their JSON aliases, the legacy light bundle, the shared MapLibre asset,
and the preview's destinations for Interfaces, Help, model documentation,
research, FAQ, attribution, and accessibility. The signed-in preview showed My Runs and passed axe in Chromium. This
used a browser-imported local smoke session after the interactive
login remained at its verification step. The signed-in check used
the real Flask session and navigation without opening a live run.

The independent follow-up review confirmed closure of all three code
findings and passed the preview scope on 2026-11-22 UTC.

## Browser evidence

The populated preview had zero axe violations in Chromium across the
five AA-validated themes. Independent computed-style contrast checks
covered the two selects that axe marked for manual contrast review.
Their text contrast was at least 4.51:1 and visible border contrast
against adjacent surfaces was at least 5.54:1.

Chromium verified the initial skip link, year filtering, retained focus
on the results heading during filter and pagination navigation, native
project disclosures, persisted theme selection, and loaded organization
logos and stylesheets. All five themes kept the document within a
320-pixel viewport. The Atlas's named overflow region was focusable with
a visible outline, and it scrolled with the Right Arrow and Shift-wheel.
A 200% layout-zoom check at 640 pixels passed. Chromium and Firefox
verified native Arrow scrolling with scripting disabled. Chromium also
verified the no-script filter form and results focus.

The preview is implemented and locally renderable. Public cutover, UI Lab
retirement and a Section 508 conformance claim require human acceptance and
remaining manual assistive-technology evidence.
