# C05/C06 Geneva implementation: independent correctness review

**Disposition: PASS for the reviewed numerical identity, native-read guard and
failure-classification scope after corrections.** Final authority/security,
representative performance, service-identity and full runtime acceptance remain
separate gates. Production and test files were read-only for this review.

Reviewed the uncommitted implementation against checkpoint `31f77bef1`:
`collaborators/_cache_freshness.py`, `hru_map_geometry_service.py`, and
`hsg_assignment_service.py`, their actual ArtifactIO/native callers, and the
canonical derived-freshness subsection. No live/named runs were used.

## Findings and disposition

| ID | Severity / final disposition | Evidence and correction |
| --- | --- | --- |
| GI-C01 | Medium, resolved | Changed sources that made native generation fail bypassed the post-read guard. Actual HRU replacement produced `contract_violation`/500; actual alignment source corruption produced `invalid_input`/400. Both should be `changed_source`/409. The per-attempt input validator now rechecks failed uncommitted work after a completed strong acquisition, records the resulting failure and preserves stable original errors. Both failing probes now pass. |
| GI-C02 | Medium, resolved | Reacquisition could raise disappearance/access errors before `_Inputs.validate`, including on cache hits outside an attempt. `validate_inputs` now translates the specified failures only after an earlier verified acquisition and is used by both hit paths. Actual removed-legend materialization/hit and removed-source alignment-hit cases now return typed 409 while preserving prior artifacts. |
| GI-C03 | Security-owned, independent final disposition required | Initial publication checked destination selection/clean companions before the dependency callback. Security reproduced a later alias/mask change and an old native 0444-target compatibility regression. Current code adds final destination/companion checks and distinguishes JSON inode-write authorization from native TIFF replacement. See the independent security artifacts for acceptance; this correctness review does not substitute for them. |

The original failure log and JSON records remain intact:
`geneva_implementation_correctness_probe_initial.log` records **2 failed,
6 passed in 9.53s**; `geneva_implementation_correctness_initial_records.json`
retains the original per-case observations before after-probes overwrote their
individual latest-result files. The failures were not fixture timing issues.

## Native evidence after correction

`geneva_implementation_correctness_probe.py` executes real GDAL/rasterio,
ArtifactIO, vectorization, nearest-neighbor alignment, embedded provenance and
publication on disposable rasters. Only the NoDb owner is a `wd`/ArtifactIO
namespace; mutation hooks bracket real native operations. No HTTP/RQ/kernel
execution, named-project mutation or deployment is claimed.

The final retained `geneva_implementation_correctness_probe_revision2.log`
records **12 passed in 10.54s**:

- Restored-time HRU pixel edits regenerate the actual feature identity; restored-
  time legend edits regenerate its actual properties. A later same-byte source
  touch retains the published GeoJSON inode.
- A changed SBS source regenerates class-3 aligned pixels. Subsequent equal-byte
  metadata changes and bound-pixel-only changes reuse the result without another
  native stacker call; the effective bound profile remains the relevant identity.
- Both geometry and alignment reject actual old/new/native-read/old input
  sequences with `changed_source`, retaining the prior output. Atomic replacement
  guarantees observable generation changes without timing sleeps.
- The corrected native-error paths return 409, while a stable invalid legend
  still returns the original `contract_violation`/500. Previously accepted output
  bytes remain unchanged in all strong-path rejection cases.
- Legend disappearance after native completion and on a geometry cache hit, plus
  source disappearance on an alignment hit, produce typed 409 and retain prior
  output.
- An old external target mask follows the original native overwrite: final
  class-3 pixels have valid masks and no unearned embedded proof. This resolves
  the earlier actual main-only replacement defect retained in
  `geneva_publication_correctness_probe.log`.
- A real unverified local VRT remains native-successful; two calls invoke native
  alignment twice and publish `dependencies: null`, never reusable proof.

## Code-path assessment and limits

Geometry binds raster closure and legend bytes, preserving a physical guard from
the same acquisition through native generation and publication. Alignment binds
source closure plus selected/resolved bound path and actual retained profile
fields; it excludes the pixel values and fields overridden by `raster_stacker`.
Its source/bound observation spans the profile read and guards both acquisitions.
Initial unverified inputs follow native behavior without acquiring false reusable
identity. Legacy/malformed proofs trigger normal regeneration.

Attempts are created before the materialization acquisition, avoiding owned
directory setup invalidating that guard. New proof and numerical payload are
published together; cached GeoJSON is returned from its single validated read.
The failure validator runs only for uncommitted work and preserves the original
native error when input validation succeeds. Initial unknown/unverified inputs
do not acquire a fabricated strong-generation error classification.

The auxiliary-target branch retains its explicitly weaker historical native
overwrite guarantee; its failure cannot be advertised as preserving all previous
output. Final QA must measure the complete current helpers and access/publication
checks, including actual cache pressure, rather than the earlier composition.
Service UID/GID/groups, ownership, mode and symlink behavior require independent
security/runtime evidence. The whole-HRU `force_rebuild=False` cache remains the
separate documented inventory boundary; C06 only applies when materialization is
actually reached.

One target-specific edge was referred to security for final classification:
cached GeoJSON whose selected alias target in another subdirectory disappears
after its read can reach the final target `_version` check. Initial target access
errors should retain their native meaning; already-observed target drift must
not be mislabeled as source-independent malformed proof. Source disappearance
coverage above does not by itself establish this target-alias case.

Reviewed after-probe identities:

```text
_cache_freshness.py 3c10fef07b76476688f98a2eb335a85f89130ac1c902ea193ca4f762260ba995
hru_map_geometry_service.py dff53fad1c39a30993126921b43c878a4878508e0dfabe5a49245b85f5f2ee36
hsg_assignment_service.py 295afbf2e63cdacb2b688f9adf7b52f7defc2b81dcb4dec6eff8aadb78775a67
```

## Same-call C06 observation refinement

**Scoped correctness remains PASS** after the performance refinement. The
initial full source/bound observations and real bound-profile read remain.
Repeated validation reuses only that call's proven graph: all physical/config
guards run before verification, every recorded path is resolved and passed to
the verified digest helper, companion membership is rescanned, then all guards
run again after the complete set. No observation survives into another request.
This avoids repeated GDAL/profile opens while retaining byte comparisons during
the digest admission interval; a stat-only shortcut would not be equivalent.

Review found and the parent corrected two intermediate gaps before the final
run: per-source postchecks occurred before the bound's potentially changing
work, and disappearance between physical check and digest could escape as raw
ENOENT. Complete-set pre/post guards and narrow observed-error translation now
cover both. Unrelated EIO retains its original exception. Candidate path
resolution still checks basename and containment in the previously resolved
private attempt; final target selection/authority remains independently checked.

`geneva_implementation_correctness_probe_revision3.log` records **15 passed in
9.78s**, preserving all twelve native controls plus actual source replacement
during the bound-digest check, source removal between physical check and digest,
and original EIO preservation. The actual performance miss remains retained by
QA and must pass final remeasurement; this review does not waive its gate.

```text
_cache_freshness.py 405223512fbf699d35d008bdb0228802ee2a39b2095dfc8ed3f67b3521b8e2b1
hru_map_geometry_service.py 98c3f8c3b67abd21c10aacf9c0b278df1874a07c2a2684c038f18f6bbfa51034
hsg_assignment_service.py 59ee01affee3b9455327868d17f4b76191d622ef2c520f7307f480fe706da96f
```
