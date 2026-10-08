# Lower Tenderfoot Creek observed streamflow

Prepared 2026-10-08 for WEPPcloud's Observed tool.

## Import

Paste the complete contents of [lote_observed_daily_1992-2015.csv](lote_observed_daily_1992-2015.csv), including its header, into the Observed tool's data field. Columns are `Date,Streamflow (mm)`; dates use `MM/DD/YYYY`. The file contains 4,142 accepted days from 1992-10-01 through 2015-09-22. Excluded dates are omitted, never replaced with zero.

Use an observed-climate simulation covering those dates, with any model warm-up before scoring. Align the modeled outlet with Lower Tenderfoot Creek (LOTE), approximately **46.926932, -110.902815** (WGS84). The archive's supplemental gauge table gives NAD27 UTM zone 12N coordinates E 507463 m, N 5196842 m. The original `turbinate-melodrama` outlet is approximately 2.8 km away and drains a different area; these observations do not validate that outlet directly.

## Area and units

Depths use the **22.8 km² gauged Tenderfoot catchment** reported by [Bergstrom et al. (2016), section 2.1 and Figure 1](https://doi.org/10.1002/2015WR017972). This is an adopted literature area, not a new delineation or the original model's 30.84 km² area. Check the gauge-aligned model's watershed boundary before interpreting fit; do not rescale observations merely to accommodate a mismatched model outlet.

```text
Streamflow (mm/day) = mean discharge (cfs) × 0.3048³ × 86400 × 1000 / 22,800,000
                   = mean discharge (cfs) × 0.10730594498021054
```

Output precision is six decimal places, which is formatting precision rather than measurement accuracy. The audit retains daily means in cfs so a justified area revision can be reproduced.

## Sources and screening

- [Smith, Glasgow, and McCaughey (2017), daily average streamflow, 1992–2001](https://doi.org/10.2737/RDS-2017-0030): manually interpreted strip charts. Retain unflagged, finite, nonnegative LOTE values before 2001-07-19. Exclude flag 1 (regression-estimated missing observations) and flag 2 (estimated winter flows). This contributes 1,618 days.
- [Glasgow et al. (2013, updated 2015), 15-minute streamflow, second edition](https://doi.org/10.2737/RDS-2010-0003.2): use arithmetic daily means from 2001-07-19, the first complete accepted LOTE logger day. Require exactly 96 distinct quarter-hour timestamps with finite, nonnegative, unflagged values. Exclude flag 1 (sensor anomalies), flag 2 (frozen-well conditions), partial days, and days with duplicate timestamps. This contributes 2,524 days.

Logger data take precedence from the transition date onward; no rejected days are filled from the earlier archive. There are no days with acceptable observations in both archives, so their agreement at the transition cannot be independently checked. No interpolation or additional outlier clipping was applied. The source authors caution that flags do not identify every error; the logger archive also contains some short download gaps estimated by its authors without separate flags.

Preserve source date labels, described as Mountain Standard Time in the metadata. The actual CSVs use month/day/year despite the metadata describing day/month/year. Five duplicated logger timestamps occur on 2010-03-14 and 2013-04-02; their days are excluded. No daylight-saving correction was inferred.

## Coverage and interpretation

[daily_quality.csv](daily_quality.csv) records the selected source, sample counts, flags, invalid values, duplicate counts, acceptance, and source mean discharge for every date in the archive span. Rejected-day means are audit information only and must not be imported as observations. [annual_coverage.csv](annual_coverage.csv) summarizes accepted and excluded dates by calendar year; 4,251 dates are excluded across the 8,393-day archive span.

Coverage is seasonal, with substantial winter gaps. Observed's daily scores use matching observation/simulation dates; its yearly aggregation sums those matched days. **Those totals are not complete annual water yields.** Use daily hydrographs and explicitly matched seasonal periods for interpretation, and inspect coverage before reporting performance. Historical harvesting in Sun and Spring Park during 1999–2000 and prescribed burning during 2001–2003 also mean the whole record is not an untreated baseline.

## Reproduction and checks

[provenance.json](provenance.json) records archive checksums, conversion, screening policy, source transition, counts, and the output checksum. Download the two ZIP archives to the ignored `raw/` directory:

- [RDS-2017-0030.zip](https://www.fs.usda.gov/rds/archive/products/RDS-2017-0030/RDS-2017-0030.zip)
- [RDS-2010-0003.2.zip](https://www.fs.usda.gov/rds/archive/products/RDS-2010-0003.2/RDS-2010-0003.2.zip)

Run from this directory with Python, pandas, and NumPy:

```bash
python prepare.py --daily-archive raw/RDS-2017-0030.zip \
  --quarter-hour-archive raw/RDS-2010-0003.2.zip --area-km2 22.8
```

Compatibility: this adds a standalone import file and audit artifacts; it changes no run state, application schema, or source archive. Validation used the actual `Observed.parse_textdata` method with a temporary output and a no-op lock, verified all 4,142 dates/depths and generated date fields, reconciled accepted rows against the audit, and independently checked source conversions for 1992-10-01, 2001-07-19, 2012-06-05, and 2015-09-22. This verifies parser compatibility, not a live-run upload or model fit.
