# Correctness and User-Experience Review - Roads WBT flow directions

## Metadata and disposition

Reviewer: `/root/roads_contract_review`, 2026-10-26 UTC. Independent read-only
review of WEPPpy caller, native adapter, native tests/release, generated project
artifacts and publication staleness disclosure. Canonical intent:
`docs/schemas/roads-flow-direction-contract.md`; lifecycle, output scope and water
accounting contracts retain their existing obligations. Checkpoint `3a542d939`
is an ancestor of the working implementation. Contract finding C1 is closed:
the decision now names the actual roads-water-accounting-contract.md.

**PASS for the bounded local implementation and isolated-environment validation.**
No medium/high findings or outstanding scoped validation conditions. The final
broad-suite ledger is independently verified below. This artifact does not approve
production deployment or claim the original project was repaired.

## User outcome and implementation

Roads now passes `wbt=True` to its native tracer. The PyO3 function appends a
keyword-only `wbt=False` argument, converts its loaded native buffer with the
existing Peridot helper only when true, and invokes the unchanged tracer.
Original raster bytes and return schema are preserved. Existing positional and
keyword TOPAZ callers retain the same default behavior. No backend UI, value
inference, rerouting heuristic or hydrologic parameter was introduced.

Fresh-process inspection confirmed the signature and source/binary hashes against
`/workdir/wepppyo3/docs/roads-flow-direction-release-20261026.json`. The consumed
module SHA256 is `5d1f7be2e8176af5d762936b8c5cbe290450c2c2cbe134055d296f8fbd730a34`.
Native tests specify compass neighbors independently of the conversion helper,
including ambiguous codes 1/2/4/8, and check path distance/drop/slope and unchanged
input bytes. Legacy default tests and CLI comparison are retained.

## Valid-state matrix

| State | Expected behavior | Evidence and limit |
| --- | --- | --- |
| Roads absent/never used | Existing behavior; no native call introduced outside execution | Caller remains inside existing non-channel tracing branch; focused controller/route suite |
| No eligible or routable segments | Existing skip/failure/report semantics | No eligibility or lifecycle changes; focused tests; not a new full-site fixture claim |
| Populated WBT raster | Correct D8 neighbor interpretation and full Roads execution | Eight direction tests and fresh isolated clogging-starch run |
| Supported native TOPAZ callers | Same default result and signature compatibility | Original native tests including Peridot CLI comparison; explicit signature readback |
| Invalid/empty direction, true loop or edge | Existing explicit termination label | Native guard tests for 0/5/255, loop, edge and step limit |
| Missing raster, bad seed/shape/limit | Existing explicit exception | Native file, seed and shape tests |
| Four NoData receiving subcatchments | Retain exclusion | Actual-project summary retains exactly 000034, 000035, 000038, 000039 |
| Old native binary with new caller | Unsupported keyword is explicit, no silent TOPAZ fallback | PyO3 signature contract; paired release required; existing caller records trace_execution_failed |

No new security or persistence boundary is introduced. Existing partial-state
retention and current-receipt rules still apply. A missing or malformed source is
an exceptional input failure; a genuinely disconnected trace remains an expected
skip. WBT-only admission is unchanged. This matrix is scoped coverage, not an
exhaustive claim over all terrains or malformed raster files.

## Generated-artifact evidence

Reviewed root: `/wc1/ablation/20261026_roads_wbt_flow_direction/candidate`.
The replay script rebases serialized paths before NoDb hydration and retains
an independent source snapshot. I independently rehashed all **677 protected
baseline files** and **1,868 source-snapshot files** against the inventories;
all match. This verifies retained snapshot/baseline integrity, not continuing
immutability of a live production project after the snapshot was captured.

| Stage | Direct evidence | Result |
| --- | --- | --- |
| Durable input | Isolated Roads settings and WBT rasters copied from the site | Original intent retained; no new backend or design choice |
| Native consumer | Fresh imported module identity, old/default and WBT trace outputs | All five previously failing traces reach channels 204/154 |
| Prepared model input | Read each recovered two-OFE `.slp`; buffer length equals native path length to emitted 0.001 m precision | Pass |
| Model execution | Read profile PASS headers, parsed daily PASS rows and watershed success text | Actual selected 260409 hill/watershed pair completes |
| Report output | Read roads_segment_loss_summary.parquet and recovered profile records | 35 report rows; all five recovered records, 16 years and positive area |
| Lifecycle/publication | Fresh current receipt and expected four skips; historical report explicitly marked stale | Scoped current output available; old numerical results preserved as history |

Independent per-segment readback:

| Segment | Native channel | Emitted buffer length (m) | PASS daily rows | Report modeled area (m2) |
| --- | --- | --- | --- | --- |
| 000001 | 204 | 102.627 | 5,844 | 1,226.56 |
| 000020 | 154 | 103.941 | 5,844 | 722.84 |
| 000021 | 154 | 102.627 | 5,844 | 412.21 |
| 000022 | 154 | 96.971 | 5,844 | 403.54 |
| 000023 | 154 | 97.799 | 5,844 | 396.23 |

Each recovered PASS has unique daily indices and finite runoff volume. These are
legacy ASCII PASS files from the project's selected 260409 executable, not v3;
the reviewer corrected an initially over-specific v3 header assertion before
checking their actual climate/year header and parsed semantics. The issue being
validated is routing representation, independent of PASS schema version.
`validation.json` also retains area/water reconciliation and output hashes.
Nullable report fields are not universally finite; the replay rejects infinities
and separately validates required water values. Do not recast that as a claim
that every cell of every table is finite or that universal hydrologic closure is
proved.

## Tests and publication

Reviewed logs show native **23 passed** on host (including CLI), **22 passed** in
container with only the cargo-dependent CLI comparison deselected there, focused
WEPPpy **108 passed**, and publication/contracts **14 passed**. The CLI case did
run on the host, so this is not an unaccounted native test exclusion. The broad
WEPPpy ledger is complete: 11,947 collected nodes, 11,795 unique passes and 152
test skips, plus one collection-module skip. Independent recomputation verifies
all 20 raw report hashes, collection and covered-node-set hashes, setup/call/
teardown success, zero missing nodes and zero unresolved failures. Both observed
failures have later passing executions: the SWAT fixture passes in an isolated
eight-test module run, and the browser chain passes with the installed browser
cache explicitly available to its child environment (36 resumed tests). Earlier
failures and recovery logs remain retained; no nodes were excluded.

The historical Roads report is explicitly stale for full-project routing, while
its profile results and execution provenance remain intact. The revised
publication test permits only the exact reviewed source drift and notice; it
still verifies original results, report body/render and provenance hashes.
This is an explicit stale declaration, not manufactured fresh provenance.
Source report and Usersum copy share the notice. A full matrix rerun is not
claimed by the repair evidence.

## Highest supported claim and remaining work

Implemented, paired native artifact rebuilt, and locally/environment validated
through a fresh full Roads workflow on an isolated copy. Five affected segments
are recovered; four legitimate NoData exclusions persist. Production deployment,
original-project rerun and browser interaction with that live project remain
outside evidence and authorization. The broad gate is now complete and retained;
all scoped correctness closeout conditions are satisfied.


## Final closeout addendum

Independently checked `broad-coverage-summary.json` against every raw JSONL report
and the collected node inventory; counts and hashes match. The additional
`profile-readback.json` confirms parsed slope geometry and daily PASS/WAT records
for each recovered profile. `segment-query-readback.json` verifies the existing
UI-facing query returns all five as completed, hit_channel, with matching run and
receiving-hillslope identifiers and no profile errors. This is direct query
readback, not a live-browser or production-deployment claim.
