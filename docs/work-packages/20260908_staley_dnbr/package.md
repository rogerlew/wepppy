# Staley dNBR backend normalization

Status: closed locally, 2026-09-09 UTC. Delivered the dNBR scientific contract, real western
US fixtures, a tested Python normalization/summary interface, and provenance.
Browser upload, NoDb/RQ mutation, and publication of live project replacements
are outside this backend increment; their design remains documented.

Read [ExecPlan](prompts/completed/dnbr_execplan.md) and [tracker](tracker.md).
The canonical module specification names `docs/dnbr_upload.md`; ADR-0054
records numeric choices. Security impact is high for raster/file references;
independent correctness and security reviews are required before closeout.
Source fixtures are USGS CC0 data, independently acquired, not pfdf fixtures.
No new external dependency, runtime acquisition, or production endpoint.

Success means exact target-grid output, explicit scaling, meaningful overlap,
partial/empty catchment reporting, actual GeoTIFF/HFA/safe-VRT tests, and
invalid inputs leaving existing products untouched. Generated artifacts and
full-suite evidence are required; no claim of browser wiring is permitted.

## Outcome

Local backend and 45 focused tests implemented; full suite 7,822 passed and
72 skipped. Independent correctness/security reviews passed after sidecar-mask
and XML/decoded-block resource findings were resolved. Two public Arizona
rasters and provenance are included. Canonical contract and ADR-0054 contain
the durable rules. No browser/NoDb/RQ integration, deployment or live mutation.
