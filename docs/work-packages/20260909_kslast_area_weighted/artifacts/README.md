# Required execution evidence

Status: planned; no implementation or integration results recorded.

Create the following during execution; retain small summaries/hashes in Git and keep large backups, rasters, and model outputs outside Git:

- `baseline.md`: host/preset, run settings, source/grid hashes, queue state, external backup location and restore procedure.
- `kernel_validation.md`: Rust and exported Python tests, independent means, alignment/mask/nodata/default behavior, bounded performance/memory observations.
- `release_manifest.json`: source commits, exact build/install commands, Python ABI, runtime paths, library hashes, relevant GDAL/PROJ versions.
- `restart.md`: local `wctl down` / `wctl up -d`, timestamps, old/new container IDs, readiness, web/worker imported extension hashes.
- `integration.md`: RQ parent/leaf IDs and final states; run settings; before/after timestamps and hashes; full hillslope/OFE input comparisons; fresh model/interchange/report evidence.
- `correctness_review.md`: independent reviewer, valid-state matrix, findings and dispositions using the repository template.
- `security_review.md`: native/raster/runtime-publication checks and findings using the repository template.
- `validation.md`: final test/doc/quality gate results and both commit/push/remote-tip records.

Write an executable integration driver here during implementation. It must use normal RQ submission, poll descendants rather than trusting parent enqueue success, and exit nonzero on any missing/stale artifact or discrepancy. Secrets must never appear in committed scripts/logs. This checklist is not test evidence.
