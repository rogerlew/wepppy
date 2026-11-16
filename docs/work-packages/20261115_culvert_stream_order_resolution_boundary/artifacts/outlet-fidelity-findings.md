# Outlet fidelity and cardinality findings

The matrix does not support replacing the nominal-resolution mapping with a
universal four-pass rule. Three passes retains all 39 native supplied points and
resolved outlets; four retains 32. Six lost outlets require 214–521 m of D8
travel to surviving streams, and 2939 terminates without reaching one. All seven
watershed polygons have zero surviving four-pass channel cells, predicting the
existing full-stream fallback. No outlet was moved in these experiments.

## Point_ID 1040 terrain comparisons

| Treatment | Passes | Hillslopes | Channels |
| --- | ---: | ---: | ---: |
| Retained ~9.33 m baseline | 1 | 726 | 298 |
| Original 1 m, 100 cells | 3 | 3344 | 1339 |
| Original 1 m, 100 cells | 4 | 783 | 313 |
| Original 1 m, 8697 m² extraction | 0 | 3718 | 1489 |
| Original 1 m, 8697 m² extraction | 1 | 892 | 357 |
| Coarsened/filled 2 m, 100 cells | 2 | 3834 | 1544 |
| Coarsened/filled 4 m, 100 cells | 1 | Failed | Failed |
| Coarsened/filled 8 m, 100 cells | 1 | 971 | 394 |
| Coarsened/filled 10 m, 100 cells | 1 | 617 | 254 |

The 4 m failure is WBT `Invalid TOPAZ ID 0 for link 1515`; keep it in the
experimental denominator. The initial commentary misidentified it as 2 m;
full retained log and successful artifacts establish that 2 m succeeded.

Fixed-area extraction plus one pass retains 37/39 supplied point intersections;
8 m and 10 m treatments plus one pass retain 22/39 and 24/39 respectively.
Passing 1040's count target does not imply whole-batch outlet fidelity.

## Interpretation limits

Coarsening includes filling and resolution-dependent minimum-length pruning.
Point occupancy is cell-size dependent. Area comparisons sample accumulation at
unchanged retained 1 m outlet locations, not a newly snapped outlet or the old
baseline's own resolved outlet. In particular, the retained baseline gives only
about 261 m² at the 1 m 1040 outlet location, despite its own successful historical
watershed; that illustrates coordinate/network disagreement, not that its
historical watershed was only 261 m². The ±20% area band in the JSON summary is
exploratory telemetry, not an operator-approved acceptance criterion.

WBT downstream distance requires negative nodata for this DEM: nodata zero
collides with zero-distance stream seeds. The diagnostic conversion proved
identical valid elevations, grid and valid mask. Invalid first outputs are
explicitly labeled and excluded. Native distance source uses D8 positive-slope
routing consistent with the pointer; distances begin at cell centers.

## Next scientific decision

Retain the supplied network as positional authority. Investigate a constrained
simplification that preserves the paths required by every culvert, or per-run
pass selection with explicit outlet/coverage checks. These are research options,
not implemented changes. Additional watersheds and genuine outlet-preserving
controls are required before adopting a selector. Terrain experiments do not
constitute complete RQ/WEPP validation.
