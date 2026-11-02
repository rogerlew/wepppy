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
The inverse theta_whole/c is not a universally validated retention law. The
explicit experimental SSURGO option below has bounded consumer admission; this
does not validate the nonporous-fragment assumption for every eligible source.
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

KSFLAG changes frost execution and conductivity adjustments in the audited
native paths, including cropland crust/tillage/canopy behavior and rangeland behavior. Compare retention within each configuration; configuration contrasts
do not isolate frost causality. A failed configured history blocks complete-
history admission even when the printed unmet withdrawal is numerically small.
Record the actual signed-input guard, its available relative ST, dry-reference
water, and producer timing before considering a tolerance or accounting change.
Zero allocatable ST is not proof of zero absolute liquid. A failure encountered
under KSFLAG1 is not proof that water was frozen at the failing boundary.

Rationale: the bounded retention/configuration experiment reached a zero-ST
signed-withdrawal stop after earlier active frost. Its last coarse snapshot had
zero frozen thickness. Subsequent producer observations attribute the deficit to
interception allocation against a rounded supply. Preserve the original failed
history and distinguish repaired completion from consumer/physical closure. See [ADR-0128](../adrs/ADR-0128-retention-frost-consumer-experiment.md).

## Frost policy and legacy compatibility

Treat frost-file parameters, actual frost execution, conductivity adjustment and
native land-use identity as separate evidence dimensions. A frost.txt sidecar is
not an activation switch. Verify flags after native overrides and observe calls;
product labels such as forest, range, disturbed or road do not identify the native
management code. Do not change land use to activate frost.

The audited2010 Roads/eRMiT binaries execute frost on their retained KSFLAG0 decks.
The audited modern gate suppresses it. A same-source frost-only bypass establishes
causality for activation and paired-output differences in the tested native-landuse1
paths while preserving exact warm and
already-active KSFLAG1 controls. This does not justify global restoration: energy,
fine/coarse stock closure, real native-range coverage and field calibration remain
separate requirements. Preserve existing production policy until those gates and
an explicit adoption decision are satisfied. Historical changes document an intent
to suppress nonagricultural frost, but the scientific calibration rationale for
that suppression and the original Roads/eRMiT calibration assumptions remain
unverified.

Use complete supported calendars per output family. The legacy eRMiT selected-year
climate is nonconsecutive; its daily water output retains source years. A current
two-year consecutive excerpt is an exploratory compatibility fixture, not a full
reproduction of the original ten-year stage. Do not silently relabel its weather
or weaken calendar validation to claim full compatibility.

Rationale and source-backed evidence: the active rock-water program's
[frost lineage](../work-packages/20261101_rock_water_development/artifacts/frost-lineage.md),
[general comparator map](../work-packages/20261101_rock_water_development/artifacts/general-native-comparator-map.md)
and [frost-only readback](../work-packages/20261101_rock_water_development/artifacts/F04-science-readback.md).
The general representation contract remains authoritative when this package closes.

## Interception ownership admission

Interception must not persist more water than its represented primitive supplies
and carried store own. Distinguish exact accepted-store feasibility from subsequent
binary64 and REAL flux rounding. Fixing an already-overdrawn consumer expression in
higher precision alone is insufficient; a small deficit does not justify spending
dry-reference water or dropping the signed demand. Assess all confirmed consumers,
including canopy carry transfer, storm depletion, daily/hourly input and effective-
plane runoff subtraction. Carry may already have been allocated by IDAT, so transfer
admission requires actual same-day producer/consumer evidence.

The expansion candidate in [ADR-0129](../adrs/ADR-0129-conservative-interception-allocation.md)
passes a bounded twelve-history panel. Full-domain and accepted-flux evidence,
shared-consumer coverage and general regressions remain required before promotion.


## Optional SSURGO retention artifact contract

The parent admission decision of 2026-11-02 accepts development of an explicit experimental option under ADR-0132. Commit this contract and ADR as an ancestor before applying the implementation. The default producer remains unchanged; the installed controller and integration gates below remain required before implementation acceptance.

The explicit `ssurgo-volume-inverse-experimental-v1` builder policy follows ADR-0132 and ADR-0127 eligibility after final source selection. It requires a source acquisition receipt SHA256 and the complete requested successful source-profile set. No other source family, default formula, persisted setting or density-changing treatment is admitted by this option.

Every opt-in source artifact contains the policy marker and a matching source-v3 companion. Source decisions bind original values, final fallback branches, selected component/horizon IDs, eligibility reasons and emitted row identities, including generated 200 mm splits. Treatment-v3, stack-v3 and stage-v3 companions bind actual parent soil and companion hashes, ordered lineage and actual settings. Final clipping remains nominal serialized support; native remapping is separate evidence.

The marker requires its companion. Missing, mismatched, malformed or foreign identity cannot silently downgrade to ordinary handling. Readback follows portable relative references only within caller-owned project/source root authority, rejects symlink traversal before reads, and preserves whole-project relocation. Source metadata cannot grant arbitrary filesystem authority.

All four opt-in producers require fresh destinations and exclusively create soils and companions. Existing files, dangling links and competing creation reject without overwrite or unlink. Default-source rebuilds reject stale opt-in treatment reuse. Unmarked ordinary inputs preserve their established behavior. Blank density lookup cells use the canonical no-override parser; actual numeric changes and recomputation reject.

P03 supplies bounded consumer admission for the fixed six-source project, unchanged-density treatments and the actual hourly engine: 142 histories, with internal observations on H11/H28/H40 and nonvacuous accepted-root withdrawal on H40. Source-to-native remapping, required consumer domains and accepted withdrawal evidence are specific to those retained inputs and source revision. This does not establish universal physical validity, thermal closure, a full-system water budget, field calibration or source-family transfer.

Mathematical eligibility is the generic API rule, not a claim of physical validation for every eligible profile. Do not introduce a case-specific source whitelist or tune the inverse to the retained six sources. Independently bound acquisition association remains mandatory for each build.

Installed-module spawn and actual generated-artifact propagation must pass after integration with no research initializer. Bind its 66 soils/193 OFEs and complete companions to the P04 artifacts already consumed by P03. Exact unchanged native inputs permit reuse of that consumer evidence; a companion or a successful job alone is not admission. Focused, stub, broad regression and independent integration outcome reviews remain required. No default migration, automatic rebuild, UI or persisted policy change, density-changing treatment or deployment is authorized.

The accepted bounded evidence and parent decision are indexed in [ADR-0132](../adrs/ADR-0132-optional-ssurgo-retention-builder.md#evidence-and-gates).


## Acquisition association boundary

`retention_source_receipt` is a caller-supplied SHA256 identifier. The API checks its syntax and internal source/decision/emitted-row/parent consistency; it does not open or independently verify the acquisition receipt, raw source snapshot or cache. A matching hash is not external source authority, institutional attestation or proof that the metadata describes an actual acquisition.

The authorized acquisition/build caller must independently bind the actual receipt to the complete consistent source snapshot, production cache schema/ordered rows/missingness, selected components/horizons and builder input fields. Retain that association evidence with the build. P04 supplies this separate evidence through its frozen P01 tables and finalized-cache/source-record audit; generic companion validation alone does not reproduce that verification. This boundary remains mandatory for every later opted-in build.
