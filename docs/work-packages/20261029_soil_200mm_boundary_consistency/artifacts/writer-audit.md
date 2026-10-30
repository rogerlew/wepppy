# Soil writer audit

Audit date: 2026-10-29. Scope is generated WEPP input-soil files, not source
catalog rewrites, model-output tables, or serialized controller state.

| Owner | Insertion / evidence |
| --- | --- |
| `wepppy/wepp/soils/utils/wepp_soil_util.py` | Ordinary `__str__` normalizes before `write` opens the destination. Disturbed converters retain their existing property overrides and split; final normalization is idempotent and rejects more than ten layers. |
| `wepppy/wepp/soils/utils/multi_ofe.py` | Normalizes every generated OFE; explicit keyword preserves uploaded topology. `nodb/core/soils.py` uses that keyword only for the uploaded-soil branch. |
| `wepppy/soils/ssurgo/ssurgo.py` | Both 7778 and 2006.2 builders, including canned urban/water profiles, normalize before file publication. Source horizon count is not mutated. |
| `wepppy/eu/soils/esdac/esdac.py` | Stages normalized text before opening output. Existing source replay fixture is retained; assertions check new boundary and copied properties. |
| `wepppy/locales/earth/soils/isric/__init__.py` | Stages normalized text before opening output; real builder tested with deterministic SoilGrids values. |
| `wepppy/locales/canada/bc/soils/sift/sift.py` | Mineral and water serializers normalize; caller now evaluates serialization before opening output. Boundary tests cover both forms. See legacy validity limitation below. |
| `wepppy/au/soils/soil_build.py` | Base/low/moderate/high output paths normalize. Corrected declared count from one to two original horizons, yielding three after insertion in the fixture. All three files read back in tests. See legacy validity limitation below. |
| `wepppy/nodb/mods/roads/roads.py` | All four direct soil assembly paths normalize. Existing 98.4 templates already terminate at 200 mm. Roads native matrix exercises those paths. |
| `wepppy/nodb/core/wepp.py` | Ordinary and MOFE preparation inherit utility serialization. Both channel writers now normalize `pw0.sol`; zero-channel files remain valid. Dedicated tests read both channel formats with zero/two profiles. |
| `wepppy/wepp/soils/utils/utils.py` | Deprecated specialization and kslast modifiers normalize before opening output, including the specialization copy branch. |
| Chile migration, soilsdb migration, ESDAC downstream, agricultural fields | Delegate to `WeppSoilUtil` or `SoilMultipleOfeSynth`; no additional writer implementation. |
| `wepppyo3/wepp_interchange/src/soil_anisotropy.rs` | Returns values in memory; Python owns input read/write. No new Rust input writer or API needed. |
| `wepppyo3/wepp_interchange/src/soil.rs`, `hill_soil.rs` | Serialize model outputs to Parquet. The test helper named `write_soil` writes model-output fixtures, not WEPP input `.sol` files. |
| `wepppyo3/wepp_viz` | Writes soil-loss rasters, not input soil profiles. |

## Intentional exclusions

Accepted uploads retain their explicit preservation path and source hashes.
Static source catalogs/templates and historical study fixtures are immutable;
normalization applies when constructing generated/prepared inputs. Fuzzing uses
the shared synthesizer. Test fixture construction is allowed to retain crossing
horizons to exercise normalization. BSON state dumps are not model input files.
There are no Rust soil-input serialization changes or native release rebuilds.

## Existing limitations found during audit

SIFT mineral headers lack the initial-saturation field expected in a 7778 header.
The Australian base 2006.2 header lacks the conductivity field supplied by its
burn-severity variants. These predate this change. Boundary tests verify emitted
counts, depths and identical copied material, but do not claim those legacy
headers now pass native input validation. Fixing their defaults requires a
separate parameterization decision; none is invented here.

Australian headers also declared one layer while emitting two. That count defect
was repaired because otherwise the normalizer cannot identify the horizon block.
Its remaining scientific formulas and historical thickness calculation are kept.

Anisotropy classification runs on supplied horizons before final serialization.
An inserted upper piece inherits the assigned ratio, even when its parent was
classified below 500 mm. The existing 500 mm rule is unchanged; this ordering is
explicit in the [anisotropy contract](../../../schemas/soil-anisotropy-contract.md).

Channel artifacts are structurally validated, not a new watershed scientific
benchmark. The retained native replay exercises ordinary hillslope preparation
with the Roads reproducer. No claim of field calibration or native invariance
for unnormalized uploaded inputs is made.
