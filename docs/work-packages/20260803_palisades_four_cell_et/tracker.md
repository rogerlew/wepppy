# Tracker - Palisades Four-Cell ET Attribution

## Quick Status

**Timezone:** UTC
**Started:** 2026-08-04 01:33 UTC
**Current phase:** Complete
**Last updated:** 2026-08-04 02:00 UTC
**Next milestone:** None; follow-up remains hillslope timing/routing
**Security impact:** none
**Dedicated security review:** no

## Task Board

### Done

- [x] Move the standalone Palisades repository into WEPPpy and remove nested
  Git ownership (2026-08-04 01:33 UTC).
- [x] Fix the four-cell scientific and cleanup contract (2026-08-04 01:33 UTC).
- [x] Pass four-cell H1 smoke including PMET markers and enriched 16,802-row
  water-balance output (2026-08-04 01:45 UTC).
- [x] Execute and aggregate 1,112 production-derived hillslope simulations
  (2026-08-04 01:54 UTC).
- [x] Publish compact results, three figures with sidecars, and the causal
  disposition (2026-08-04 02:00 UTC).

## Decisions

- **2026-08-04 01:33 UTC** - Use every production hillslope rather than a
  sample. This preserves the actual burned severity and land-cover mosaic.
- **2026-08-04 01:33 UTC** - Change `pmetpara.txt` presence only within each
  land-state pair. Burned versus undisturbed retains the corresponding
  management and soil state so the factorial interaction answers whether PMET
  amplifies the land-state contrast.
- **2026-08-04 01:33 UTC** - Run hillslopes only. Daily runoff and full-profile
  soil water diagnose runoff generation; existing sub-daily channel evidence
  remains the authority for routed peak shape.

## Risks

- The pruned undisturbed Omni run no longer contains `wepp/runs`. The runner
  reconstructs it from canonical undisturbed management templates and the
  original, unmodified soil files retained beside the disturbed variants.
- Raw water-balance files would exceed practical documentation size. Each is
  validated before deletion; lossless area-weighted daily and annual tables
  retain the variables needed by this experiment.

## Verification Checklist

- [x] 1,112 runs completed and row-count/finite-value gates passed.
- [x] Four-cell PMET marker checks passed.
- [x] Sidecars and source hashes recorded.
- [x] `/wc1/ablation/palisades-four-cell-et-20260803` removed.
- [x] `/workdir/wepp-forest_260430_baseline` remains clean.
- [x] Scoped documentation lint passes.

## Outcome

PMET materially changes `Es`/ET but does not dry burned profiles or reduce
burned runoff. It weakens the burned-minus-undisturbed runoff contrast by 1.56
mm/year relative to legacy ET. Continue with timing/routing hypotheses rather
than PMET antecedent drying.
