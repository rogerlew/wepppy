# C03/C04 bounded raster cache checkpoint

Base: 36744f3b3. Status: independent correctness/security and measured-budget reviews pass; runtime implementation not started.
Authority: owner requested execution of this freshness package, including its
confirmed content-dependency defects and staged checkpoint commits.

## Intended change and applicable authority

The native MOFE and SBS probes reproduce old numerical values after changed
raster bytes with restored metadata. Adopt the new canonical
`docs/schemas/raster-dependency-freshness-contract.md` for verified local GTiff/AAIGrid
dependency observation and cache admission. Existing NoDb persistence/concurrency,
file-dependency freshness, shared digest admission ADR and artifact observability
contracts continue to apply. C03 persisted signature evolution is additive within
existing private fields; legacy signatures miss without migration. No numerical
formula, classification threshold, workflow authority or file access changes.

The initial proposal to hash a flat GetFileList was rejected by real nested VRT,
ZIP external-reference and symlinked Zarr probes. Those findings do not require a recursive framework for these numerical caches:
explicit uncached native execution is sufficient outside the verified local
GTiff/AAIGrid subset. Security also proved eager local WarpedVRT opens can fetch remote
children before reporting them. Driver/auxiliary eligibility must precede
discovery opens; a root suffix is insufficient. Universal GDAL closure is not
supportable:
explicit unverified observations bypass reuse, preserving the original native
operation and its error boundary. No new remote lookup is introduced. C01 and
Geneva publication remain separate, open waves.

## Regression, states and performance

The canonical matrix covers missing, empty, populated, legacy and hostile inputs,
with actual native success/error outcomes. Preserve reusable summaries for valid
unchanged large SBS rasters: removing all caching would add roughly0.49s per
summary. Measure the whole new observation, including authority checks, to avoid
the CLI prototype's omitted-guard mistake. Budgets and retained baseline sources
are specified in the canonical contract. Actual C03 generated management areas
and WEPP input propagation are required, along with source-mutation admission
rejection, read denial, unverified VRT/Zarr/ZIP native compatibility and native reader-version evidence.

Security impact is moderate: native inventory traverses the same accepted source
relationships, without new run-root restrictions or remote fetching. Missing
proof must never enable old-cache access; no source-writing GDAL mode is allowed.
Native errors remain observable. No new persistent artifacts are produced by the
observation helper; existing management outputs retain their archive lifecycle.

## Review disposition

Independent reviews in `raster_cache_correctness_checkpoint.md`,
`raster_cache_security_checkpoint.md` and `raster_consumer_contract_qa.md` pass
the bounded final contract. RC-01/R-S01 pre-open eligibility, RC-02 paired input
validation, RC-03 post-check cache admission/prior-value retention and RC-04
whole-consumer budgets are resolved at design level. All native probes and the
rejected recursive/blanket-budget proposals remain evidence. Commit this reviewed
checkpoint as a standalone ancestor before runtime or test implementation; final
guard-inclusive timings, actual eviction, generated managements and runtime
acceptance remain open.

Pre-open eligibility refinement: independent loopback-only native probes confirm
remote reads through disguised mask/overview VRTs and an internally stored TIFF
OVERVIEW_FILE. Companion preflight, opaque-PAM exclusion, restricted driver open
and pre-GetFileList metadata eligibility are required. Actual plain GTiff and
AAIGrid+.prj controls make no requests. AAIGrid is included for the real large
TOPAZ MOFE source; QA retained complete native/NoDb management measurements and interleaved controls. The canonical whole-consumer and lock budgets now include settled and cold/evicted validation separately; final implementation remeasurement remains mandatory.
