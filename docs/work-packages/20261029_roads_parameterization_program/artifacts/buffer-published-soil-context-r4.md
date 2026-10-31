# Published SOIL context for the frozen buffer observations

This post hoc readback uses the nine already selected legacy/conditioned-generated
pairs. It does not change seed selection, execute WEPP, or establish causality.
The modern lane is the U12 `erosion_road_cap` candidate, not unmodified SSURGO soil.

All 18 full-period SOIL outputs were freshly converted using the canonical Rust
reader: 315,576 rows, complete calendar coverage and unique day/OFE keys. Source
records and SOIL files were hashed before and after conversion. The
[receipt](buffer-published-soil-context-r4.json) binds the executed script,
actual native library, Python facade/wrapper, frozen seeds and results.

Legacy buffer roughness is 100 mm throughout all nine histories. Six generated
buffer histories start at 17.34–22.95 mm and decline to 6 mm: the three selected
small-reference misses, the passing control with the same event signature, the
small-reference passing control, and the meaningful overprediction. All three
selected underprediction histories retain 100 mm in both lanes.

The source-observation study must determine whether the SOIL consolidation branch
and IRS depression-storage calculation explain the different hydrology. The
association alone does not identify a defect, justify a roughness override, or
show that a change would preserve passing controls. These nine selected cases
are not a population estimate. Printed SOIL values retain their published
precision; this readback does not reconstruct hidden state or interpret TSW as
whole-profile storage.

[Independent review](buffer-published-soil-context-r4-independent-review.md)
recomputed all summaries and checked the callable/library identity, original
artifacts, logical tables and calendar coverage. The
[retention receipt](revision4-buffer-published-soil-context-retention.json)
verifies all 65 archive members, including superseded attempts.

## Reproduction and retained attempts

From the WEPPpy repository, with the frozen source runs available:

```sh
.venv/bin/python docs/work-packages/20261029_roads_parameterization_program/artifacts/read_buffer_soil_context_r4.py \
  --seeds docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-process-observation-r4/seeds.json \
  --output /workdir/wepppy/out/roads-parameterization-program-20261031/buffer-published-soil-context-r4-replay
```

The destination must not exist. Conversion writes only to that destination.
Native outputs remain read-only. Raw evidence roots are
`buffer-published-soil-context-r4`, `buffer-published-soil-context-r4-v2` and
`buffer-published-soil-context-r4-v3` under the dated output directory above.

The first two attempts bound Python module identities without binding the native
library itself. Their exact executed scripts and superseded summaries remain
retained; v3 additionally resolves the converter callable's native module and
hashes it before and after conversion. All 18 logical Arrow tables and result
fields other than Parquet byte hashes agree across successive attempts. An
overly strict v2 comparison that included regenerated Parquet hashes failed and
remains recorded; metadata-dependent file bytes are not a logical-data comparison.
