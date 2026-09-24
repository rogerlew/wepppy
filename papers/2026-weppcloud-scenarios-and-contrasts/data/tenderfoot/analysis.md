# Tenderfoot thinning: analysis and proposed paper narrative

Analysis snapshot: September 23, 2026, 17:41 UTC. Source:
[animal-misgiving](https://wepp.cloud/weppcloud/runs/animal-misgiving/disturbed9002_wbt/).
This is an analysis of model responses, not validation against observations.

## Recommended narrative

**From treatment prescriptions to spatially explicit watershed consequences:
why hillslope changes must be routed through the channel network.**

Use the two scenarios to establish the watershed-scale response to alternative
canopy and ground-cover prescriptions. Then use the 36 contrasts to show how
responses depend on treatment location and the condition of the rest of the
watershed. The strongest result is that isolated sediment effects do not add up
to the full-scenario effect, even though isolated water-volume changes nearly do.
That is a direct demonstration of why OMNI retains process-based watershed
routing rather than simply summing hillslope responses.

This is a more defensible central narrative than demonstrating a benefit from
thinning. Both modeled prescriptions increase long-term mean soil loss and
outlet sediment relative to the baseline. Neither prescription simulates the
probability or severity of a future wildfire. Canopy and ground cover change
together, so these runs do not isolate their individual effects.

## Experiment represented by the saved artifacts

The modeled contributing area is **26,992.7 ha (269.927 km²)**, with **2,149
hillslopes and 918 channels**. Hillslope area totals **26,956.978 ha**; channel
area accounts for the remaining approximately 35.7 ha. Full scenarios change
25,768.182 ha of evergreen forest, about 95.6% of hillslope area. Other land-use
classes remain outside the thinning treatment.

The scenarios prescribe **30% canopy / 75% ground cover** and **65% canopy /
90% ground cover**. These numbers are remaining cover settings, not percentages
of trees removed. The latter management class is labeled “Forwarder” in the
export, but the analysis does not equate either scenario to a measured operation.

Climate metadata identify **100 synthetic years**, PRISM stochastic mode,
station `mt241552`, and CLIGEN seed `76729`. The simulation produces mean annual
precipitation of about **559.7 mm** over this basin. These are not calendar-year
observations. WEPP binary selection is `wepp_260803`, with snow and baseflow
enabled and frost disabled; channel critical shear is 19 Pa. Run metadata report
an unknown source commit, so this snapshot does not establish complete runtime
provenance.

Contrasts use stream-order grouping with three order-reduction passes, not
single-hillslope substitutions. There are **18 disjoint spatial groups**, each
run with both prescriptions against the baseline. The groups collectively cover
all modeled hillslopes. Analysis group IDs 1–18 pair contrast IDs 1/2, 3/4, …,
35/36; these are analysis labels, not the dashboard's geographic group labels.
The exact TOPAZ membership is retained in `results/group_membership.csv`.

The Forest Service describes the experimental forest as **9,125 acres**, about
36.9 km², and documents its instrumented headwater catchments. The modeled basin
is therefore much larger than the experimental forest. Call this a
**Tenderfoot-area watershed demonstration** until the delineation is overlaid
with the official boundary and monitoring stations. Do not describe it as a
reconstruction of the experimental thinning treatment or compare its outlet
directly with an internal experimental-forest gauge.
[Forest Service site description](https://research.fs.usda.gov/rmrs/forestsandranges/locations/tcef).

## Full-scenario results

All values below are long-term annual means. Hillslope soil-loss density uses
summed hillslope soil-loss mass divided by summed hillslope area. Outlet densities
and water depths use total contributing area, including channels.

| Metric | Baseline | 30/75 cover | 65/90 cover |
| --- | ---: | ---: | ---: |
| Hillslope soil loss (tonne/ha/year) | 0.004071 | 0.031104 | 0.012733 |
| Hillslope soil loss (tonne/year) | 109.747 | 838.469 | 343.239 |
| Outlet water discharge (mm/year) | 71.084 | 147.059 | 127.613 |
| Gross channel soil loss (tonne/year) | 1,162.6 | 2,507.4 | 2,125.9 |
| Outlet sediment discharge (tonne/year) | 426.9 | 631.5 | 547.2 |
| Outlet sediment discharge (tonne/ha/year) | 0.015815 | 0.023395 | 0.020272 |

Relative to baseline, 30/75 increases mean outlet water by **106.9%** and sediment
by **47.9%**; 65/90 increases them by **79.5%** and **28.2%**. Soil loss increases
by factors of 7.64 and 3.13, respectively, but remains small in absolute terms.
Report absolute values alongside these large relative changes.

Gross channel erosion exceeds gross hillslope erosion in every full scenario.
This supports examining channel response, but does not identify the proportion
of outlet sediment originating from channels: erosion, deposition, and sediment
storage intervene between sources and outlet.

Water increases in all 100 simulated years. Outlet sediment increases in 76 years
under 30/75 and 78 under 65/90. Median annual sediment increments are 92.2 and
69.3 tonnes, versus mean increments of 204.6 and 120.3 tonnes. Annual responses
are skewed and can change sign. Simulated years characterize climate variability
within this realization; they are not independent field treatment replicates or
an estimate of parameter uncertainty.

## Spatial contrasts and routing

### Location changes the response

For 30/75, isolated-group outlet sediment increments range from **−1.7 to
+57.1 tonne/year**. For 65/90 they range from **−4.8 to +39.0 tonne/year**. Group
areas differ considerably; `contrasts.csv` therefore includes both selected and
actually treated areas and effects per treated hectare.

Two examples illustrate why a hillslope-only ranking is insufficient:

- Under 65/90, group 6 adds **55.42 tonne/year** of hillslope sediment delivery
  but only **6.2 tonne/year** at the outlet. Group 17 adds **17.45 tonne/year**
  of hillslope delivery but **39.0 tonne/year** at the outlet, accompanied by
  a larger change in gross channel erosion.
- Group 12 increases local hillslope delivery and water discharge under both
  prescriptions, but mean outlet sediment changes are **−1.7 and −2.9
  tonne/year**. These are small simulated net responses, not evidence that
  thinning generally reduces erosion or a validated management benefit.

Across groups, the rank correlation between added hillslope delivery and added
outlet sediment is 0.815 for 30/75 and 0.639 for 65/90. Local erosion is informative
but does not uniquely determine outlet response. Changes in transport and
storage are a plausible interpretation; identifying the responsible channel
reaches requires channel-resolved contrast outputs, which were disabled in this
run.

### Isolated effects are not additive

Let the isolated effect of group g be its contrast outlet value minus baseline.
Compare the sum of those 18 effects with full-scenario minus baseline. Because
the groups partition the watershed, this tests whether simultaneous treatment
can be approximated by adding independent group effects.

| Prescription | Sum of isolated sediment changes (tonne/year) | Full-scenario change (tonne/year) | Excess relative to full-scenario change |
| --- | ---: | ---: | ---: |
| 30/75 | 309.0 | 204.6 | 51.0% |
| 65/90 | 164.2 | 120.3 | 36.5% |

Hillslope soil-loss increments sum exactly when calculated from the source
hillslope summaries. Outlet water increments sum to within **0.004%** of the
full-scenario increment. Outlet sediment does not: the discrepancies are 104.4
and 43.9 tonne/year, far larger than the 0.1-tonne reporting resolution.

This result supports using contrasts as **conditional marginal responses**:
treating one group while the others retain their baseline condition. They are
not additive shares of a treatment portfolio. A proposed combination needs its
own assembled-and-routed evaluation. These results demonstrate workflow value,
not independently verified accuracy of WEPP's channel physics.

## Suggested manuscript text

> A Tenderfoot-area watershed application compared an undisturbed modeling
> baseline with two thinning prescriptions and 36 spatial contrasts spanning
> 18 watershed groups. Mean annual hillslope soil loss increased from 0.0041
> tonne/ha/year to 0.0311 and 0.0127 tonne/ha/year under 30/75 and 65/90
> canopy/ground-cover prescriptions, respectively. Outlet sediment increased
> by 47.9% and 28.2%, with substantial variation among treatment locations.
> Summing the isolated group sediment responses overestimated the corresponding
> full-scenario increments by 51.0% and 36.5%, whereas water-discharge increments
> were nearly additive. The example illustrates that treatment effects at the
> outlet depend on watershed routing and the treatment configuration elsewhere
> in the basin. OMNI contrasts support evaluation of these conditional responses
> while retaining a common watershed delineation and source scenario outputs.

Keep the Lookout case as a complementary postfire scenario example if desired.
Tenderfoot supplies the stronger demonstration of spatial contrasts and
nonadditive routed responses. Neither case currently establishes full-run versus
assembled-contrast equivalence or computational speedup.

## Data quality and validation

The analysis verified all **743 snapshot file SHA-256 hashes**, **72 recorded
source-output SHA-1 dependencies**, and all 36 contrast sidecar hashes. It checked
pass-file assignments against selected TOPAZ IDs, paired group memberships,
complete spatial coverage without overlap, completed-status artifacts, raw
outlet summaries against combined exports, and annual means against long-term
summaries. Mixed hillslope soil-loss totals reconstructed from baseline and
selected scenario hillslopes agree with the routed contrast reports within
0.12 tonne/year, allowing printed-value rounding. These checks establish internal
artifact consistency, not independent model validation.

Three artifact limitations are retained explicitly:

1. **Contrast controls:** `contrasts.out.parquet` copies each contrast's own values
   into `control_v` in stream-order mode. All stored differences are consequently
   zero, and 172 control entries disagree with the actual baseline. The source
   implementation at `wepppy/nodb/mods/omni/omni_artifact_export_service.py`, in
   the `selection_mode == "stream_order"` branch, explains this behavior. The
   analysis recomputes treatment-minus-baseline from the individual output
   files; it does not edit the production export. Discrepancies are recorded in
   `results/export_control_mismatches.csv`.
2. **Rounded density:** the outlet report prints mean sediment density as zero
   at its coarse precision. The analysis recomputes density from mass and area.
3. **Daily labels:** each full-scenario event table contains one duplicate date
   label in simulation year 100 (day 356). All event rows are retained for totals,
   which agree with long-term reports; annual analysis uses the separate annual
   loss tables. Daily timing and event-frequency analysis require resolving this
   label issue first.

Before publication, confirm the geographic scope, document the treatment
parameterization against actual management inputs, and perform at least one
independent full-run comparison for an assembled contrast. Observational
validation requires matching the modeled contributing area and climate to an
appropriate gauge; this stochastic run cannot be fitted directly to dated
observations.

## Reproduction and retained artifacts

From the repository root, using the existing virtual environment:

```bash
.venv/bin/python papers/2026-weppcloud-scenarios-and-contrasts/data/tenderfoot/analyze.py
```

To deliberately acquire a new snapshot (SSH access to `wepp1` required):

```bash
.venv/bin/python papers/2026-weppcloud-scenarios-and-contrasts/data/tenderfoot/fetch_snapshot.py
```

Fetching is read-only on production but replaces corresponding local snapshot
files and the manifest. Preserve the existing snapshot before fetching if the
production run has changed. The snapshot is not an atomic filesystem snapshot;
subsequent hash, dependency, and cross-table checks detect the inconsistencies
covered by those checks. Raw artifacts are retained locally under `raw/` and
excluded from Git due to size (~224 MB). Archive that directory with the paper's
research data for durable reproduction; a future download from a mutable run
cannot guarantee the same bytes. The tracked manifest records each input's path,
size, and SHA-256.

`fetch_snapshot.py`, `analyze.py`, and `snapshot_manifest.json` are retained with
all generated CSVs and PNG/SVG figures under `results/`. Environment versions and
check counts appear in `results/validation.json`. Existing dependencies are
pandas, NumPy, PyArrow (Parquet), and Matplotlib; no new dependency was installed.
The script checks input hashes before analysis and fails on required consistency
checks. No production model, report, or parameterization was changed.

Figures: `scenario_comparison`, `contrast_location_response`, and
`routing_nonadditivity`. Positive changes throughout mean treatment minus
baseline, the opposite sign of the documented production `control-contrast_v`
column. All tables are generated from the retained snapshot.
