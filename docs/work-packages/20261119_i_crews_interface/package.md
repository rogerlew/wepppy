# I-CREWS interfaces in WEPPcloud

**Status** Open, scaffolded on 2026-11-19 at 20:15 UTC.

## Outcome

Add one **I-CREWS** card to **Site Specific Resources** on the WEPPcloud
Interfaces page. Offer two run launches from that card. Both open on Idaho
and require the channel delineation extent to intersect the Idaho boundary.

| Preset | Source | Proposed button |
| --- | --- | --- |
| `i-crews.cfg` | `disturbed9002_wbt.cfg` | Start I-CREWS WBT Run |
| `i-crews-mofe.cfg` | `disturbed9002-mofe.cfg` | Start I-CREWS Multiple OFE Run |

The Multiple OFE preset retains the source's TOPAZ delineation and multiple
overland flow elements, which allow a hillslope to be represented by multiple
segments. Keep the model executable, scientific parameters and modules from
each respective source preset. Public Preview under the existing project
creation policy is the proposed launch posture.

## Proposed card copy and credit

> Use WEPPcloud to explore how wildfire and land management affect runoff,
> erosion, and sediment delivery in watersheds that overlap Idaho. This
> interface supports Idaho Community-engaged Resilience for Energy-Water
> Systems (I-CREWS), an Idaho NSF EPSCoR project studying how communities can
> adapt their energy and water systems to changes in climate, population, and
> technology.

> This product was made possible by the NSF Idaho EPSCoR Program and by the
> National Science Foundation under award number OIA-2242769.

Include visible credit on the card and on direct visits to either run
interface. Confirm the final disclaimer and placement during the contract
checkpoint. [I-CREWS research](https://idahocrews.org/research/) ·
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

- [ ] Each card button creates the intended run through the existing form and
  lands on the matching run URL. The image and both labels work in the
  existing card layout. The funding text appears on the card and both run
  surfaces.
- [ ] Read back both generated run configs, including the Idaho map settings,
  WBT versus TOPAZ, and the MOFE flag on the second preset. Prove the
  preset-policy corpus still loads and existing project creation still works.
- [ ] Both interfaces show the same Idaho polygon. Exercise an inside extent,
  a cross-border extent, and a disjoint extent on both launch paths. Confirm
  that accepted jobs keep the full extent and rejected requests preserve
  existing channel artifacts and readiness.
- [ ] Read back fresh channel outputs and map layers from disposable WBT and
  TOPAZ runs. Verify a prepared multi-OFE hillslope input from the TOPAZ preset
  retains multiple segments. Record exact candidate and runtime identity.
- [ ] Complete contract-first, correctness review and regression gates. The
  highest current claim is scaffolded, with a validated candidate polygon.

## Owners and review

WEPPcloud maintainers own launch and runtime integration. The I-CREWS
operator owns access and attribution decisions. Security impact is high because the legacy creation handler applies the
existing override allowlist for these new presets. A dedicated security
review artifact is required.

## References

- [Implementation ExecPlan](prompts/active/implementation_execplan.md)
- [Package tracker](tracker.md)
- [Channel boundary contract](../../schemas/channel-delineation-map-boundary-contract.md)
- [Existing channel boundary work package](../20261119_channel_delineation_map_boundary/package.md)
