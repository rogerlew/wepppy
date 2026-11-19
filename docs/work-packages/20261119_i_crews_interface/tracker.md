# I-CREWS interface tracker

## Status

Scaffolded on 2026-11-19 at 20:15 UTC from `79ab5239d`. The
[ExecPlan](prompts/active/implementation_execplan.md) records the implementation
and validation milestones.

## Tasks

- [x] Confirm the two source presets, shared boundary design, and proposed card
  copy and credit.
- [x] Validate the candidate Idaho GeoJSON and record its provenance.
- [ ] Ratify the canonical launch and attribution contract.
- [ ] Wire the card, two presets, application assets and run credit.
- [ ] Verify project creation, both channel backends, and prepared MOFE output.
- [ ] Complete independent correctness review and run the repository gates.

## Decisions

- The operator specified one Site Specific Resources card with two launch
  choices. The MOFE choice uses `disturbed9002-mofe.cfg` as its source and is
  named `i-crews-mofe.cfg`.
- The MOFE source inherits TOPAZ from `_defaults.cfg`, uses
  `wepp_260714`, and sets the maximum to five overland flow elements.
  Carry these values through. The other source explicitly selects WBT and
  uses `wepp_261118`.
- Both presets explicitly use `intersects` and share the Idaho polygon.
  Propose center `[45.6, -114.15]` in latitude/longitude order and zoom 5
  for orientation. Users zoom in before choosing a delineation extent.
- Proposed defaults are a public Preview card under the normal creation
  policy, direct run launches, and an I-CREWS project link. Confirm any
  partner-only access requirement and final NSF disclaimer wording at the
  contract checkpoint. The specified TOPAZ lineage needs no decision unless
  the operator wants a WBT-based MOFE preset instead.

## Evidence and handoff

The Census 2025 candidate contains one valid WGS 84 polygon with 3,254
exterior coordinates. It is 90,579 bytes raw and 26,090 bytes gzipped.
The existing validator admitted an inside extent and a cross-border extent
and rejected a disjoint extent and an extent outside the polygon but inside
its bounding box. The WBT preset snapshot probe preserved the map values.
Both native workflows remain implementation acceptance tests.

The provided 960 by 960 illustration is `/tmp/i-crews-interface.png`
with SHA-256
`f8a86060e3df8f542de6ceeca9daae49c305c5dd2c3a6a551a66fa144b9b3569`.
The candidate is `/tmp/icrews-boundary.pllq3m/idaho-boundary.geojson`
with SHA-256
`3561a63bf7e46cb84ead392d2ddfeccf8f2ae7a900bc360f2e0cab7be0dab336`.
The ExecPlan includes the source and regeneration instructions for the
boundary. Promote the artwork to a tracked static asset at implementation.
