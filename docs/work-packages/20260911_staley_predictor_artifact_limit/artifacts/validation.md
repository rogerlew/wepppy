# Validation

Checkpoint: `c145e73ce`. Operator-selected cap: 96 MiB (100,663,296 bytes).
Original failed job: `04289cc1-c890-42db-9315-fdce44d0d491` on addicted-reservist.
The generated slope TIFF was 74,129,489 bytes, above the rainfall 64 MiB default.

- Focused rainfall/results suite: 65 passed. Exact-96-MiB sparse controlled
  predictor artifact completes build and final recheck; mutation/hash mismatch,
  over-96-MiB and over-1-MiB JSON rejection pass. Default rainfall cap remains
  64 MiB. Controlled bytes test hash admission; real terrain is verified below.
- Existing final-recheck mutation wrapper now accepts/forwards the new limits
  argument, retaining its original incomplete-publication assertion.
- Documentation lint, whitespace check, and broad-exception gate passed.
- Independent correctness and security reviews passed the source change; no
  unresolved findings. Both required explicit limits through final recheck.
- No frontend logic changed in this repair. Full Python suite remains on hold.

Live UI submission returned job `c885f28b-e292-4046-853a-d3b8898caa39`, attempt
`3d7fd3391ebb40169cedd5c2367abe37`. It finished 02:17:15 UTC after starting
02:16:43 UTC. The actual UI displayed completed status, the new job link and
four output downloads; the downloads and job link persisted after reload.
All published artifact signatures verify. See [browser log](model_browser.log).

The run is scientifically partial under existing uncertainty policy: F and S
are available with full support, but T is unavailable (`unknown_intersection`):
114 of 4,311,420 basin cells lack resolved slope/SBS intersection. T bounds are
0.056235764550890424–0.0562622059553465. This separate diagnostic is preserved;
no uncertainty or numerical policy was changed by the resource-limit repair.

Development web/RQ-engine refreshed; no production deployment or native change.
Implementation remains uncommitted; contract checkpoint alone is committed.
