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

The exact expansion allocation and confirmed IDAT, daily/hourly FIN and ROCHEK
consumers are admitted as a bounded numerical water-ownership repair. A05 records
30,974,527 executed domain observations with no flagged domains; A06 records
64,935,267 with no flagged domains, joins actual producers to consumers, and
retains selected accepted-flux checks and negative relative-coordinate flags.
These counts are evaluations, not independent states or whole-history closure.
A07 observes changed storm/depletion versus later carry allocation, but its
selected event does not enter GRNA/ROCHEK or prove water creation. No additional
carry fallback or timing repair is admitted from that observation.

Final source `d2e14d96af5942409c9a315dc8594fcc164a702a` combines this repair with
the separately admitted snow-pack debit and donor-limited freeze-restoration
repairs (ADR-0130 and ADR-0131). Combined18, 1,394 native tests, 31 watchlist
cases, two host smokes, six legacy histories, Disturbed, clean and observed
Roads840 panels, and the 492-history application comparison have completed
bounded independent review and parent admission. The exact matched pair is
installed locally with rollback evidence; deployment and final publication
remain separate. These later decisions supersede the historical release hold,
not its retained observations.

Roads engine compatibility and capacity/particle arithmetic are accepted; the
original parameterization screen still fails at 744/840. No threshold was relaxed
and no field calibration follows. Application changes include 978 of 3,443
files, outlet volume −1,129.18 m3 and sediment −49.22 kg, with unchanged maximum
peak. Material storage/lateral timing, liquid/ice partition and channel-area
consequences remain disclosed. Neither these comparisons nor unchanged outputs
prove universal thermal validity, cold-snow budgets, whole-system conservation
or retention defaults. Optional retention has separate bounded P03/P04 and installed-controller
admission; its validity must not be inferred from this numerical repair.

Current parent decisions and independent evidence are retained in the active
program: `combined18-final-execution-v3/parent-acceptance-v1.json`,
`legacy-frost-final-renewal-v1/parent-acceptance-v1.json`,
`final-roads-parent-disposition-v1/decision.json` (SHA-256
`fb384407f3d7cf85046e24103ef5fa15e0b415e71d3c9ef5e18579ef4f18c473`), and
`final-application-parent-disposition-v1/decision.json` (SHA-256
`615cedebc5ad2c19e3ca18ac930030f4a9f7aef7decd1b2cdf0a50b59d298194`).
The latter binds actual science, implementation and security reviews. The
program's N01/A05/A06/A07, combined18, native, legacy, Disturbed, final Roads
and application review artifacts retain the precise tested scopes and limits.

## Optional SSURGO retention artifact contract

### Known native coefficient ownership defect

The following records revision 5/S01 history. Current bounded revision 6
conformance is recorded under "Revision 6 ownership correction" below.

S01's four heterogeneous histories on source `d2e14d96af5942409c9a315dc8594fcc164a702a`
confirm that dynamic consumers on OFEs 1/2 use layer-only FC/HK coefficients last
initialized by OFE 3. For each default/optional policy, 10 of 15 observed layer slots
differ from their own initialized coefficients; all 15 HK slots execute the
sub-0.95 power branch. Seven ordinary output files match exactly within each
plain/observer pair. That parity validates observation neutrality, not correctness
of coefficient ownership. Finite conductivity/drainage domains do not cure it.

Unrestricted heterogeneous-use readiness is on HOLD. The coefficient ownership
structure predates revision 5, but inherited source does not prove unchanged
exposure, output consequences or safety. Prior accepted campaigns remain evidence
of their actual measured scopes; neither repeated source material nor mathematical
eligibility establishes a general safe-use class. Management and layer support can
also affect initialized coefficients. No repaired-model counterfactual has been
executed, so these observations do not quantify a hydrograph correction.

Keep the existing default and explicit optional API unchanged. Do not promote the
optional policy to a default, claim universal cancellation, or change existing
project soils on this evidence. A separately authorized native repair requires
source-owned correction, independent reviews and affected-consumer validation.
Local revision 5 artifacts may document the known defect and bounded validation;
they do not establish general release readiness or close the native correctness
gate. This limit supplements, rather than erases, the retained P03/P04 evidence.

Actual execution receipt `fde3107595602efc7a51e057363342694ec255e1dcab5cfc14b8939623a78ebc`,
science disposition `9794141799ccaa81074ab0cad02364d515d3671911c1ee766c789ed94d3e1695`
and implementation review `ec1114fb243da32c563c09121ca777fa8e819e1f6a7882c8b3a8364bad185ace`
are retained under `out/rock-water-development-20261101/`. The active program's
S01 reports identify the exact inputs, observer and source-history evidence.

### Revision 6 ownership correction

MIPA-02 authorizes the bounded per-layer/per-OFE FC/HK repair under the
[native coefficient contract](native-mofe-coefficient-contract.md). Preserve the
existing formulas, initialization schedule, retention defaults and guard behavior.
Native source `b581352b6` implements the ownership correction in local undeployed
revision 6. Four default/optional daily/hourly histories change first observed
wrong-owner consumer states from 20/30 to 0/30 per history, with 15 actual unsaturated
HK powers and exact ordinary plain/observer output parity. Single/repeated-material
controls retain exact outputs. Historical S01 and revision 5 claims remain history.
This closes the bounded FC/HK ownership defect, not 9005/RAP compatibility, later
density/tillage validation, field calibration or universal physical validity.
Final release verification is recorded in the revision 6 release evidence.

### Existing bounded artifact admission

The explicit experimental option under ADR-0132 is accepted for canonical local integration following the contract/ADR ancestor and actual installed-controller review. The default producer and formulas remain unchanged. Bounded P03/P04 applicability and independent acquisition association remain mandatory. Broad repository regression passes; the known native correctness and general release HOLD remains separate.

The explicit `ssurgo-volume-inverse-experimental-v1` builder policy follows ADR-0132 and ADR-0127 eligibility after final source selection. It requires a source acquisition receipt SHA256 and the complete requested successful source-profile set. No other source family, default formula, persisted setting or density-changing treatment is admitted by this option.

Every opt-in source artifact contains the policy marker and a matching source-v3 companion. Source decisions bind original values, final fallback branches, selected component/horizon IDs, eligibility reasons and emitted row identities, including generated 200 mm splits. Treatment-v3, stack-v3 and stage-v3 companions bind actual parent soil and companion hashes, ordered lineage and actual settings. Final clipping remains nominal serialized support; native remapping is separate evidence.

The marker requires its companion. Missing, mismatched, malformed or foreign identity cannot silently downgrade to ordinary handling. Readback follows portable relative references only within caller-owned project/source root authority, rejects symlink traversal before reads, and preserves whole-project relocation. Source metadata cannot grant arbitrary filesystem authority.

All four opt-in producers require fresh destinations and exclusively create soils and companions. Existing files, dangling links and competing creation reject without overwrite or unlink. Default-source rebuilds reject stale opt-in treatment reuse. Unmarked ordinary inputs preserve their established behavior. Blank density lookup cells use the canonical no-override parser; actual numeric changes and recomputation reject.

P03 supplies bounded consumer admission for the fixed six-source project, unchanged-density treatments and the actual hourly engine: 142 histories, with internal observations on H11/H28/H40 and nonvacuous accepted-root withdrawal on H40. Source-to-native remapping, required consumer domains and accepted withdrawal evidence are specific to those retained inputs and source revision. This does not establish universal physical validity, thermal closure, a full-system water budget, field calibration or source-family transfer.

Mathematical eligibility is the generic API rule, not a claim of physical validation for every eligible profile. Do not introduce a case-specific source whitelist or tune the inverse to the retained six sources. Independently bound acquisition association remains mandatory for each build.

Parent decision `out/rock-water-development-20261101/P04-parent-integration-disposition-v1/decision.json`
(SHA256 `5b426af69fe64e6c7ced5adbe0edbe22e38598ef80ba094028498543075cb855`)
accepts the canonical local explicit opt-in implementation and installed-controller
artifact gate. Actual receipt `e44238519b8e9f8cbe76c13deba7cd43ec02b114afd0a982128eb27ac4ef19dc`
binds exact reproduction of all 66 soils and companions through ordinary installed
modules. Independent science, implementation and security outcomes pass. Canonical
validation `a22256d2a08140d78e936d1a8b9f5a882a635eaedbe97c91220c1b07a710c694`
records 84 focused tests, 346 affected tests, two stub modules and test-stub checks
passing. Exact unchanged inputs permit reuse of bounded P03 evidence without a
new native campaign. At that integration checkpoint, broad repository validation
and final documentation, archive, public selection and release signoff remained
open. Broad-v2 subsequently passes 12,729 tests with 423 skips and unchanged bound
code/binaries; parent `c72571780b7552e3840d5c5cfc90cddda623343054a4679e986f593974c504d9`
accepts that regression evidence. It does not resolve the native ownership HOLD.
No default adoption, deployment,
universal physical validation or relaxation of acquisition association follows.

No default migration, automatic rebuild, UI or persisted policy change, density-changing treatment or deployment is authorized.

The accepted bounded evidence and parent decision are indexed in [ADR-0132](../adrs/ADR-0132-optional-ssurgo-retention-builder.md#evidence-and-gates).


## Acquisition association boundary

`retention_source_receipt` is a caller-supplied SHA256 identifier. The API checks its syntax and internal source/decision/emitted-row/parent consistency; it does not open or independently verify the acquisition receipt, raw source snapshot or cache. A matching hash is not external source authority, institutional attestation or proof that the metadata describes an actual acquisition.

The authorized acquisition/build caller must independently bind the actual receipt to the complete consistent source snapshot, production cache schema/ordered rows/missingness, selected components/horizons and builder input fields. Retain that association evidence with the build. P04 supplies this separate evidence through its frozen P01 tables and finalized-cache/source-record audit; generic companion validation alone does not reproduce that verification. This boundary remains mandatory for every later opted-in build.
