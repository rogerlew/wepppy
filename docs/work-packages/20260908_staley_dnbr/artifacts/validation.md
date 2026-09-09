# dNBR validation

## Source fixtures

USGS CC0 Sky Island 2011-2017 release, DOI 10.5066/P99S0I9W. Selected two
unmodified Arizona GeoTIFFs plus metadata and hashes, about 160 KiB total.
MTBS continuous fire-level dNBR was also located; its current viewer queues
downloads with email, so no queued request was submitted. USGS direct download
provided the independent public fixtures without using GPL pfdf data/tests.

## Focused tests and artifacts

Command: `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_dnbr.py --maxfail=1`.
Result: 45 passed, two preexisting dependency deprecation warnings.
Final focused log: `/tmp/dnbr-final-focused.log`.

Both real 30 m source rasters are tested on their native grids and exact 10 m
targets; source hashes match the manifest. Constant synthetic DEMs and binary
footprint masks isolate normalization behavior, not watershed science.
[Development output records](development_outputs.json) preserve generated
10 m grid, hashes, ranges, mean and coverage; paths under /tmp may be ephemeral.
The two 10 m conversions took approximately 0.08 and 0.03 seconds locally for
640,053 and 168,399 target cells. These are sample timings, not a throughput SLA.
Coverage was about 31.1% and 15.3% of the deliberately full-rectangle test masks.
No claim is made about real watershed coverage or overlap with the soil panel.

Independent analytical tests cover negative/zero preservation, sentinel/mask
support, integer/float equivalence, offset/metadata handling, reprojection,
resolution/origin shifts, all-invalid and subpixel/disjoint overlap, date errors,
resource limits, VRT paths/program rejection, IMG, and failure cleanup.
The nearest/bilinear comparison confirms interpolation alters observations on
a shifted hole-containing raster while nearest keeps sampled values and holes.

## Reviews and broad validation

Independent [correctness](20260909_correctness_review.md) and
[security](20260909_security_review.md) reviews passed after all medium findings
were fixed and independently rechecked. Full suite passed via
`wctl run-pytest tests --maxfail=1`: **7,822 passed, 72 skipped**, 3,106 warnings,
788.44 seconds. Log: `/tmp/dnbr-full.log`.
Documentation lint passes for module, ADR and work package; local link/spelling
checks pass. No production endpoint, NoDb publication, deployment,
or live project mutation was performed.
