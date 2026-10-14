# Future EDDE v2 climate

Select **Future EDDE v2**, a driving model/scenario, and full future years. MPI projections support 2025–2099; NorESM supports 2025–2079. Choose the auxiliary CLIGEN station and optionally a seed. Blank seed uses the existing automatic replay behavior; explicit seeds are retained unchanged.

The method is offered for continental U.S. and Canadian locales. Coverage is partial in Canada. Each build checks the actual watershed location against EDDE's native land grid. Multiple PRISM also checks all hillslope locations and requires valid PRISM normals. Multiple Interpolated is unavailable. Stored project capabilities retain their prior choices until an explicit supported capability refresh; older configurations may require creating a current project.

EDDE supplies future daily precipitation and maximum/minimum temperatures as provided. The 12 km grid limits representation of local elevation effects. Model bias and elevation effects are not corrected. The selected CLIGEN station supplies storm structure/intensity, radiation, wind and dewpoint; these fields do not represent projected EDDE changes. Existing CLIGEN quality guards and format rounding apply.

Multiple PRISM applies existing monthly precipitation ratios and temperature offsets, including the documented midpoint repair for introduced temperature inversions. Optional scalar, monthly and spatial precipitation scaling remains separately attributed. AnnualMonthlies matching against observed reference years is unavailable for future EDDE.

Reports identify the published projection, period, station, seed and native cell. The climate browser retains `edde-build-*` attempts with extracted daily data, source identities, generated files and diagnostics. Failed and superseded attempts remain visible; previous published climate is preserved when acquisition, replay, spatialization, scaling or finalization fails. Automatic seeds are not claimed to be reproducible.

## Operations and compatibility

Use the existing authenticated build-climate endpoint/job and normal WEPP preparation. No new queue or service is required. Acquisition uses isolated temporary yearly caches with a four-billion-byte yearly source budget; a multiyear build can transfer substantially more than that in total. Planned years/bytes are recorded in the attempt. Source NetCDF cache bytes are discarded; retained manifests and extracted data support diagnosis and reconstruction. Cancellation or worker termination may leave an incomplete attempt.

Capability-only reader floor `26c9e86ca` registers the four additive U.S./Canada ordinary/single-input capability structures before writer exposure. Preserve that reader floor in any rollback after new graphs have been stored. That graph floor alone cannot deserialize saved `ClimateMode(17)`. Once EDDE selections are saved, retain EDDE-aware NoDb readers/builders from `d2ca5821b` and the published-calendar correction in `202ab65f3` in any rollback candidate. No full rollback deployment was validated. No stored graph is automatically migrated. Source selection/projection fields are additive, and absent values remain unselected. Production deployment and rollback follow the existing deployment entry point and require their separate acceptance; this work package does not deploy production.

See [EDDE-WEPP-01](../schemas/edde-v2-weppcloud-contract.md) for the normative contract and [integration tracker](../work-packages/20261013_edde_v2_weppcloud_integration/tracker.md) for current validation status.
