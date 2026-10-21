# Correctness and user-experience review: water output documentation

## Metadata and authority

Independent reviewers: `/root/contract_review_a` (scientific/accounting and native
artifact review), `/root/contract_review_b` (UX/discovery/link review), 2026-10-20 UTC.
Starting implementation `1ecf04735`; reviewed checkpoint `14c7eebb1` precedes
implementation. Canonical authority: Usersum specification, section Water output
interpretation publication; hillslope-water-aggregation contract and ADR-0099
retain numerical authority. Security impact low; existing gates and URL helpers
unchanged, no new endpoints or path inputs.

## User outcome and valid states

Users can read the guide/reference and distinguish local area weighting,
terminal physical runoff and filtered PASS delivery. Source and isolated-runtime
validation pass; the operator authorized the index update and actual catalog publication now
passes normal-user browser/search checks.

| State | Required outcome | Evidence |
| --- | --- | --- |
| README absent | General guide available, run README link hidden | Single-storm/continuous render matrix |
| README present | General guide plus renamed run-specific reference | Same render matrix |
| Empty Parquet | Schema and no-rows preview | Existing bounded-preview tests for 0 rows |
| Populated Parquet | Actual metadata and at most three rows | 6,576-row WAT/PASS native output readback |
| Legacy metadata / missing manifest | Preserve data, identify version as unknown and explain limitations | README regression and historical cache wording |
| Roads resources pending/ready | Guide remains available; scoped report links retain readiness gate | Added Roads render matrix |
| Dirty/stale generated catalog | Do not overwrite unrelated edits; publication incomplete until authorized | Explicit operator authorization, preservation receipt and final publication review |
| Malformed/hostile paths | Existing Usersum and browse guards unchanged | Existing route regression suite; no new path-taking API |

No new user-reachable exceptions are introduced. Missing optional run outputs do
not disable general help. Working/failed/completed and archive/restore behavior
has no new state or persistence logic; the guide remains ordinary Usersum content.
No exhaustive security or production-browser claim is made.

## Generated artifact evidence chain

The source fixtures are copied to scratch and processed by the rebuilt native
writer, then Python facade fields are compared to actual Parquet fields including
metadata. Independent reviewer A repeated this readback in the weppcloud
container, verified hashes and 6,576 rows in each file, and confirmed the retained
README equals generated output. Comparing schema snapshots after removing only
descriptions confirms unchanged names/types/units. See
[generated receipt](generated_artifact_checks.json) and
[generated README](generated_interchange_readme.md).

Fresh catalogs are built from the real manifest and Markdown. Actual Usersum
routes/search run against those isolated catalogs, including browser navigation
under `/weppcloud`. Final browser checks use the published repository catalog through the unmodified
runtime loader; no production deployment is claimed. See [browser evidence](browser_checks.json).

No project persisted-state mutation or new executable model input is involved.
No production deployment, historical report repair, or original run-file rewrite
is claimed.

## Findings and disposition

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| CONTRACT-01 | Medium | Temporary catalog is not runtime publication | Separate publication gate retained; explicit permission requested |
| CONTRACT-02 | Medium | Machine-unit edits can affect export values/names | Description-only changes; physical-unit reference and compatibility follow-up |
| CONTRACT-03 | Medium | Canonical specification not named by nearest AGENTS | Canonical pointer added in checkpoint |
| UX-01 | Medium | Generated README hardcoded production URLs | Portable Help/search instructions; template links retain app prefix |
| UX-02 | Medium | Current-accounting copy could certify historical cache | Explicit current-accounting and historical/unverified qualification |
| UX-03 | Medium | Roads pending state lacked guide link | Unconditional guide plus pending/ready tests |
| DOC-COR-01 | Medium | Default yearly exclusions called simulation years | Corrected to first two available water-year bins, possibly partial |

Both independent reviewers confirmed all implementation findings resolved.
Reviewer A independently verified actual native artifacts. Reviewer B verified
all new guide relative links. No unresolved high/medium source findings.

## Verdict

Source correctness: pass. Authorized catalog publication and actual-catalog
normal-user browser/search validation pass. The inherited PASS
machine-unit labels remain explicitly deferred compatibility work, not repaired
labels. Normal-user isolated browser checks passed after review; live deployed
browser behavior is not asserted.

## Publication sign-off (2026-10-21 UTC)

Reviewer B independently approved actual index publication: all 74 unrelated
entries and ordering preserved, two existing entries updated, two new guides and
only their nav leaves added, affected hashes matching source files, and receipt
hashes matching backup/current artifacts. The operator explicitly authorized this
publication. Real-loader browser checks passed. Broad validation completed with
fixture/environment corrections recorded in validation. No unresolved medium/high
findings remain. Repository publication gate: pass; no production deployment.
