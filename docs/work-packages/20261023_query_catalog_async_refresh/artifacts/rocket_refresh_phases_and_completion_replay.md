# Rocket NFS refresh phases and completion-hint replay

On November 22, 2026, two experiments measured publication work and scheduler confirmation delay separately. The fixture exercised the deployed strict refresh in the existing wepp1 and wepp2 worker containers. The scheduler experiment replayed previously observed production ticks offline.

## Matched project refreshes

The selected slow `wc1:runs` project had 693 indexed entries, including 621 Parquet datasets (589 under `climate`). Its catalog recorded 316 MB of Parquet, with a median file size of 227 kB. Bounded directory listings found 588 files in each of six WEPP run-file classes. The first 4,097 output entries were HBP or DAT files. The two other slow scopes had 36 and 1,111 Parquet datasets, illustrating the limits of using one project shape.

Both synthetic projects had the same directory layout, 102 generated assets and 82 two-row Parquet files. The fixture sampled approximately one in eight assets per folder and extension group, retained selected schema widths, used synthetic integer columns, and grouped deep export paths. One fixture additionally had 1,264 noncatalog files under climate and WEPP runs/output. Catalog asset membership and schemas were identical between arms. Production project data stayed in place.

Four paired blocks ran serially under the normal worker identity on Rocket NFS, with two blocks per host and both orders on each host. The clients kept their normal caches. Each fixture had a successful strict refresh before measurement. Each measured trial issued one full receipt, invoked the installed native scanner and both normal strict verifications, then read the result from the opposite host. Peer checks covered digest, full asset membership, all 82 schemas, acknowledgment of the exact receipt, zero pending receipts and a planned DuckDB sum of 40.

Phase timers measured exclusive wall time. The native scan includes its internal metadata work. The Arrow phase counts Python-visible `pyarrow.parquet.read_schema` calls. Strict inventory covers both required-file walks. Publication times the catalog/status write and digest work. Acknowledgment includes the published attempt and receipt removal. CPU time is for the process. Wait-channel observations sampled the main thread at roughly 100 ms intervals. Per-client mount counters also include unrelated production traffic.

| Measurement, median seconds | Catalog assets only | With 1,264 extra files |
| --- | ---: | ---: |
| Strict refresh | 12.42 | 16.12 |
| Process CPU | 0.63 | 1.42 |
| Receipt creation to publication | 12.50 | 16.09 |
| Native scan | 1.66 | 3.96 |
| Arrow schema reads | 8.76 | 8.57 |
| Two strict inventory walks | 0.29 | 1.08 |
| Remaining entry verification | 0.13 | 0.11 |
| Catalog publication | 0.62 | 0.26 |
| Receipt acknowledgment | 0.33 | 0.13 |

| Paired block | Reader | Assets only (s) | Extra files (s) | Change in strict inventory (s) |
| ---: | --- | ---: | ---: | ---: |
| 1 | wepp1 | 8.24 | 9.03 | +0.60 |
| 2 | wepp2 | 22.31 | 26.63 | +8.75 |
| 3 | wepp2 | 16.61 | 22.63 | +0.72 |
| 4 | wepp1 | 4.67 | 9.62 | +0.98 |

The main thread was in kernel RPC wait in 1,072 of 1,185 samples. Every strict refresh made 321 Arrow schema calls. The full collection and two strict checks account for 246 calls on 82 Parquet files. Canonicalization also rebuilds entries for the 74 climate and one watershed Parquet in this fixture. Native metadata reads are outside the Arrow count. The first warm-up exposed the extra 75 calls when an expected-count assertion failed after successful publication. Measured trials followed verified warm-ups and used observed call counts.

The fixture demonstrates the effect of unrelated files on strict inventory and the cost of repeated footer reads on Rocket. The scaled datasets use simple types and small footers. Background demand and NFS cache state varied, and the production scope contained more unindexed files than the bounded listings captured. These trials cannot predict the wall time of a full-size project or isolate NAS server saturation. For a full refresh, prototype deferring schema reads during canonical path selection until collection reads the final selected paths. Keep both strict checks and test replaced sources and parent-backed paths. Standalone catalog builders still need to return complete entries.

A further mixed-fixture diagnostic on wepp1 timed each schema call by its caller. The peer verified the resulting artifact. This diagnostic was excluded from the paired medians.

| Caller | Arrow opens | Arrow wall time (s) |
| --- | ---: | ---: |
| Canonical path selection | 75 | 0.94 |
| Full collection | 82 | 0.49 |
| First strict verification | 82 | 0.46 |
| Second strict verification | 82 | 1.43 |

## Replaying the same eight scheduler ticks

The zero-hint control reproduced the complete ordered cursor at all eight checkpoints from 16:41:03 to 16:45:03 UTC. Eleven successful refresh jobs joined to distinct pending locators by exact path. On wepp2, each retained publication attempt matched the job's incarnation, completion interval, acknowledged receipt IDs and catalog digest. Every scope had drained its receipts. All eleven locators still appeared on the production cursor at 16:53:35 UTC, 530–707 seconds after publication (median 629 s). The actual eventual confirmation times are right-censored.

Each replay tick had 25 visits. The simulation first spent up to the indicated number on eligible hints in RQ completion order, then spent the rest on FIFO. A hint became eligible only after the recorded job finished. The simulation used the recorded exit tick as the first known clearance time for other locators. It carried displaced FIFO work into subsequent ticks. The worker arrivals, publication times, completion times and permit budget were fixed.

| Maximum hints per tick | Hinted publications visited | Other cursor exits | Total exits in 200 visits | Original head locators still awaiting a visit |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 14 | 14 | 0 |
| 1 | 7 | 12 | 19 | 7 |
| 2 | 11 | 12 | 23 | 11 |
| 4 | 11 | 12 | 23 | 11 |

With two slots, publication to the **start of the modeled confirmation tick** was 14.2–27.9 s (median 20.6 s). Across eight ticks, 46 original head visits moved to a later tick or beyond the window. All ten real in-window refresh enqueues mapped to head paths that still received visits in their original tick. In an independent wepp1 read, checking the locator, identity, writable state and empty receipt set twice took 0.080–0.508 s per scope (median 0.139 s). The replay omits time spent on earlier visits in a tick, Redis bookkeeping, concurrent new receipts and signal-delivery overhead. Historical receipt creation times for the acknowledged requests were unavailable. The replay holds production publication times fixed by design.

A completion signal can schedule a check. The production scheduler must still validate scope identity and pending receipts and preserve its producer-race recheck before retiring a locator. This replay supports a bounded trial of two hints per tick with fallback to FIFO. A trial should measure confirmation delay, ordinary arrivals, displaced FIFO admissions and oldest unresolved receipt age. The replay establishes neither a fleet-optimal hint count nor a 24-hour capacity pass.

## Evidence

Scripts, private job bindings and raw captures are retained under `/home/workdir/query-catalog-studies/phase-replay-b5B3SCsc`. The isolated NFS fixtures are under `/wc1/query-catalog-validation/phase-replay-b5B3SCsc`. The replay input and event ordering are described in the [visit experiment](../tracker.md#november-22-reconciliation-visit-experiment).

| Capture | SHA-256 |
| --- | --- |
| phases.jsonl | `ce21e789c1d67bf8ac3f8d305f67484019fed2e06f135051f2dca27875f79058` |
| eligible.json | `b653ec4dc7f4e2443797b89f05def3f8c8f6a01af8ab90a11caa7f806795e9eb` |
| replay.json | `fae346d241d6c9c06d5d82927127a3532eed558a25193ab529ceb44b613f5c9f` |
| hint-cost.json | `367e92f4f3550e9bee45c4c4ed9269f580096937fb82f9dbe10e65b0b7086a19` |
| split.json | `78ed9a395a73e6babdb2c788a9ae64cd815a989f2460a2d556e62314b18a8417` |
