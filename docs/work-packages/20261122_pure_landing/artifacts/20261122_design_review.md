# Landing design review disposition

Base `e683323fa`. The operator requested implementation after choosing
public-only labels through scheduled compilation. The current landing
contract's Reviewed presentation section records the decisions. Preview
conformance and rendered checks are pending. Scope is the landing surface.

| Finding | Disposition and rationale |
| --- | --- |
| Header hierarchy, brand, auth link and edges | Strengthen the wordmark with the existing site mark, align with the content and use a distinct account button. Collapse navigation on phones. Retain all theme choices and shared preference handling in a compact disclosure. |
| Boxed introduction, missing visual, headline, actions | Use a split, borderless introduction with existing watershed imagery, outcome-led copy and stacked mobile actions. Keep watershed planning and post-fire uses. |
| Repeated rules, cards, blue underlines, palette and eyebrows | Use spacing, themed surface bands and distinct content layouts. Emphasize action links and keep inline links underlined. Avoid decorative eyebrows or a second brand palette. |
| About and orphan links | Three task columns and named model and FAQ links. |
| Stats position, type and date | Keep all three metrics immediately above the Atlas per operator order. Use larger numbers, one compact responsive group, a readable access date and exact time in the time element. |
| Opening camera, blank wedge and overlapping bubbles | Level the camera, frame the contiguous US responsively and lower the radius cap. Preserve square-root area, outlines, zoom controls and reset. World copies are already disabled. A global fit would let remote points dominate the view. |
| Suspected offshore coordinate | Inspect the actual snapshot, do not alter coordinates based on screen position. |
| Legend wording, color and placement | Preserve the requested chip labels and overlay locations. Expand SBS in accessible text and legend title, use ember plus outline. |
| Wheel and touch controls, static map option | Keep the explicit desktop wheel tip and interactive map; omit the irrelevant tip on touch-only devices. MapLibre is noninteractive beneath Deck, so its cooperativeGestures setting cannot control input here. |
| Mobile resource and contact columns, titles, gaps and orphan cards | Use single-column resource links and compact contact rows on phones. Keep all contacts and expertise. Remove Jackson's duplicated wording. Preserve Pete's supplied institutional history and email. |
| Affiliations, slogans, duplicate logos, funding | Use a responsive logo wall and relocate hosting credit. Keep names accessible and logos legible on all themes. Keep sponsors separate in original order, with full acknowledgments and unbroken grant IDs in a disclosure. |
| Contributor list and name | Flow names down columns. Correct Jim Frankenberger, confirmed in the WEPPcloud README. |
| Attributions, hydrography label, legal and footer | Compact native disclosures keep credits, use limitations and full disclaimer accessible in the original order. Correct the flowline link text. Link to resources, credits, contributors, accessibility and legal from the footer. |
| Run IDs in map and JSON | Apply the already-reviewed public-only compilation rule. Public run labels are intentional. Revocation rolls over at the next successful build. |

Verify rendered mobile and wide layouts, disclosure access, keyboard focus,
theme switching, Atlas controls, rendered tile readiness and five AA theme
axe scans. Public cutover and manual accessibility acceptance remain gated.

Both independent reviewers accepted the scope. Retain visible names next
to logos, leave basemap credits beside the map, and target visible section
headings from footer links. Hide the Ctrl tip only without a fine pointer
and keep the separate keyboard instructions. Use native disclosures with
working no-script navigation.
