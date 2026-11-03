# Retention trial: source-supported initialization layer map

**Verdict: no mapping blocker for the four prepared cases under the bound inputs and selected source.** The [machine-readable map](resumption-r7-retention-initial-layer-map.json) establishes the expected initialization tag/OFE/layer inventory and source-derived depth intervals. It does not establish an observed coefficient response or authorize execution. No model call, native build, production edit, or retained-artifact modification was made.

## Expected inventory and changed input support

Every case has three OFEs, ordered **1 road, 2 fill, 3 buffer**. Both policies have identical layer geometry. Require exactly one `WBH_HK_FCUL` and one `WBH_HK_RATIO` row for each `(e, c=0, s)` below, with no missing, duplicate, or unexplained owner/index keys.

| Case | Serialized bottom | Native initialization bottom | Internal indices per OFE | Selected rows per observed arm | Indices receiving changed FC/WP input support |
|---|---:|---:|---|---:|---|
| B2 | 1600 mm | 1800 mm | 1–10 | 60 | 6–10 |
| B3 | 1600 mm | 1800 mm | 1–10 | 60 | 6–10 |
| B4 | 400 mm | 600 mm | 1–4 | 24 | 1–4 |
| B5 | 1600 mm | 1800 mm | 1–10 | 60 | 1–8 |

The same column applies to all three OFEs. Across four cases and two observed policy arms, the expected inventory is **408 selected rows**, representing 204 FCUL/RATIO pairs. The eight ordinary runs are separately required by the frozen parity protocol; this inventory applies only to the eight observer replicas.

| Internal index `s` | Source-derived initialization depth interval |
|---:|---|
| 1 | 0–100 mm |
| 2 | 100–200 mm |
| 3 | 200–400 mm |
| 4 | 400–600 mm |
| 5 | 600–800 mm |
| 6 | 800–1000 mm |
| 7 | 1000–1200 mm |
| 8 | 1200–1400 mm |
| 9 | 1400–1600 mm |
| 10 | 1600–1800 mm |

B4 stops at index 4. Its 400–600 mm interval, and index 10 in the longer profiles, are native-added support beyond the serialized profile bottom. These intervals are not additional measured soil horizons or evidence of actual physical profile depth.

For B2/B3, only serialized horizon 8, **990–1600 mm**, changes: FC/WP tokens `0.1851/0.0823` become `0.1751/0.0778`. The native reader extends that last horizon to 1800 mm. Consequently index 6 receives 10 mm of changed support, **5% of its 200 mm property average**; indices 7–10 receive 100% changed support. Indices 1–5 provide unchanged-input comparisons. The primary deeper witness should include indices 7–9, which lie wholly inside the serialized profile, and disclose index 10 separately as native extension.

B4 has changed source support at every index. B5 changes source horizons 1–6, ending at 1270 mm: index 8 mixes changed 1200–1270 mm support with unchanged 1270–1400 mm support; indices 9–10 are unchanged-input comparisons. The JSON retains each source horizon's original/native bounds, overlap, exact decimal weight, original FC/WP tokens and changed-support flag.

## Source path and management readback

All eleven source units bound in the JSON match selected commit `e0abe0581f77c6f66917e90daf8f8f429e9315c8` byte for byte. The relevant sequence is:

1. `contin.for:438–448` calls `infile`, then `input`, then `tilage`. `inidat.for:1141` initializes `tilflg=0`.
2. `infile.for:1366–1384` reads initial management tillage depths. All four bound management files have SHA256 `6ed3319bd1bce803b0cd2efbf631765b6d6e1f00bd2534f59358df11f9ecb31c`: three OFEs, ROAD/FILL/FOREST using cropland format, with initial depths 0.1/0.2 m. Each bound slope file independently declares three OFEs.
3. `input.for:545–590` reads the 9002 horizons, adds 200 mm to the final depth, and caps depth at 1800 mm. The special shallow-profile padding branch does not apply to these cases. `input.for:703–930` constructs 200 mm cells and thickness-weighted source-property averages. Their original horizon counts fit `pmxnsl.inc:7` (`mxnsl=10`).
4. `input.for:965–971` sets tillage depths to 0.1/0.2 m after management readback. `tilage.for:519–668` initializes two tillage layers and the remaining cells. Both top layers inherit the **same full 0–200 mm property average**. They must not be interpreted as independent averages of original 0–100 and 100–200 mm horizons. The resulting internal counts, 10 or 4, fit the selected native limit.
5. `contin.for:487–504` calls `scon`, `soil`, and `watbal` with `iflag=0`. `scon.for:160–345` applies bulk-density handling, rock/entrapped-air corrections, and moisture/porosity limits. These affect FC, dry reference and porosity after remapping. `watbal.for:253–255` selects the hourly routine under the bound `wepp_ui.txt` marker. `watbal_hourly.for:287–317` computes and logs FC, UL and their ratio for every internal layer.

The map uses exact decimal source-boundary arithmetic to describe the source-supported intervals. Actual internal depths are native floating-point quantities, and the observer emits neither `DG` nor a depth coordinate. Thus these are source-derived initialization coordinates, not directly observed depths or an exact binary-state reconstruction. Later management operations do not turn later diagnostic records into substitutes for the required initialization inventory.

## Interpretation and acceptance limits

Use the key inventory after exact ordinary/observer output parity passes. Preserve initialization dates as emitted; they are not daily climate coverage records. Retain complete original traces and selected tokens, and compare the policy arms at matched `(e,c,s)` keys. A changed-support flag means that the input alteration reaches that layer's property average; it is not a numerical prediction that every FC, UL or ratio token must differ after native corrections and rounding.

There is intentionally **no numeric FC/UL/HK prediction** in the helper. Native `scon` adjustments and the observer's `1pe12.4` formatting remain authoritative. Report actual token changes or their absence, including unchanged-input comparisons. Do not create a tolerance to force a visible response. FCUL is initialized available water depth above the dry reference, not the serialized volumetric FC value. A source-derived HK estimate from a printed ratio remains distinct from observed stored HK or execution of the PERC branch.

The prior [installed-observer review](resumption-r7-retention-native-observation-review.md) continues to govern parity, source/executable identities, marker behavior and scientific limits. This map provides no whole-system water closure, real pore-capacity validation, unique drainage/ET attribution, or production rollout evidence.

## Retained bindings and checks

The [case-bound helper](map_r7_retention_initial_layers.py) reads and validates the preparation declaration/result/readback, actual prepared soil bytes, bound management/slope/run/UI bytes, and exact selected source. It refuses a different declaration, management identity, source revision content, geometry outside these cases, or policy differences outside FC/WP horizon fields. It writes a new output exclusively and never invokes native execution.

- Preparation declaration: `5be61161a62c428867735328cd9b085da64473e13d26d92f8b8aae88bb87da7b`.
- Prepared case readback: `6c5e0797fa5795c74416087b9ba227272226d7d94feb69c89b618c20cb448fa2`.
- Mapping JSON: `5dcc0c68d3dd4213c1ae1cbc5bf7b18393318f962b2dde80f1d3b6f329c653c7`.
- Helper: `29d967c45d94f1fbc64c4aebfd01c33d8c01ac5ff31eda8d59046e417f23e732`.

The helper completed on all eight prepared soils. A separate direct readback checked the twelve paired OFE mappings against literal expected depth lists, changed-index sets, unique tag inventories, shared first-200-mm averages, each 200 mm native extension, and the B2/B3 10 mm/5% overlap. All checks passed; all eleven native source files were rehashed unchanged. These are read-only source/artifact checks, not a substitute for later observed initialization readback.
