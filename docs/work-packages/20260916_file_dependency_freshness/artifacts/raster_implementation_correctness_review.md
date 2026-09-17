# C03/C04 implementation correctness review

**Current disposition: PASS for scoped code correctness after the R-CI03
native-interval guard correction.** The original findings, superseded approval
and failing controls remain below. Final performance, affected-suite and
runtime/package gates remain separate.
Read-only production/test review against contract ancestor `ceb715c08` and its
reviewed amendment. Only this review and disposable artifact probes were edited.

## Findings

| Finding | Severity and disposition | Concrete boundary |
| --- | --- | --- |
| R-I01, shared with security | Medium; amendment approved, implementation pending | `raster_freshness._Observation.discover` initially lets root GetFileList reopen a replaced mask/overview after recursive eligibility. Security's actual GTiff-to-WarpedVRT mask replacement performs HEAD/GET before failure. Inspection-only siblings and explicit separately observed auxiliary edges are required; native calculation options stay unchanged. |
| R-CI02 | Medium; finite correction approved in sibling amendment | The first sibling allowlist hides native `.tiffw` and `.RPB` dependencies, rather than treating them as unproven. Actual world-file geometry and RPC metadata differ between unrestricted/restricted inspection. Use source-extension-aware world candidates and explicit opaque external-metadata exclusion; preserve arbitrary valid source suffixes. No RPC numerical-output defect is claimed. |
| Recorded dependency disappearance | Conformance correction verified | An already-observed file becoming unavailable must raise ESTALE, not return the initially-unverified sentinel. The parent added identity/companion revalidation on failed inspection and unavailable-to-ESTALE conversion. The independent disappearance probe was collected after that concurrent correction and passes; it is not a retained failing baseline. |

The exact sibling proposal, failed controls, passing proposed-policy seam and
canonical/decision hashes are retained in
[the checkpoint review](raster_cache_correctness_checkpoint.md#inspection-sibling-amendment-review).
Its approval does not approve production code before the sibling behavior lands.

## Reviewed numerical and state behavior

`raster_dependency_signatures` observes the complete selected input set, then
hashes all recorded ordinary files and validates their selected/resolved versions
and companion membership. The identity contains paths and byte digests rather
than timestamps/inodes. These metadata fields remain coherent-read guards.
Effective configuration is read and rechecked. Explicit unverified observations
never become reusable cache keys.

`Landuse.build_managements` requires a non-None new signature before reuse, so
legacy tuples miss. It keeps the existing counts/signature until successful
post-validation and area calculation. Runtime-generated summary fallback now
deep-copies the old object before changing its area, which preserves prior
Python values on rejection even though the existing lock has no rollback.
Both selected rasters plus MOFE structure are checked again before area
publication. Labels remain outside the count key and current cell area is
applied in the caller. Existing dump/trigger boundaries remain intact.

`sbs_map._summarize_sbs_raster_cached` performs its post-observation inside the
eight-entry cached function. A failed native miss therefore cannot populate
the old key. The outer observation also guards settled hits. Initially
unverified inputs invoke the original native function directly. The retained
required-native and optional-summary error semantics remain under review with
the affected suite; there is no new raster decoder or Python summary fallback.

## Independent native probes

[Probe source](raster_implementation_correctness_probe.py),
[initial log](raster_implementation_correctness_probe.log), and
[expanded log](raster_implementation_correctness_probe_revision2.log) retain
**6 passed**, then **7 passed in 14.55s**:

- Joint observation rejects replacement of the first raster after hashing the
  second, using an actual inode-changing replacement rather than relying on a
  timestamp quantum.
- An actual native SBS summary followed by source replacement raises ESTALE
  before LRU admission; cache size stays zero and a normal retry equals the new
  native class-3 summary.
- An actual VRT remains unverified and invokes native summary on both accesses;
  changing its source changes returned native class counts.
- Actual native MOFE counting followed by byte, selected-path or structure drift
  rejects all three cases while preserving the original management dictionary,
  generated-summary values and exact prior count/signature association.
- Actual management synthesis and WEPP input preparation succeed after corrected
  native coverage, as detailed below.

[The disappearance log](raster_implementation_correctness_disappearance_after.log)
adds **1 passed** for unlinking a recorded file after its digest is returned.
The corrected observer raises ESTALE. These are tiny disposable fixtures;
no named run was mutated and no heavy benchmark was performed.

## Existing generated-management route

The smallest canonical downstream boundary is
`Landuse._write_mofe_management_file_task` (used by `_build_multiple_ofe`) followed
by `wepp.prep_multi_ofe_hillslope`. The former synthesizes
`landuse/hill_<topaz>.mofe.man`; the latter parses that management, expands the
requested years and writes `wepp/runs/p<wepp_id>.man`, alongside ordinary slope
and soil preparation. Aggregate `ManagementSummary.area` is not an input to the
per-OFE management parameters: those use `domlc_mofe_d` assignments.

The independent probe uses actual default management records, the real
management synthesizer, a repository soil fixture combined by
`SoilMultipleOfeSynth`, and the real preparation function. No management/soil
parser or writer is stubbed. Restored coverage goes from 0.27/0.09 ha to
0.09/0.27 ha after the raster change, while the same two OFE assignments produce
the same 4,251-byte three-year `p7.man`. Equality is expected here; changing
management parameters solely because aggregate reporting area changed would
be a regression. Owner access/locking and persistence notifications are isolated
in this tiny probe, so it does not replace actual NoDb/Parquet persistence,
RQ orchestration or WEPP model execution evidence.

## Remaining scoped gates

Review the actual amended helper after its standalone checkpoint, including
explicit auxiliary edges, symlink contexts, source/companion error paths and
native compatibility of rejected coverage. Promote durable regressions for
the retained eager-open and hidden-sidecar cases. Final affected suites,
stub checks, actual source/read-denial behavior and the final whole-consumer
budgets with real 512-entry digest pressure remain required. C01/C02/C05/C06,
S01 and production-equivalent runtime/package acceptance are separate and open.

## Final implemented sibling correction

The actual observer now passes restricted `sibling_files` only to inspection
OpenEx, records `(native_members, companions)` in the graph, recursively observes
eligible auxiliary rasters and hashes their recorded files. Dynamic world-file
names are classified as ordinary inputs and included in the sibling list; known
external RPC/IMD/RRD layouts are rejected before native inspection. Both identity
and companion-directory unavailability during revalidation become ESTALE, and
failed inspection validates collected observations before returning unverified.
The existing numerical native functions receive unchanged arguments.

[Final independent probes](raster_implementation_correctness_final.log) give
**15 passed in 15.28s** against this actual helper. The proposal seam is disabled;
`RASTER_IMPLEMENTED_COMPANIONS=1` only selects implementation assertions. In
addition to all prior admission, disappearance, VRT, mutable-summary and real
management-preparation cases, actual world files appear in the resulting proof,
and changing each native-used world file changes the proof. RPB inputs return
unverified. The source-extension and uppercase controls retain native geometry
and membership. The earlier failed native-membership records remain in their
logs and [original JSON records](raster_sibling_unknown_original_records.json).

R-CI02 is resolved in code for the proven companion mechanisms. R-I01's
inspection-order correction is present; the security reviewer owns the final
loopback request regression and authority disposition. No remaining correctness
blocker was found in this scoped code review. This is still bounded local
GTiff/AAIGrid coverage, not general native dependency closure. Final guard-inclusive
timings, real digest eviction and affected-suite results must be recorded by
their owners before claiming the implementation wave accepted.

## R-CI03: retain version guards across native work

**Medium, open implementation finding; static review confirmed, actual native
reproduction awaiting an isolated timing window.** The parent identified this
gap after the preceding scoped review. Each call to
`raster_dependency_signatures` validates its own `_Observation`, then discards
the observed physical versions. C03 compares only returned content identities
before/after pair counting. C04 likewise compares only content around native
summary. An old/new/old byte cycle during native work can therefore restore
both compared identities while the native result reflects the temporary new
bytes. The old pre-observation version would reveal ordinary observable writes,
but neither consumer retains it across that interval.

Keep selected/resolved versions, membership and relevant configuration guards
from before native work through its completion, separately from numerical cache
identity. Validate those guards before admitting counts or a summary, including
inside the C04 cache-miss admission boundary. A fresh caller guard must also
cover cache-hit selection. Metadata-only changes between completed calls should
still allow numerical reuse after content verification; putting timestamps into
the cache key is not the remedy.

The 15 passing probes remain valid evidence for their asserted paths, including
changed content that stays changed. They do not settle this newly identified
case. Geneva's proposed joint guards similarly need to span actual
materialization, not merely each independent observation call. No new runtime
acceptance is claimed while this finding is open.

### R-CI03 correction and final independent disposition

**Resolved in the reviewed code and bounded native probes.** The parent's
[actual pre-fix control](raster_native_aba_initial.log) reproduces admission of a
class-3 native result after restoring class-1 bytes. The new frozen
`RasterDependencyObservation` retains physical file/resolved identities,
companion-parent directory versions and effective configuration from the same
acquisition as its content signature. Equality/hash exclude `read_guard`, while
C03/C04 explicitly compare the guard across native work and cache-hit selection.
The check is inside C04 miss admission. Content-only convenience functions remain
available, with materializers directed to retain the observation instead.

The parent also preserves native symlink/`..` semantics by using `Path.absolute`
instead of lexical `abspath` normalization. This applies to selected paths and
native file-list members; resolved paths remain separately represented.

[The expanded independent run](raster_implementation_correctness_guard_final.log)
retains **17 passed, 1 fixture failure**. Both actual SBS and MOFE old/new/old
generation probes passed: native computation sees the temporary new bytes,
restoration returns the original content, admission raises ESTALE and previous
cache/management state is retained. Atomic replacements guarantee an observable
generation difference without timing sleeps. The only failure was an absent
logger in the disposable `Landuse.__new__` fixture when its new roundtrip test
first reached the ordinary cache-hit debug call. After adding that fixture logger,
[the one-case rerun](raster_implementation_correctness_roundtrip_after.log) gives
**1 passed in 9.38s**. The private signature survives actual jsonpickle
encode/decode, then a same-byte touch reuses counts without native counting.
No production code was changed by this reviewer.

The resulting 18 independent assertions/cases pass across the retained run and
targeted fixture correction. Original pre-fix and fixture failures are retained.
No remaining scoped correctness blocker was found; final QA performance and
security authority evidence remain separately owned, and this does not claim
runtime/package acceptance.

Reviewed source identities:

```text
raster_freshness.py 7e218d1e7ec5e4da55914e8bbfd695dd423a2d1ae890afd87baf343761f80b24
landuse.py 46954d6d325789972af2ad901458c3106f5d88dde1212715fd409baba5012cd8
sbs_map.py 5212036fa8357987b65c7add0da435a1b4a95f26b510b18b44eba075cd4242b7
```
