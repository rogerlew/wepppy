# Next audit: generated road-role hydraulic consistency

Status: designed, not executed. Continue the active program plan with artifact
revision 3 and current hourly/PMET/snow settings. No production parameter change.

## Question

Does the experimental road/fill preparation represent the intended constructed
surface consistently across density, pore space, retention and conductivity?
The current road-cap transformation changes `ksatadj` and upper 200 mm conductivity;
it preserves bulk density, organic matter and water-retention inputs. First-day
state readback establishes that preservation, not whether it is physically adequate.

## Required evidence before selecting numerical rules

1. Trace actual generated input fields through the Roads research adapter and
   native initialization/update routines: `bd`, organic matter, rock, `fc`, `wp`,
   `ksat`, `ksatadj`, suction and restrictive layers. Identify units, derivations,
   rounding and initialization versus subsequent daily changes. Use the final
   source 6112b68bc and unchanged binary pair; trace both hydraulic runtimes only
   as source context, keeping candidate execution settings fixed.
2. Inventory all seven development profiles by road/fill/buffer and depth. Preserve
   raw generated source provenance and normalized 200 mm break. Compare native
   effective hydraulic state with legacy controls without splicing formats 98.4
   and 9002 or assuming equivalent textual values imply equal initialization.
3. Locate the intended construction/treatment semantics in existing Roads and
   Disturbed code/specifications. Distinguish a confirmed implementation mismatch
   from a missing experimental hypothesis. Natural source-soil values are not
   automatically defective because they differ from a road-template prior.
4. Obtain primary physical support for any proposed role-compaction/exposure rule,
   including a physically coupled retention/conductivity response and applicable
   ranges. Do not invent a universal bulk-density target from sediment fit alone.
5. Predeclare the smallest supported coupled contrast with material/deeper-layer
   preservation, current runtime, passing controls and retained low/high/small
   failures. Read back emitted inputs and native state before interpreting sediment.

## Acceptance and stop conditions

The deliverable is a source-to-native state mapping, concise physical justification
and a reproducible declared contrast. Numerical agreement alone is insufficient.
Any source-equivalence probe must preserve all non-target inputs and document
actual native initialization, rather than treating day 1 output as pre-event state.
If a physically consistent candidate emerges, recheck the full 840 development
matrix before using withheld materials. Keep 95%/90% criteria, all failure classes,
climate-runtime validation and the human UI specification/layout gate unchanged.

Scope is experimental Roads preparation. No general soil-writer, SSURGO,
Disturbed, production default, native binary or UI change is authorized by this
audit declaration alone. Existing broader authority supports proposing a bounded
repair if a confirmed defect is found, with its own evidence and disposition.
