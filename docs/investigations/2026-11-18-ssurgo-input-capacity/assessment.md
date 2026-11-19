# National SSURGO native input-capacity requirement

Date: 2026-11-18 Pacific. Status: inventory complete; recommendation only.
The operator requested the necessary capacity from the full database in
`/workdir/soil-data-access`. No production parameter or binary was changed.

## Finding and recommendation

**21 input horizons is the minimum required by the current WEPPpy SSURGO writer
for the national October 2026 release. Recommend a native input capacity of 23**
to accommodate the observed maximum 22 source horizons plus a 200 mm split,
without depending on current horizon-validity exclusions to reduce the count.
Keep calculation capacity `mxnsl=10`. Eleven was sufficient only for the original
incident, not national coverage. This inventory does not validate a larger native
binary: the completed native evaluation tested eleven.

| Measure | National result |
| --- | ---: |
| Components in source | 1,204,944 |
| Components with horizon records | 953,134 |
| Horizon records scanned | 3,855,789 |
| Maximum raw horizons per component | 22 |
| Upper bound after necessary current validity conditions | 20 |
| Actual maximum emitted after the 200 mm split | 21 |
| Raw-source-preserving capacity including one split | 23 |

The seven 22-horizon components are Puaulu in survey HI701, Hawaii Volcanoes
National Park, Hawaii. Each contains two zero-clay horizons (`Cd1`, `Cd2`),
which fail the current positive-clay validity test. Numeric zero is not replaced
by a missing-data default. The other twenty horizons remain; no restrictive
conductivity cutoff removes them. Their 80–220 mm horizon crosses 200 mm,
requiring one copied record. The final depth is 1400 mm, so these are not merely
extra deep horizons below the existing native 1800 mm clamp.

Five map units select Puaulu and actually serialize 21 horizons:
`2371321`, `2371376`, `2371879`, `2372202`, `2372203`.
Two other map units containing Puaulu, `2371377` and `2372204`, select a higher
percentage component and serialize nine. The source maximum must be counted per
component, not by summing components within a map unit.

## Proof and scope

The inventory scans every `chorizon` record. A second whole-table query applies
necessary conditions from `Horizon.valid()` with the standard missing-value
defaults: nonorganic designation, a bottom depth, and positive sand, clay and CEC.
It intentionally omits hydraulic estimation and restrictive truncation, so its
maximum of twenty is an upper bound on successful current-writer output before
normalization, not a count of successful national builds. The writer cannot add
horizons before normalization; normalization adds at most one per OFE. Thus no
current generated SSURGO profile can exceed 21 for this release.

The real `SurgoCollectionWorkerViewFactory` and `WeppSoil` then build all seven
map units containing maximum-count components, with source `muaggatt` fields
joined as in the SDA component query. Five achieve that upper bound. Actual
serialized files and canonical boundary insertion establish the lower bound of
21, making the minimum exact without running Rosetta for every national horizon.
The witness validates normalization idempotence and a single 200 mm boundary.

Only the ten-horizon rejection comparisons in a process-local copy of the
canonical normalizer are lifted for this diagnostic. The normalizer source,
production writer, databases and native binaries are untouched. The generated
witness is an evaluation artifact and is not suitable for historical binaries.
The relevant writer/factory classes in the task checkout and shared checkout
were AST-identical; source identities are retained in `report.json`.

## Source and reproduction

Source, opened with SQLite `mode=ro` and `PRAGMA query_only=ON`:

`/workdir/soil-data-access/data/national/extracted/All_SSURGO_10_01_2026.gpkg`

Size: 117,836,186,624 bytes. Source size and modification time remained unchanged.
Existing importer metadata identifies the national 2026-10-01 release and records
GeoPackage SHA-256 `b971fea0a1a40cad85a28b24b33eaeef1a850723cb993a2260a7f37548df11a2`.
This inventory did not rehash the entire 118 GB source. Metadata is retained at
`/workdir/soil-data-access/artifacts/national/metadata.json`.

From the task worktree, use a fresh output directory:

```bash
PYTHONPATH=/workdir/wepppy-native-soil-capacity /workdir/wepppy/.venv/bin/python \
  docs/investigations/2026-11-18-ssurgo-input-capacity/inventory.py \
  --database /workdir/soil-data-access/data/national/extracted/All_SSURGO_10_01_2026.gpkg \
  --output /workdir/native-soil-capacity-evidence/national-inventory-repeat
```

See [inventory results](report.json), [executable inventory](inventory.py), and
[21-horizon serialized witness](2372202-normalized.sol). Complete local witnesses
are retained in `/workdir/native-soil-capacity-evidence/national-inventory/`.
The serialized witness retains writer-emitted comment whitespace verbatim;
whitespace-check findings in that artifact are intentional.

## Follow-up acceptance

The recommendation is source-specific, not a promise about future SSURGO releases,
STATSGO2, or arbitrary uploaded profiles. Retain explicit excess-count rejection.
Before adopting 23, extend the native tests to 21/22/23 input records, rejection
at 24, mixed-count OFEs, and the actual Puaulu profile. Repeat old-input parity
and paired hillslope/channel execution. Document the selected capacity and
executable compatibility in the production ADR/soil contract before integration.
No horizon-merging or validity-rule change is part of this recommendation.
