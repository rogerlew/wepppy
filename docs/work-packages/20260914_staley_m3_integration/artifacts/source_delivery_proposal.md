# Bounded source delivery and soil decision proposal

Status: recorded-depth policy ratified at `89d673c38`; reusable basin-independent
source preparation required by owner clarification. Network acquisition is now
explicitly [authorized](20260914_acquisition_authorization.md), with all recorded
limits unchanged. Earlier scientific proposal language below is historical.
Evidence: [development inventory](source_inventory.md).

## Recommended scientific direction

The owner rejected the original strict-material proposal. Advance the
[depth-based replacement](depth_policy_assessment.md): include documented H
and weathered Cr with ordinary O/A/E/B/C, exclude explicit hard R, derive
contiguous recorded thickness from representative endpoints, and retain
separate thickness-field disagreement as an audit warning. Keep malformed
depths, unexplained gaps/overlaps and conflicting IDs unavailable. H alone
restores thickness estimates for every development basin cell before SBS
intersection; fallback is no longer required merely to compensate for H rejection.
Original THICK's retained extraction has no explicit bedrock filter. Its
fallback does not prove H/Cr material was excluded: material treatment is
source-specific, with the original dataset's aggregation limits retained.

Use positive usable component percentages to normalize each map-unit mean.
Individual weights must be finite and within 0–100; invalid individual weights
make the map unit unavailable. Zero weights contribute nothing. Permit totals
above 100 with a diagnostic; retain known, usable, nonsoil and rejected weight
totals without calling them spatial coverage. Missing or unusable components
never become zero thickness. For each cell choose usable primary thickness,
then original THICK; if neither works, exclude it from common support.
Explicit all-R components remain nonsoil and outside usable primary weight,
matching the strict helper. A finite zero THICK value remains eligible under
the original dataset's nonnegative-value contract; absent horizons, invalid
intervals and the negative sentinel never establish measured zero.

Examples: 60% at 100 cm and 40% unavailable gives 100 cm on that map-unit pixel,
with usable weight 60. Two equal-area pixels with estimates 100 cm (usable
weight 60) and 200 cm (usable weight 100) give a spatial mean of 150 cm;
offline fractional weighting gives 162.5 cm. With weights 70 and 50 at 100
and 200 cm, normalize by 120 to obtain 141.6666666666667 cm, and disclose
the overfull total. No observation is manufactured for missing components.
An R-only primary component at 100% has no usable primary mean and triggers
fallback; a THICK cell of 0 inches contributes 0 cm if SBS is valid, whereas
-0.1 inches excludes that source cell and never becomes zero.

The [NRCS Fundamental Query](https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf)
documents paired transitional horizons and component totals above 100.
Identical endpoints alone do not identify a legitimate pair. The replacement
assessment proposes a bounded two-record combination-horizon rule and retains
all other overlap rejection. Sixteen analytical cases pass, including a named pair,
ordinary duplicate ranges, conflicting IDs and soil below R. The live/frozen
fixtures have no pairs, so authentic pair evidence remains absent. Current NSSH
guidance asks for contiguous representative intervals; the proposal distinguishes
legacy paired records explicitly. Offline defaults remain unchanged.

## Acquisition delta for approval

Implement reusable project-scoped preparation of the native-resolution USGS
THICK window covering the selected project's DEM extent, using only the exact
USGS object in the inventory. Derive the extent from that project's grid, not
from a named validation run. Retain the native window and request metadata in a new,
visible `postfire_debris_flow/source_preparation/<unique-id>/` directory.
Do not overwrite an existing record or write to the shared soil cache.

Use HTTP range reads with a 30-second per-request and 120-second overall
deadline, no whole-CONUS download, and a 96 MiB aggregate response-body ceiling
including metadata/auxiliary reads. No automatic retries. Abort and retain diagnostics if the reader
cannot enforce that bound. Record object identity before/after, source CRS,
native window, units, nodata, request outcome and resulting file hash. Treat
object drift as an explicit abort. Pin each range request to the inventoried
object identity established for that preparation with `If-Match`, reject responses that ignore the requested range, and
reject redirects outside the exact approved object location. The implementation
must prove these controls before this acquisition can run. Treat
negative values and nonfinite values as unavailable; convert valid inches
to cm with 2.54. Align with nearest-neighbor sampling to avoid creating
interpolated thickness across missing cells. Retain the native window so
this resampling choice remains reproducible. Execution must still demonstrate
that the existing predictor artifact limit is sufficient.

Also prepare one bounded read-only NRCS SDA query for the unique original
map-unit keys found within the selected project's watershed mask, joining
mapunit/legend/sacatalog to retrieve collection identity and
current survey version only. This does not establish the historical version
of the existing cached horizons; retain their retrieval sidecar and content
hashes, and label historical survey version unknown unless separately proven.
Cap response at 1 MiB, with a 30-second timeout and no
automatic retries. Retain query and response in that same visible preparation
record; do not fetch replacement horizons or refresh shared caches. If source
lineage cannot be established, do not label those keys SSURGO primary.
The only SDA endpoint is `https://SDMDataAccess.nrcs.usda.gov/Tabular/post.rest`;
reject redirects. Current associations alone must not be presented as verified
historical record provenance.
Absent primary mapping/cache or no usable original keys skips this query and
allows fallback-only preparation; malformed present files remain errors.
Incremental unique-key collection and the final encoded SDA request each have
a 1 MiB ceiling. Abort rather than automatically batching or expanding requests.

The 34 cached keys and raster extent in the original development inventory are
observations, not generic query inputs or limits. Reuse the same preparation
entry point across eligible basins; validate it on distinct key sets and grid
extents, with primary, fallback and missing-source cases. Do not close this work
with a one-off download script or manually assembled named-basin inputs.

This preparation proposal adds no runtime acquisition service or dependency.
General runtime delivery remains prepared local inputs; missing delivery must
be reported explicitly. Network, parsing, path and database corruption errors
must not become successful scientific fallback. If approval changes the soil
policy, quantify that choice and amend the canonical contract and proposed ADR
before independent checkpoint approval and the standalone ancestor commit.

## Historical checkpoint work before ratification

S05 requires the H/Cr and paired-horizon disposition; S06–S07 require ratifying
the weighting and per-cell/resampling rules above. S08 requires acquisition
authority and verified lineage/delivery. S09 still needs exact additive schemas,
source snapshot/reuse identities and measured resource bounds. No implementation
checkpoint or review signoff is claimed by this proposal.
