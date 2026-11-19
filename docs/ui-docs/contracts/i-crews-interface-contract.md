# I-CREWS WEPPcloud interface

Implementation conformance is pending.

The Interfaces page offers one public **I-CREWS** card in **Site Specific
Resources**. Its launch actions use the existing project creation endpoint,
visibility rules, account preferences and anonymous CAPTCHA policy.

| Launch label | Named preset | Source preset | Default delineation |
| --- | --- | --- | --- |
| Start I-CREWS WBT Run | `i-crews` | `disturbed9002_wbt` | WBT |
| Start I-CREWS Multiple OFE Run | `i-crews-mofe` | `disturbed9002-wbt-mofe` | WBT with multiple overland flow elements enabled |

Both presets are Preview interfaces with standard user visibility. Preserve
the source preset's scientific settings and allowed creation-time overrides.
The card submits no backend override. Both creation modes validate overrides
for the two named presets against their existing inherited allowlists.
Reject unsupported overrides and alternate config selectors before run
allocation using HTTP 400 with `project_config_validation_failed`.
The two presets share `static/mods/i-crews/idaho-boundary.geojson`, center
`[45.6, -114.15]` in latitude/longitude order, and zoom `5`. The initial view
orients users before they select an extent. The config owns the boundary and
`boundary_check = "intersects"`. A selection that touches or overlaps Idaho
passes Idaho boundary admission at its full extent. Existing extent, DEM and
backend checks still apply under the
[channel delineation map boundary contract](../../schemas/channel-delineation-map-boundary-contract.md).

Show the Idaho outline by default on the run map for these two presets. The
boundary is a line overlay loaded from the same local polygon used for
admission. Existing presets retain their map behavior.

The card explains WEPPcloud's watershed modeling role in I-CREWS and links to
the project website. The user-supplied illustration shows a river and dam.
The Interfaces card and both run pages display the Idaho EPSCoR product
acknowledgment for NSF award OIA-2242769 and the Idaho EPSCoR disclaimer that distinguishes the authors' views from NSF as text. Run attribution follows the active run's saved configuration
identity and appears on direct links. Limit the credit to I-CREWS surfaces.

Funding wording follows the
[I-CREWS product acknowledgment](https://idahocrews.org/wp-content/uploads/2024/10/VIP_RFA_Y2_2024.pdf)
and [Idaho EPSCoR citation guidance](https://www.idahoepscor.org/cite-epscor).
See also [NSF publication guidance](https://www.nsf.gov/policies/pappg/24-1/ch-11-other-post-award-requirements).
