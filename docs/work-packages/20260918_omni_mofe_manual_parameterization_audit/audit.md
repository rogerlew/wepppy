# Read-only audit findings

Audit date: 2026-09-18. Source host: `wepp1`. Source run: `/geodata/wc1/runs/ve/ventilated-gag`. No production files were written and no scenario was rerun.

## Evidence captured

The parent `omni.nodb` records `canada-wbt-mofe.cfg` and these exact scenario definitions: `uniform_low`, `uniform_moderate`, `uniform_high`, `prescribed_fire`, `thinning` with `40%` canopy/`75%` ground, and `thinning` with `65%` canopy/`85%` ground. Each child contains 455 hillslope assignments and 1,065 MOFE segments. The derived summary is `omni/scenarios.out.parquet`; its copied SHA256 is `a5ba8f30b30f1915d0eb99c48632750416f2f144cbc932b2d57fb743504322a3`. Source NoDb hashes are in the generated comparison CSV.

The captured `landuse.nodb` states show the expected distinct fire management parameters: low key `406` (canopy 0.75, ground 0.85), moderate key `418` (0.60, 0.60), and high key `405` (0.40, 0.30). The manual implementation in `wepppy/nodb/core/landuse.py:2156-2236` validates the selected key, rewrites the selected hillslope and all of its OFE segments in MOFE mode, then rebuilds multiple-OFE inputs and cover defaults. Therefore the persistence layer does not collapse the three classes.

Important distinction: Omni also rebuilds a complete MOFE assignment structure, but its treatment scenarios are selective. `omni_mode_build_services.py` first selects hillslopes whose dominant class is eligible (forest for thinning/prescribed fire), and `Treatments.build_treatments()` resolves each OFE segment independently. An ineligible OFE keeps its existing management. Thus “1,065 MOFE segments captured” means the structure is complete, not that all 1,065 segments received the treatment.

## Watershed comparison

Values below are average annual output metrics from `scenarios.out.parquet`:

| Scenario | Sediment outlet (tonne/yr) | Water outlet (m3/yr) | Hillslope soil loss (tonne/yr) | Dominant management |
| --- | ---: | ---: | ---: | --- |
| uniform_low | 237.3 | 20,046,158 | 121.6 | 406, low fire |
| uniform_moderate | 237.3 | 20,046,158 | 121.6 | 418, moderate fire |
| uniform_high | 265.4 | 20,075,650 | 246.8 | 405, high fire |
| prescribed_fire | 288.1 | 20,137,835 | 931,367.6 | 410 on 21 hillslopes; 424 on 434 |
| thinning_40_75 | 281.8 | 20,156,975 | 931,358.2 | 424 on 455 |
| thinning_65_85 | 280.7 | 20,145,464 | 931,357.1 | 426 on 21; 424 on 434 |

The low/moderate pair is an exact equality across sediment, water, hillslope soil loss, channel soil loss, and sediment-delivery ratio. That is a zero-percent difference, but it is not an acceptable severity rank signal: two distinct fire parameterizations produce the same result and low/moderate/high are not strictly ordered. This is **investigate / do not silently waive**. The evidence points to a downstream generated-input or WEPP interpretation issue rather than a missing persisted management key; a follow-up should compare the generated `.mofe.man`/`.mofe.sol` content and WEPP input references for one common hillslope under all three children.

The high scenario is not within 20% of low/moderate for hillslope soil loss (246.8 versus 121.6; 103% higher), but the user asked for approximate consistency rather than byte precision. The important defect signal is the exact low/moderate equality and the resulting rank failure, not the fact that high severity is materially larger.

## Manual Modify Landuse parity

Manual Modify Landuse is a direct spatial assignment operation. It accepts a management key from the run's mapping catalog and applies it only to the selected Topaz IDs; in MOFE mode it updates every OFE segment for each selected hillslope. Omni uniform severity is a whole-watershed scenario generator, so it is not spatially paired with a manual edit unless the manual user selects the same 455 hillslopes and the same management key. The two workflows should therefore be compared by parameter mapping and direction, not by exact bytes.

The treatment parameter mappings themselves are coherent for the two thinning children: `424` is `thinning_40_75` (0.40 canopy, 0.75 ground), and `426` is `thinning_65_85` (0.65 canopy, 0.85 ground). The manual treatment catalog documents additional options (`40/93`, `40/90`, `40/85`, `65/75`, `65/90`, `65/93`) that are not present in this Omni configuration. This is an **accepted workflow-scope difference**, not an error; a like-for-like manual comparison must choose one of the two Omni options.

Prescribed fire is materially different from thinning in this run: only 21 hillslopes carry management `410` (`forest prescribed fire`), while 434 retain `424` (`thinning_40_75`). At the MOFE-segment level, the child retains 1,009 segments at management `90` and 13 at `200`; those are not prescribed-fire replacements. The Omni source contract says prescribed fire applies only to forest vegetation. This distribution is therefore **investigate** until the parent vegetation/management classification is confirmed: it may be correct filtering, but it can also indicate that the scenario cloned a previously treated landuse state. A manual run selecting the same 21 forest hillslopes is the appropriate parity test.

## Disposition and next action

No production remediation is authorized by this read-only package. Keep the low/moderate equality open as a likely parameterization/output defect. Before changing either workflow, run a controlled non-production reproduction that compares one hillslope's generated MOFE management and soil files, file references in the WEPP input, and the resulting interchange rows for low, moderate, and high. Separately verify why prescribed fire sees only 21 forest hillslopes in this parent state. If those checks show the generated inputs differ but WEPP outputs remain identical, escalate to the MOFE/WEPP execution path; if inputs are identical, fix the Omni scenario build parameterization. Manual Modify Landuse should not be altered unless the same controlled test proves its key-to-MOFE propagation diverges from Omni.
