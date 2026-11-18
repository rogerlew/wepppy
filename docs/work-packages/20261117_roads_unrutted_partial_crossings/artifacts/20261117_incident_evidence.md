# Retained incident observations

Recorded 2026-11-17 17:45 UTC from read-only inspection during this conversation.
These are summarized observations, not a captured reproducible run fixture.

Host: `wepp1`. Run: `misty-eyed-divorcee`.
Host root: `/geodata/wc1/runs/mi/misty-eyed-divorcee`.
Container root: `/wc1/runs/mi/misty-eyed-divorcee`.

Earlier investigation observed 38 prepared unrutted segments, none passing 60%.
The updated `roads/roads.uploaded.geojson` has 55 source features; current
`wepp/roads/segments/roads.inslope.monotonic.geojson` has 9 prepared features.
Do not interpret that count as 55 features merged into 9: preparation can omit
parts without valid DEM samples and split other parts.

RQ job `1e6a36e1-72fe-46f1-94d4-5a521cefc7e6` started
2026-11-16 18:36:35 UTC and failed 18:37:15 UTC. Redis `Job.fetch`, `get_status`
and `exc_info` confirmed `Roads segment execution failed for 1 segment(s)`.
`roads.nodb` and `wepp/roads/roads.log` identify `roads-seg-000009::h141`:
overlap 108.376673 m, ratio 1.207921, missing `buffer_length_m`,
`buffer_slope_pct`, `fill_length_m`, and `fill_slope_pct`. Zero profiles executed.
This is a separate blocker from the earlier 60% exclusion.

Read-only commands included `ssh wepp1 hostname`, `wctl docker compose ps`,
container run-path checks, Python JSON readback, and RQ fetch through
`wctl docker compose exec -T rq-worker python -`. Relevant services were running.
No production files or jobs were changed.

Source inspection found `_split_line_to_monotonic_segments` executes before
road-design branching. Existing Step-4 code already constructs strip contributors
and an unaffected remainder, then uses replacement aggregation. The specification
says monotonic geometry is not required for this path but also retains segment
eligibility rules: reconcile this discrepancy at checkpoint.

Future fixture acquisition must retain input hashes, source revision, binary
identity and acquisition time. Use a disposable copy; no production rerun follows
from this evidence. Hillslopes 141 and 42 are proposed acceptance cases, not proof
that the proposed abstraction works.
