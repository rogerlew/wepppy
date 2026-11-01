# Whole-soil water capacity contract

Status: evidence and change-admission contract. Existing production formulas,
source priorities, missing-value behavior and native caps remain unchanged.

## Source basis and preparation

NRCS defines SSURGO wthirdbar_r and wfifteenbar_r as whole-soil volumetric
percentages. The fragment and sieve fields used by the current Horizon adapter
are mass percentages. Preserve original horizon/component/mapunit keys, nulls,
source timestamp and size support. Separate chfrags volume records are not an
interchangeable replacement for the sieve-derived mass fraction.

References: [NRCS SSURGO field definitions](https://www.nrcs.usda.gov/sites/default/files/2022-08/SSURGO-Metadata-Table-Column-Descriptions-Report.pdf)
and [NRCS soil properties guidance](https://directives.nrcs.usda.gov/sites/default/files2/1725389482/Part%20618%20Subpart%20A%20%E2%80%93%20General%20Information.pdf).

For mass fraction w, fine-earth bulk density rho_f and fragment density rho_r,
the additive-volume fine-earth share is:

    c = rho_r*(1-w)/(rho_f*w + rho_r*(1-w))

Under the additional nonporous-fragment assumption, theta_whole = c*theta_fine.
The inverse theta_whole/c is a diagnostic, not an approved retention law.
Porous fragments, interfaces, density basis and incompatible source estimates
can invalidate this approximation. An inverse above unity or fine-earth porosity
identifies assumption/source incompatibility; it does not alone prove the
published whole-soil measurement invalid.

The current SSURGO source branch divides retention by 1-min(w,0.5), a mass
complement rather than c. Subsequent native multiplication by c therefore does
not generally recover source whole-soil retention. Before native guards, at the
same assumed density, the ratio is c/[1-min(w,0.5)]. Its direction is not universal,
especially beyond the mass cap. Native density adjustments and the 85% mass cap
must be distinguished from this diagnostic.

Missing FC and WP can independently select Rosetta; invalid prepared pairs can
replace both values. Preserve final branches as well as attempted source notes.
Measured zero is distinct from missing: the adapter can retain zero while native
nonpositive-input handling estimates retention. Do not silently introduce a new
zero, fallback, clipping or denominator-floor policy.

## Generated artifact evidence

Any preparation change must retain source, prepared and serialized values and
actual writer/parser readback, including four-decimal FC/WP, two-decimal BD/RFG,
all 200 mm boundary split rows and source-to-row identity. A controlled single
horizon verifies preparation and serialization only; it does not verify actual
mapunit/component selection, a complete field profile or native execution.
Bind loaded source modules and Rosetta model assets. Preserve excluded rows and
explicit failures. Verify native reader interpretation separately before promotion.

## Native consumer domains

Native CPM conversion, entrapped-air adjustment, retention guards, density
recalculation and dry-reference offsets are separate operations. Their order
and executed branches must be retained. With layer thickness h and dry reference d,
current UL=(POR-d)*h and FC=(theta_fc-d)*h; DRFC includes an air adjustment.
Do not infer that multiplying POR by CPM is safe merely because retention limits
are ordered.

A candidate must independently establish finite, valid domains for conductivity
(including FC/UL and its logarithm) and drainage (including UL-DRFC), under both
frozen and unfrozen branches. A proposed strict 0<FC/UL<1 admission test must not
be confused with a claim that current native guards enforce it. Zero denominators
must be resolved physically, not hidden with arbitrary floors.

For fixed coarse coordinates total water is ST+FRZW+d*h; the liquid and ice dry
references depend on frozen thickness. Changing capacity requires explicit
ownership of displaced water, accepted fluxes and reference changes. Retain signed
relative coordinates separately from absolute liquid/ice validity. Validate actual
branch execution and per-stage closure before annual-output comparisons.

## Change admission and rationale

A replacement requires an ADR describing density and water bases, caps, missing
and zero semantics, compatibility on rebuild, native constitutive domains and
an overflow policy. Use source-bound actual generated files, native reader and
complete histories with a zero-rock control and supported high-rock/freeze-thaw
cases. Validate stocks and accepted fluxes, not only persisted parameters or job
success. Do not alter uploaded files or existing projects implicitly.

An admissible staged experiment is a bounded preparation prototype comparing the
volume inverse with the current heuristic, accompanied by native guard and
capacity-domain readback. It is not authority to promote the inverse or a global
porosity multiplier. Source incompatibilities must remain visible. Surface area,
exposure and RUSLE overlap remain separate under the
[rock representation contract](rock-fragment-representation-contract.md).

## Native support and execution coverage

The audited native input path adds200mm to the final source boundary before its
1800mm cap and computational resampling. Keep emitted support and consumed layer
depths separately; compare integrated stocks using actual native thickness. Bind
the exact reader/build, because a file boundary alone does not prove native depth.
Native input density floors/caps and binary32 remapping can also prevent source
density or nominal RFG from reaching SCON unchanged. Preserve these stages.

Winter summary records can count eligible gates before a KSFLAG skip. Establish
actual frost routine calls from payloads and their source-owned counter semantics,
not the number of summary lines or the length of the climate history. A paired
change in relative ST must be interpreted with its dry-reference offset; it does
not alone demonstrate changed absolute initial water or available storage.


## Configuration and signed-input failure admission

KSFLAG changes both frost execution and rangeland conductivity in the audited
native path. Compare retention within each configuration; configuration contrasts
do not isolate frost causality. A failed configured history blocks complete-
history admission even when the printed unmet withdrawal is numerically small.
Record the actual signed-input guard, its available relative ST, dry-reference
water, and producer timing before considering a tolerance or accounting change.
Zero allocatable ST is not proof of zero absolute liquid. A failure encountered
under KSFLAG1 is not proof that water was frozen at the failing boundary.

Rationale: the bounded retention/configuration experiment reached a zero-ST
signed-withdrawal stop after earlier active frost. Its last coarse snapshot had
zero frozen thickness; retained evidence does not establish the signed-input
origin. Preserve failed histories and defer consumer/closure claims that depend
on their completion. See [ADR-0128](../adrs/ADR-0128-retention-frost-consumer-experiment.md).
