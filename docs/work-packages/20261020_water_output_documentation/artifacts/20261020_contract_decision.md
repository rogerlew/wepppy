# Water documentation publication decision

Starting revision: WEPPpy `1ecf04735`, native `54d0867`. Authorization: operator requested scaffold and execution after the full documentation audit; session commit authority already granted.

Applicable contracts: Usersum specification (publication amendment below), hillslope-water-aggregation contract and ADR-0099 (unchanged science), output-scope contract (unchanged baseline/Roads isolation), report-cache-freshness contract (unchanged cache markers), contract-first change standard.

Delta: publish two user-role guides under Technical Reference; expose interpretation independently of generated README existence; rename the existing Results README link “Output files, columns, and sample data”; add contextual report help. Describe native WAT/PASS row grain, units, normalization, thresholds and provenance accurately in metadata and generated README. Preserve names, dtypes, numerical results, cache behavior and auth. This is a documentation/UI discoverability intent change plus metadata conformance correction, not new hydrologic behavior. Rationale: schema previews alone cannot explain scientific aggregation.

Security impact low: existing URL helpers and visibility gates; no new endpoint or access privilege. Compatibility: additive docs and descriptive text only. Metadata corrections apply to regenerated files; old artifacts remain historical. No native schema version bump solely for prose.

## Valid states and regression evidence

Absent/never-generated README: interpretation link works and run-specific link stays hidden. Present-empty output: guide remains accessible; generator reports missing files using existing behavior. Populated output: bounded previews and scoped links retained. Supported legacy output: explain unknown model/consumer provenance and old metadata; never certify corrected values from README/schema version alone. Malformed/hostile paths: no new path inputs; existing Usersum/browse guards and prefix-safe URL helpers remain authoritative. Single-storm and continuous results both expose interpretation; Roads links retain their existing output scope. Archived/restored outputs retain ordinary browse behavior and help remains independent of run artifacts. Working/failed/completed simulation state does not determine guide availability.

Evidence: manifest/nav validation; user-role route/search checks against freshly generated catalog; rendered Results and report links with and without README; generated new/legacy README and native Parquet metadata; existing aggregation regression suites. No user-reachable exceptions are added.

Independent reviews and disposition: pending.

## Review disposition

Reviewers A and B identified the stale generated index as a distinct runtime state. The operator has been asked for the explicit index-edit exception required by root AGENTS. Until answered, preserve the dirty index. If approved, retain a byte-for-byte backup and merge only task-affected document/nav entries from a fresh no-vendor-sync build, preserving every unrelated entry; validate a newly loaded catalog and route/search behavior. If not approved, source work may proceed but discovery publication remains explicitly incomplete. Temporary-index tests alone never establish active-runtime publication. Worker catalog caches require restart/reload at deployment; no deployment is included.

Reviewer B requested explicit canonical authority: Usersum AGENTS now names specification.md.

Reviewer A identified that machine-readable unit corrections affect downstream project-unit conversion and column suffixes. This package changes descriptions only, including explicit warnings where legacy machine-unit labels are wrong or absent. The user variable reference states verified physical units. No `units` metadata changes, cache changes, or conversions are authorized here; a follow-up must cover downstream unit-conversion/schema compatibility before changing those machine labels.

Independent reviewer A approved at 2026-10-20 22:29 UTC after re-review; reviewer B independently approved after re-review. Both medium findings are closed for checkpoint acceptance. Both require actual authorized index publication and fresh-catalog normal-user route/nav/search checks before discovery completion. No high/medium contract findings remain. Reviews were read-only and preceded implementation.
