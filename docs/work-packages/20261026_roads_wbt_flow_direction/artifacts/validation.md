# Validation evidence

Checkpoint: 3a542d939. Native local release SHA256:
5d1f7be2e8176af5d762936b8c5cbe290450c2c2cbe134055d296f8fbd730a34.

Native regression: 23 host Python tests pass including existing Peridot CLI
parity. All eight Whitebox neighbors have independent expected positions.
Container-native 22 tests pass; CLI parity runs on host because the runtime
container does not contain cargo. Cargo test build succeeds (zero Rust unit tests
in this wrapper crate). Retained pre-fix tests fail for absent wbt keyword and
missing caller propagation. Focused WEPPpy 108 and publication 14 pass.

The actual production snapshot was copied read-only via rsync from wepp1 into
/wc1/ablation/20261026_roads_wbt_flow_direction/source, excluding histories/logs,
then independently cloned and path-rebased before controller hydration. Fresh
prepare/run with current caller/native artifact completed 35 segments versus 30:
all five recovered IDs reach expected channels 204/154; only four subcatchment
NoData outlets remain skipped. No selected design, binary or physical input was
changed. The project uses wepp_260409. The full 16-year 2000-2015 workflow and all
required report resources complete; current receipt is valid. Twenty Parquet
artifact hashes/row counts are retained. Report has 35 segment rows.

Independent readback confirms recovered two-OFE slope files contain the traced
buffer lengths rounded to 3 decimals and existing bounded slopes rounded to 6
places. Each recovered profile has 5,844 PASS days and5,844 distinct water days
(11,688 per-OFE water rows). Required scientific water/PASS numeric fields are
finite. Generic Parquet scan rejects infinity, not optional null/NaN metadata;
no blanket all-fields-finite claim. Existing daily area/water reconciliation
passes. Original snapshot and candidate baseline hashes are unchanged.

Historical published matrix results and execution provenance are byte-preserved;
visible stale notice labels old full-project coverage. Exact reviewed source
changes are recorded separately and tests reject unacknowledged drift. This does
not republish or replace the historical 516-profile analysis or four-design comparisons.

Broad suite began with canonical wctl run-pytest tests --maxfail=1, then was
interrupted during expensive Rosetta cases after 405 passes/27 skips. Remaining
collected nodes ran in explicit segments. Final ledger covers all 11,947 nodes:
11,795 unique passes and 152 test skips, plus one collection-module skip.
SWAT fixture setup failed in one split ordering, then all eight module tests
passed in isolation. The browser chain failed with an existing incorrect cache
path, then passed with the installed cache explicitly selected (36-test tail).
The slow rest segment was also split with complete remaining-node accounting.
Every earlier failure has a later passing execution; no missing or unresolved
nodes remain. See broad-coverage-summary.json, retained failures and recoveries. No exclusions
or tolerance changes. Production deployment and original-project recovery remain
outside scope; source-only or locally validated status does not imply rollout.

Fresh controller detail queries also report completed/hit_channel with no profile
error for every recovered segment; see segment-query-readback.json. Native
implementation and paired release are committed at wepppyo3 71ec98a.
