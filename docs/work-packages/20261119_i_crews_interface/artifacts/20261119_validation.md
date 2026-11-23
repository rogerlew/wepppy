# I-CREWS local validation

Both launch presets were tested after the WBT-MOFE lineage correction
`ac1e41236`. Tests ran in the task worktree with WhiteboxTools 2.4.0. Native and API checks ran as
UID 1000 and GID 993 in the dev image
`sha256:659eb59a98ce2e69a74cd36538b9e392c8e33d66de3c8ee5303e02bd243d01a0`.

| Gate | Result |
| --- | --- |
| Focused Python | 640 passed, one skipped without disposable Redis. Isolated receipt `e9165eec56c04f2a84872246330a4b3f`. |
| Shared Upload DEM and RQ workflow | All 39 channel-boundary tests passed with disposable Redis and a real worker. Upload, native channel products, and retained readiness and content after a disjoint request passed. |
| Both create modes with real NoDb | Four API creations in disposable run directories. All redirected to the matching preset and reloaded the center, zoom, Idaho intersection mode, units, WBT, and MOFE flag. All rejected a boundary override before allocating a run. The snapshot writer replayed the same redirect using real disposable Redis. CAPTCHA verification and allocation root were injected by the fixture. |
| Frontend | npm lint passed. 126 Jest suites with 1,092 tests and nine Node tests passed. Chromium verified two real browser form submissions against the rendered card, loaded the supplied image, and checked both mobile and anonymous-disabled presentation. Browser requests were captured and separately exercised against the creation handler. |
| Run template and map | The real run template emits the shared Idaho outline and credit for both saved preset IDs. The map controller activates a toggleable outline without duplicate registration. The Lake Tahoe template regression preserves its existing behavior. |
| Documentation and test hygiene | Changed Markdown lint and test stub completeness passed. Changed-file broad exception enforcement found zero new catches. |
| Broad pytest | Stopped after 3,111 passes and 155 skips once the unchanged SSURGO fixture failure was reproduced separately. Isolated receipt `d02ed217cd5c4a47974ae0cc1d0da1b5`. |

The parallel observability command updated the tracked `code-quality-report.json`
during the interrupted run, so the broad receipt also flags a source
manifest change. The generated report was restored before handoff. The
focused and baseline probe receipts recorded no source changes.

## Repository baseline

The focused baseline probe on this branch reproduced
`test_project_ssurgo_cache_paths_are_derived_from_soils_dir` failing with
`AttributeError: 'Soils' object has no attribute '_config'`. Isolated
receipt `2b7327c698b5463687959970508ecd49`. The test, soils controller and
NoDb base are byte-identical to the prior baseline that reproduced the same
failure. See the [prior baseline result](../../20261119_channel_delineation_map_boundary/artifacts/20261119_validation.md).

## Generated products

Both presets ran on a 96 by 96 cell, 30-meter synthetic Idaho valley. Each
produced a fresh WBT network raster with positive channel cells and nonempty
GeoJSON map features.
Additional border-crossing tests produced channel raster cells and GeoJSON
features north and south of 42° N for both presets. A disjoint extent inside the
state's bounding box failed before either channel artifact changed. Restoring
the admitted extent allowed the same runs to build again.

The normal preset materializer and Ron initializer loaded each complete source
outside the map stanza. The corrected WBT-MOFE preset enabled MOFE and
retained `mofe_max_ofes = 5`, `wepp_261118`, and RAP time series. The
production WEPP preparation function read a seeded two-segment hillslope and
wrote `wepp/runs/p1.man` and `wepp/runs/p1.slp`. The management parser
returned two element records and the prepared slope header declared two
elements. Local model verification ends at executable input preparation.

## Static assets

The tracked boundary is one valid WGS 84 Idaho polygon with 3,254 exterior
coordinates, 90,579 bytes raw and 26,090 bytes gzipped. It uses Census 2025
1:500,000 state boundaries, state FIPS 16, and six decimal places. Its
SHA-256 is `3561a63bf7e46cb84ead392d2ddfeccf8f2ae7a900bc360f2e0cab7be0dab336`.
The included 960 by 960 PNG matches the supplied illustration byte for byte.
Its SHA-256 is `f8a86060e3df8f542de6ceeca9daae49c305c5dd2c3a6a551a66fa144b9b3569`.
See the [implementation plan](../prompts/completed/implementation_execplan.md)
for the polygon source and regeneration command.

## Scope

Highest completion claim: locally validated. The production site, public
CAPTCHA service, and a hosted browser-to-worker or full WEPP run are outside
this local validation. Verify that the map and worker see the same packaged
boundary when rolling out.
