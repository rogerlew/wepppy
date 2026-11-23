# WEPP 261010: Hourly Return Peaks and Source Normalization

2026-10-10. Roger authorized promotion after the Topanga diagnosis, paired
watershed comparisons, mutation study, disturbed rankings and Cedar rerun.
This replaces the undeployed wepp_261009 distribution in WEPPpy. Its historical
Forest artifacts and scientific evidence remain available; they are not the
current release. Release/vendoring does not deploy production services.

## Physical Changes

This release retains hourly MIXPEAK: preserve the existing rainfall-only peak
and add the maximum calculated hourly surface-return rate. The component peaks
are assumed to coincide; this is not a reconstructed mixed hydrograph. Runoff
volume is unchanged, while corrected physical peak and V/P duration feed
erosion hydraulics and sediment calculations. The producer scope remains
single-OFE, non-contoured, continuous-hourly cases; no-return and out-of-scope
producer cases retain their existing paths.

PASS v3 separates rainfall and returned-water components. The channel return
source uses the existing bounded rectangular support approximation, respecting
the hourly return ceiling. The previously accepted channel-state continuation
retains the internal routed profile across days and transfers it when the
computational grid changes. No new transport, parameter or routing architecture
is added. This does not reintroduce the superseded 261007 experimental bundle.

The only model-source change versus 261009 corrects CHRQIN sample accounting:
subtract the time-zero sample from the normalization sum only when it was
actually included. On initialized calls, the first real sample was previously
removed from the denominator but still delivered with an inflated multiplier.
Tiny rainfall components could therefore produce enormous artificial pulses.
The defect also affected ordinary source reconstructions; the repair is not
conditionally restricted to surface-return cases.

## Validation and Consequences

Topanga's January 18, 1993 undisturbed peak changes from 707.63910 to
12.50683 m3/s; event volume is +0.0113% versus wepp_260803. All four complete
Topanga/Rattlesnake scenario runs succeeded with 714 fresh hillslope passes.
Ordinary-event consequences remain disclosed: one burned Rattlesnake peak
falls 44.54780 to 20.21181 m3/s; another event's outlet sediment changes
140954.78 to 621811.88 kg with unchanged hillslope sediment inputs. Full-record
agreement is not a substitute for those event-level findings.

The mutation census completed 1368 cases plus ten observer controls. Full
runoff/peak and sediment ledgers and standard outputs exactly match 261009.
The paired 96-case disturbed matrix also matches exactly, including young
forest and adopted low-burn forest RRINIT 6 cm. Ordering remains 23/24 for
runoff, 24/24 for delivered sediment and 18/24 for maximum peak.

Cedar's complete 1980-2003 rerun uses 864 fresh hills per build, unchanged
10 cm RRINIT and a full 600-second outlet series. Candidate totalwatsed is
identical to 261009 and +0.393 m3 versus 260803 over 24 years. Sampled outlet
volume is +0.001008% versus 260803 and -0.049858% versus 261009. The remaining
integral-ledger gap is slightly smaller than 260803's but larger than 261009's;
this is not conservation closure. October event volume is +0.179% versus
260803, peak 50.5 to 46.2 m3/s, with unchanged peak time. Across 322 screening
windows, volumes range -0.154% to +0.619% versus 260803. Large first-maximum
timing shifts were traced to rounded plateaus/near-equal crests and remain
documented alongside centroids, not silently removed.

Detailed receipts, figures and limitations are in WEPPpy's
`docs/work-packages/20261009_topanga_jan1993_outlier/`: candidate-results.md,
hillslope-studies.md and cedar-results.md. These external watershed studies
are supplementary evidence, never mandatory private-resource gates.

## Compatibility

Use the paired wepp_261010 and wepp_261010_hill binaries and regenerate all
hillslope passes for a watershed rerun. No cross-release PASS swapping.
The existing paired PASS-v3 reader/combiners remain required. Public output
schemas, runtime flags, model banner, capacities and general project defaults
are unchanged. Locally saved 261009 selections must explicitly select 261010;
there is no hidden alias to a different binary. Historical result provenance
continues to identify the executable that actually produced each result.

Default Forest pytest discovery now targets the maintained tests/ suite.
Archived research scripts remain explicitly runnable but are not implicitly
collected as release gates. Their dependencies and duplicate module names
caused the earlier bare-discovery failure; no maintained test is excluded.

Source is `7471bb5e981d14d0b8c1cdb88a16af305aed1b67` on the default branch.
The paired sidecars and [validation record](wepp_261010_validation.md) contain
the artifact hashes, completed gates, unavailable optional fixture replay
and remaining limitations. Both rebuilt executables match the validated
candidate after removal of debug information and GNU build identity.
