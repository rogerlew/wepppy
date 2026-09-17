# C02/C07 remaining closure: bounded QA assessment

Reviewer: `freshness_qa`, 2026-09-17. Read-only source and retained-evidence review;
no new runtime reproduction, production change or broader acceptance claim.

**Later C02 evidence:** the requested shipped mixed-profile runtime has now
passed after the coordinated restart. See
[runtime QA acceptance](runtime_features_dtale_qa_acceptance.md): real CSV/GPKG
exports, selected GeoJSON/Parquet/NoDb/Unitizer inputs, touch/equal-byte hits,
changed rows/geometry/units against fresh native controls, and complete named
source verification. The minimum C02 experiment proposed below is therefore
complete. Arbitrary indirect/native closure and the C07 ordinary-workflow
question remain separate; the original discovery rationale is retained below.

## C02 Features export

The verified main-file and publication correction remains accepted at its stated
scope. `features_implementation_correctness_review.md` records199 affected tests,
native GeoPackage/OpenFileGDB output checks, source-change rejection, preserved
prior bindings and failed native work. The new freshness test uses an explicitly
substituted one-layer catalog with a real GeoJSON carrier and Parquet attributes.
It is strong evidence for those paths, not a full shipped-profile closure proof.

The actual shipped read path narrows the remaining question:

- `layer_catalog.yaml` resolves carrier geometry through
  `nodb:watershed.subwta_shp` / `channels_shp`. Despite their names, the actual
  `Watershed` properties return JSON/GeoJSON for TOPAZ, WBT and TauDEM.
- `geometry_carriers._load_vector_dataframe`, the legacy loader in `service.py`
  and `discovery._load_vector_attributes_dataframe` materialize archived paths
  then call real GeoPandas/GDAL readers. `discovery` loads Parquet attributes with
  pandas and separately reads their schema for unit metadata. DuckDB joins the
  resulting dataframes; that join does not independently discover raster inputs.
- `dependency_tracker` hashes selected regular catalog files, plus the declared
  controller/manifest and project-unit dependencies. Directories retain their
  previous metadata identity. This is no recursive dataset proof. Neither the
  `.shp` property names nor a directory-backed FileGDB **output** establishes an
  actual shapefile/FileGDB **input** in a maintained profile.

Minimum next evidence is one retained export using the real shipped catalog and
profile on a unique copied project, with real detached NoDb hydration and project
units. Record every selected locator, materialized path, file kind, units source
and actual native-read path. Assert exported values/geometries against a forced
fresh output after a Parquet change, carrier-geometry change and real Unitizer
preference change; preserve same-byte rewrite/touch cache-hit controls and the
existing rejected-publication/prior-artifact guarantees. Include archive-backed
materialization if that copied project uses it. This closes a concrete mixed
GeoJSON/Parquet/NoDb/units workflow without inventing a raster reader.

Only then classify indirect cases. A maintained locator that actually accepts a
multifile native dataset needs an actual companion-only change demonstrating its
effect on the exported output, then a bounded authority/compatibility checkpoint.
A type not reachable from the maintained catalog can be documented as outside
that catalog's dependency set; generic reader capability alone is insufficient
evidence of a supported-path defect. Do not silently restrict readers to make
the audit pass. Arbitrary change-and-restore entirely during materialization
remains explicitly unproven under the accepted initial/final observation contract.
The safe present disposition is **main-file correction verified; complete native
and cross-input closure unresolved**, with those exact evidence limits.

## C07 Omni stream-order pruning

`omni_pruning_native_probe.py/.json` proves an actual numerical stale-reuse
mechanism: with the completion receipt deliberately fixed, changed network bytes
leave `needs_prune=false` and retain5 stream cells; actual native recomputation
retains1. It does not establish an ordinary writer omitting completion. The
temporary raster directory is gone; the script/log/numerical result survive.

The production read set is concrete. `OmniContrastBuildService` selects
flovec/netful/relief/chnjnt/bound/subwta plus `outlet.geojson`, using the existing
TIF/VRT resolver. Pruning consumes flovec/netful; subsequent Strahler/junction/
hillslope work consumes the selected sources and generated pruned maps. Final
group assignment intersects source subwta with generated pruned subwta. Reduction
passes, source selection and the completion receipt also affect reuse.

Ordinary sequencing is not disproven by the retained probe:

- `WatershedOperationsMixin.build_channels` removes subwta; Omni's required-source
  validation rejects its absence before reuse.
- `build_subcatchments` removes the completion timestamp before native work and
  stamps successful completion; older cached products then become stale.
- `symlink_channels_map` changes linked/VRT channel sources and only stamps
  build-channels. The actual callers found are CulvertsRunner creation/repair.
  A supported ordinary Omni regeneration sequence through that path is not yet
  demonstrated. Shared backing changes, restoration and incomplete generation
  remain separate questions. An absent completion receipt currently makes
  `_is_stale` false for existing products.

Minimum next evidence is a disposable actual watershed/Omni sequence with real
completion state: establish cached pruning, run the ordinary producer and compare
the subsequent complete consumer with a forced native result. Retain receipt
values, selected read set and numerical maps/group assignments. Include the
missing-receipt/incomplete-producer case so readiness cannot be confused with
freshness. If claiming shared/VRT or restore support, first trace its maintained
entry point, then perform exactly that workflow; another manually held receipt
does not add the missing evidence.

If that sequence is unavailable within this bounded execution, the package's
allowed **justified unresolved** disposition must state the confirmed native
mechanism and the unverified ordinary workflow separately. Preserve completion
receipts as orchestration authority; replacing them with hashes is not justified.
Any future correction needs a separate source-proof and publication contract for
the actual selected native set, with representative cost and partial-output
behavior measured. There is presently no measured C07 whole-consumer budget or
authority basis for introducing that contract as a routine helper reuse.

These recommendations do not mark either complete closure or the work package
done. The governing allowance is `package.md`, Complexity budget: every inventory
entry must be fixed, verified-safe, a nondependency, or explicitly justified
unresolved; omission is not a disposition.
