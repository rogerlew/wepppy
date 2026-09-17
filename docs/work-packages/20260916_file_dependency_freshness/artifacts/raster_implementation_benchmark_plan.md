# Actual raster implementation benchmark adaptation

Status: preparation only; **no timing run until the parent explicitly clears
the test window and the security-sensitive helper is stable**. Runtime/test
files remain read-only. Preserve all existing baseline scripts/JSON/logs.

## Actual code boundary

Current C03 `Landuse.build_managements` calls its real joint signature method
before and after pair-count selection; that delegates to
`raster_freshness.raster_dependency_signatures` and includes MOFE structure.
C04 `_summarize_sbs_raster` calls the real single-source helper before and after
the cached call; a numerical miss also checks inside the eight-entry cached
function before admission. Thus C04 currently has two observations on hits and
three on misses. The old `observe_under_lock`/`observed_summary` compositions
must not wrap these consumers: that would double-count new validation and
would still not prove the final authority checks were measured correctly.

The retained native baselines remain historical observations of old code.
Running their scripts against the changed working tree cannot be labeled an
old-code baseline and would overwrite useful evidence. New filenames must
identify the actual implementation and retain before/after module hashes.

## Adaptation

- Reuse the retained uniquely named disposable WBT/TOPAZ owner clones and SBS
  files, or make new unique copies beneath `/wc1/batch`. Capture selected source
  and companion bytes/versions/modes before and after; no operation writes to
  named runs. Keep manifests and failed attempts browsable.
- Invoke actual SBS wrappers and real `build_managements` with existing NoDb
  acquisition, persistence, catalog and Parquet publication. Transparent wrappers
  may count/time native calls, the actual signature method/helper, and real
  `locked()` occupancy; they must return the original operation's result and
  preserve exceptions. Hash-byte instrumentation wraps the ordinary digest's
  actual reads, not a replacement hash. Distinguish native metadata/pixel I/O
  from full payload hashes.
- Keep source shapes/sizes and native row/value controls identical to the
  baseline. Warm owner imports/catalog hydration outside steady measurements,
  but retain an initial legacy-signature admission measurement separately.
- For paired same-owner controls, retain the exact old `build_managements` and
  old signature methods from checkpoint ancestor `ceb715c08`; record revision
  and source hashes. Execute only those retained method definitions against
  the existing class/owner within a scoped restoration context, not a duplicate
  imported NoDb class. Prime each version's own signature outside its timed
  hit, because alternating legacy/current formats otherwise manufactures
  numerical misses. Label these historical controls explicitly. Actual
  implementation measurements always call the real new helper and all guards.
- Measure actual native SBS directly as the miss baseline. Compare actual
  wrapper summaries exactly; record numerical-cache calls and observation
  counts, including the extra miss admission check.
- Record settled hit, settled forced numerical miss, helper-cold/admission hit
  and miss, and actual shared-cache eviction. Helper-cold means local cache
  clearing with warm filesystem pages, never cold storage. Settled preparation
  allows the existing one-second admission interval and a subsequent admission
  call; do not monkeypatch the clock for timing.
- Produce **512 distinct pressure files**, observe them, allow admission, and
  read them again so the actual ordinary digest LRU fills with pressure entries.
  Verify `cache_info()` bounds and that target access rehashes. A 600-file
  sequential scan can continually evict the observation timestamps before
  digest admission, so do not confuse that pattern with filling both LRUs.
  Keep pressure setup outside timed target operations. Numerical cache entries
  remain intact during digest eviction; unchanged source bytes must still hit.
- Use interleaved controls and retain per-repeat values, rather than subtracting
  native time from a separately hydrated owner's first operation. Record both
  whole elapsed time and acquisition/body/persist-unlock components. Include
  final directory scans, driver/configuration eligibility, access/coherence
  checks and any approved race remedy inside timing.
- Compare management dictionaries and Parquet row types/values to retained
  baseline, output/owner modes, and source hashes. Final generated `.man`
  propagation stays a separate required correctness/runtime acceptance unless
  the parent supplies that normal preparation path for this benchmark.

## Gates and stopping rule

Apply the ratified targets in
[raster_consumer_contract_qa.md](raster_consumer_contract_qa.md): C04 hit ≤25 ms,
miss-added ≤50 ms; C03 complete validation ≤75 ms settled/≤400 ms cold-evicted,
whole-operation and lock-added ≤100/450 ms. Settled ordinary payload hashes
must be zero on these representative working sets. Admission/eviction must not
wrongly force unchanged numerical recomputation.

If the final security policy marks a representative previously eligible layout
unverified, record actual native fallback and the lost reuse cost explicitly;
do not skip the case or change expected call counts to manufacture a pass.
If timings miss, retain the failure and profile the exact actual guard/helper
cost before proposing code changes or an explicit contract amendment. The
baseline's source copies are filesystem-warm local evidence, not production
tail-latency or concurrent-writer isolation claims.
