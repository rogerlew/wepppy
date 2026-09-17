# D-Tale content generation implementation security review

Independent reviewer: `freshness_security`, 2026-09-17 UTC. Reviewed the working
implementation after checkpoint `fbac92404`, the accepted D-Tale contract,
correctness findings, native-reader tests and retained performance evidence.
Only disposable probes and review artifacts were written by this reviewer.

## Findings and disposition

**Scoped PASS after the verified corrections below.** No unresolved medium/high
security finding remains in this bounded D-Tale change. This is not deployment
or package closeout approval; remaining runtime gates are stated below.

- **DT-S01, Medium, closed:** optional map read denial/removal previously left
  accepted GeoJSON and references active. `_remove_geojson_asset` now removes
  the affected key from `REGISTERED_GEOJSON`, upstream `CUSTOM_GEOJSON`,
  `MAP_CHOICES` and `MAP_DEFAULTS`. An independent real chmod denial and absent
  controller probe verifies affected references disappear while unrelated
  records remain. The corrected default selection preserves a remaining valid
  overlay. Original baseline and initial review evidence remain retained.
- **DT-I03, Low, closed:** an exception after third-party eager registration
  published its frame left partial state without `DATASETS` metadata. The
  independent CSV/Parquet fault probe reproduced this for CSV. The narrow
  `_initialize_dtale_dataset` exception boundary now logs the dataset ID,
  discards only that dataset and re-raises the original error. The after-probe
  verifies both formats leave no frame, metadata or lazy registration; the
  original HTTP 500 remains. The deliberate boundary has allowlist entry
  `BEA-20260917-DTALE-0001`.
- **DT-S02, Low, closed:** retargeting an allowed local alias to a symlink loop
  raised Python 3.12's resolution `RuntimeError`, giving the grid a hidden
  HTTP 500. `_resolve_source_path` now translates only errors around
  `Path.resolve`; the after-probe verifies the original cause is retained and
  the actual grid returns the visible `changed_source` envelope without rows.
  Unrelated native runtime/query errors are not blanket-translated.
- **DT-I01/DT-I02, closed:** correctness review identified stale feature-ID
  references and lost surviving defaults during optional map replacement.
  Reviewed the corrections that replace matching-key choices across referencing
  datasets and retain unrelated selections. Independent revision2 cleanup
  evidence also exercises the restored default.

## Independent evidence

The retained probes use actual local CSV/Parquet/GeoJSON files, maintained
loaders and real native readers in the canonical test container. Read-denial
cases assert a non-root identity and obtain actual `PermissionError`, rather
than replacing the digest with a mocked exception. Named projects and live
service state were not mutated by these probes.

| Evidence | Observation |
| --- | --- |
| `dtale_implementation_security_probe.py/.log` | 5 passed: actual read denial on cached count/sample/page, filtered native count failure after schema drift, scoped optional cleanup, absent controllers, config fallback selection changing to an equal-byte preferred root source. |
| `dtale_implementation_security_probe_revision2.py/.log` | 5 passed after the default-selection correction; surviving optional default is required. |
| `dtale_partial_registration_security_probe.py/.log` | 2 characterization cases retain the original CSV partial-publication failure and Parquet cleanup behavior. |
| `dtale_partial_registration_security_after_probe.py/.log` | 2 passed: both formats clean partial publication and preserve the original failure. |
| `dtale_alias_resolution_security_probe.py/.log` | 1 characterization case retains the original local-alias-loop HTTP 500. |
| `dtale_alias_resolution_security_after_probe.py/.log` | 1 passed: translated cause and HTTP 200 failure envelope, no successful row result. |

The native count probe changes the actual Parquet schema before the maintained
filtered DuckDB query executes. Its `BinderException` is followed by a generation
check and becomes `changed_source`; no row count is cached. The stable-source
control still raises the native binder error. Real permission loss after count
and sample caching blocks those cached accessors and pages. The actual loader
returns HTTP 409 with the structured error and matching description; the grid
returns HTTP 200 with `success=false`, string guidance and `code=changed_source`.

Maintainer evidence reviewed: `dtale_affected_tests_revision2.log` records
**22 passed** with the initial browse redirect/fallback fixture issues corrected,
and `dtale_stubtest.log` passes. Earlier failed and skipped logs remain retained;
they are not substituted for runtime acceptance.

## Integrity, authority and compatibility

`_fingerprint` uses the shared verified digest helper after existing target and
token checks. Reuse requires equal bytes plus the same logical and selected
resolved source paths. This prevents an equal-byte alias retarget or newly
preferred root source from leaving lazy reads attached to the older selection.
Timestamp-only changes preserve reuse. Hashes do not authorize any path.

Lazy instances bind schema, sample and counts to an accepted source generation.
Before/after checks surround native reads, including their failure paths;
cached counts/samples validate before return. Count caching occurs only after
the post-read observation succeeds. Eager acquisition verifies before publishing
its in-memory frame; an accepted eager frame remains a point-in-time view until
relaunch. Dataset IDs and filter partitions are unchanged, and relaunch
revalidates filters rather than silently dropping invalid predicates.

Optional map errors preserve table availability and remove only affected map
state. Bounded DuckDB/PyArrow page reads, one-row initialization, non-lazy
delegation, file/row limits, initial missing-file behavior, unsupported types and
unsupported lazy export remain intact. Browse authorization, internal token,
existing NoDir/path resolution and external read capability are unchanged. The
review probes do not independently certify all authorization permutations.

## Performance and remaining acceptance

The reviewed large-file evidence uses a read-only 81,150,978-byte Parquet with
3,646,034 rows under UID 1000/GID 993. A normal page performs one cached-count
check and two page checks: cold 0.859 seconds and 243,452,934 hash bytes; after
actual 512-path eviction 0.886 seconds and the same three hashes. Settled pages
average 55–57 ms with zero hash bytes. First uncached count has two checks; a
normal page with that count can require four. These fit the accepted measured
budget for this representative file. No OS page-cache flush or maximum-size
workload claim is made.

Actual browser/backend behavior after restart, browse/filter/map workflows with
production-equivalent identity and mounts, representative map cost and archive
restoration remain package acceptance gates. Prior Chromium response interception
proves error-envelope presentation, not the complete changed-source workflow.
Before/after observations are not arbitrary-writer isolation, a table/map
transaction or a per-browser snapshot protocol; explicit relaunch can replace
the shared stable dataset ID used by other tabs.

Reviewed code SHA-256: `dtale.py`
`a5c150af6a57a40fa6a773b685cad7b0aec1fc518051998157d270c210851ea7`;
`dtale.pyi`
`8e10e5cd37e03fb95f9e5b7145ea4856a13341f6d6eabedb93a701411ca372cc`.
