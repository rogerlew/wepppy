# Derived input correctness checkpoint

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Reviewed the
revised `derived_input_contract_decision.md`, canonical NoDb contract's Derived
input byte verification section, `_derived_build.py`, both Climate/RAP callers,
existing contention/publication tests, actual-finalizer baseline and owned
native raster reader. Starting implementation revision: `984023c18`, with prior
reviewed waves in the working tree. No implementation edits made by this reviewer.

**Verdict: PASS for the revised main-path-only checkpoint.** The original flat
GDAL-list proposal was insufficient; its retained finding remains an OPEN
dependency-closure defect and package blocker, explicitly excluded from this
bounded implementation. This is not approval to close C01 in full.

## Findings against the superseded proposal

| ID | Severity | Evidence and disposition |
| --- | --- | --- |
| DERIVED-C01 | High | A single `GDALDataset.GetFileList()` is not transitive. `derived_gdal_closure_probe.py/.json` constructs valid projected `outer.vrt -> inner.vrt -> base.tif` inputs. GDAL 3.10.3 lists only outer and inner. Equal-size/restored-time base mutation leaves every listed file's bytes and metadata unchanged, but the actual native median changes from 3.0 to 7.0. The original proposal could publish obsolete numerical results. OPEN in the separate closure wave; fixed scope language no longer claims this is covered. |
| DERIVED-C02 | Medium | Rejecting all nonlocal/VSI names would introduce a new reader restriction. Current acquisition materializes local GeoTIFFs, but that does not establish that every valid existing raster is a plain local file. The security review's local ZIP/VSI case and this review's real `/vsimem` VRT read disprove that assumption. Revised checkpoint removes the new restriction and GDAL discovery entirely. No such rejection is authorized by this wave. |
| DERIVED-C03 | Medium acceptance risk | A 26.4 MB single-file benchmark does not bound a multi-year RAP set. Adding full hashes inside `_check_inputs` lengthens the held NoDb finalization lock. Revised checkpoint explicitly requires complete-set hash and lock-duration evidence, with a 10-second hash-work shipping budget. Performance remains unverified; this is a measurement gate, not permission to weaken verification or silently raise the budget. |

The retained nested-VRT probe executes the owned
`identify_median_single_raster_key`, not only GDAL metadata inspection. Its
fixtures live in a disposable temporary directory. Native raster code reads
band values, geotransform, projection and NoData; external masks are not used
by its current `Raster.read/read_band` methods. A future closure design must
cover consumed metadata and recursive/virtual dependencies with native evidence,
without claiming every auxiliary file can be treated as an independently
openable raster. Shared sources also require deduplication and cycle handling.

## Revised bounded behavior

The retained baseline exercises real PRISM and RAP finalizers with injected
numerical collection. Both currently publish after main-file bytes change with
size and mtime restored. Adding an uncached digest to the existing resolved
path/mtime/size tuple directly fixes that demonstrated comparison defect.

Keep the resolved main path in the position consumed by the numerical callers;
preserve all existing controller, years, bands, watershed and manager provenance.
No persisted tuple migration is needed: these signatures are local to one build.
Do not modify `_identity`, rollback ownership, publication, unrelated-field
preservation, durable hydration, lock ownership or stale-write behavior.

One descriptor must supply the bytes and checked metadata. Bound reads by the
captured size plus one byte and reject observed byte-count, descriptor or path
drift explicitly. Required absence and read errors must not produce an empty or
reusable signature. Empty files remain hashable; validation belongs to the
existing numerical consumer. Do not cache transaction hashes or add a metadata
admission interval to this build-only path.

The returned transaction signature retains mtime, so a touch during collection
may still supersede a build. Device/inode/ctime may guard an individual read but
must not become new persisted transaction comparisons: identical readable bytes
with the same original path/size/mtime should not newly conflict solely because
of hard-link creation or replacement outside a read. Existing permitted symlink
resolution remains supported. A complete old read overlapping an unobservable
later write remains subject to the canonical point-in-time/atomic-producer
limits; no arbitrary-writer snapshot guarantee is created.

## Required implementation and delivery evidence

- Convert both actual-finalizer baselines into superseded regressions with real
  restored-time changes, verifying prior published bytes and NoDb remain intact.
- Exercise growth, truncation, pathname/descriptor drift and read failure with
  real opened files; retain empty-file and ordinary unchanged-input success.
- Preserve existing unrelated-field, failed-publication, rollback and lock
  contention tests. Legacy state and numerical reader behavior must remain valid.
- Measure collection/finalization calls over representative complete RAP inputs,
  with no per-band/per-pixel hashing, and retain both hash cost and held-lock time.
- Complete full sanity and restarted native build/archive acceptance. No live
  runtime acceptance is implied by this checkpoint.

Independent security disposition and a standalone checkpoint ancestor commit
remain prerequisites to implementation. Recursive/VSI-compatible dependency
closure stays OPEN for C01 and the related raster consumers; the package cannot
close on this narrower fix alone.
