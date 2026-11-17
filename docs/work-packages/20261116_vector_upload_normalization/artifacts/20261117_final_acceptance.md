# Final local acceptance

Status: accepted locally; M0-M5 complete. Final source is
`4da014fee8a3c80643fc542165d6c529a85532ad`; executable files are unchanged
from independently reviewed `f96483108`. Subsequent acceptance-document commits
do not change executable files. No deployment, image publication or remote
integration is part of this acceptance.

## Scope and policy

Roads, AgFields, Omni contrasts and Batch Runner normalize Shapefile ZIP and
single-file GeoParquet uploads to canonical GeoJSON while preserving workflow
validation, retained originals, provenance, access controls and recovery.
Batch uploads require polygons. Culvert API paths remain excluded and D-Tale
remains deferred.

Public/team fork inheritance follows the operator's decision in the canonical
[sharing contract](../../../schemas/vector-upload-normalization-contract.md#sharing-copies-and-existing-workspace-resets).
No additional owner approval or evidence filtering was introduced. Original
upload actors remain provenance; verified copying principals incur new storage
charges. Existing direct sensitive-download restrictions remain in force.

## Runtime evidence chain

The final machine-readable receipt records commands, Git revisions, source/image/
fixture hashes, per-test results and skip reasons. Snapshots are isolated Git
checkouts in the existing development container; shared source/mounts are unchanged.

| Source | Coverage | Result |
| --- | --- | --- |
| `224184ecd` | Broad suite through the Roads publication gate | 7,966 passed, 205 skipped; stopped on the reviewed source-hash mismatch |
| `13feaac92` | Complete affected workflows, retained copies/resets, routes, native downstream and signed sessions | 721 passed, no skips |
| `111dd982c` | Bounded ZIP successor, archive recovery, helper and native workflows | 142 passed, no skips |
| `467e9db1b` | Archive creation/restore/recovery, cleanup faults and exact accounting | 98 passed, no skips |
| `f96483108` | Reconciled-source copy preflight, all copy consumers, native workflows and signed sessions | 130 passed, no skips |
| `4da014fee` | First broad continuation; stopped on missing native build products | 1,719 passed, 259 skipped |
| `4da014fee` | Native-binary continuation; stopped on missing generated bundle | 2,422 passed, 15 skipped |
| `4da014fee` | Controller-bundle continuation; stopped on missing Node dependencies | 1,533 passed, 1 skipped |
| `4da014fee` | Final browser continuation with locked dependencies and built assets | 854 passed and 1 skipped; no failures |

The [validation receipt](20261117_final_validation.json) retains individual test
results and skip reasons; overlapping successor counts are not additive.

The broad gate is a source-qualified prefix/suffix chain, not a claim of one
full-suite pass at the final revision. The suffix retains an ordered collection
manifest. Successor affected tests cover the later archive bounds, directory
durability and copy-accounting changes. Roads historical output/provenance hashes
and stale notice are preserved; its descriptor records the reviewed rollback
source changes without claiming fresh scientific validation.

The exact converter remains
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.
The receipt binds readiness and fixture hashes. Native parser, resource,
cancellation, dependency and SBOM qualification remain in the M1/M2 evidence;
parser/image sources did not change during receiver/lifecycle corrections.

The first continuation at `4da014fee` passed 1,719 cases with 259 skips, then
stopped because an isolated Git checkout contains no native build products.
The converter startup correctly rejected missing parser provenance. Both parser
binaries and JSON sidecars were copied unchanged from the qualified final5 image
into an isolated temporary directory and configured through existing parser-path
environment variables. All four abuse-control tests then passed. A second
inclusive continuation starts at that failed converter test; the receipt retains
both selections and verifies that no failed or omitted node remains unresolved.
No runtime source or readiness validation was weakened.

The native-binary continuation passed 2,422 cases with 15 skips and 12 subtests,
then found the ignored `controllers-gl.js` build product absent. The canonical
`build_controllers_js.py` generated it from the frozen checkout; tracked files
remain unchanged. The final inclusive continuation begins at the bundle check.
The receipt retains the generated bundle hash and build command. Collection-only
skips and overlapping checks are retained per invocation, not added into a
misleading total.

The controller-bundle continuation passed 1,533 cases before a browser test
reported missing `node_modules/@playwright/test`. The existing installed Node
dependencies match the frozen package lock and are exposed through a snapshot-only
symlink; the browser cache is selected by its existing environment setting.
Both affected Chromium cases pass. The canonical npm build and documented asset
copy supply ignored vendor assets as well. Tracked source remains clean. The
last continuation begins at that browser test and covers the remaining suffix.

QA independently reconciled the ordered collection to 14,497 passing and 476
skipped nodes, with zero uncovered nodes. All four prior failed nodes pass at
final source `4da014fee`. Repeated collection skips and 15 subtests are retained
separately; this is source-qualified cumulative coverage, not one invocation.
## Reviews and supporting checks

Code, correctness, security and operations source reviews accept `f96483108`
with no unresolved High or Medium findings. QA additionally reviewed the Roads
staleness descriptor in `4da014fee` and accepts the completed source-qualified
runtime evidence chain.
Independence exclusions and reviewed revisions are stated in each
`20261117_resumed_*_review.md`.

Frontend sources are unchanged since the retained passing lint, 126 Jest suites
(1,091 tests), and nine Node tests. The RQ graph differs only in source line
locations; no queue/dependency edges or live jobs were introduced. Stub
completeness and changed-file broad-exception checks pass. Existing profile
exception allowlist line references were relocated to unchanged handlers; no
new broad catch was added. Scoped Markdown lint passes.

Code-quality observability remains non-blocking. Lifecycle/archive additions
implement shared accounting, scope fencing, durable repair and bounded writes;
existing large orchestration functions remain intact. Radon is unavailable in
this environment, so Python complexity is unavailable, not zero.

## Recovery and rollout boundary

The [operator guide](../../../dev-notes/vector-upload-operations.md) and canonical
contract describe admission, sharing, copying-principal attribution, recovery
and disable behavior. Deployment still requires the retained M3-M5 activation
plan, real production identities/mounts/umask, readiness and per-workflow canaries.
No production parity or rollout claim is made here.

Failed private cleanup keeps its reservation. Persisted incomplete receipts
support exact actor-aware reconciliation. If receipt persistence itself fails,
the error is logged and the charge remains; these new tests do not claim to
exercise subsequent corrupt-receipt recovery, whose existing implementation is
unchanged.
