# Roads modeled-area water accounting

**Status**: Accepted and implemented locally on 2026-10-22 after independent contract and implementation reviews. No production deployment.

## Authority and scope

Roger directed retaining modeled MOFE footprint areas and removing the proposed
geographic-overlap requirement. Geographic road unions, terrain-derived fill
placement and spatial ownership are not required. This is an area-conserving
mixture of existing modeled responses, not a measured geographic land partition.
The routing target remains the allocation unit. Do not claim physical geographic
overlap removal or changed residual-hillslope simulation.

The scope includes canonical Roads PASS construction before watershed routing,
water aggregation and affected aggregate reports. Baseline execution, existing
AgFields behavior, model executable physics and watershed connectivity are
unchanged. Roads totalwatsed is summed hillslope delivery, not routed outlet flow.

## Modeled area ledger

For each canonical routing target h, let A_h be its baseline modeled footprint
and C_h the sum of complete active contributor footprints (all native OFEs,
including road, fill and buffer). Retain each contributor's complete modeled
area. For a point-source target, assign baseline remainder B_h = max(A_h-C_h, 0)
and modeled target area T_h = B_h+C_h. When C_h exceeds A_h, retain all contributor
area, omit the exhausted baseline response and explicitly record expansion
T_h-A_h. Never scale roads down to fit or silently report a negative remainder.
This bounded modeled-domain expansion is not a test of geographic exterior area.

For existing outslope-unrutted replacement, use its existing strip and remainder
profiles and exclude baseline; T_h is their summed source modeled area, including
all remainder profiles. Retain full source areas and record T_h-A_h as serialized
replacement reconciliation, rather than rescaling responses to force equality.
The existing replacement construction's area-closure gate remains required;
report aggregation does not invent an additional arbitrary tolerance. Replacement
supersedes additive contributors for the same target, preserving existing routing
precedence. Untouched targets retain baseline representation.

Record original source identity, target ID, native OFE topology, modeled area,
represented area, weight, role, policy version and source hashes. WAT and PASS
must use the same represented-area ledger. A source's response weight is its
represented area divided by its own serialized modeled area. For continuous runs, footprint authority is the sum of stationary local OFE
areas in each source WAT. This preserves baseline report area and retains the
full road MOFE water footprint. PASS scaling uses represented area divided by
that source's serialized PASS-header area; record both areas and that scale.
For single-storm runs lacking WAT, use native parsed PASS-header areas. Never
mix area bases within one ledger. No geographic ownership inference is performed.

A zero-contributor continuous run uses baseline WAT and unchanged canonical
baseline PASS and must reproduce baseline named water quantities within floating
summation precision. Unchanged targets retain original PASS bytes. Source WAT
geometry must be stationary; no guessed area or arbitrary closure tolerance.
Native weighted PASS's existing serialization error budgets apply to its own
readback. Differences between independently serialized WAT/PASS areas are
recorded and reconciled by the declared scale, not mistaken for physical changes.

## Composition and native water reduction

Canonical PASS comprises each target once. Reconstruct it from original baseline
and contributor PASS, never from already-weighted combined files. Use the native
weighted combiner with an explicit Roads strategy. Scale extensive water,
sediment and hydrograph quantities and recompute derived quantities as the
existing native combiner does. Set its header to target represented area and
reparse output to verify composition. The Roads strategy preserves existing
Roads first-source particle-header semantics while combining class-wise sediment
masses; differing baseline/road particle diameters remain admitted. AgFields
retains its existing strict header validation. Standalone contributor PASS is diagnostic
and must not be added again to totalwatsed.

Water reductions retain source-qualified native identity until outlet selection.
Local WAT fluxes/stocks use local area-weighted volumes and ledger weights.
Physical Q uses each profile's terminal Q over its full profile area; lateral
uses terminal latqcc over terminal local OFE area. Sum each native outlet once.
Multiple profiles assigned to a target must not be merged before terminal
selection. Preserve raw source WAT. A dedicated `H.accounting.wat.parquet` may represent
each canonical target as one equivalent reporting OFE after native reduction,
with physical Q and lateral depths and target represented area. It must be marked
as derived accounting data and used by the average hillslope report; it is not
raw WEPP output. Raw H.wat, dashboard and export semantics remain unchanged.

Totalwatsed MUST aggregate the ledger's original source profiles directly, not
reinterpret the equivalent report WAT as raw native profiles. Its literal Q and
QOFE diagnostics retain the existing all-OFE volume reductions, weighted by the
ledger. Optional soil/element diagnostics preserve per-source native joins and
valid support-area denominators before target aggregation; missing optional
sources retain existing null/absence behavior. This prevents equivalent-profile
collapse from changing TotalWatSed diagnostics or optional-resource weights.

Total report Area = sum(T_h), including explicit expansions. Runoff retains
canonical PASS volume / represented area * 1000. Groundwater recurrence and saved
coefficients stay unchanged, with percolation from the same weighted WAT basis.
Streamflow remains Runoff + Lateral Flow + Baseflow. All complete road-profile
local terms participate, not just road-surface runoff. Fixed-baseline-area and
boundary-injection drafts are superseded.

## Integration and compatibility

Use translator canonical IDs and completed execution-manifest roles, not numeric
ID cutoffs. Native source identities must not collide silently. Persist the ledger
before PASS reconstruction and run watershed routing with those rebuilt files.
Historical unweighted combined PASS cannot be certified through report-only
regeneration. Retained baseline Parquet is supported after raw WAT cleanup.

Totalwatsed and average annual hillslope accounting must share the ledger.
Preserve raw contributor diagnostics and explicitly distinguish downstream raw
views from corrected aggregate views. Preserve column names/units and the distinct Q meanings above. No Python numerical fallback.

A valid zero-contributor manifest uses baseline-equivalent accounting. Absent or
malformed metadata is not empty. Missing required IDs, dates, terminals, duplicate native rows, invalid outlet
fluxes or nonpositive/nonfinite modeled areas fail explicitly before
publishing ready outputs. Zero baseline remainder is valid. Skipped/failed
contributors do not participate. A failed segment execution still fails the
whole run under existing orchestration; this rule does not authorize partial
success. Only intentional skips may yield a successful reduced contributor set.
Local optional NULL/NaN behavior follows the existing aggregation contract;
strict outlet validation must not silently turn unavailable terminal water into
zero. Single-storm runs retain their existing report
availability and use modeled PASS geometry for applicable area composition.

Writes remain roads-scoped; preserve baseline bytes. Validate output aliasing and
publication failure behavior. Record policy and input provenance so old unmarked
outputs cannot be mistaken for corrected accounting. Optional diagnostic joins
remain source-qualified and must never attach baseline soil to a different native
replacement profile.

## Validation and rationale

UM1 demonstrated missing baseline WAT, a road-only denominator and duplicate
PASS contributions. Its modeled-area partition must be reconstructed, routed,
and read through daily/yearly reports on an isolated copy. Cover multiple OFEs,
replacement remainders, mixed precedence, zero/full occupancy, expansion,
missing/empty/legacy/malformed inputs, and source isolation. Preserve non-Roads
numerical behavior and AgFields strategy tests.

The modeled-area rule avoids inventing unrecorded fill/buffer placement and
retains all MOFE footprint areas as requested. Spatial footprint audit results
are diagnostic history, not allocation inputs. Review and ADR must retain the
response-mixing assumption and modeled-domain versus geographic-domain distinction.

See [output scope](output-scope-contract.md),
[hillslope water aggregation](hillslope-water-aggregation-contract.md), and
[Roads specification](../../wepppy/nodb/mods/roads/specification.md).

## Optional sources and cache readiness

Optional sources absent or present-empty preserve current native absence/null
semantics. Partial SOIL/ELEMENT observations contribute only their existing valid
support areas, with source-qualified native joins before reduction. Malformed
present schemas fail explicitly. Optional WAT profile stocks preserve the
existing native column-specific null rules; the area repair does not redesign
storage semantics or convert missing data to physical zero.

A corrected ready-report record requires a versioned ledger, source hashes,
canonical PASS provenance, totalwatsed policy marker, and marked
`H.accounting.wat.parquet` for continuous average-hillslope reporting. Equivalent
rows use canonical target wepp_id, ofe_id/OFE=1, normal date keys, represented
Area and the existing WAT water columns. Source-profile identity remains in the
ledger and raw WAT archives. Totalwatsed reads original weighted profiles directly.

A completed historical report without this marker remains a historical result;
file presence alone does not upgrade it. Corrected report selection validates the
ledger and derived marker, then uses the accounting WAT hash in the existing
cache provenance. Never reuse a raw-backed or old-accounting cache merely because
timestamps match. Missing/mismatched corrected artifacts fail regeneration/readiness
rather than falling back to historical raw water. Baseline/raw diagnostics remain
explicitly separate, with no auth or endpoint-selection changes.
