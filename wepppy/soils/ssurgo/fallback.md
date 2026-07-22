# SSURGO Fallback Specification

**Status:** Approved production policy; implementation pending
**Authority:** [ADR-0025](../../../docs/adrs/ADR-0025-ssurgo-local-vector-profile-fallback.md)
**Scope:** Gridded SSURGO `Soils._build_gridded()` assignments

## Policy Order

The fallback is an ordered, per-affected-hillslope policy:

1. **Recover the source MUKEY.** Run the ordinary SSURGO conversion path and
   retain the raster-selected MUKEY whenever it produces a valid `WeppSoil`.
2. **Match a local profile.** If the source remains residual-invalid but has
   direct shallow-profile evidence, select a buildable local donor by the
   vector rule below.
3. **Use the global donor.** If either earlier stage cannot produce an
   assignment, use the current watershed-global valid MUKEY.
4. **Use STATSGO only if SSURGO has no valid soil.** This existing outer
   fallback is unchanged.

Stage 1 is the existing source recovery/conversion behavior: documented
defaults, authorized Rosetta estimates, water-content sanitization,
restrictive-layer handling, and validation. This policy does not invent a new
synthetic-soil or source-data imputation rule.

Candidate discovery depends on the source raster location, not on watershed or
hillslope topology. A hillslope contributes only its raw dominant MUKEY and
source longitude/latitude; two geographically separate occurrences of the
same MUKEY can therefore receive different local donors.

## Conditional Candidate Preparation

Candidate preparation occurs only after the primary project SSURGO build has
identified one or more hillslopes whose raw dominant MUKEY remains
residual-invalid. If there are none, do not retrieve a padded map, enumerate
added MUKEYs, or create a candidate collection.

For an affected run:

1. Read the canonical full 2025 gNATSGO MUKEY VRT at
   `$GEODATA_DIR/ssurgo/gNATSGSO/2025/.vrt`.
2. Crop the project SSURGO extent expanded by **2,000 m** on every side in the
   source raster CRS. Persist this categorical candidate raster with the run,
   including source identity, bounds, CRS, and checksum.
3. Enumerate positive MUKEYs in the padded raster. Reuse the primary build
   outcome for MUKEYs already in the project map and build every added MUKEY
   with the same SSURGO source version, converter settings, defaults, and
   initial saturation. Together, these outcomes cover every padded MUKEY.
4. Keep the candidate collection separate from primary project soils. A
   MUKEY is eligible when it has a valid outcome in the current build: its
   primary-collection outcome when it is in the project map, otherwise its
   added-candidate outcome. Collection origin must not exclude a MUKEY.
   Materialize only selected **added** donors into the final run soil set;
   selected primary donors are already materialized by the primary build.

The persisted padded map is the only selection raster. Do not query the
national VRT or unpadded project map during donor selection. Missing, corrupt,
or provenance-mismatched raster or candidate-build evidence skips stage 2 for
that record and enters stage 3. The global donor is calculated solely from
valid primary-collection MUKEYs; candidate outcomes never change that baseline.

## Local Candidate Set

For each residual-invalid source location, query the persisted candidate raster
using WGS84 longitude/latitude with radii **250 m**, **500 m**, **1,000 m**,
then **2,000 m**. Exclude all residual-invalid MUKEYs. The first radius with
at least one buildable donor is the *smallest successful spatial window*.

Only donors in that one window are ranked. Do not expand to a larger radius to
find a closer profile, and do not use elevation, terrain, watershed frequency,
or hillslope topology in the v1 score. Adjacent source locations may share
one crop/read for performance, provided their individual results are identical
to an independent bounded query.

## Shallow-Profile Vector Match

For source and candidate, inspect raw SSURGO horizons in stored order and use
the first horizon for which `om_r` is finite and in `[0, 20]` percent and at
least three vector fields are valid. Only directly observed SSURGO values are
eligible; do not score defaults, Rosetta estimates, derived WEPP values, or
inferred rock content.

| Field | Accepted range | Units |
| --- | --- | --- |
| `dbthirdbar_r` | `[0.5, 3.0]` | g/cm³ |
| `ksat_r` | `[0, 100000]` | µm/s |
| `cec7_r` | `[0, 200]` | meq/100 g |
| `hzdepb_r` | `(0, 1000]` | cm |
| `fraggt10_r` | `[0, 100]` | percent |
| `frag3to10_r` | `[0, 100]` | percent |
| `sandtotal_r` | `[0, 100]` | percent |
| `claytotal_r` | `[0, 100]` | percent |

When both texture fields participate, require
`sandtotal_r + claytotal_r <= 100`. A source and candidate are comparable only
when they share at least three valid fields. For shared fields `F`:

```text
scale_f = max(0.05 * abs(source_f), 0.05 * abs(candidate_f), 1e-6)
distance = mean(abs(source_f - candidate_f) / scale_f for f in F)
```

Choose the donor with the lowest distance. Exact ties break by greater
categorical pixel support in the successful window, then ascending numeric
MUKEY. If the source is profile-free/unusable or no local donor is comparable,
stage 3 is mandatory.

## Global Fallback and Provenance

The global donor is calculated exactly as it is today: the most common valid
primary-collection MUKEY in the watershed. It remains the final SSURGO
continuity path, including candidate-raster failure, candidate-build failure,
profile-free evidence, insufficient common vector fields, and donor
materialization failure.

`raw_ssurgo_domsoil_d`, `domsoil_d`, `ssurgo_domsoil_d`, and the existing keys
in `ssurgo_substitution_d` retain their current meanings. Each substitution
adds the following evidence without removing old keys:

| Field | Meaning |
| --- | --- |
| `selection_policy` | `ssurgo_local_vector_profile_v1` or `watershed_global` |
| `global_mukey` | Global comparator and last-resort donor |
| `source_location_wgs84` | `[longitude, latitude]` used for local support |
| `candidate_raster` | Persisted padded-raster identity and checksum |
| `search_radius_m` | Successful radius, or `null` |
| `candidate_support` | Ordered buildable local donors and pixel support |
| `source_profile` | Source horizon identity and direct accepted values |
| `selected_profile` | Donor horizon, shared fields, scales, and distance |
| `fallback_reason` | Explicit disposition/failure reason |

`soils/soils.parquet` receives nullable additive representations of the same
evidence. The source location, candidate raster, support, and profile fields
are JSON values in NoDb and nullable JSON-encoded strings in Parquet; scalar
policy, MUKEY, radius, and reason fields retain their scalar types. Legacy NoDb
instances hydrate absent additive fields to null/empty values, and existing
consumers of the original substitution keys remain compatible. A successful
stage-1 source recovery keeps the raw MUKEY and needs no substitution record;
its ordinary build diagnostics remain the recovery evidence.

## Failure, Rollback, and Verification

No fallback stage may select an unbuilt donor or silently replace the specified
algorithm. Candidate preparation uses a configured canonical source resolver:
the resolved regular, readable source must be inside the approved gNATSGO 2025
root and no request, NoDb value, or caller-supplied path may select it. A source
mount symlink is permitted only when its resolved file remains inside that
root; candidate output symlinks are never permitted. The fixed active artifact
is `soils/ssurgo_candidate_mukey/active.json`. It names immutable, same-directory
versioned GeoTIFF and metadata siblings below that directory. Reject path
traversal and symlink escapes, write each sibling to a same-directory temporary
file, fsync, atomically replace it, then checksum and validate both before
atomically replacing the active manifest. A failed publication therefore leaves
the preceding active pair untouched. A source identity/version, bounds, CRS, or
checksum mismatch makes the candidate unavailable and uses stage 3; never reuse
a stale crop.
All candidate preparation, replacement, candidate construction,
materialization, and persistence occur under the existing soils lock. A missing
native categorical-support dependency is an explicit build error. An operator
rollback disables stage 2, leaving stage 1 recovery and stage 3
watershed-global substitution intact.

Required verification includes deterministic stage-order, radius, vector,
texture-balance, tie, and unavailable-candidate tests; primary and added donor
eligibility; legacy NoDb/Parquet hydration; and a hermetic run that proves only
selected added donors are materialized and all final assignment artifacts
agree. Failure injection must prove a donor-materialization failure leaves no
partial `.sol` or dangling final mapping/provenance and returns stage 3, while
a clean retry produces one coherent candidate checksum/provenance set.
