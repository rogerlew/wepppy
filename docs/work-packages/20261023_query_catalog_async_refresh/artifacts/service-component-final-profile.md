# Final-membership catalog component profile

Date: 2026-10-27 UTC. Bounded read-only component measurements; no fleet-capacity or ordinary-job-delay guarantee.

## Design

The final classifier contains 30,891 scopes: 18,514 writable and 12,377 READONLY, with no unwritable scopes or recorded classification errors. Freeze the 12 smallest SHA256 path digests among writable, non-READONLY scopes in each namespace (48 total). This is deterministic digest selection, not workload weighting or stratification by catalog presence/owner size. Reuse 26 completed exploratory measurements whose digests remain selected; retain six other completed exploratory measurements outside this final population separately. Run the remaining 22 final selections serially with a 300-second whole-child limit and 1,800-second overall follow-up bound. All earlier attempts remain retained.

The exact read-only call chain, identity, native inspection and Python audit-hook protection are documented in [the exploratory report](service-component-profile.md). Follow-up uses the same UID 1002/GID 130 and existing wepp1 batch container/mounts; there are no project writes, guards, publication, live queue jobs or service changes. New phase events include elapsed process timestamps; component timers exclude imports. Source hashes match across all 48 reused and new samples.

The 60-second exploratory limit was a diagnostic bound, not a production timeout or a failure finding. Its final 2.138-second deadline-exhausted child is not evidence of a slow component. Longer-bound results supersede censoring for matching digests without deleting the original observations.

## Coverage and interpretation

Strict `refresh_catalog` calls collection once and verification twice, with the second verification inside the lifecycle guard. Each measured pass here calls collection once and verification only once. Thus `component_seconds` is not the complete read-only part of a strict refresh. A formula such as measured collection + 2 × measured verification is only a conditional cost model; it does not measure the second guarded verification, lock delay, or publication, and cache/source state can differ. Separate collection and verification timings are retained.

Read-only catalog-presence metadata finds existing catalogs in 6/12 primary, 12/12 batch, 1/12 culvert and 0/12 legacy samples. The selected set lacks missing-catalog batch and existing-catalog legacy strata. Both measured passes explicitly request a full rebuild in memory, regardless of catalog presence; this does not estimate the cheaper unchanged-catalog path.

These measurements exclude guard waiting, durable publication, intent receipts, RQ orchestration and queue delay. They do not measure whole-job service. Samples have heterogeneous assets and may share owners. Earlier runs overlap inventory/classification traffic, subsequent runs inherit filesystem cache effects, and pass 1 is not a guaranteed cold-cache measurement. This is read-only performance evidence from real sources, not an isolated benchmark or a no-load fleet forecast.

## Retained evidence

- `service-component-final-membership.json`: final classified population and digest membership/reuse counts.
- `service-component-final-probe.py` / `service-component-final-controller.py`: exact follow-up harnesses.
- `service-component-final.json`: sanitized measurements with reused and new records.
- `service-component-final-metadata.py` / `.json`: digest-only catalog-presence readback.
- `service-component-final-progress.jsonl`: follow-up progress; original attempts remain in `service-component-exploratory.json`.

## Final bounded results

All 48 final selections were attempted: 26 measurements reused and 22 follow-ups. Follow-up elapsed 1,450.084 seconds, within the 1,800-second bound. Collection completed for all 48 first passes; 47 first verifications completed, and 46 samples completed both full passes. Two children reached the 300-second process bound; no schema/application error result was emitted. All five earlier full 60-second censors completed under the larger bound. The earlier deadline-exhausted batch child now has a completed first pass; its second verification is the batch censor described below.

All completed timing values are finite and nonnegative. All 48 start markers report the same source hashes; all 46 completed pairs have equal entry digests. No blocked mutation attempt was recorded. Cleanup readback confirms no owned probe/controller processes remain.

Each table cell shows the mean of completed measurements and its count. Counts differ where verification was censored: **do not add means across unequal cohorts**. Completed-component means exclude unresolved verification and are not fleet-service estimates.

| Namespace | First collection mean seconds (n) | First verification mean seconds (n) | First collection + one verification mean seconds (n) | Observed first collection entry range |
| --- | --- | --- | --- | --- |
| wc1:runs | 28.866 (12) | 5.906 (11) | 14.078 (11) | 10–1463 |
| wc1:batch | 35.817 (12) | 22.722 (12) | 58.539 (12) | 21–378 |
| wc1:culverts | 3.974 (12) | 0.386 (12) | 4.360 (12) | 12–50 |
| legacy:runs | 6.251 (12) | 1.951 (12) | 8.202 (12) | 10–104 |

| Namespace | First completed component min–max seconds | Second completed component mean seconds (n) | Second completed component min–max seconds |
| --- | --- | --- | --- |
| wc1:runs | 0.268–145.072 | 1.793 (11) | 0.031–18.262 |
| wc1:batch | 1.061–277.591 | 9.602 (11) | 0.178–30.135 |
| wc1:culverts | 0.538–10.048 | 0.667 (12) | 0.050–2.450 |
| legacy:runs | 0.648–43.573 | 1.201 (12) | 0.043–4.330 |

## Remaining censoring and disposition

- Batch digest `01830c72f105…`: first collection 165.079 s and verification 112.512 s completed (277.591 s combined, 260 entries). Second collection completed in 16.210 s; second verification entered at process elapsed 298.577 s before the 300-second process limit. First-pass evidence is complete; its repeat verification is censored.
- Primary digest `00aa3deaaebc…`: first collection completed in 256.494 s with 1,463 entries; first verification entered at process elapsed 261.631 s and remained unfinished at the 300-second process limit. No complete first component total or second pass is available.

The source hashes and exact phase-entry timestamps remain in the aggregate. Process timeout includes imports and prior phases; 300 seconds is not an observed component duration or the production job timeout. Neither timeout establishes a corrupt schema or production failure. No additional experiments beyond the authorized bounds were started.

Final sample-membership reconciliation and bounded measurement are complete. This reduces uncertainty substantially and exposes a heterogeneous tail; it does not close full-job service, shared-batch capacity, queue-delay, or fleet-enablement gates. The incomplete first verification prevents treating the primary completed-component mean as a complete sample mean. Further capacity arithmetic must preserve that censoring and the strict-refresh two-verification call count.

`service-component-final-summary.json` is generated by `service-component-final-summarize.py`; it includes separate collection, verification and component counts/ranges. `service-component-final-cleanup.json` retains the empty owned-process readback. Private project paths and raw native output remain outside the repository.
