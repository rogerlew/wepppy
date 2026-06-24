# CLAUDE.md — Treasure Valley Hydropower Gauge Validation

> Operating guide for validating hydropower-plant ↔ USGS streamgage mappings in the
> I-CREWS Idaho hydropower-prediction dataset (Treasure Valley). Maintained by Claude Code.

## Authorship
This file, like all CLAUDE.md files, is maintained by Claude Code. Edit it when the method,
tooling, or known traps change.

## What lives here
- `treasure_valley_hydropower_gauges_revised.csv` — corrected plant↔gauge table. Author's
  capacity columns preserved verbatim; gauge columns corrected; validation columns appended.
- `gauge-audit-report.md` — the audit: verdicts, per-plant findings, web references.
- This file — how to do (and re-do) the validation.

The dataset spans four flow systems: **Boise River** cascade (Anderson Ranch → Arrowrock →
Lucky Peak → Diversion/Barber), **Boise-Project irrigation canals** (New York / Mora / Wilder —
the canal-drop plants), **Snake River** (Swan Falls, C.J. Strike), and **Payette River**
(Black Canyon, Horseshoe Bend). Treat the canal plants as a separate class from river dams.

## Evidence-class discipline (inherited from repo root CLAUDE.md)
Label every report **Static** (read NWIS/source, reasoned) or **Executional** (data series
actually pulled and checked) in the opening line. Validating a *mapping* is static; it does not
confirm the gauge has a usable period of record or live telemetry. The current revised CSV is
static — **mean-annual-flow was not re-derived** and corrected rows carry a `re-pull`/`verify`
flag. Do not present a flagged MAF as confirmed.

## Identification & validation method
Run these checks for every plant before trusting a gauge assignment:

1. **Read the station name back.** Never accept a station ID on its own — adjacent IDs are real,
   wrong stations (13185**000** vs 13185**500**; 132**4**2500 vs 132**4**7500). Resolve the ID to
   its name and confirm it names the right stream and reach.
2. **Confirm the flowline.** Plot the plant's lat/lon and verify the gauge is on the *same* stream,
   not merely nearby. Two plants in this set were on the Snake at 11,200 cfs but sit on a canal
   ~17 mi away. Coordinates alone can disprove a basin assignment.
3. **Choose inflow vs. release vs. diversion deliberately.**
   - Storage reservoir + you model **water balance** → upstream **inflow** gauge(s).
   - Storage reservoir + you model **generation** → **release/through-turbine** gauge below the dam.
   - Run-of-river dam → inflow ≈ outflow; nearest up/downstream gauge is fine.
   - Canal-drop plant → **no natural-stream gauge exists**; use diverted canal flow.
4. **Sum tributaries for multi-input reservoirs.** Arrowrock = mainstem (Twin Springs) + S Fork
   Boise arm. C.J. Strike = Snake (Murphy) + Bruneau. Lucky Peak = upstream Boise + Mores Creek.
   A single upstream gauge under-counts.
5. **Mind diversions between gauge and plant.** On the Boise urban reach the New York/Ridenbaugh
   canals divert *between* 13202000 (above) and the at-Boise reach. A gauge above a major diversion
   over-states a plant below it during irrigation season, and vice-versa.
6. **Check active vs. discontinued.** A correct-name gauge is still useless if its record ended.
   13203000 (New York Canal) ended 1995; 13185500 (Cottonwood Ck) ended ~1942. Substitute USBR
   Hydromet where continuous real-time data is required.

## Tooling (operational reference, for Claude Code's use)
**Prefer the RDB web services over the HTML station pages.** The human-facing
`waterdata.usgs.gov/monitoring-location/USGS-<id>/` pages are JS-rendered — WebFetch returns mostly
nav chrome, not station facts. The legacy `nwis/inventory` URL now 301-redirects there. Use the
plain-text (`format=rdb`) services instead:

- **Site metadata (name, lat/lon, drainage area, HUC, county)** — read-back step 1:
  `waterservices.usgs.gov/nwis/site/?format=rdb&siteOutput=expanded&siteStatus=all&sites=<id>`
- **Mean annual flow** — average annual means over the period of record:
  `waterservices.usgs.gov/nwis/stat/?format=rdb&statReportType=annual&statTypeCd=mean&parameterCd=00060&sites=<id>`
  Do **not** use `statReportType=daily` for MAF — it returns per-calendar-day means; averaging those
  is the trap that produces a wrong "annual" number on third-party sites.
- **Daily / instantaneous series** for modeling:
  `waterservices.usgs.gov/nwis/dv/` and `.../iv/` (`format=json|rdb`, `parameterCd=00060`).
- **Find gauges from a point / navigate upstream** (inflow-gauge discovery) — USGS NLDI:
  start from `api.water.usgs.gov/nldi/linked-data/comid/position?coords=POINT(<lon> <lat>)`, then
  navigate upstream-main (`UM`) for `nwissite` features. Confirm the path against current NLDI docs;
  the API is versioned.
- **Reservoir storage & canal flow** (the canal plants and reservoir water balance) — USBR Pacific
  Northwest Hydromet: `usbr.gov/pn/hydromet/` (arcread/webarcread daily and instantaneous queries).
  This is the only source for the New York / Mora / Wilder canal drops.
- **Authoritative reach definitions** — IDWR Water District 63 accounting diagrams (Boise / Payette /
  Upper Snake). They formally bind each gauge to a reach; use them to settle ambiguous assignments.
- **Forecast/alt gauges** — NWS/NOAA `water.noaa.gov` (e.g. canal gauge `bsei1`, `bddi1`).

Parameter codes: `00060` discharge (cfs), `00065` gage height (ft), `00010` water temp.

## Known traps in this dataset
- **Off-by-digit station IDs** land on defunct creeks or headwater tributaries instead of erroring.
  Always do the read-back (step 1).
- **Anderson Ranch is on the South Fork**, not the mainstem Boise — do not give it a Twin Springs gauge.
- **MC6, Mora Drop, Fargo Drop are the same plant type** (Boise-Project canal drops). Treat them
  consistently as canal — none belong on the Snake; none has a stream gauge.
- **Barber vs. Diversion** sit on opposite sides of the New York Canal head. The Diversion plant runs
  on canal flow (13203000 / Hydromet); Barber runs on the river below the diversion (13206000 / 13203510).
- **Swan Falls** has a canonical accounting gauge — 13172450 (the 3,900-cfs Swan Falls Agreement point).
- **C.J. Strike** needs the Bruneau arm (13168500) added to the Snake arm (13172500).

## Open items
1. Re-pull MAF from the NWIS statistics service for every corrected/flagged row.
2. Source canal-flow series (USBR Hydromet / Boise-Kuna Irrigation District) for the four canal plants.
3. Decide inflow vs. release per storage reservoir based on the model target (generation vs. balance).
