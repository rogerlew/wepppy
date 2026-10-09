# ADR-0083: Low-Severity Forest Initial Random Roughness

Status: Accepted
Date: 2026-10-09

## Context

The standard forest sequence used initial random roughness of 10 cm unburned,
4 cm low severity and 6 cm moderate/high severity. Young forest starts at 8 cm
unburned and shares the forest burn templates. Roger requested a bounded
canonical-matrix assessment before harmonizing low severity with the other
burned forest defaults. Random roughness affects erosion as well as hydrology;
a consistent parameter table is not itself evidence of greater accuracy.

## Decision

Set initial random roughness (`ini.data.rrinit`) in
`wepppy/wepp/management/data/UnDisturbed/Low_Severity_Fire.man` from
0.04 to 0.06 m. Update the same field in all four corresponding texture rows
of `wepppy/nodb/mods/disturbed/data/extended_land_soil_lookup.csv`.
Correct the low-severity forest parameterization inconsistency. The revised
event-level sediment ordering supports this correction; changed sediment
delivery is a modeled consequence, not an accepted degradation or a trade-off
for cosmetic consistency. This does not claim calibration against observations.

## Decision Provenance

- Decision Venue: Roger/Codex workspace conversation, 2026-10-09,
  America/Los_Angeles timezone; exact message time not retained.
- Participants Present: Roger Lew and Codex.
- Decision Owner: Roger Lew, explicitly approving the change and ADR after
  reviewing the sandy-loam severity series. Roger subsequently clarified that
  the decision corrects a parameterization inconsistency and improves the
  sensibility of event rankings, rather than accepting a sediment trade-off.
- Implementer: Codex.

## Change Summary

Only the shared low-severity forest template RRINIT and its four packaged
extended-lookup cells change, 0.04 -> 0.06 m. Standard remapping applies this
template to forest, deciduous forest, mixed forest and young forest when
classified as low burn. Other mappings referencing this same template also
inherit the change; maps selecting different templates are unchanged.

Preserve `rhinit` at 0.04 m, all cover/soil/routing fields, unburned and other
burn-severity defaults, and model binaries. The base lookup has no RRINIT
column and requires no edit. Unrelated preexisting differences between the
packaged extended lookup and templates are outside this decision.

## Rationale

The 112-run assessment (96 fresh canonical controls plus 16 low-burn trials)
found effectively unchanged runoff and unchanged full-record severity rankings.
The subsequent same-date sandy-loam PASS sediment comparison identifies
17 dates with low-burn delivery greater than moderate burn at 4 cm, versus
zero at 6 cm. This is improved event-level ordering, distinct from the already
ordered full-record totals. Three
soil fixtures have identical compared runoff/peak/sediment outputs at output
precision. In sandy loam, PASS surface volume changes -0.0000326% and maximum
peak +0.0176%. Adopting the already-used burned-forest value avoids an
unsupported non-monotonic roughness sequence without adjusting other parameters.

## Alternatives Considered

1. Retain 4 cm: rejected because it preserves the identified low-severity
   parameterization inconsistency and less sensible event-level sediment ordering.
2. Reduce all forest roughness values: rejected as out of scope and unsupported
   by the broader soil-state-dependent sensitivity results.
3. Tune for strict event rankings or repair roughness decay/interrill algorithms:
   rejected. No such model changes are necessary for this bounded decision.

## Consequences

These are documented model responses to the correction, not evidence that
lower sediment is inherently worse. Absolute sediment accuracy still requires
independent evidence; improved ordering alone does not establish that accuracy.

The sandy-loam fixture retains its assigned roughness. Raising 4 to 6 cm
crosses the existing approximately 4.96 cm interrill-delivery cutoff. PASS
delivered sediment decreases 17.49%, from 9.10 to 7.51 kg/ha/year, and 24 of
30 sediment-producing dates become zero-delivery dates. Remaining rill
processes still produce sediment. This is not a uniformly scaled erosion
reduction or proof of physically zero sediment on those dates.

The canonical evidence covers one synthetic 100-year climate and one steep
profile, not field-observed sediment accuracy or watershed outlet response.
Preserve both rounded EBE and higher-precision PASS measures in the evidence.

## Evidence

- [Targeted 4-versus-6 cm results](../work-packages/20261009_rrinit_parameter_review/low-forest-4v6-results.md)
- [Case comparisons, ranks and provenance](../work-packages/20261009_rrinit_parameter_review/artifacts/low-forest-4v6/)
- [Broader sensitivity study](../work-packages/20261009_rrinit_parameter_review/sensitivity-results.md)
- [Static flow and override assessment](../work-packages/20261009_rrinit_parameter_review/assessment.md)

## Risk and Rollback Notes

Review this choice if representative observations or independent cases show
unacceptable loss of small-event sediment or other material regressions.
Rollback must restore the template and all four lookup cells together to
0.04 m, retaining this ADR and experiment evidence. Do not compensate by
tuning other parameters implicitly.

Existing prepared inputs, cached/project-local managements and exported
lookups are not automatically migrated. Regenerate intended project artifacts
before rerunning, inspect final `p*.man` values, and preserve user-specified
overrides. New watershed simulations must use fresh same-build hillslope
passes; changing this default does not authorize deployment or rerunning projects.

## Implementation and Validation Plan

No schema, column, class name or override-precedence changes. Verify the
template through the existing Management parser and CSV through `csv.DictReader`.
Compare the production diff field by field to establish exactly five RRINIT
changes and no other data changes. Serialize the four affected forest aliases
through the canonical management-preparation helper and read back 0.06 m.
No new tests or simulation campaign are required for this literal-only change;
the accepted model behavior is already represented by the 112-run evidence.
Lint the ADR and affected documentation, and retain historical study artifacts
without regenerating them against the newly adopted default.

Implementation readback passed: exactly one template field and four CSV cells
changed. All 16 generated canonical low-forest managements parse to 0.06 m
RRINIT, retain 0.04 m ridge height and match the accepted candidate managements.
