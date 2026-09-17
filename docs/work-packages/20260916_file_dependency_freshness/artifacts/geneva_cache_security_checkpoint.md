# C05/C06 Geneva cache security checkpoint

**PASS for the refined bounded checkpoint; implementation and runtime gates
remain pending.** The original publication finding remains below and is closed
at design level by the explicit compatibility disposition. No Geneva runtime
implementation has been reviewed or approved. Reviewer: `freshness_security`; existing source
at `308f9edee`, plus the proposed specification's “Derived raster/geometry
freshness” section and `geneva_cache_contract_decision.md`.

## Findings and required precision

**G-S01, medium, closed at design level: the original main-file publication
proposal did not preserve the effective existing GTiff output.** The independent correctness probe
`geneva_publication_correctness_probe.py/.json/.log` demonstrates the issue with
actual `raster_stacker`: direct replacement removes an old external mask and
returns mask values 255; `os.replace(candidate, target)` leaves the old mask and
returns values 0, despite identical new main-file pixels. A fresh embedded tag
would not make that old sidecar part of the new producer generation. This is a
confirmed valid-state compatibility/integrity defect in the proposed publication
primitive, not a hypothetical multi-file driver. Decide a bounded auxiliary-
bearing output disposition preserving native behavior and retained artifacts
before approving the checkpoint. Do not silently call every GTiff a single-file
publication or delete project records merely to remove the discrepancy.

The following design requirements are now explicit in the refined draft and
need actual implementation evidence; they are not claims that nonexistent
code is vulnerable:

- Cached aligned-output metadata inspection must establish eligible local GTiff
  authority before a native open. A `.tif` name does not prove its driver.
  Unproven target descriptions must not cause eager WarpedVRT child reads just
  to determine that provenance is missing. The retained raster security probes
  establish that this native-open ordering matters. Preserve the original
  numerical native call when rebuilding; do not impose a blanket input ban.
- Distinguish absent/malformed provenance from access and I/O failures. Denied
  GeoJSON/TIFF reads must not become a rebuild path that bypasses existing read
  permissions by returning in-memory data. Initial source/legend availability
  envelopes and native errors must retain their existing meanings.
- Apply candidate confidentiality from creation, including any native temporary
  files, through a private retained attempt directory and applicable payload
  modes. A final chmod alone is insufficient. Recheck the existing ArtifactIO
  root/destination authority before publication; do not add blanket restrictions
  to the already supported run-root/source symlink arrangements.
- Preserve selected output symlinks by publishing to their same validated
  resolved target and rechecking selection. Preserve each writer's actual access
  boundary: GeoJSON currently uses ordinary truncating `open('w')`, while
  `raster_stacker` uses the native GTiff writer. Do not assume their read-only
  target behavior is identical. Retain real mode/denial controls before choosing
  a shared write-access check, including confidentiality of 0600/0640 artifacts.

## Compatible design and code trace

`GenevaHruMapGeometryService` reads masked raster pixels, CRS/transform and legend
rows. Its current mtime comparison misses proven pixel, external-mask and legend
changes. Binding all those inputs, reading a cached GeoJSON once and returning
that same verified payload addresses this actual boundary without changing
feature properties, availability envelopes, vectorization or reprojection.

`GenevaHsgAssignmentService` prefers the existing Disturbed SBS source, permits
explicit burn override pass-through and resolves the fixed output through
`GenevaArtifactIO`. Preserve that selection contract and recheck it after native
work. `raster_stacker` already forces GTiff output for every bound driver; the
earlier draft's non-GTiff output exception was incorrect and has been removed.
It overrides driver/count/compress/nodata/dtype, so the revised bound identity
correctly omits those bound values while retaining actual grid/CRS and the other
creation options. Bound pixels and masks are not its alignment inputs.

The bounded raster observer can support source proof; unverified input coverage
must remain explicit and uncached. An unverified bound must bypass reuse before
an added unrestricted profile-open attempt. The existing native operation may
still read that accepted input. Do not attach verified provenance to an
unverified source/profile observation. Before/after checks must bind the actual
legend read and profile generation rather than tagging older data with later
path metadata. This does not require hashing bound pixels as scientific inputs.

Additive embedded provenance preserves coherent GeoJSON features/proof and TIFF
pixels/proof for an eligible generation. Legacy or malformed proof can trigger
normal regeneration without manufacturing historical identity. Relocation may
conservatively rebuild; no persisted NoDb migration or new scientific policy is
needed. No new auth/session/queue boundary is proposed. The existing ArtifactIO
root resolution remains authoritative; a generic ArtifactIO refactor is outside
this wave.

## Evidence limits and gates

The retained native baseline proves the stale outputs; the copied 990-feature
QA measurements support provisional service budgets, not final publication or
permission acceptance. Rasterio and osgeo/native readers use different installed
GDAL builds; require actual mask/georeference/profile parity for this bounded
coverage rather than relying on the observer's library version alone. This is
an acceptance constraint, not a newly demonstrated configuration defect.

This review performed code/contract reads only while QA measured raster costs.
It adds no concurrent native workload and no production/test changes. The
publication mask finding reuses the correctness review's retained real probe.
Final acceptance must cover failed native/conversion/publication work, prior
output and companion preservation, modes/symlinks, malformed versus denied
proof, source changes, actual geometry/kernel input consumption and canonical
browse/archive/restore of success and failure attempts. Package runtime gates
and C01/other open consumers remain separate.

## Refined checkpoint disposition

The canonical refinement bounds atomic TIFF publication to clean target
companion layouts and rechecks that condition before commit. Existing auxiliary-
bearing targets take their original native overwrite path uncached, with explicit
attempt evidence and no verified proof stamp. This preserves the demonstrated
native mask behavior without introducing an atomic bundle protocol. The branch
retains its preexisting weaker failure/publication guarantee; it does not promise
rollback of prior outputs. After a native overwrite leaves a clean target, a
later normal request can establish embedded provenance through the guarded
candidate path. The final report must retain this scoped limitation.

This is a deliberate compatibility branch under the existing native authority,
not permission to hide failures, delete evidence through new cleanup, or claim
all publication paths now have identical guarantees. Test retained failed native
output/diagnostics in this branch as well as retained candidates in the atomic
branch. Preserve the original failing mask comparison as evidence.

The refinement also pins exact embedded proof names/shape, private attempts and
status from creation, writer-specific access and output-symlink selection,
eligible target metadata inspection, joint dependency guards, automatic source
reselection at publication, typed changed-source errors and the replace commit
point. Post-commit status errors must not misreport failed publication. All
initial permission/native/error semantics remain implementation gates.

One compatibility acceptance constraint needs care: ordinary JSON `open('w')`
preserves an existing inode's uid/gid, whereas replacement can inherit the
candidate's ownership/group. Mode alone does not prove compatibility. Verify
actual supported service/group identities and preserve the existing writer's
access behavior without adding an unsupported ownership ban. No mixed-owner
workflow failure has been demonstrated here; this is not a new blocking finding.

No unresolved medium/high design finding remains in this refined scope.
Implementation approval, actual publication/permission/retention tests, final
timings and full package runtime acceptance remain pending.

Final precision retains physical guard versions from the same verified
acquisition across the entire native operation, separately from numerical
identity. Attempt setup precedes that acquisition so owned directory creation
does not itself trigger a source-parent guard. This closes the gap illustrated
by C03/C04's real change/read/restore regression; it is a conformance clarification
of the already required complete-set guards. The scoped checkpoint PASS remains.

Reviewed document SHA-256 values:

```text
specification.md b245cb2c57d806888f38e0d2c228da805aadcdecc69f8b52ef90d4eb5c9c5510
geneva_cache_contract_decision.md f38d1c913b79c85af0bc84861ba88fa9851cd660dcd5e92ef39e9c73483cb097
```
