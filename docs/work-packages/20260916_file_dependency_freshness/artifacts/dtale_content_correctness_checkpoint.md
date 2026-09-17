# D-Tale content-generation correctness checkpoint

Independent correctness reviewer: `freshness_correctness`, 2026-09-17 UTC.
Reviewed the D-Tale decision artifact and canonical freshness amendment against
the maintained loader, lazy backend, GeoJSON registry, browse bridge and nearest
service instructions. No production/test edits. **Scoped PASS for the revised
canonical checkpoint.** The findings below are resolved in the intended contract;
implementation, performance and UI/runtime acceptance remain required.

## Findings and checkpoint precision

**DT-C01 — Medium, resolved:** lazy page reads can reliably reject drift
against their accepted server-side generation, but stable dataset IDs do not
provide isolated generations for each browser tab. An explicit second launch of
the same run/config/path/filter replaces the shared D-Tale instance. An older tab
requesting that ID then addresses the replacement instance. The existing real
probe already shows a later launch changing the same ID's available schema.

The revised canonical text now states that the no-silent-refresh rule prohibits
automatic refresh inside page/count reads. Explicit relaunch retains its existing
shared-instance reset behavior; other open tabs may need to reopen. No new tab
token, changing dataset IDs, service or protocol is added for this repair.

**DT-C02 — Resolved in revised proposal:** optional overlays must not make an
otherwise valid table unavailable. `_load_geojson` currently treats malformed
JSON/read failures as optional omission. The canonical amendment now preserves
table launch for missing controller/path, parse or read failures and explicitly
removes the affected old registration, choices and defaults. This avoids both
stale overlay reuse and a new mandatory-map availability dependency. Retain
contextual logging; do not leave a broken choice pointing at removed data.

The added query-failure recheck is also correct: source changes can make DuckDB
raise before a successful return. Detectable generation drift must still become
an explicit changed-source response; stable-source parser/query errors retain
their established error contract.

The final source-path precision is required and accepted: a reusable dataset
must match both the digest and resolved target. A permitted same-byte symlink
retarget otherwise leaves a lazy instance reading its former target, so later
changes to the newly selected file escape that instance's checks. Rebuild on
resolved-path change using the existing containment policy; do not change the
stable ID. Retain a regression that edits the new target after such a retarget.

## Accepted behavior and compatibility

- Retained live evidence proves eager CSV stale rows and a lazy Parquet stale
  schema/DuckDB failure after equal-size/restored-time changes. Real isolated
  GeoJSON registration also reuses old labels. Replacing metadata-only tokens
  with the reviewed byte digest directly addresses those failures. Fingerprints
  remain opaque in-process observation strings; no persisted migration is needed.
- Verify before/after table acquisition and lazy schema/sample/count construction,
  then publish only associated state. Initialization rejection must remove the
  target dataset's partial D-Tale global state, lazy instance and metadata. Keep
  unrelated datasets and valid shared overlays intact.
- Lazy instances retain an accepted fingerprint. Guard every filesystem-backed
  page/count observation, including failures, and guard returns of cached counts
  or samples. Reject changed/unreadable source with explicit reopen guidance.
  Loader acquisition uses structured HTTP409; lazy grid errors use upstream's
  HTTP200 envelope with `success=false`, string `error`, and `code=changed_source`,
  without successful rows. The latter is a failed read, not a successful dataset.
  Returning old count/schema alongside current rows is not permitted. A no-data
  endpoint response need not invent a file read merely to exercise a guard.
- Eager data already materialized in memory remains a point-in-time view until
  explicit relaunch. This differs from lazy data, which reopens its file per
  query; the distinction is justified and should remain visible in service docs.
- Preserve initial missing-target 404, file/row limits 413, filter 422, unsupported
  reader 415 and unsupported lazy export 501. Do not replace a stable malformed
  file's existing parser failure with a freshness error. Empty but reader-valid
  sources remain valid; absent optional map state is not table corruption.
- Keep dataset ID/run/config/filter partitioning, identifier aliases, table sort/
  paging semantics, token/access/containment checks and NoDir materialization.
  Do not add request-side thaw cleanup, a full pandas Parquet fallback or an
  upstream endpoint fork. The shared helper follows caller-permitted ordinary
  file paths; it does not grant additional path authority.

## Required direct validation

Exercise actual maintained loader and D-Tale data endpoints with real CSV,
Parquet and GeoJSON parsers. Retain rows and column/schema evidence, not only
fingerprint differences. Cover same-size/restored-time content changes; readable
touch/link/same-byte replacement; source removal/read denial during acquisition
and lazy access; and a mutation that causes a native query error before its
normal return. Verify a stable malformed source still gives its original error.

Cover filtered datasets whose selected rows change, aliases and sort/page output,
cached counts/sample paths, stable IDs across explicit relaunch, and separate
filter IDs. A valid empty dataset, absent/malformed optional GeoJSON and a removed
previous overlay must still reach their contracted table outcome. Verify failed
initialization does not retain old data as current or remove an unrelated dataset.

The browse bridge propagates loader error status and description/error detail.
The revised canonical grid envelope follows QA's installed-upstream evidence
that non-2xx response bodies are dropped. Reviewed
`dtale_ui_contract_probe.cjs` and its JSON result: actual installed Chromium UI,
with the disposable grid response intercepted, displays the HTTP200 envelope's
guidance in its alert and does not display the HTTP409 envelope. The probe
reproduces the proxy prefix mapping and records no browser script errors. This
supports the chosen response contract without a frontend transport patch; it
does not yet establish an implemented backend mutation reaching that UI. Actual
loader and grid error presentation from the implemented service still needs
acceptance at both boundaries.
Do not treat existing tests that skip launch 404 as service-enabled acceptance.

## Performance and acceptance limits

Settled shared-helper checks must meet the existing sub-millisecond per-file
budget and perform zero content rereads. Measure actual launch/page costs too:
the service permits files up to 512 MB, while schema, sample, count and page
guards can call the helper repeatedly during its one-second uncached admission
interval. Interleaving enough datasets can evict observations and restart that
interval. Bounded memory does not imply bounded startup latency.

Retain cold/changed/settled measurements using representative Parquet and GeoJSON
under the service's real identity/mounts, including first-second page cadence and
the actual 60-second browse request timeout. The revised checkpoint correctly
budgets the existing accessor sequence: two checks per row range plus one cached
count check (three for a normal page), with an uncached count using its own pair.
This retains standalone accessor guards without a new reentrant validation
protocol solely to save a cold check. Measure actual bytes/calls and compare
latency to native-query cost plus the corresponding verified-hash costs; retain
admission and eviction results. A tiny CSV or helper-only benchmark is not that
acceptance. No new cache or watcher is authorized by an unmeasured performance
concern.

The before/after protocol is a bounded observation, not arbitrary-writer or
multi-file snapshot isolation. The existing GeoJSON registry is shared by run
and overlay key; this checkpoint must not imply per-tab map snapshots. Full
browser/map behavior after restart, permission/mount parity, representative
performance and archive restoration remain OPEN until directly exercised.
