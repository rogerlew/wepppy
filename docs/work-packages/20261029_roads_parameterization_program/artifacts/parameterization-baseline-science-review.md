# Independent baseline scientific/source review

Reviewer: `/root/baseline_science_review`, 2026-11-03. Scope: repository baseline
contract/inventory and the scientific definitions/resolution in the replacement
project contract. No production source edited, native execution performed or field
calibration claimed by this review.

## Final disposition

**PASS for scientific/source contract scope.** BS-01 is resolved: the final project
contract explicitly requires raw numeric validation before permissive parser
normalization, expected `urr`/`ufr`/`ubr` by role, and disabled erodibility/conductivity
recomputation. No unresolved scientific/source finding remains. This is not an
implementation, runtime-workflow or field-calibration certificate. No new scientific
default or numeric upper bound is justified by this review.

Resolved BS-01 (initial medium finding): the initial saved-baseline validation requires the owned soil parser, but
its successful parse alone cannot establish a well-formed retained template.
`wepppy/wepp/soils/utils/wepp_soil_util.py` preserves unknown numeric tokens through
`try_parse`, can normalize sand/clay and defaults malformed saturation. Its optional
compute flags can replace explicit erodibilities/conductivity. Source templates
also legitimately contain symbolic `urr`, `ufr`, `ubr` fragment tokens. Require raw
numeric validation before normalization, exact expected fragment marker per role,
and parse without coefficient recomputation. Validate actual resolved fragment
numbers separately during assembly. Otherwise a malformed retained baseline could
be silently interpreted differently from the visible source.

## Independently checked evidence

A separate readback reconstructed every source file from inventory numbered records
and compared exact bytes and SHA256: all18 assets passed. Independently parsed all
16 `.sol` files and compared every conductivity/Ki/Kr/shear value in all48 role rows
against the Markdown matrix; all passed. The production Roads source SHA256 is
`7506718831d8a8b11ca0877cd75aa82596d0aeb900cf04505f29df864bd77a4d`.

All four inventoried native files (`input.for`, `tilage.for`, `scon.for`,
`param.for`) match both their inventory hashes and `git show` bytes at source
`e0abe0581f77c6f66917e90daf8f8f429e9315c8`. Selected release HEAD is
`547b9e7eb73f484687af0721490022f2cc7d82f2`.

Source readback confirms:

- Legacy98.4 AVKE is an OFE header input, converted from mm/h to m/s in
  `input.for:495–499`; positive AVKE supplies primary tillage-layer conductivity
  in `tilage.for:578`, copied to the secondary layer at line597. It is not an
  independently editable deep-horizon conductivity or instantaneous infiltration.
- Source declarations use native `real`; the selected makefile does not promote
  default real to64 bits. Serialization/native-conversion checks must catch zero,
  underflow and overflow. Representation alone does not bound later products.
- Nonpositive Ki, Kr and shear activate estimation in `scon.for:611,669,704`;
  nonpositive AVKE bypasses its positive replacement. Reset/disable must be a
  separate mode rather than numeric zero.
- `param.for:412,416,488–508` uses coefficients with native adjustments, flow,
  transport and intensity. Increasing an input is not a guarantee of proportional
  outlet export or independent hydrologic/sediment responses.
- All four Roads soil writers apply quarter scaling only to road Ki/Kr for
  low/no traffic. AVKE and shear remain template values. Paved suffix1 contains
  road shear2 Pa. Fill/forest baseline values and depth splitting match source.
- Management diff changes road/fill plant and initial-condition values under no
  traffic, retaining yearly/surface-effect schedules. It must not be described as
  merely a road Ki/Kr change or removal of annual blading.

The retained-baseline prototype reports168 writer cases and336 exact soil/management
pairs. Its stated scope is appropriately limited: source-text retention and current
writer byte parity, not real NoDb lifecycle, canonical fork/archive or native
execution. This review uses it as feasibility evidence only; independent detailed
prototype verification belongs to the correctness review.

## Scientific limits and remaining implementation evidence

The baseline contract accurately separates repository values, project state and
executed artifacts. Role-scoped overrides after ordinary traffic adjustment are
mechanically interpretable. Template Forest applies only to template-owned rows;
it must not be silently applied to source upstream landuse or shared Disturbed
soils. Retained baseline versioning must include actual selection/assembly semantics,
not just assets.

No calibrated interval or universal safe large-value ceiling is established.
Bounded new native contrasts establish only their declared contexts. Save/reload,
actual writer propagation for every role and branch, current-result invalidation,
and browser-to-native/report evidence remain postapproval obligations. Native failure
under an extreme positive input must remain visible and fail publication; it cannot
be reclassified as successful parameter propagation.

## Final reviewed identities

These hashes bind the reviewed snapshot; later edits require delta review.

| File | SHA256 |
| --- | --- |
| `docs/schemas/roads-parameterization-baseline-contract.md` | `d2a73ccd22884b1f9040d259c54c374589e2576201c1ca1ebade9b5220e37aea` |
| `docs/schemas/roads-settings-contract.md` | `8c849bbc6ee34926caa505d78c6c076407a440cee75fc64ad659107110d18ed7` |
| `docs/adrs/ADR-0135-roads-settings-controls.md` | `c24df1c900787ff7f21cb76805915d2f86c28da40c1f954b80a10ef94f62c42e` |
| `docs/work-packages/20261029_roads_parameterization_program/artifacts/parameterization-baseline-inventory.py` | `59ae5c176935b3af046c7e2a020e2fc4af4393e105fabf91d7048819630bbaa1` |
| `docs/work-packages/20261029_roads_parameterization_program/artifacts/parameterization-baseline-inventory.json` | `0df45896deb664c3cc5d33754fcecad9650f5ba9f6da98b85c0cfc11cfb0976a` |
