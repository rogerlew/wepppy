# Treasure Valley Hydropower → USGS Gauge Mapping: Validation Audit

**Project:** I-CREWS Idaho hydropower prediction dataset (Treasure Valley site)
**Artifact audited:** author's plant↔gauge table (12 plants)
**Revised data file:** `treasure_valley_hydropower_gauges_revised.csv`
**Date:** 2026-06-24
**Author:** Claude Code

---

## Evidence class

**Static.** Every station ID, station name, river assignment, gauge role, and active/discontinued status below was verified by reading USGS NWIS (Water Data for the Nation) station pages and corroborating USGS/USBR/IDWR/FERC sources. **No flow series or long-term statistics were pulled in this pass** — mean-annual-flow (MAF) values were *not* independently re-derived. Where a gauge was corrected, the MAF cell in the revised CSV is flagged `re-pull`/`verify` rather than carried forward, because the author's original value belonged to the wrong station. MAF re-derivation is the one open item (see Recommendations).

This is a desk validation of the *mapping*. It is strictly weaker than an executional check against the actual NWIS daily-values record, which would also catch period-of-record gaps and telemetry status.

---

## Summary of findings

12 plants reviewed. **7 gauge assignments are wrong** (3 keyed to the wrong station, 2 to the wrong river/basin, 2 to the wrong tributary); **5 are defensible**, of which 4 warrant a refinement.

| # | Plant | Original gauge | Verdict | Corrected / preferred gauge |
|---|---|---|---|---|
| 1 | Anderson Ranch | 13185000 | ❌ wrong river | **13186000** (inflow) / 13190500 (release) |
| 2 | Arrowrock | 13185500 | ❌ defunct station | **13185000** (+ SF Boise arm) |
| 3 | Lucky Peak | 13185500 | ❌ defunct station | **13202000** (+ Mores Ck 13200000) |
| 4 | Barber Dam | 13202000 | ⚠ wrong side of diversion | **13206000** / 13203510 |
| 5 | Boise River Diversion | 13206000 | ⚠ wrong side of diversion | **13203000** (canal) / 13202000 |
| 6 | MC6 Hydro | 13172500 / "Snake R" | ❌ wrong basin | NY Canal (no streamgage) |
| 7 | Mora Drop | 13172500 / "Snake R" | ❌ wrong basin | Mora Canal (no streamgage) |
| 8 | Swan Falls | 13172500 | ⚠ refine | **13172450** |
| 9 | C.J. Strike | 13172500 | ⚠ refine | 13172500 **+ 13168500** (Bruneau) |
| 10 | Black Canyon | 13242500 | ❌ wrong tributary | **13247500** |
| 11 | Horseshoe Bend | 13242500 | ❌ wrong tributary | **13247500** |
| 12 | Fargo Drop | 13213000 | ✅ OK (proxy) | 13213000 (canal driver, river proxy) |

---

## Cross-cutting patterns (root causes)

Three failure modes explain every error, and each is preventable with one habit.

1. **Right magnitude, wrong station ID.** Errors #1–3 and #10–11 land on *real* stations whose numbers are one digit off the intended one — 13185**000** vs 13185**500**, 132**4**2500 vs 132**4**7500. A typo therefore silently resolves to a defunct 21-mi² creek (13185500 = Cottonwood Creek at Arrowrock, discontinued ~1942) or a headwater tributary (13242500 = Lake Fork Payette near McCall) instead of erroring out. **Fix:** open `waterdata.usgs.gov/monitoring-location/USGS-<id>/` and read the station *name* back before accepting an ID.

2. **Gauge assigned by proximity, not by flowline.** Errors #6–7 put two Boise-Project canal plants on the Snake River at 11,200 cfs. Their own coordinates (Kuna canal corridor, ~17 mi north of the Snake) disprove it. **Fix:** confirm the gauge is on the same NHD flowline as the plant; plot lat/lon on the NWIS map.

3. **Inflow vs. release vs. diversion not chosen deliberately.** Multi-tributary reservoirs need summed gauges (Arrowrock = mainstem + S Fork; C.J. Strike = Snake + Bruneau; Lucky Peak = upstream Boise + Mores Creek). Run-of-canal plants have *no* natural-stream gauge — their driver is diverted canal discharge. The Barber/Diversion pair (#4/#5) was assigned to the wrong sides of the New York Canal head.

A notable internal inconsistency: **Fargo Drop, MC6, and Mora Drop are the same plant type** (Boise-Project irrigation-canal drops), but only Fargo was tagged "Boise R canal" — MC6 and Mora were sent to the Snake.

---

## Detailed findings

### 1. Anderson Ranch — 13185000 → 13186000 (inflow) / 13190500 (release) ❌
Anderson Ranch is on the **South Fork Boise River**. The assigned 13185000 is *Boise River near Twin Springs* — the **mainstem**, which is Arrowrock's inflow, not the South Fork. Reservoir inflow is gauged at [13186000 SF Boise nr Featherville](https://waterdata.usgs.gov/monitoring-location/USGS-13186000/); the regulated release is [13190500 SF Boise at Anderson Ranch Dam](https://waterdata.usgs.gov/monitoring-location/USGS-13190500/). The author's MAF (~680 cfs) is South-Fork scale, so the *number* was right while the *ID* pointed at the wrong river. ([NPS: Anderson Ranch / Boise Project](https://www.usbr.gov/pn/))

### 2. Arrowrock — 13185500 → 13185000 ❌
[13185500](https://waterdata.usgs.gov/monitoring-location/USGS-13185500/) is *Cottonwood Creek at Arrowrock Reservoir*, a 20.9 mi² tributary discontinued around 1942 — it never carried ~1,280 cfs. Arrowrock's mainstem inflow is [13185000 Boise R nr Twin Springs](https://waterdata.usgs.gov/monitoring-location/USGS-13185000/); the **South Fork arm** (Anderson Ranch release, [13190500](https://waterdata.usgs.gov/monitoring-location/USGS-13190500/), or [13192200 SF Boise at Neal Bridge nr Arrowrock Dam](https://waterdata.usgs.gov/monitoring-location/USGS-13192200/)) must be added for total reservoir inflow. The author's 1,280 cfs is the Twin Springs value. ([NPS: Arrowrock Dam](https://www.nps.gov/articles/idaho-arrowrock-dam.htm); [LIHI #81 Arrowrock](https://lowimpacthydro.org/lihi-certificate-81-arrowrock-project-idaho/))

### 3. Lucky Peak — 13185500 → 13202000 ❌
Same defunct creek station, and far too high in the basin: Lucky Peak sits **below Arrowrock plus Mores Creek**. Use [13202000 Boise R nr Boise](https://waterdata.usgs.gov/monitoring-location/USGS-13202000/) for the integrated managed flow, adding [13200000 Mores Ck ab Robie Ck nr Arrowrock Dam](https://waterdata.usgs.gov/monitoring-location/USGS-13200000/) for the incremental tributary input. The author's 1,280 cfs (Twin Springs) under-counts this reach.

### 4 & 5. Barber Dam and Boise River Diversion — gauges effectively swapped ⚠
The river order is **Diversion Dam → Barber Dam → Glenwood**. Critically, [13202000 Boise R nr Boise](https://waterdata.usgs.gov/monitoring-location/USGS-13202000/) is located **above** the New York/Ridenbaugh canal diversions (the canals divert *between* 13202000 and the at-Boise reach), and there is a dedicated [13203510 Boise R bl Diversion Dam](https://waterdata.usgs.gov/monitoring-location/USGS-13203510/).

- **Diversion powerplant** generates on water diverted into the New York Canal, so its best gauge is [13203000 New York Canal bl Diversion Dam](https://waterdata.usgs.gov/monitoring-location/USGS-13203000/) (USGS record Feb 1989–Sep 1995, now discontinued; live data via USBR Hydromet / NOAA `bsei1`). The original 13206000 (Glenwood) is *below* the diversion and under-states it. ([NPS: Boise River Diversion Powerplant](https://www.nps.gov/articles/idaho-boise-river-diversion-powerplant.htm); [Boise River Diversion Dam — Wikipedia](https://en.wikipedia.org/wiki/Boise_River_Diversion_Dam))
- **Barber Dam** is run-of-river *below* the canal head, so it should use [13206000 Boise R at Glenwood Bridge](https://waterdata.usgs.gov/monitoring-location/USGS-13206000/) (downstream) or 13203510. The original 13202000 is *above* the diversion and over-states Barber's flow during irrigation season. ([FWEE: Barber Dam](https://fwee.org/barber-dam-boise-river-id/))

### 6 & 7. MC6 and Mora Drop — wrong basin ❌
Both are [Boise Project](https://www.boiseproject.net/public/home/about/) irrigation-canal micro-hydro near **Kuna**, on the [New York Canal](https://www.usbr.gov/pn/programs/nycanal/index.html) / Mora Canal system — not the Snake River. The assigned [13172500 Snake R nr Murphy](https://waterdata.usgs.gov/monitoring-location/USGS-13172500/) at 11,200 cfs over-states their throughput by roughly 10–50×, and the Snake is ~17 mi south of their coordinates. These plants have **no representative natural-stream gauge**; their inflow is diverted Boise River water governed by the Diversion Dam head gate, so the dataset needs canal-flow records (USBR Hydromet / Boise-Kuna Irrigation District), with [13203000](https://waterdata.usgs.gov/monitoring-location/USGS-13203000/) as the system-head reference. ([MC6 Hydro — gridinfo](https://www.gridinfo.com/plant/mc6-hydro-facility/64607); [Mora Drop — gridinfo](https://www.gridinfo.com/plant/mora-drop-hydroelectric-project/56498); [New York Canal — Wikipedia](https://en.wikipedia.org/wiki/New_York_Canal))

### 8. Swan Falls — 13172500 → 13172450 ⚠
Defensible, but the canonical gauge is [13172450 Snake R bl Swan Falls Dam nr Murphy](https://waterdata.usgs.gov/monitoring-location/USGS-13172450/) — the exact "Adjusted Average Daily Flow" point where the **3,900 cfs Swan Falls Agreement** minimum (cited in the Min-Flow column) is measured. ([IDWR: Swan Falls Settlement](https://idwr.idaho.gov/settlements/swan-falls-settlement/); [USGS: middle Snake seepage/discharge uncertainty](https://www.usgs.gov/publications/evaluation-seepage-and-discharge-uncertainty-middle-snake-river-southwestern-idaho))

### 9. C.J. Strike — add Bruneau ⚠
[13172500 Snake R nr Murphy](https://waterdata.usgs.gov/monitoring-location/USGS-13172500/) captures only the Snake arm. The author's own note ("Bruneau arm + Snake R") implies the second input: add [13168500 Bruneau R nr Hot Spring](https://waterdata.usgs.gov/monitoring-location/USGS-13168500/), which joins just above the reservoir. Release is [13171620 Snake R bl CJ Strike Dam nr Grand View](https://waterdata.usgs.gov/monitoring-location/USGS-13171620/).

### 10 & 11. Black Canyon and Horseshoe Bend — 13242500 → 13247500 ❌
[13242500](https://waterdata.usgs.gov/monitoring-location/USGS-13242500/) is *Lake Fork Payette River below Lid Canal near McCall* — a headwater tributary, wrong reach. The Payette mainstem gauge is [13247500 Payette R nr Horseshoe Bend](https://waterdata.usgs.gov/monitoring-location/USGS-13247500/): it is *at* Horseshoe Bend (run-of-river ⇒ plant flow) and is also the principal inflow to Black Canyon immediately downstream. One gauge correctly serves both rows.

### 12. Fargo Drop — 13213000 ✅ (proxy)
Basin correct. [13213000 Boise R nr Parma](https://waterdata.usgs.gov/monitoring-location/USGS-13213000/) is a reasonable downstream river proxy for this Wilder-area canal drop, but the true driver is canal flow (Wilder Irrigation District). Confirm MAF via NWIS statistics — the ~1,760 cfs figure seen on third-party sites is a single-day mean, not the annual mean.

---

## Recommendations

1. **Re-pull mean-annual-flow** from NWIS daily-values statistics for every corrected gauge (rows 1, 3, 4, 5, 8, 10, 11) and validate the carried-forward values (2, 9, 12). MAF was not re-derived in this pass.
2. **Source canal-flow data** for MC6, Mora Drop, Fargo Drop, and the Diversion powerplant from USBR Hydromet / Boise-Kuna Irrigation District — no USGS streamgage represents canal drops.
3. **Decide inflow vs. release per plant** for the storage reservoirs (Anderson Ranch, Arrowrock, Lucky Peak, C.J. Strike, Black Canyon) depending on whether the model predicts generation (use release/throughput) or reservoir water balance (use summed inflow + storage).
4. **Flag discontinued stations** in the dataset: 13203000 (NY Canal, ended 1995) and the previously-used 13185500 (Cottonwood Ck, ended ~1942) have no live telemetry; substitute USBR Hydromet where continuous real-time data is required.
5. **Cross-check against the authoritative reach definitions** in the [IDWR Water District 63 accounting diagrams](https://idwr.idaho.gov/wp-content/uploads/sites/2/legal/WD63/WD63-IDWR-File-Notes-Water-Right-Accounting-Systems-Diagrams-Boise-Payette-Upper-Snake.pdf), which formally bind each gauge to a Boise/Payette/Upper-Snake reach.

---

## Reference gauge table (verified this pass)

| Station | Name | Role in this dataset | Status |
|---|---|---|---|
| 13185000 | Boise R nr Twin Springs | Arrowrock mainstem inflow | Active |
| 13185500 | Cottonwood Ck at Arrowrock Reservoir | (mis-assigned; defunct) | Discontinued ~1942 |
| 13186000 | SF Boise R nr Featherville | Anderson Ranch inflow | Active |
| 13190500 | SF Boise R at Anderson Ranch Dam | Anderson Ranch release; Arrowrock SF arm | Active |
| 13192200 | SF Boise R at Neal Bridge nr Arrowrock Dam | Arrowrock SF arm (alt) | Active |
| 13200000 | Mores Ck ab Robie Ck nr Arrowrock Dam | Lucky Peak incremental inflow | Active |
| 13202000 | Boise R nr Boise | Lucky Peak system flow; Diversion arriving flow (above canals) | Active |
| 13203000 | New York Canal bl Diversion Dam | Diversion plant / canal supply | Discontinued 1995 |
| 13203510 | Boise R bl Diversion Dam nr Boise | Barber inflow (alt) | Active |
| 13206000 | Boise R at Glenwood Bridge nr Boise | Barber throughput | Active |
| 13213000 | Boise R nr Parma | Fargo Drop river proxy | Active |
| 13172450 | Snake R bl Swan Falls Dam nr Murphy | Swan Falls (Agreement point) | Active |
| 13172500 | Snake R nr Murphy | C.J. Strike Snake-arm inflow | Active |
| 13168500 | Bruneau R nr Hot Spring | C.J. Strike Bruneau-arm inflow | Active |
| 13171620 | Snake R bl CJ Strike Dam nr Grand View | C.J. Strike release | Active |
| 13242500 | Lake Fork Payette R bl Lid Canal nr McCall | (mis-assigned; tributary) | Active |
| 13247500 | Payette R nr Horseshoe Bend | Horseshoe Bend flow; Black Canyon inflow | Active |

---

## Sources

- USGS NWIS / Water Data for the Nation — station pages linked inline above (`waterdata.usgs.gov/monitoring-location/USGS-<id>/`).
- [IDWR — Swan Falls Settlement](https://idwr.idaho.gov/settlements/swan-falls-settlement/)
- [IDWR — Water District 63 accounting-system diagrams (Boise/Payette/Upper Snake)](https://idwr.idaho.gov/wp-content/uploads/sites/2/legal/WD63/WD63-IDWR-File-Notes-Water-Right-Accounting-Systems-Diagrams-Boise-Payette-Upper-Snake.pdf)
- [USGS — Evaluation of seepage and discharge uncertainty, middle Snake River](https://www.usgs.gov/publications/evaluation-seepage-and-discharge-uncertainty-middle-snake-river-southwestern-idaho)
- [NPS — Arrowrock Dam](https://www.nps.gov/articles/idaho-arrowrock-dam.htm) · [NPS — Boise River Diversion Powerplant](https://www.nps.gov/articles/idaho-boise-river-diversion-powerplant.htm)
- [FWEE — Barber Dam](https://fwee.org/barber-dam-boise-river-id/)
- [USBR — New York Canal](https://www.usbr.gov/pn/programs/nycanal/index.html) · [Boise Project](https://www.boiseproject.net/public/home/about/)
- [Wikipedia — Boise River Diversion Dam](https://en.wikipedia.org/wiki/Boise_River_Diversion_Dam) · [Wikipedia — New York Canal](https://en.wikipedia.org/wiki/New_York_Canal)
- [LIHI #81 — Arrowrock Project](https://lowimpacthydro.org/lihi-certificate-81-arrowrock-project-idaho/)
- [gridinfo — MC6 Hydro Facility](https://www.gridinfo.com/plant/mc6-hydro-facility/64607) · [gridinfo — Mora Drop Hydroelectric](https://www.gridinfo.com/plant/mora-drop-hydroelectric-project/56498)
