# dNBR tracker

Status: completed locally, 2026-09-09 UTC. Backend Python interface first; browser/endpoint scope question
was offered while independent research proceeded. No answer required for
this bounded implementation assumption.

- [x] Read draft and existing compiled GDAL raster-warp precedents.
- [x] Acquire two Arizona dNBR rasters and public-domain metadata.
- [x] Freeze backend contract and ADR.
- [x] Implement and validate real artifact pipeline and edge cases (45 focused tests).
- [x] Independent correctness/security review approved; three medium findings closed.
- [x] Full tests: 7,822 passed, 72 skipped. Durable docs and ADR updated.

Source discovery: MTBS individual-fire dNBR exists, but its current viewer
queues bundles using email. No email submitted. USGS Sky Island 2011-2017
release supplies directly downloadable CC0 dNBR; selected two Arizona files.
Actual files are Float32 x1000, contradicting metadata's 8-bit prose; embedded
processing code establishes x1000. Masks include both extreme sentinels and NaN.

## Current evidence

[Validation](artifacts/validation.md), [correctness review](artifacts/20260909_correctness_review.md),
[security review](artifacts/20260909_security_review.md), and
[real-file development outputs](artifacts/development_outputs.json).
All backend gates passed. Browser/NoDb/RQ publication remains deferred.
No deployment or live-project mutation; changes remain uncommitted.
