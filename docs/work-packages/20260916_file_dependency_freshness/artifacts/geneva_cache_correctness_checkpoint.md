# C05/C06 Geneva checkpoint correctness review

**Disposition: PASS for the revised bounded design; security, implementation and
runtime acceptance remain separate.** This review follows the C03/C04 sibling
amendment and reads the actual geometry, alignment, artifact I/O, preparation
callers and native stacker. No production/test files were edited.

## Findings and reviewed corrections

| Finding | Disposition | Evidence and bounded correction |
| --- | --- | --- |
| G-C01: old target auxiliaries survive main-only replacement | Medium; corrected in checkpoint | Actual existing raster_stacker removes an old external mask; candidate plus os.replace leaves it active. Atomic publication is now restricted to clean target layouts. Existing auxiliary-bearing targets use original native overwrite uncached, with explicit attempt evidence and weaker failure guarantee; they receive no strong proof. |
| G-C02: mistaken non-GTiff output branch | Corrected | `geo.py:raster_stacker` forces output driver GTiff for every bound driver. Preserve normal single-TIFF output for native-successful VRT/AAIGrid bounds; unsupported bound discovery bypasses reuse rather than becoming a new format rejection. |
| G-C03: effective profile identity | Corrected | The stacker overrides bound driver/count/compress/nodata/dtype. Exclude those and bound pixel/mask values from accepted numerical identity; retain grid, CRS and all other passed-through profile fields. Metadata guards can remain stricter during reads. |
| G-C04: incomplete generation/admission details | Corrected in checkpoint | Named versioned embedded proof, joint set guards, source-selection validation inside publication, typed changed_source/409 and replace-as-commit semantics are now explicit. Recheck cache hits and return the already-validated GeoJSON payload. |

### Retained native publication failure

[Probe](geneva_publication_correctness_probe.py),
[JSON](geneva_publication_correctness_probe.json) and
[log](geneva_publication_correctness_probe.log) retain **1 failed in 2.29s**.
Both outputs contain class-3 pixels. Existing direct native overwrite removes
the old `.msk` and returns an all-255 valid mask; candidate replacement leaves
the old all-zero mask active. This is an actual reader-visible regression from
main-only publication, not a hypothetical concern about all raster formats.

The revised compatibility branch is the smallest supported correction. It
preserves the old native writer's accepted destination behavior without adding
a multi-file transaction protocol. Its failure can retain the old writer's
partial/changed canonical output; no prior-output preservation or atomic rollback
is claimed. Keep that exception explicit in attempt status and tests. After the
native writer leaves a clean destination, a subsequent normal request can build
and atomically publish a proved generation. Do not merely attach current proof
to the unverified compatibility output.

## Identity, valid states and publication

C05 uses HRU raster dependencies and the exact legend generation consumed by the
native feature builder. The complete set must remain guarded while observing
individual members, reading legend rows and vectorizing masked pixels. Matching
independent file digests are insufficient if a previously observed member changes
while another is read. The current source/legend missing-input availability
envelopes remain unchanged; the existing service requires both even if historical
GeoJSON exists. Legacy or invalid proof triggers a normal source-backed rebuild.

C06 uses the selected auto-discovered SBS dependency graph and the effective
canonical bound profile. Selected/resolved paths distinguish changed sources,
including an older alternate SBS path. A bound pixel-only change with unchanged
effective profile should preserve reuse across calls; a transform/CRS/retained
creation-option change should regenerate. Unverified bound formats must not be
opened by a new discovery path merely to obtain a profile; preserve the original
native operation without claiming verified reuse. Explicit burn overrides keep
their original pass-through behavior.

Auto-selection revalidation must occur before candidate publication, including
appearance of a new preferred SBS while the previously selected fallback still
exists. A check in `resolve_prepare_input_refs` after the materializer returns
would be too late to preserve the prior accepted target on drift. Native generation
must be bracketed by complete observations; no arbitrary-writer isolation after
the last validation is promised. Retain pre-observation physical versions across
the entire native interval separately from the content key. The parent's new
C03/C04 R-CI03 finding shows why independent internally guarded observations
alone can miss an observable old/new/old content cycle around a native result.
The Geneva implementation must not inherit that admission gap.

The fixed `_wepppy_freshness` GeoJSON member and `WEPPPY_GENEVA_FRESHNESS` TIFF tag
bind version, kind, attempt identity and canonical dependencies into the same
published artifact. Null dependencies are explicitly unverified, never a reusable
key. Invalid/unknown versions or kinds cannot become a proof. Existing read/access
errors retain their error boundary rather than being silently recast as legacy
metadata. Unknown target raster formats cannot be eagerly opened just to look
for a tag. Preserve selected output symlink, write authorization and target mode;
security owns the full identity/permission review.

For the clean atomic path, all native, serialization, proof and precommit status
work precedes replacement. An error there preserves the old accepted output and
retains the candidate/status. Replacement commits the generation; a later
diagnostic write error is logged and cannot truthfully be described as rollback
or failed publication. New attempt records must remain visible under
`geneva/cache_attempts/<uuid>/`, normally browsable and archived/restorable.
Do not change unrelated `GenevaArtifactIO` writers to achieve this scope.

## Measured provisional cost gates

Reviewed [QA's component report](geneva_consumer_performance_qa.md) and its
[raw measurements](geneva_consumer_performance_baseline.json). The 990-feature
copy reproduces native geometry and aligned pixels/profiles exactly, reports
all six named inputs unchanged, and measures settled digest payload reads as
zero. Geometry native miss/hit means are 884.35/16.15 ms; composed hit means
are 24.03 ms settled and 25.60 ms helper-cold. Alignment native miss/hit means
are 29.35/0.91 ms; composed hits are 14.19/14.32 ms.

Ratify the proposed finite targets: C05 hits <=40/75 ms settled/cold-or-evicted
and native-miss added <=100 ms; C06 hits <=25/40 ms and miss-added <=35 ms. This
is filesystem-warm copied NFS evidence for these service components, not full
owner/HTTP/RQ or cold-storage performance. The composition predates final raster
security changes and atomic metadata/publication work, and it clears helper
caches rather than exercising actual 512-entry pressure. Final complete checks
and real eviction must be measured without subtracting required work. Larger HRU
fragmentation remains a workload risk, not authority for a new cache design.

## Scope and implementation acceptance

`GenevaHruPreparationService.prepare_hrus(force_rebuild=False)` can return a
saved HRU summary before resolving input rasters. Its existing currentness test
uses CN lookup identity and required output existence. C06 fixes alignment when
that materializer runs; it does not revise the separate whole-HRU reuse contract.
The normal run-all request explicitly forces HRU preparation, so downstream
acceptance should exercise that route and verify the corrected aligned path
enters the real kernel request. Preserve explicit cached-preparation behavior
and retain broader input-sensitive HRU reuse as a separate inventory decision.

Required implementation evidence includes changed HRU pixels/masks/legend,
changed SBS/source path/bound profile, same-byte reuse, bound-pixel-only reuse,
proofless/malformed/unverified/denied states, source and selection races on hits
and misses, actual target-sidecar fallback, clean-target atomic failure retention,
postcommit diagnostic failure, and ordinary archive/restore of attempts. Native
GeoJSON and aligned TIFF results must propagate through their real consumers.
The retained publication failure remains a regression until the implementation
demonstrates both clean and auxiliary-bearing target branches. No package/runtime
acceptance or new generalized raster-closure claim is made here.

Reviewed draft identities before implementation:

```text
geneva/specification.md 09af934c1c6dec05ecbb0332ee2493989b02c153403be491636f392902d3167b
geneva_cache_contract_decision.md 34b16b82ae6aef3098dba2490f4621c027ef1ed70c6485723005c521b95d4ec9
```

The subsequent precision remains **PASS at checkpoint level**: retain the
same-acquisition physical guard through all native work, create attempt
directories before taking that guard, skip added profile inspection for
unverified bounds, and verify supported UID/GID/service-group parity alongside
mode. These clarify the reviewed authority and coherent-generation boundaries;
they do not authorize changing native reader options or target ownership.
Final reviewed identities are:

```text
geneva/specification.md b245cb2c57d806888f38e0d2c228da805aadcdecc69f8b52ef90d4eb5c9c5510
geneva_cache_contract_decision.md f38d1c913b79c85af0bc84861ba88fa9851cd660dcd5e92ef39e9c73483cb097
```

## Explicit complete-operation performance amendment

**PASS for this finite budget amendment, pending fresh acceptance measurement.**
Independent correctness reviewed `geneva_performance_budget_amendment.md`, the
canonical specification change, and the raw revision2 acceptance/component
JSON. The original failed gates remain failures; this does not retroactively
approve them or substitute a component profile for complete service timing.

Ratify C05 hits unchanged at40/75ms settled/cold-or-evicted and native-miss
addition<=125ms; C06 hits<=30/40ms and native-miss addition<=65ms. Both miss
limits include the settled and helper-cold paired operations against ancestor
`31f77bef1`. The same representative990-feature copy, mean statistic, warm
filesystem scope, complete publication boundary and zero settled digest reads/
native generation remain mandatory. No broader workload or HTTP/RQ guarantee
is inferred.

The original composition did not include the implemented retained attempt/
status and full publication/authority lifecycle. A concrete optimization has
already removed duplicate native source/bound acquisition without weakening
content, companion or joint physical/config validation; the independent final
15-case correctness probe covers that current implementation. The raw revision2
file records the same helper/service hashes, unchanged inputs/modules, six real
512-entry evictions, valid geometry/pixels/profile, zero settled payload reads,
and `acceptance_passed: false` with four failed original gates.

The costs remain explicit: geometry cold addition106.47ms; burn additions51.73ms
settled and37.10ms cold; burn secondary settled hit25.07ms. The isolated current
miss leaves38.42ms outside native stacking, including retained status work and
verified paths. Inclusive profile components overlap and are not additive proof
of a threshold. The revised finite headroom addresses the documented incomplete
estimate and observed local variation; dropping required work or introducing
cross-request state merely to meet the old estimate would require a separate
correctness justification.

Approval requires a separately named complete run under the adopted amendment,
preserving all samples, original failure files, source/module identities, actual
admission/eviction preparation, native parity and permissions. A new miss remains
a failure to investigate, not authority for another automatic increase. Owner,
HTTP/RQ, archive/service identity and whole-package runtime gates stay open.

Reviewed SHA-256 values:

```text
geneva/specification.md 2757606ceb39a77a88ada8b24a5c99dca16930ccdcac48016685a65620453f9b
geneva_cache_contract_decision.md 3a29b3d77ac410d4ec62bc618d37999604d034df9a4dd4f45983e732d4b96152
geneva_performance_budget_amendment.md 2cce7aefcefd0299c6fdf8ca89a25175d514a5d2f100ae781f70deef64c67871
```
