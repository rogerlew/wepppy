# Original versus corrected roughness experiment methods

## Matched experiment

The site is warming-championship on forest, with 864 hillslopes, 1,904 overland-flow elements, 371 channels and outlet element 1235. All 24 calendar years, 1980–2003, are simulated. Each original-build lane uses the exact executable inputs of its corrected-build counterpart, verified by every input file's SHA-256 hash. The only physical input difference among roughness lanes is the initial roughness in 1,885 records originally set to 0.1 m. The 0.06 m and 0.008 m records remain unchanged. Climate, soil, cover, channel parameters, hourly water balance and routing timestep are held fixed.

The original pair is `wepp_260803` and `wepp_260803_hill`, verified against their retained release hashes. The corrected pair is the previously tested surface-return candidate; its binary hashes remain in the reference package. The source audit compares the original release commit with the retained unpatched tree, normalizing the four root capacity includes to their saved watershed versions because `make wepp_hill` swaps them. All 485 source/include/build files match. The retained corrected tree differs only in `irs.for`, `surpeak.for` and `makefile`. This source comparison does not independently recreate compiler or linker provenance.

## Water and peak measures

The watershed EBE daily peak is the primary outlet peak measure. EBE daily volume is checked against `chanwb.out` outflow. Printed `chan.out` discharge has a 600-second timestep and three significant digits; integration is retained as a separate measure, not substituted for the ledger or silently normalized. The earlier corrected experiment identified an approximately 1.3% difference between this integral and the ledger.

Native PASS conversion provides daily hillslope runoff volume in m³ and peak in m³/s. Native WAT and PASS are used to rebuild totalwatsed. Its streamflow is PASS surface runoff plus bottom-OFE lateral flow plus calculated groundwater baseflow. The baseflow settings are initial storage 0 mm, coefficient 0.04/day and deep seepage coefficient zero. No source-run cached summary is used. Optional soil-moisture and ash fields are not needed for this flow comparison.

Cross-build differences are corrected minus original. Within-build roughness differences are 17 or 60 cm minus 10 cm. Daily peak percentage ratios require positive original peaks; hillslope summaries also report thresholds of 0.001 and 0.01 m³/s to expose small-denominator effects. Sums of peak rates in diagnostic JSON are not water volumes and must not be interpreted as such.

## Acceptance and limitations

Successful execution is necessary but not sufficient. Verify all intended roughness tokens, all matched input hashes, fresh terminal records, output hashes, fourteen unchanged hillslope controls across roughness lanes, and channel output-mode parity. Check 8,766 daily outlet records and sample timing. Compare water-volume conservation separately from peak changes; retain both increases and decreases. A reported zero peak with positive daily volume is an anomaly to preserve and compare across builds, not automatically a patch regression.

Large peak differences with nearly unchanged volume are consistent with altered rate assignment, but do not alone prove that the corrected estimate is physically exact. The patch is not full coupled routing of return water through depression storage and kinematic-wave equations. This is a site-specific comparison of the requested builds, not a deployment, calibration, or release approval.
