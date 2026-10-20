# Final correctness reviews

Two independent read-only reviewers examined the implementation and repeated
boundary probes. Both closed all high/medium findings on 2026-10-20.

## Source and scientific accounting

Closed: duplicate daily native/OFE rows on all report paths; per-native terminal
cardinality before dashboard mapping; unavailable full PASS sums preventing
numeric Ash correction; missing/zero-area baseline preventing numeric zero;
full model/native mapping and selected subtraction IDs in provenance.
Independent probes covered duplicate/missing terminals, NULL/NaN/inf PASS,
missing baseline dates, zero area and empty supplied hydrology. Final clarification:
invalid baselines may fail reconciliation rather than produce null; neither may
publish a certified numeric correction.

## Compatibility and historical availability

Closed: removal of pre-validation historical deletion; early return for initial
no-results UI; narrow handling of absent archived translator prerequisites;
pickle-only history notices; list/partial JSON proof validation; exact model and
output coverage; source replacement checked using pre-read hashes plus metadata; one shared
WAT digest per explicit parent batch; complete native mapping.
Repeat probes verified swapped mappings, metadata-preserving source replacement,
malformed and partial proofs. Historical watershed/contaminant browser checks
subsequently returned HTTP200 with visible unverified notices.

## Evidence boundaries

The actual Ash integration replay uses a constructed one-hill PASS baseline,
not a routed watershed replay. Contour normalization has source-formula support,
not contour runtime certification. Legacy hashes identify artifacts, not their
producing binary. An isolated six-year model replay fails in evap.for in2025;
five-year daily and hourly replays complete. Native release checks and application
artifacts establish development acceptance only, with no production deployment.

## Late broad-gate provenance correction

An equal-size, restored-mtime rewrite exposed timestamp-granularity ambiguity.
The loader now binds the digest before querying WAT, so replacement cannot attach
new source identity to already loaded values. Review then identified that global
memoization prevented fresh regeneration after indistinguishable metadata drift.
Memoization is now scoped to an explicit Ash batch; standalone loads and new
batches always rehash. Independent real-Parquet collision/retry probes close this
finding with no remaining high/medium issues. The additive private loader keyword
is mirrored in its stub; focused regressions pass 33 tests.
