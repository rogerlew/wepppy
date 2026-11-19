# I-CREWS interfaces in WEPPcloud

**Status** Local implementation closed 2026-11-19. Repository-wide
acceptance is blocked by the existing SSURGO fixture.

## Outcome

Add one **I-CREWS** card to **Site Specific Resources** on the WEPPcloud
Interfaces page. Offer two run launches from that card. Both open on Idaho
and require the channel delineation extent to intersect the Idaho boundary.

| Preset | Source | Launch button |
| --- | --- | --- |
| `i-crews.cfg` | `disturbed9002_wbt.cfg` | Start I-CREWS WBT Run |
| `i-crews-mofe.cfg` | `disturbed9002-wbt-mofe.cfg` | Start I-CREWS Multiple OFE Run |

The Multiple OFE preset retains the source's WBT delineation and multiple
overland flow elements, which allow a hillslope to be represented by multiple
segments. Keep the model executable, scientific parameters and modules from
each respective source preset. Both are public Preview interfaces under the existing project creation policy.

## Card copy and credit

> Use WEPPcloud to explore how wildfire and land management affect runoff,
> erosion, and sediment delivery in watersheds that overlap Idaho. This
> interface supports Idaho Community-engaged Resilience for Energy-Water
> Systems (I-CREWS), an Idaho NSF EPSCoR project studying how communities can
> adapt their energy and water systems to changes in climate, population, and
> technology.

> This product was made possible by the NSF Idaho EPSCoR Program and by the
> National Science Foundation under award number OIA-2242769.

Include visible credit on the card and on direct visits to either run
interface. The credit includes the Idaho EPSCoR disclaimer on each surface. [I-CREWS research](https://idahocrews.org/research/) ·
[I-CREWS product acknowledgment](https://idahocrews.org/wp-content/uploads/2024/10/VIP_RFA_Y2_2024.pdf) ·
[Idaho EPSCoR citation guidance](https://www.idahoepscor.org/cite-epscor) ·
[NSF publication guidance](https://www.nsf.gov/policies/pappg/24-1/ch-11-other-post-award-requirements)

## Scope and complexity budget

Reuse the existing card, creation forms, named preset snapshot, static
boundary asset delivery and channel validator. Wire the existing map layer
registry for the Idaho outline. Apply the preset override policy in legacy
creation as well as through the snapshot writer. Both presets share one static polygon.
Add one card, two named presets, their registry and preset-policy entries, and
shared attribution. The budget permits zero new endpoints, permissions,
services, queues or geospatial dependencies. A partner-only launch or curated
results page would require a separate scope decision.

## Acceptance

- [x] Verify that each card button submits the intended preset ID and that
  the creation endpoint redirects to its matching run URL. Verify the
  image, responsive card and credit on the card and direct run templates.
- [x] Read the generated snapshots and preserve the full settings of each
  source outside the Idaho map stanza. Verify WBT on both, the second
  preset's MOFE flag, and the existing preset and project creation checks.
- [x] Verify the same Idaho outline in both run-page bootstraps. Check inside,
  border-crossing and disjoint selections for both configs. Read back both
  sides of the border in channel output, compare retained bytes after
  rejection and retry on the same run.
- [x] Read fresh channel rasters and map GeoJSON for both disposable WBT runs
  and the two prepared WEPP input files for a seeded MOFE hillslope.
- [x] Complete the contract checkpoints, independent review and focused
  regression gates. See [validation](artifacts/20261119_validation.md) for
  the broad gate and limits of the local evidence.

## Owners and review

WEPPcloud maintainers own launch and runtime integration. The I-CREWS
operator owns access and attribution decisions. Security impact is high because the legacy creation handler applies the
existing override allowlist for these new presets. A dedicated security
review artifact is required.

## References

- [Implementation ExecPlan](prompts/completed/implementation_execplan.md)
- [Package tracker](tracker.md)
- [Canonical interface contract](../../ui-docs/contracts/i-crews-interface-contract.md)
- [Channel boundary contract](../../schemas/channel-delineation-map-boundary-contract.md)
- [Existing channel boundary work package](../20261119_channel_delineation_map_boundary/package.md)
