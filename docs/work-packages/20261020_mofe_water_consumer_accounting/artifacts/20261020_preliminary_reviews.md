# Preliminary M1 Reviews

Two independent read-only reviewer agents were invoked during execution on
2026-10-20. These reviews assess source semantics and compatibility before
canonical amendments. Neither is contract ratification or implementation review.

## Source review: `/root/source_review`

High: WAT terminal runoff and PASS surface export are different products.
Current `wshpas.f90:139` uses internal runoff >= 0.001 m, whereas ordinary WAT Q
also scales by efflen/totlen. Binary pass writers preserve the event distinction.
AshPost must subtract the same PASS contribution included in its watershed
baseline regardless of the hillslope display source decision.

Medium: upstream `wepp-forest/docs/schemas/watbal_output_mapping.schema.md` A3
still prescribes area-weighted Q/QOFE. Reconcile through an explicit tested
consumer exception or contract amendment before implementation.

Current hillslope input forces constant width; terminal Q times summed OFE area
therefore matches pre-filter model volume for ordinary and contour expressions.
Unknown lineage or arbitrary variable-width Parquet does not inherit this proof.

Independent paired readback under
`/workdir/wepp-forest/docs/work-packages/20260503-wb01-waterbalance-baseline-characterization/artifacts/replays/`:

| Lane | WAT days / OFEs | Joined PASS days | Positive Q on non-EVENT days | Sum Q on those days |
| --- | --- | --- | --- | --- |
| UP_H5_HOURLY | 2062 / 3 | 2022 | 12 | 1.93983663 mm |
| UP_H5_REQ_HOURLY_EFF_DAILY | 2062 / 3 | 2023 | 11 | 1.82715068 mm |
| DP_P962_DAILY | 6210 / 1 | 6210 | 0 | 0 mm |

WB01 `artifacts/baseline_command_log.md` records source
`e7eff0e968a959d0697bc5dd00a7458b84bf05f7` and binary hashes, but no rebuild.
Both H5 replays terminated with SIGFPE. These are observed-day source evidence,
not complete-run acceptance. Current contour execution evidence remains absent.

Disposition: retain the findings; source-product question pending. Explicitly
acknowledge lateral PASS's small-volume suppression as well. Require fresh paired
provenance evidence, sparse-day policy and final reviews before checkpoint.

## Compatibility review: `/root/compatibility_review`

High: export event filtering precedes temporal reduction in
`carrier_layer_materializer.py`. Selecting max OFE from that filtered frame can
promote an upstream OFE when the real terminal is absent. Determine topology
and full geometry from unfiltered, source-specific native identities, then apply
selectors and mapped feature combination. TotalWatSed's global-terminal logic
still synthesizes zero on upstream-only days, so it is not a sparse-day lateral
oracle.

High: Ash result predicates in `ash.py` inspect file existence, and AshPost getters
read existing artifacts directly. AshPost version invalidation on explicit
postprocessing does not invalidate model outputs generated from old daily Q.
Define separate model-input and postprocessing provenance and visible
historical/unverified behavior. Never claim corrected model outputs merely
because postprocessing reran.

High: subtracting WAT volume from PASS-based watershed Runoff would introduce a
source mismatch, hidden by current negative clipping. Name the AshPost subtraction
authority separately from the chosen hillslope runoff product.

High: unavailable Q cannot be passed as NaN to Ash models. Existing threshold
comparisons can silently bypass transport branches and retain initialized zero
transport. Validate finite required model inputs before simulation.

Medium: preserve exact joined-source column bindings and add any new PASS,
topology or provenance dependencies to cache fingerprints. Current report proof
dependencies contain only source and mapping. Give every diagnostic, stock and
optional field an explicit missing/null/nonfinite and temporal disposition.
Legacy `report.Rmd` still calls raw `calc_watbal`; a visible unsupported-MOFE
error is a bounded option pending review, rather than silently keeping incorrect
closure or deleting shared helpers. The second helper's complete path is
`weppcloudR/templates/scripts/users/chinmay/weppcloudr_report_functions.R`.

Disposition: all findings retained as M1 obligations. No implementation fixes or
closed findings are claimed. Final independent reviews must inspect the actual
prepared canonical amendments after the operator's source choice.
