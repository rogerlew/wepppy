# Hillslope Water Aggregation Contract

## Scope and status

On 2026-10-20 the operator authorized MOFE water consumer correction and selected
**physical WAT runoff**, retaining subthreshold runoff omitted from PASS export.
Implementation conformance was validated in WEPPpy `1ecf04735` with native
release `54d0867`; contour runtime coverage and the six-year model failure remain
limitations recorded in the 20261020 consumer-accounting validation artifact. Earlier ET/Dp conformance
remains established. Deployment and historical regeneration are separate actions.
This governs native hillslope reports, daily loaders/Ash inputs, selected and
comparison dashboard events, and H.wat Features Export across baseline, Roads
and admitted AgFields sources. See ADR-0099 for scientific decision provenance.

## Scientific source and geometry

For supported WEPP hillslope daily/hourly writers, terminal WAT Q is physical
outlet runoff in mm over the native hillslope area. Current ordinary writers use
`1000*runoff*efflen/totlen`; contour writers use `1000*runoff`. Hillslope input
uses constant width, so `fwidth(1)*totlen` equals the sum of local OFE areas.
Unequal OFE areas are supported. QOFE is version-sensitive: historical local
normalization and current Q aliases both exist. Never infer source version from
Q/QOFE equality or use QOFE to calculate physical hillslope runoff.

Schema-conforming canonical run H.wat artifacts are admitted under the existing
WEPP hillslope producer contract, including legacy artifacts without binary-hash
lineage. Record that trust boundary: a source hash proves bytes, not historical
normalization, and no claim of verified producer lineage follows. Known custom
variable-width
or explicitly unknown-normalization inputs are outside it and must not be relabeled verified
scientific output. This correction does not invent a new normalization for them.
Current contour formulas are source-verified; runtime contour conformance requires
paired evidence before claiming that execution matrix covered contour behavior.

Determine terminal OFE and stationary geometry per native WEPP ID from the full
source, before date/year selectors or mapping multiple native IDs to a feature.
The terminal is the maximum OFE ID in that native hillslope's complete topology.
Area_m2 sums first-observed local footprints, once per native ID/OFE. Changing,
nonfinite or nonpositive observed areas fail explicitly. Do not select one global
terminal after merging native hills or infer an outlet from a day's observed max.

## Field matrix and temporal policy

| Fields | Daily hillslope reduction | Temporal policy |
| --- | --- | --- |
| P, RM, Irr, Ep, Es, Er, Dp | sum(local depth * local Area) / sum(represented Area) | Sum daily fluxes before existing annual averaging |
| ET | Sum reduced Ep, Es, Er | Same as local fluxes; derive before selection |
| Q | Each native terminal Q * full native hill Area; sum volumes then divide full area of contributing native hills | Sum daily physical outlet depths; no PASS threshold |
| latqcc | Each native terminal local depth * terminal Area; sum volumes then divide full area of contributing native hills | Sum daily outlet-equivalent depths |
| QOFE, UpStrmQ, SubRIn, Tile | Retain consumer diagnostic reductions; raw mode always unchanged | Not certified whole-hill external fluxes; never use QOFE as Q |
| Soil water, frozwt, snow, optional profile/interception stocks | Daily loader retains local area-weighted snapshots; export retains legacy representative behavior | Existing export annual sums are legacy diagnostics, not storage balances; no storage temporal redesign in this correction |
| Area / identity columns | Static topology / existing public identity layout | Never interpret summed area-days as footprint |

Local flux denominators preserve the represented-day area policy. Outlet
reductions use full stationary native geometry even when an upstream row is
missing. When a native hill has observations but its known terminal is absent,
report generation and daily loading fail explicitly, exports requesting that
outlet field fail materialization,
and dashboard Q is unavailable. A wholly unobserved date is not a fabricated zero;
empty exports preserve geometry with null metrics. No-observation native hills
are not silently added to daily denominators. Duplicate daily native OFE rows
are malformed; preserve existing rejection and do not deduplicate by guessing.

Keep public raw schemas, report labels/columns/units, temporal selection,
`max(number_of_years - 1, 1)` report divisor, and scope isolation. Native identity
requires sim_day_index qualified by water_year. Export accepts existing calendar
identities and aliases. Use exact joined WAT source bindings for IDs, date, Area
and measures, including hidden reduction dependencies. Existing AgFields
many-to-many rejection remains; do not redesign joins.

## Missing and invalid values

Required keys/columns and finite positive Area are mandatory for populated data.
Native/export local null or NaN flux retains zero-contribution semantics;
infinity and arithmetic overflow fail. Daily loader preserves SQL SUM compatibility for local measurements: mixed NULL
values contribute zero numerator with all represented Area in the denominator;
all-NULL yields NULL; IEEE NaN propagates. Absent optional stock columns yield
NULL. These cases must be tested separately. Outlet Q/latqcc null,
NaN or infinity is unavailable, never zero: report/loader/export fail explicitly;
dashboard returns null. Dashboard invalid area or flux arithmetic is unavailable
for P/Q/ET and remains null in ranges, differences, colors and tooltips.
Outlet validation in exports is conditional on selected fields: Q-only validates
Q, lateral-only validates latqcc, and local-only P/ET/Dp selection retains sparse
represented-day weighting without requiring outlet observations. Both outlet
fields require known full topology and geometry.
Required Ash model inputs must be finite before simulation; unavailable daily Q
must not silently bypass transport branches and leave initialized zero outputs.

## PASS, diagnostics and Ash compatibility

PASS export is a separate product. Its EVENT gate uses internal terminal runoff
>= 0.001 m, not printed WAT Q >= 1 mm. SUBEVENT/NO EVENT omit surface runoff;
small lateral volumes can also be suppressed. TotalWatSed named Runoff and
watershed routing retain PASS volumes. Preserve existing named hydrology and
raw TotalWatSed Q/QOFE diagnostic meanings; label those as internal/version-
sensitive diagnostics, not physical outlet runoff. Its sparse-day lateral zero
behavior is a documented legacy limitation, not a correctness oracle.

Ash models consume corrected physical WAT Q; calibration remains unchanged.
AshPost subtracts selected ash hills' H.pass runvol from its PASS-based watershed
Runoff before adding modeled ash replacement. Bind native IDs and dates exactly;
missing required PASS rows/files for selected ash hills and dates actually used
fail rather than falling back to WAT/QOFE. Never-used/empty model output retains
the existing successful no-data outcome without requiring PASS or provenance.
Preserve existing clipping after source correction. If any same-scope PASS
contribution is NULL/NaN/nonfinite, the correction is unavailable even if the
selected subset is finite: an unverifiable total cannot certify numeric subtraction.
Infinite input values fail. A missing baseline date, empty supplied baseline, or
nonpositive/nonfinite baseline area yields unavailable correction or explicit
reconciliation failure, never numeric zero.

Persisted Ash model and post artifacts require distinct numerical provenance.
Fresh model runs record physical-WAT algorithm identity and a source fingerprint
captured before the daily queries, never a later hash attached to an older frame.
The Ash parent batch memoizes one pre-read digest by source identity; each new
batch or standalone daily load computes a fresh digest. Metadata
checks detect ordinary drift. A metadata-signature collision retains the pre-read
digest; final post admission independently hashes current sources and requires
an exact match, including when metadata alone did not expose replacement;
fresh post runs require corrected model provenance whose WAT fingerprint matches
the current source. Post generation must reconcile the full same-scope daily PASS runvol sum to
the totalwatsed3 Runoff baseline used, failing on disagreement rather than
assuming that simultaneously present files share lineage. This numerical check
certifies the subtraction basis, not historical producer identity. Floating-point
comparison allows only accumulation roundoff (rtol 1e-10, atol 1e-8 m3).
Post provenance binds actual model artifact hashes, the
current WAT, PASS and totalwatsed3 hashes, the consumed native-to-feature
identity/area mapping, selected subtraction native IDs, and the post algorithm identity.
Changed dependencies make model/post results stale; unavailable dependencies
permit only historical/unverified reading with a warning, not fresh publication.
Old artifacts remain downloadable as historical/unverified with a visible warning;
never delete or relabel them as corrected automatically. Explicit model regeneration
is required before corrected postprocessing. A post-only version bump is insufficient.

Legacy raw R calc_watbal must explicitly reject MOFE inputs pending a separately
reviewed closure repair; preserve single-OFE behavior. Audit tools must label
QOFE normalization assumptions and distinguish intentional local transfer sums
from whole-hill export. Small residuals alone never establish physical closure.

## Cache compatibility and recovery

Advance native/report aggregation marker to `mofe-water-v2`. Require it in schema
and proof before publishing verified current summaries, independently of source
hash equality. Keep filenames, schemas and version-1 proof envelopes. Preserve
existing explicit historical_unverified warnings and native-unavailable
source-newer guard. A callable old/unmarked writer cannot publish a current cache.
Preserve atomic publication, permissions and previous bytes on failure.

Advance Features Export numerical version. Include any added topology/source
inputs in fingerprints; topology derived from full WAT remains covered by its
source fingerprint. Preserve archived bytes and normal archive/restore freshness
rules. No bulk deletion, model rerun or production deployment is implied.
Rollback pairs native/Python revisions and numerical markers.

## Regression obligations

Daily areas 250/750 produce P10/Q8/lateral4.5/ET5/Dp7 for the retained fixture.
Exercise unequal three-OFE serial routing, single OFE, mapped native hills,
missing terminal versus missing upstream, local nulls versus outlet nulls,
invalid/changing areas, joined sources, hidden Area, all temporal modes and
positive-WAT/zero-PASS days. Verify native serialized summaries, report HTML/CSV,
generated selected/base SQL, actual exports and corrected Ash input/output/post
artifacts. Test historical model/new post rejection and visible stale outputs.
Retain source/binary hashes, cold/warm/stale/failing/restored cache evidence and
runtime contour/width coverage limits. See ADR-0098 for preserved ET/Dp rationale.

## Roads modeled-area accounting amendment

Roads PASS construction and aggregate water reporting follow the
[modeled-area accounting contract](roads-water-accounting-contract.md). Complete MOFE contributor
areas replace the corresponding modeled baseline remainder, with explicit
modeled-area expansion when contributors exceed baseline area. Geographic
intersection is not required. Existing replacement precedence is preserved.
Canonical PASS is reconstructed before routing, selected exactly once in reports,
and paired with the same source-qualified water ledger.

A dedicated derived `H.accounting.wat.parquet` supports Roads average hillslope
water reports with canonical IDs and one equivalent reporting OFE after native
terminal selection. Raw H.wat and raw dashboard/export views retain their existing
semantics. TotalWatSed uses original weighted profiles directly, retaining its
Q/QOFE diagnostics and optional support-area weighting. Baseline behavior and
public report columns/units remain unchanged. Historical results without corrected
accounting provenance are not certified by this amendment.
