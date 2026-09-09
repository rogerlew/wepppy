# Independent correctness review

Reviewed 2026-09-09 by the independent correctness reviewer. Scope:
`integration.py`, `m1_inputs.py`, the integration tests, the frozen M1 contract,
ADR-0059, and the existing dNBR, RUSLE K and owned WBT producer contracts.
Implementation changes belong to the executing agent; this reviewer only
maintains this artifact.

Final disposition: all four medium findings are closed. No open medium/high
correctness findings remain within the trusted local integration scope.
The rebuilt final-assessment Wallow evidence also closes the authentic-source
and available-point-T acceptance gaps; see the final section below.

## Findings and disposition

### C01 — Medium: external dNBR masks failed at the helper boundary

The original `_f_predictor` in
`wepppy/nodb/mods/postfire_debris_flow/integration.py` passed the original
dNBR file directly to `summarize_dnbr`. The new contract admits hashed external
`.tif.msk` masks, while `dnbr._raster` rejects external companions. An admitted
source therefore raised `DnbrError` instead of producing the documented bundle.

Disposition: closed. Implementation now writes and verifies a self-contained
prepared dNBR copy before invoking the existing helper. The independent review
regression run passed the external-mask case with 24 observed basin cells and
the expected F value.

### C02 — Medium: K metadata presence did not establish the required contract

`integration._k_predictor` initially accepted `selected_modes: null` because
the selection check skipped null while the required-key check accepted it.
It also accepted malformed fragment metadata and omitted Nomograph texture,
structure and permeability mappings. Those cases could make S available without
the required scientific provenance.

Disposition: closed. Null selection, mapping identities and fragment object/status
validation were added during review. An independent `wctl run-python` probe
and two focused regression cases confirmed null selection/fragment now raise
`M1Error` with `provenance_mismatch`. Empty required dictionaries now leave S
unavailable with `missing_provenance`; fragment status must be a nonempty string.
The final independent four-case K regression run passed both empty-container
cases and repeated the null-field cases successfully.

### C03 — Medium: WBT support products were not reconciled with summary counts

`integration._tool_result` originally checked allowed support codes and the
domain mask, but did not reconcile support bits with `slope_valid`, `sbs_valid`
and `jointly_valid`, or check slope support against the support raster. A
readable but inconsistent product could be published as complete. Missing
`tool_version` also passed validation and later raised an unclassified
`KeyError` during manifest construction.

Independent reproduction used the actual binary and fixture inputs through
`wctl run-python`, built a complete bundle, changed every in-domain support
sample to zero while retaining the outside-basin mask, then invoked
`_tool_result` again. It returned `status: complete`. Probe artifacts were
retained in container `/tmp/m1-correctness-7606s95q`.

Disposition: closed. The validator now reconciles support bits, prepared SBS
class counts, finite slope support/range, areas, parameters, grid and version.
Four direct altered-product tests passed in the independent review run. The
adapter does not recompute threshold classification from output slope values.

### C04 — Medium: newly appearing raster companions escaped the final hash set

`integration._sources` initially enumerated raster companions only at startup.
`m1_inputs.read_raster` rediscovered and honored companions later, while the
final check rehashed only initially enumerated paths. A new external mask
appearing between those operations could change support without entering the
bundle's provenance or triggering `source_changed`.

Disposition: closed. Finalization now rediscovers and revalidates the source
and companion set and maps any change to `source_changed`. The independent
added-companion regression passed. Trusted immutable ownership remains the
documented admission condition; this is not a hostile-concurrency guarantee.

## Independent validation

The following container command passed **9 tests**, with 38 deselected, in
11.43 seconds. Existing dependency deprecations and the expected ungeoreferenced
external-mask warning were emitted; there were no failures.

```bash
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_integration.py -k 'null_k_provenance_rejected or inconsistent_wbt_products or external_mask_dnbr or added_external_mask_detected or collision_free_dem_sentinel' --maxfail=1
```

The sentinel regression confirms that a valid extreme Float64 sample survives
preparation while a separate finite sentinel represents missing samples. This
covers the GDAL approximate-NoData comparison issue discovered during execution.

After the final C02 change, the following command passed **4 tests**, with 45
deselected, in 10.34 seconds. Only the two existing dependency deprecations were
emitted. Two null-field cases overlap the earlier review run.

```bash
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_integration.py -k 'empty_k_provenance_unavailable or null_k_provenance_rejected' --maxfail=1
```

## Scientific assessment and remaining evidence

The implemented scientific choices agree with ADR-0059: customary-scale
Nomograph K uses multiplier 1, incomplete K preserves diagnostic support but
withholds S, valid zeros remain available, partial dNBR retains its independent
observed-support estimate, and unknown T does not erase F/S. The owned binary
computes Horn and intersection classification; Python does not substitute an
alternate terrain algorithm.

The preparation implementation verifies exact grids, valid samples and masks
after conversion. Palette SBS is decoded as indices. Explicit nearest
alignment is confined to SBS; K and dNBR grids must match exactly.

POLARIS equivalence to calibration STATSGO and automatic controller freshness
remain outside this evidence. The executing agent owns broader focused/full-suite
results and demonstrations; these remain separate from this focused review.

## Historical Wallow July 1 source review

The owner-supplied Wallow archive and `woolen-refusal` project close the previous
authentic co-located dNBR source gap. Independent container checks verified the
pinned archive hash, exact original-member hashes, unchanged copies of all nine
project inputs, and every source/prepared/product hash in the generated bundle.
The initial inspected bundle is under `artifacts/generated/wallow/bundle`.
[The reproduction](reproduce_wallow.py) now accepts completed processing with
partial scientific availability and retains the original source artifacts.
The historical [committed evidence](wallow_evidence.json) matches
`artifacts/generated/wallow-final/evidence.json` byte for byte; its predictors,
normalization, tool identity and all 23 recorded original project-source hashes
were independently checked against the generated products and source files.

At this earlier review, project `disturbed.nodb` named
`wallow_20110701_barc256_alb.img`. Its SHA-256
matches that archive member exactly:
`221eabc006ec73b7975650856cce6e78f506b294308d949f4bb4324c869b7dfa`.
The matching original July 1 dNBR member has SHA-256
`b763b0aee765a5367daa323850b01f08dab3805b1338ec4569ad539350c47001`.
Retained metadata is byte-identical to the archive; it identifies pre/post
imagery dates 2011-05-30/2011-07-01 and dNBR scale 1000. Normalization at 0.001
therefore agrees with the source declaration. The final June 23 severity
fixtures are a separate assessment and were not substituted into this project.

Independent reductions verified 12,973 full-domain cells and area 11.6757 km².
F = 0.6589354043877701 and S = 0.43397823632668575 both have full domain support.
All domain slopes are valid, while prepared SBS has 10,627 valid cells and
2,346 missing cells. The intersection raster contains 2,438 true, 10,386 false
and 149 unknown cells. Thus T was unavailable, with accepted bounds
0.1879287751483851–0.19941416788715025. The area warning is required. Explicit
storm examples must retain null probability while T is unavailable. All three
final 15/30/60-minute examples were verified to contain null probability,
`missing_predictors`, real-source labeling and the study-area warning. The
normalized basin dNBR range is approximately -0.401 to 1.099; negative observed
values are retained.

The original reproduction incorrectly asserted complete predictor availability;
review caught that assertion before an evidence report was emitted. It now
requires processing `status: complete`, preserving the scientifically correct
partial result. Authentic-source acceptance does not imply an available point T
or a real-project probability. The existing controlled complete-input examples
cover the scalar scenario path separately.

Independent read-only inspection also confirmed 12 saved Soils records with
nonempty corresponding `.sol` files. This establishes local artifact presence;
it does not add production freshness enforcement or runtime publication.

## Rebuilt Wallow final-assessment acceptance

After the owner rebuilt `woolen-refusal` with the final polygon severity TIFF,
the independent review verified complete authentic T/F/S availability in
`artifacts/generated/wallow-rebuilt-final/evidence.json`. The retained report is
[wallow_rebuilt_evidence.json](wallow_rebuilt_evidence.json). July 1 evidence
above describes the preceding project state and remains separate history.

The current project configuration names `wallow_finalsoilburnseverity.tif`.
Its SHA-256 is
`ed99c81b229cf4c241e055f97c8b068eb1b9def6c1cceb80b200fa54ae38ed3b`,
matching the polygon-rasterization manifest. All four original shapefile
component hashes were independently checked against the pinned archive. The
project's normalized SBS preserves the uploaded raster's grid and mask and
maps every valid source class exactly from 1–4 to 0–3.

The dNBR member is the matching `FinalSoilBurnSeverity/wallow_dnbr.img`, with
SHA-256 `f6494b9faba696ca7deef6765313e23556fe08af6086b4f73f8c323715f35194`.
Its source metadata matches the archive exactly and specifies pre/post imagery
dates 2011-05-30/2011-06-23 and scale 1000. The generated normalization manifest
retains those dates and scale factor 0.001. The July 1 dNBR was not reused.

Independent container reductions and source checks established:

- 12,973 full-domain cells, 11.6757 km²; slope, SBS, dNBR and K all have complete
  basin support. The intersection raster has 2,458 true, 10,515 false and zero
  unknown cells.
- T = 2458/12973 = 0.1894704386032529; F = 0.6141950971236625;
  S = 0.43397823632668575. Both continuous means match direct Float64 reductions
  of the saved raster samples. T equals both retained bounds.
- The explicit 10/20/30 mm accumulation examples over 15/30/60 minutes match the
  existing scalar engine: 0.9866102237667208, 0.998507412524049 and
  0.9866885015218513. All carry `area_outside_study_range` and real-source labels.
- All 24 recorded original-source hashes, every bundle source/prepared/product
  hash, and the actual executable hash match. Twelve saved Soils records and
  corresponding nonempty `.sol` artifacts are retained in the source evidence.

No runtime code changed for this acceptance rerun, and no new correctness
finding was identified. This closes the local real-project evidence gate;
it does not establish calibration equivalence, rainfall frequencies, production
freshness enforcement, or NoDb/UI/RQ publication.
