# RUSLE source/proxy audit

## Disposition

Audit now; do not transplant the RUSLE auto estimator into Roads. The current
source contains a reproducible SoilGrids unit ambiguity in the C fallback, and
the preferred surface-fragment producer is absent from the inspected standard
SSURGO serialization path. Neither finding proves activation in the nine Roads
contrasts. No production code, parameters, or native histories were changed.

## Preferred source provenance

`wepppy/nodb/mods/rusle/c_integration.py:193` consumes four optional columns from
`soils/soils.parquet`: `cosurffrags_cover_pct`, `surface_rock_cover_pct`,
`surface_rock_cover_percent`, `sfragcov`. A current Python source search under
`wepppy` finds those names only in this consumer. The standard production chain
is `SoilSummary.as_dict` (`wepppy/soils/ssurgo/ssurgo.py:828`) to
`Soils._subs_summary_gen` (`wepppy/nodb/core/soils.py:2188`) to
`Soils.dump_soils_parquet` (`:2264`). The summary's explicit fields do not include
surface fragments, and the intervening builder adds substitution/provenance
fields, not surface cover. Thus that inspected standard chain does not supply
the advertised preferred proxy. An external/custom producer is not ruled out;
the search is not a claim about every historical run or separate repository.

The reader selects the first matching column even if it has no usable rows;
it does not try subsequent aliases in that circumstance. It weights available
rows by positive area, without reporting how much total run area lacks a value.
Those are concrete coverage/alias limitations, not demonstrated selected-case
failures. Missing surface-cover observations must not be equated with zero rock.

## Selected artifact support

The immutable accepted response declaration supplies 36 histories (all nine
contrasts, two lanes, two modes) and 18 distinct direct source-case folders.
For each history and corresponding source-case root, the reader checks the exact
four expected paths: soils parquet, both supported top-horizon cfvo rasters, and
a RUSLE manifest. None exists at those checked roots (72 checks of root scopes,
288 candidate-path existence checks; source-case roots repeat across modes).
All 18 source record hashes match the accepted declaration. These are native
experimental capsules, not full watershed run snapshots. Their absence does
not prove that a remote/original watershed never contained those inputs, and
there is no observed RUSLE auto execution to attribute to these Roads histories.
Do not fabricate a zero-rock or fallback-used observation from this inventory.

## Confirmed current-code units inconsistency

The C fallback (`c_integration.py:287`) divides raw cfvo by ten only when the
maximum finite value inside the footprint exceeds 100. It does not use the
source identity to determine units. The K reader (`k_integration.py:566,632`)
uses /10 for its recognized SoilGrids-backed sources. The existing SoilGrids
conversion contract in `wepppy/locales/earth/soils/isric/__init__.py:133` also
specifies /10 from cubic centimeters per cubic decimeter to volume percent.

The executable control compiles the actual function AST bodies, injecting only
the raster-loading/filesystem seams. For synthetic SoilGrids raw values [20,80],
C interprets a mean 50 percent proxy (0.5), while the independent unit reference
and K path give 5 volume percent (proxy 0.05). At raw 100 C returns proxy 1.0;
at 101 it returns about 0.101. This footprint-dependent scale discontinuity is
an actual current-code numerical defect for recognized per-mille inputs with
maximum <=100. It is not evidence of a bad Roads result or an end-to-end raster
failure; no selected cfvo raster was available in the capsule.

Changing C units needs a separately scoped correction with source-identified
units and real raster/manifest regression coverage. It must not silently change
the physical assumption that profile volume is used as surface area: those are
separate questions. No correction is implemented here.

## Aggregation and overlap

Both actual auto functions divide total-surface proxy by mean bare fraction and
clip to [0,1]. Controls verify zero bare returns zero, excessive proxy saturates
at one, and RAP/SBS arithmetic agrees for equivalent bare arrays. With proxy
0.2 and bare fractions [0.2,0.8], the shared control is 0.4 and implied local added
cover is [0.08,0.32]. This preserves the mean when unclipped, but redistributes
rock in proportion to bare and does not retain local rock/bare co-location.
A run-level average cannot identify road tread, fill, ditch, or buffer armor.
This is an estimator limitation, not necessarily a violation of its declared
run-scalar contract. Preserve its explicit prior/uncertainty labeling.

## Reproduction and limits

Run from the repository root with NumPy installed:

    python -B out/roads-parameterization-program-20261031/rock-cover-audit-r4/sources/audit_rusle_sources_v2.py --repo . --out /tmp/rock-source-review-UNUSED

The destination must not exist. Five unit controls and three normalization
controls pass. `readback-v2/source-audit.json` binds 27 input files by SHA256,
size and mtime and verifies unchanged readback. The script is source-free and
contains no native source. Version 1 is retained: its exact floating comparison
against decimal 0.101 failed due to representation; v2 uses a 1e-15 absolute
bound for that assertion. No production arithmetic changed. The original empty
v1 readback directory remains retained. No field cover, live soil query,
withheld material, or original raw sieve observation was substituted.
