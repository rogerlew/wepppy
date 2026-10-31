# NFMS-01 successful-path cost observations

Baseline captured 2026-10-31 UTC before base implementation edits, ancestor
`2b998e08d`. Command:

    wctl run-pytest docs/work-packages/20261030_nodb_failed_mutation_state/artifacts/performance_probe.py -q -s

Actual Soils/Wepp controllers created with `canada-wbt-mofe.cfg`; real serializer,
atomic files, validation and logging. Redis lock stub and disabled Redis payload
cache isolate local overhead; Wepp.clean is disabled solely to avoid unrelated
climate-dependent initialization. Five warmups, 40 measured locked updates per
controller. Separate 100,000 direct field reads. This is a small default-controller
measurement, not a production latency benchmark or populated-project cost claim.

| Controller | Serialized bytes | Median locked update ms | p90 ms | 100k field reads ms |
| --- | --- | --- | --- | --- |
| Soils baseline | 1054 | 3.473 | 3.700 | 8.164 |
| Wepp baseline | 2224 | 20.218 | 21.346 | 8.609 |

Run: one passed, four warnings, 10.87 seconds, exited zero. Warnings are existing
deprecations/marks from importing the test utility outside tests/conftest.py.
Candidate comparison follows below. No successful-path serialization/deep-copy/reload
solely for recovery is planned; quarantine guarding may add field-access cost.

## Candidate observation

Same probe and runtime, 2026-10-31 UTC, candidate working tree after checkpoint:

| Controller | Serialized bytes | Median locked update ms | p90 ms | 100k field reads ms |
| --- | --- | --- | --- | --- |
| Soils candidate | 1054 | 3.803 | 4.391 | 63.180 |
| Wepp candidate | 2224 | 22.633 | 24.164 | 58.664 |

One passed, four warnings, 12.51 seconds. Median locked-update differences were
+0.330 ms (9.5%) and +2.415 ms (11.9%); broad suites were running concurrently,
so these are observations rather than isolated causal estimates. Read fencing
adds roughly 0.50–0.55 microseconds per attribute access in this probe. It is
needed to make already-held references refuse unsafe state after failed recovery;
cache-only invalidation cannot enforce that guarantee. Healthy updates do not
serialize, deep-copy or reload solely for recovery. Option map helpers copy only
their small option object when preparing maps.

This guard cost is a known tradeoff. No new disk schema/serialized bytes, dependency,
service or background work was added. Large project/native execution timing is
not measured here; no zero-cost or production-throughput claim is made. Repeated
real-controller failures separately retain logger/listener/handler identities
and bounded descriptors in `test_failed_mutation_consumers.py`.

## Final-source repeat

After final ownership/recovery reservation fixes and after stopping the outdated
broad-suite processes, the same probe passed again (one test). Soils: 3.757 ms
median, 3.958 ms p90, 61.688 ms/100k reads, 1054 serialized bytes. Wepp: 23.195 ms
median, 24.577 ms p90, 59.172 ms/100k reads, 2224 bytes. Relative to the original
baseline, median locked updates are +8.2% and +14.7%; read overhead remains about
0.5 microseconds each. Retain both candidate samples rather than selecting the
smaller delta. These small-controller observations bound this local evidence only.
