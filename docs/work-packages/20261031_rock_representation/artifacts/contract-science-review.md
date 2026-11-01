# Independent scientific contract review

Reviewer: `/root/rock_contract_science`, 2026-11-01 UTC. Starting implementation
revision: `7d7d8c72e`. Reviewed the package, active ExecPlan, contract-decision,
rock-fragment representation contract and ADR-0125, plus actual ISRIC extraction,
HorizonMixin serialization, SSURGO retention preparation and native INPUT/SCON.

Disposition: **PASS for the bounded development checkpoint**. No blocking
scientific finding for the two stated dimensional repairs. This is permission to
implement and validate the declared repairs, not final implementation acceptance,
field validation, a native physics change or deployment approval.

## Independent evidence

The official [ISRIC property metadata](https://maps.isric.org/soilgrids.html)
identifies bdod as fine-earth bulk density. The [SoilGrids layer table](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html)
search readback specifies cfvo in cm3/dm3 and division by10 to volume percent,
and bdod division by100 to g/cm3 (equivalent kg/dm3). Direct opening of the FAQ
timed out during this review; no successful direct retrieval is claimed.

The [USDA-hosted 2004 WEPP correction](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/docs/wepp_rock_correction_issue.pdf)
defines the conversion using fine-earth bulk density and fragment density,
with the existing mineral convention 2650 kg/m3. The contract's two equations
are algebraic inverses of that corrected relation. They do not assume that
coarse-fragment mass and volume percentages are identical.

Current ISRIC extraction normalizes cfvo and bdod before ISRICHorizon. The
constructor assigns cfvo directly to rfg. HorizonMixin emits rfg as the final
7778 horizon token, and native INPUT reads that token into rfg2, caps it at85
percent and divides by100. SCON uses that mass fraction and fine-earth density
to calculate CPM. Thus the source-to-serializer chain supports the proposed
basis correction; this is not inferred from variable names alone.

An independent scalar example, v=0.20, rho_f=1.3 and rho_r=2.65 g/cm3, gives
w=0.3375796178343949 and inverse v=0.20. Relabeling v as mass instead gives
native-inferred v=0.10924369747899161 at the same density. This example verifies
basis arithmetic, not field accuracy or emitted-file precision.

Source hashes inspected:

- ISRIC module: `c9bb373ab0801698c12ab9cc7c46c409547c1f705032be2b39b8d3fce7918037`
- HorizonMixin: `e803959e3281f00c6d6b60e2431bff0586a8a169972e80f7072a85feabf29d53`
- SSURGO module: `02d3b1da89195077d32df279790314d89d19183518450ca30b9231f32390bb27`

## Required implementation acceptance evidence

The plan's proposed real raster/manifest and generated-soil/native interpretation
gates are appropriate. Acceptance must distinguish source value, rounded emitted
value and native consumed value. HorizonMixin currently writes density and RFG
with one decimal. Native INPUT additionally bounds positive density to0.8–2.0
g/cm3 and mass RFG to85 percent. Test ordinary non-capped round trips within
explicit serialization bounds, plus capped/high-rock and out-of-range-density
cases as documented departures; do not claim exact volume conservation across
those native operations. Preserve the normalized200mm boundary and explicit
user cover overrides. Test both cfvo paths and both C modes using actual raster
I/O rather than replaying only extracted arithmetic.

A fixed2.65 density is a model convention, not a measured property of every rock.
It is justified here by consistency with the existing native consumer and must
remain visible in provenance. Zero-volume and full-volume mathematical endpoints
can be tested, but a100percent fragment input is not proof that the mixed-soil
model faithfully represents bare rock: native caps remain active. Missing or
invalid density must not silently select a new density.

## SSURGO retention research boundary

The [NRCS SSURGO metadata, printed page9](https://www.nrcs.usda.gov/sites/default/files/2022-08/SSURGO-Metadata-Table-Column-Descriptions-Report.pdf)
defines wthirdbar and wfifteenbar as whole-soil volumetric water percentages.
Current SSURGO preparation divides these by one minus mass-derived rock fraction,
with a50percent cap. That is not the dimensional inverse of a nonporous-fragment
volume correction. The discrepancy warrants a separately retained quantitative
investigation, including original density support, whether fragment pores store
water, native retention caps and the existing heuristic's provenance. It must not
be represented as a validated volume conversion. The current package explicitly
leaves this heuristic unchanged; that boundary is scientifically defensible for
the two confirmed unit/basis repairs, but broader rock-support completion must
retain it as unresolved rather than silently exclude it.

## Surface and storage limits

The overlap bounds and distinction between total and exposed rock are sound.
Scalar fraction-of-bare normalization does not establish co-location. Preserving
existing RUSLE proxy behavior during a unit repair avoids introducing an
unreviewed scientific substitution. Permanent surface rock must not be modeled
by newly added decomposing biomass or a landuse switch. Native capacity ordering,
freeze/thaw and full stock/flux accounting remain separate gates. The contract
correctly rejects field/annual-causal claims from dimensional tests alone.

No production file was edited by this reviewer. Final implementation and generated
artifact review remains required after execution.
