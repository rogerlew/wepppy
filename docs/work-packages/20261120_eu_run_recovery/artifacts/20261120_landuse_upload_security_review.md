# Land-use upload security review

## Metadata and scope

Independent correctness and security review covered the staged upload route,
worker receipt, publication and batch leaf path under the linked
[upload checkpoint](20261120_landuse_upload_preflight_checkpoint.md).
The review was performed on 2026-11-20 in the isolated land-use worktree.
Route and file handling changes give this slice high security impact.

## Findings and disposition

| Surface | Evidence | Disposition |
| --- | --- | --- |
| Authorization | Existing JWT scope, token classes, run access and form parsing stay in the entry point. Focused route tests exercise the existing guards. | Existing authority preserved |
| Raster input | Same admitted driver checks. Real matched raster, unmapped class 999, a valid class zero, uncovered hill and OFE, and incompatible Disturbed table controls. | Explicit safe rejection before enqueue |
| Artifact paths | Receipt directories open without following links. Tests exercise a valid managed land-use projection, an external land-use link and a hostile attempt-root link. | Scoped paths only |
| Queue binding | The canonical job ID, run, basename and RQ-bound receipt digest associate the upload. Tests modify a receipt, approved TIFF, and applied raw bytes. | Changed inputs cannot reach publication |
| Worker retry | Private HTTP and actual RQ use a current same-ID retry after interruption. A selection drift control fails before file and timestamp changes. | Current work can recover, stale work stops |
| Custom management authority | Review found a mutation could occur after worker verification while only the worker held the root lease. Upload, delete, map save and map clear now contend on the same root through actual worker use. | Producer and editor serialization shared |
| Batch lock | The batch base and leaf use the effective-root scope. A private HTTP control held the leaf-equivalent lock and observed canonical rejection before any raw bytes were written. | Lock scope verified |
| Retention | Definite invalid admission removes its private staging. Successful jobs remove duplicate rasters and retain a compact receipt. Admitted interrupted work retains its staged files. | Retry evidence remains available |

Managed NoDir projections are valid only inside the project's own configured
NoDir projection tree. Runtime processors preserve the linked output
directory identity and reject external directories. The negative path
tests use harmless temporary trees.

The prior report may remain visible if a later native build fails after
new input publication. The worker removes its previous completion marker
before committing the new generation, so a preserved report cannot certify
the new inputs. A definite NoDb commit fault can conservatively leave the
previous input files without a success marker. Whole-build rollback is
outside this accepted admission slice.
