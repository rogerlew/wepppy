# Independent DEPEND G1 scientific output review

Disposition: retain G1 as an unpromoted numerical candidate. No G1-specific
accounting regression was found, but a confirmed pre-existing particle allocation
mismatch prevents scientific promotion under the program's prohibition on
unexplained accounting mismatches. Cedar/Disturbed and other delivery gates remain
separate requirements; passing them cannot silently waive this finding.

Candidate watershed SHA256:
`635ec1fce1aba3dd2ac166a56751971c90857d5daecc5b5fee9064318b77de50`.

## Complete paired output readback

Independently rehashed all emitted input/output files and source records for all
840 Roads and 348 downstream cases. Inputs equal their paired original inputs.
All 1,188 pass the existing nonnegative/finite, calendar and sediment-report
reconciliation audit. This existing `physical_pass` is not a complete water or
particle-conservation certificate.

Roads: 840/840 existing audit passes; 166 cases have changed output files. Annual
sediment decreases in 15 and is unchanged in 825; none increases. Largest decrease
is 214.1036743361 to 198.4133708414 kg/year (7.3284%) for
site/1718465/outunrut/gravel/none. Frozen magnitude classifications remain exactly
713/766 meaningful and 31/74 small-reference: zero recoveries, zero regressions.

Downstream: 348/348 existing audit passes, versus 347 previously. The prior
SIGFPE case now yields 192.1200073517 kg/year against reference14.0091995489 and
still fails the magnitude criterion. Among the other347 cases, 16 annual exports
decrease and331 are unchanged; none increases. Largest decrease is
446.0529136360 to429.2849794067 kg/year (3.7592%), buffer_cap/site/1718465/outunrut/
gravel/none. No previously successful magnitude classification changes. Original
passing controls remain19/20 fill_fixed,17/20 buffer_cap,17/20 both. All formerly
successful water and soil output files remain byte-identical.

These numerical changes do not qualify a Roads parameterization candidate or
change the rejection of the three standalone downstream treatments.

## Particle evidence and limits of the prior audit

Scanned all PASS EVENT rows: 117,145 Roads,4,695 fill_fixed,7,013 buffer_cap and
6,912 both. Concentrations/fractions are finite and nonnegative. The historical
particle checks documented in the active ExecPlan explicitly checked finite and
nonnegative values; they did not prove fractions sum to1 or class-total/bulk-load
closure. No new fitted tolerance is introduced here: displayed precision bounds
are computed from half the last decimal place of each emitted field.

Positive-sediment fraction sums exceed their print-rounding bound in41 rows:
19 Roads,0 fill_fixed,8 buffer_cap,14 both. One Roads discrepancy is only
1.5e-8 beyond its print bound and may be ordinary native float arithmetic; the
substantial remaining findings cannot all be explained that way. In20 rows the
sum of class concentrations times runoff volume also differs from the ELEMENT
last-OFE boundary sediment mass beyond the combined output-printing bound.

Worst fraction sum is1.00711 versus a print bound0.000016, in buffer_cap/
site/1718465/outunrut/gravel/low,2012 day302. Class mass is17.077241792 kg versus
ELEMENT boundary16.9403551468 kg: discrepancy0.1368866452 kg versus combined
printing bound0.0225151222 kg. This is more than a display-rounding effect.

Every flagged candidate PASS EVENT record and matching ELEMENT row is exactly
equal to its pre-G1 counterpart. Therefore no G1-specific regression is established;
the mismatch predates G1. Exact rows, source/candidate record hashes, PASS/ELEMENT
file hashes, concentration/fraction values, mass calculations and printing bounds
are retained in `depend-particle-quantification.json`.

The existing audit's narrow pass result should remain recorded accurately. The
new evidence blocks an unrestricted physical-acceptance claim and release
promotion until its source and disposition are resolved; it is not authorization
to relax a frozen gate or normalize fractions after the fact.

## Next observation, without behavior changes

Use ordinary baseline case
`roads/site-1718465-inveg-paved-high-erosion_road_cap-project` at2005 day309 as the
primary seed. It needs no downstream parameter treatment: class mass1.4957288415 kg
versus bulk1.485 kg differs by0.0107288415 kg, exceeding print bound0.00206033315 kg.
Use the same run's immediately preceding runoff event2005 day308 as the temporal
control, after verifying its native state. Add buffer_cap/site/1718465/outunrut/
gravel/low at2012 day302 as the larger-discrepancy secondary seed; compare its
original generated baseline case and last prior sediment event2012 day92.

Replay each full configured input period from copied, hashed inputs. Add
observation-only, date/OFE/segment-gated signals at ROUTE's ENRICH call boundaries,
ENRICH entry/exit and SLOSS concentration construction. Retain pre/post `frcflw`
and its sum; `ldtop`, `lddend`, `theta`, `xtop`, `xdetst`, `intlod`, and unclamped
and clamped `rillod`; deposition `gend`, `sedmax`, `sumg` when active; SLOSS
`avsole`, `runoff`, `efflen`, width, and per-class `sedcon`. Require exact ordinary
output parity against the corresponding uninstrumented binary.

Source hypothesis only: ENRICH computes
`rillod=max(ldtop-lddend-intlod,0)` before dividing all class contributions by
`ldtop`. If `lddend+intlod>ldtop`, normalization can exceed1. Observation must
establish the actual path and earliest inconsistent load before proposing any
behavioral repair. Do not clip or renormalize output fractions to hide the cause.

## Reproduction artifacts

- `depend-scientific-output-review.json`: complete paired inventory/magnitude readback.
- `depend-particle-review.json`: full EVENT scan and flagged coordinates.
- `depend-particle-quantification.json`: exact paired rows, hashes and mass bounds.
- `/tmp/depend_review_outputs.py`, `/tmp/depend_review_particles.py`, and
  `/tmp/depend_particle_quantify.py`: executable independent readback scripts.

Review performed read-only against model/source artifacts; only temporary review
artifacts were written. No model behavior, released binaries, defaults or UI changed.
