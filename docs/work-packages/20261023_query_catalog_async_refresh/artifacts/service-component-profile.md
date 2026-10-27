# Read-only catalog component profile

Date: 2026-10-27 UTC. Exploratory incomplete-classification sample; fleet capacity remains unproven.

## Scope and safety

The bounded probe calls only `_updated_catalog(base, None, [None], prefer_canonical=True)` followed by `_verify_required(base, catalog, [None])`, twice per sample. Inspection of the selected call chain found catalog collection, traversal, stat and schema reads, and in-memory normalization; it does not enter publication, receipt acknowledgement, scope creation, lifecycle guards, or NoDb hydration. The native catalog scanner was inspected separately for read-only behavior. A Python audit hook rejects filesystem mutation after imports; this is additional protection, not a sandbox for native code.

Execution uses the existing wepp1 batch container as UID 1002/GID 130, unchanged production modules and mounts. Scratch harness/output files stay in private `/tmp`; no real project files are deliberately mutated. Reads can affect filesystem caches and normal access-time accounting. Raw paths and native diagnostic output remain private. Repository evidence contains namespace, digest, timings, counts and source hashes only.

## Sampling and bounds

The controller freezes the classifier's then-current digest-selected sample: up to 12 smallest path SHA256 digests among classified writable, non-READONLY scopes per namespace. At freeze, 17,430 scopes had been classified and 30,734 discovered; discovery and classification were incomplete. Parent subsequently reports a final discovery denominator of 30,891. This is not a final representative fleet sample or a random independent sample.

Samples run serially in round-robin namespace order, with a 60-second whole-child timeout and 720-second overall controller bound. A child preloads dependencies before emitting its start event and before measuring components. Safe phase-entry events distinguish collection from verification for a timeout after preload; a timeout without events cannot be assigned to either component. The final child may have less than 60 seconds remaining. Censored process duration must not be substituted for component service time.

## Interpretation

Strict `refresh_catalog` calls collection once and verification twice, with the second verification inside the lifecycle guard. Each measured pass here calls collection once and verification only once. Thus `component_seconds` is not the complete read-only part of a strict refresh. A formula such as measured collection + 2 × measured verification is only a conditional cost model; it does not measure the second guarded verification, lock delay, or publication, and cache/source state can differ. Separate collection and verification timings are retained.

Successful timings measure collection plus required-inventory/schema verification only. They exclude process preload, guard waiting, queue delay, receipts, durable publication, and the rest of a real refresh job. Repeated pass 2 is cache-influenced; pass 1 is not a guaranteed cold-cache measurement. Concurrent read-only inventory, classification and profiling traffic also affects observed cost. Live source changes may legitimately cause verification conflicts.

Success-only summaries exclude censored samples and cannot be multiplied by fleet counts as an unbiased work forecast. No tail percentile, whole-job mean, spare-worker estimate, backlog acceptance, or fleet-enablement approval follows. The earlier real eight-scope/two-worker canary remains separate whole-job evidence.

## Evidence

- `service-component-probe.py` and `service-component-controller.py`: exact retained harnesses.
- `service-component-exploratory.json`: sanitized aggregate with paired timings, entry counts, entry digests, source hashes, phase markers and timeout records.
- `service-component-progress.jsonl`: bounded controller progress.

## Bounded results

Controller stopped at 720.016 seconds: 38 of 48 selected samples attempted, 32 completed both passes, five hit the full process timeout, and one final child exhausted the remaining 2.138-second budget before emitting its start event. Ten samples were not attempted. There were no explicit component error results and no recorded blocked mutation attempts. All 37 children reaching the start marker reported identical source hashes. These are bounded diagnostic outcomes, not a passing fleet capacity gate.

| Namespace | Attempted / complete | Censored | Successful entries | Pass 1 seconds: min / mean / max | Pass 2 seconds: min / mean / max |
| --- | --- | --- | --- | --- | --- |
| wc1:runs | 10 / 9 | 1 | 11–34 | 0.511 / 1.058 / 2.179 | 0.034 / 0.159 / 0.381 |
| wc1:batch | 10 / 6 | 4 | 21–135 | 1.061 / 7.473 / 13.509 | 0.178 / 0.835 / 1.472 |
| wc1:culverts | 9 / 9 | 0 | 12–50 | 0.538 / 4.891 / 10.048 | 0.050 / 0.751 / 2.450 |
| legacy:runs | 9 / 8 | 1 | 15–182 | 0.742 / 14.015 / 29.990 | 0.060 / 2.837 / 10.090 |

Four full-timeout children were in first collection (three batch, one primary run). One legacy child entered first verification after a measured 21.769-second collection producing 40 entries. Phase entry is retained; exact phase elapsed at termination is not measured. The last batch child has no start marker and is separately censored by the overall deadline.

The final process readback found no owned probe/controller processes. Classification was still incomplete at 27,039 / 30,891; final digest-sample membership reconciliation remains outstanding. Retained measurements can be reused when their digests remain selected; this report does not initiate additional profiling.

`service-component-summary.json` contains the table values; `service-component-cleanup.json` retains process cleanup and sanitized classification readback. No routing, queue, service, production configuration or runtime source change was made.


## Final-membership follow-up

The later [final-membership profile](service-component-final-profile.md) reconciles completed classification, reuses matching measurements and extends only missing/censored final samples under separately authorized bounds. The exploratory counts above remain a historical checkpoint; they are not the final coverage result.
