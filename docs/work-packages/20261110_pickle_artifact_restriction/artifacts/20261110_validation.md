# Focused validation receipt

Date: 2026-11-11 UTC. Base `991fc5e2c3`; contract ancestor `aeab3c3e1`;
reviewed archive clarification `e2b9f6b35`. All tests ran through the existing
Compose weppcloud container using wctl. No production changes were made.

## Approved gates

| Command after `wctl` | Result | Receipt |
| --- | --- | --- |
| `run-pytest tests/weppcloud/bootstrap/test_pre_receive.py --maxfail=1` | 27 passed | `green-bootstrap.log` |
| `run-pytest tests/microservices/test_browse_routes.py tests/microservices/test_files_routes.py --maxfail=1` | 130 passed | `green-browse.log` |
| `run-pytest tests/microservices/test_browse_dtale.py tests/microservices/test_dtale_freshness.py --maxfail=1` | 48 passed | `green-dtale.log` |
| `run-stubtest wepppy.webservices.dtale` | Success, 2 modules | `stubtest.log` |
| `check-test-stubs` | All stubs complete | `test-stubs.log` |

Scoped documentation lint passed for the package, three canonical contracts,
Bootstrap specification, and both service READMEs/AGENTS (`docs-lint.log`).
Spelling previews and `git diff --check` were also run.

205 focused tests passed. Full Python and frontend suites intentionally not run
per the operator-approved waiver. Existing deprecation warnings remain.

## Red evidence and corrections

`red-tests.log`: 36 failures before implementation, including eight accepted Git
pushes, reader/forwarder sentinels and preview capability mismatches. Eight
archive cases exposed an obsolete planning assumption instead of the pickle
failure: virtual archive access is retired. Corrected coverage preserves those
errors and tests physical files under NoDir roots. `red-corrected-tests.log`
records 12 intended failures and four preserved archive-retirement controls.

`red-merge.log` reproduced two legacy branch merge bypasses after the initial
patch. `red-merge-expanded.log` records six failures for both parent orders and
already-reachable fast-forwards, with three allowed text controls passing. Final
Bootstrap coverage also retains an unchanged inherited pickle in the receiving
baseline and proves rejected ref/push-log state is unchanged.

The first supported eager control expected NumPy int64; the existing reader
normalizes to pandas nullable Int64. Corrected the expected frame with
`convert_dtypes()`; runtime behavior was unchanged. Initial stubtest reported
nine preexisting declaration mismatches (DatasetMeta fields and response helper
keyword arguments). `stubtest-initial.log` retains them; declarations now match
the existing runtime, with no authentication or execution changes.

## Artifact and source evidence

`test_pickle_legacy_metadata_and_bytes` compares exact delivered bytes and
SHA-256 for dedicated downloads, browse downloads, raw query and Raw header,
for both suffixes/case variants and physical files under NoDir roots. Inert
fixture digest: `c03857fe75800bfa7b6295ee0481e3126b88fb4045ee98c144e6c1b084b6d0bb`.
No pickle payload was deserialized. Listing/metadata remain observable with no
D-Tale links or preview capability; direct preview/representation returns415.

`test_pickle_bridge_rejects_before_downstream_work` proves zero materializer and
HTTP client calls; retired archives preserve409. Direct loader tests reject
before fingerprinting/cache/reader dispatch. Eager CSV/TSV/Feather/Arrow controls
read actual values; existing Parquet tests retain lazy/source-generation proof.

`source-search.log` contains only denial guards, restriction docs and accurate
references. No `read_pickle` or pickle reader registry remains in either service.
Internal migration/process serialization is excluded and not globally certified.

## Claim boundary

Implemented and locally validated. Independent review artifacts cover the final
source. No wepp1 rollout, production identity/mount parity, production smoke or
incident-resolution claim is made. M4 requires separate explicit authorization;
rollback must retain an equivalent restriction.
