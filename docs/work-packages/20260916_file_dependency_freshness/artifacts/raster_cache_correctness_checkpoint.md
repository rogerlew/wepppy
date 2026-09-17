# C03/C04 raster cache checkpoint: correctness review

**Current disposition: PASS for the final bounded GTiff/AAIGrid checkpoint.**
The original findings and superseded proposals remain below; their final
dispositions and the reviewed document identities are recorded in the last
section. Implementation, runtime and package acceptance remain pending.
Production and tests were read-only for this review.

Reviewed `raster-dependency-freshness-contract.md`,
`raster_cache_contract_decision.md`, the retained recursive/native probes,
`Landuse.build_managements` and `baer.sbs_map` summary callers. The canonical
owner is the new raster contract, with NoDb concurrency, ordinary digest
admission and artifact-observability contracts continuing to apply.

## Findings and required precision

| ID | Severity / disposition | Concrete issue and smallest treatment |
| --- | --- | --- |
| RC-01 | High authority gate, pending; shared with security R-S01 | A local VRT's driver name alone cannot authorize opening it for discovery. The actual WarpedVRT probe performs HTTP HEAD/GET in `OpenEx`, before `GetFileList` can report the nonlocal source. Decide unverified coverage before an eager or unproven open; keep the original requested native operation available uncached. Do not remove the no-extra-network rule or ban accepted native inputs. |
| RC-02 | Medium, precision incorporated | C03 consumes a pair of rasters. Independent sequential observations cannot establish their coherent joint identity. The revised consumer section now requires complete paired pre/post observations on hits and misses plus MOFE structure/source-selection checks before admitting counts or publishing management areas. Retain that requirement in implementation and tests. |
| RC-03 | Medium, precision requested | A verified pre-observation becoming changed/unverified after native work must fail without admitting the result. An initially unverified observation instead follows the original uncached native success/error boundary. C04's eight-entry LRU must admit only after the successful post-check: decorating the raw native function and checking outside it can retain a wrong result under an old key even when the first caller receives an error. |
| RC-04 | Performance checkpoint pending | The retained discovery routine omits some final coherence/consumer work. A single-graph 10-ms budget cannot alone accept C04's two observations or C03's paired pre/post checks under the existing lock. Ratify whole-consumer limits using actual representative baseline measurements, then test the complete implementation against them. |

RC-01 is confirmed by `raster_discovery_security_probe_revision2.py`, its log and
`raster_discovery_security_warped_revision2.json`: IdentifyDriver makes no request,
but OpenEx makes HEAD and GET. A SimpleSource VRT makes no HTTP request through
GetFileList in that probe. This distinction supports conservative coverage before
opening; it does not establish all VRT subclasses as eager or safe. The fixture
uses only a disposable loopback server. No named project or remote service was
mutated. Security is retaining the authority review and remedy constraints.

## Correct binding and compatible states

The actual C03 baseline executes native pair counting and management area
calculation: a restored-time pixel rewrite keeps the old 3:1 pair counts until
explicit invalidation, while a direct native count returns 1:3. C04's native
baseline similarly reuses old class counts while direct native summary sees the
new raster. These establish fixes at the consumer boundary, not merely changes
to a hash predicate. Final tests must propagate corrected management areas into
the normal persisted/generated artifacts; the initial probe isolated those
persistence hooks.

For C03, both raster dependency graphs plus the existing MOFE structure digest
are the count identity. Management labels and current cell area are applied
after counting and remain current on reuse. Changing a management label without
changing the key structure must not require counting again. New private
signature representation must differ unambiguously from the legacy tuple;
legacy and rollback readers conservatively miss without rewriting project
state during reads. An unverified observation must be tested explicitly before
cache equality; two unavailable/sentinel identities never authorize a hit.

On a source-change failure, do not install mismatched counts/signatures or
publish changed management artifacts. `build_managements` shallow-copies
`existing_managements`, and its runtime-generated-key compatibility branch
returns the existing `ManagementSummary` object. That object can be mutated
before the current pair-count block. `NoDbBase.locked` unlocks on failure without
rolling back Python objects. Place the new validation before such mutation or
stage those values independently; cover retained prior runtime-generated
management values as well as on-disk files. This is a narrow new-failure-path
constraint, not authorization for a general NoDb rollback redesign.

C04 keeps eight entries and its original native summary semantics, including
required-native failure and optional empty summary behavior. The returned
summary must match the actual validated graph; metadata-only changes reuse it
after byte revalidation. Invalid/missing/denied discovery never authorizes an
old cached summary. Unsupported/unverified cases invoke the unchanged requested
native operation with an explicit diagnostic reason and do not populate a
reusable numerical entry. The bundled color-map resource remains a separate
code/config input; no runtime writer defect for it was established.

Native path/reader support is broader than verified cache coverage. Preserve
source links, valid local ZIP plain/braced forms, directory-backed stores and
their original native outcomes. Follow directory links with cycle control;
serialize path/link/membership identity, not inode/timestamp traversal aids as
scientific identity. Recurse through reported dataset dependencies and hash
ordinary auxiliary leaves. Optional mask, world-file and PAM additions/removals
require rediscovery on every reuse attempt. Native inventory must not create
auxiliary files or change process-global GDAL behavior for other requests.

## Cost and remaining acceptance

The retained representative discovery-only means are about 2.1 ms per SBS
graph and 3.7 ms for the 26.4-MB DEM graph; they include content-cache reuse but
are not final guarded consumer timings. The proposed additional gates discussed
with the parent are C04 hit <=25 ms, C03 cache-validation <=50 ms, and native-miss
overhead <=100 ms on representative ordinary local single/two-raster inputs.
Those are provisional until actual whole-consumer baselines and their precise
included operations are retained. Measure complete C03 management elapsed time
and lock occupancy separately. Do not use an arbitrary 10-second whole-lock
target unless the existing representative operation supports it, or subtract
existing required work merely to satisfy a new validation-only target.

The shared digest cache stays at 512 entries. Zero settled payload rereads must
be demonstrated on the representative working sets, with admission and actual
eviction measured separately. The retained 580-file Zarr mechanism necessarily
rehashes during sequential scans exceeding that cache's capacity; do not claim
zero rereads for all supported directory stores or invent an aggregate cache
without a failed real-workload gate. Document store/archive size and membership
costs separately from the simple TIFF benchmark. OS-cache-warm NFS measurements
are not cold-storage or tail-latency guarantees.

Before ancestor approval: finalize RC-01/RC-03 precision, retain and ratify the
whole-consumer baseline/gates, and obtain the independent security disposition.
After implementation: actual restored-time outputs, same-byte operations,
paired mutation and cache-poison regression tests, legacy/unverified/native
compatibility, denied paths, cycle/link/archive cases, source noninterference,
prior-value preservation and generated-management propagation remain required.
C01 outside-lock finalization and Geneva artifact publication remain separate;
an uncached numerical result is not proof for either publication boundary.

## Reviewed smaller scope proposal

The parent subsequently proposed **verified local GTiff reuse only** for C03/C04,
with all VRT, Zarr, VSI and other unproven inputs explicitly using the original
native operation uncached. This is preferable to adding a recursive VRT coverage
protocol for these two numerical caches: the actual expensive SBS workload and
the confirmed MOFE reproduction use TIFF, and no representative non-TIFF workload
has demonstrated that uncached execution misses an agreed budget. Unverified
inputs remain accepted by the same native engine; they simply cannot reuse old
numerical values. This addresses their stale-cache defect without asserting
verified graph completeness or safe C01/Geneva publication.

Approval of that scope still needs a concrete revised canonical checkpoint and
actual GTiff discovery authority evidence. Auxiliary filenames do not by themselves
prove their driver: test applicable mask/overview/PAM relationships before
claiming every local TIFF inventory is safe and complete. Security is probing
that boundary. RC-02 joint coherence, RC-03 admission ordering, failure retention
and the whole-consumer cost gates remain necessary. The earlier recursive
proposal and WarpedVRT finding above remain retained evidence; they do not
authorize a recursive implementation or new native input restrictions.

The concrete GTiff-only revision now incorporates RC-02 and RC-03, including
paired hit/miss checks, source-selection/structure rechecks, post-check-before-LRU
admission, initially unverified native behavior and prior runtime-generated
management retention. Those documentation findings are resolved; implementation
and regressions must still demonstrate them.

RC-01 remains open after the narrower root-driver proposal: security's
`raster_discovery_security_gtiff_mask_revision3.json` records a genuine GTiff
whose disguised WarpedVRT `.msk` causes HEAD/GET during `GetFileList`; the
overview variant records eight requests. IdentifyDriver reports GTiff and OpenEx
does not make requests in either case. Thus auxiliary eligibility must precede
the inventory call itself, not merely root metadata open. The root's GTiff driver
is insufficient evidence. The final pre-inventory eligibility policy and actual
whole-consumer performance baseline remain the two open checkpoint gates.

## Final checkpoint disposition

**PASS to commit the standalone contract ancestor and implement this bounded
scope. No unresolved medium/high correctness finding remains in the revised
design.** This disposition supersedes the pending entries above; it does not
erase their evidence or approve a recursive raster framework.

RC-01 is resolved at checkpoint level by the explicit ordering now reviewed in
[the security checkpoint](raster_cache_security_checkpoint.md): effective
configuration and selected/resolved companion eligibility precede restricted
read-only opens; companion datasets satisfy the same rules; nonempty OVERVIEWS
or another unproven external relationship excludes verified reuse before
GetFileList. Opaque PAM, unknown drivers, denial and cycles are unverified.
The WarpedVRT, disguised TIFF mask/overview and internal OVERVIEW_FILE probes
remain concrete implementation regressions. Unknown coverage invokes the
original native operation uncached, preserving accepted paths and errors.
Effective thread-local configuration must be included, and supported static
default configuration is a bounded assumption, not a theorem about arbitrary
past GDAL process state. No configuration mutation is authorized.

RC-02/RC-03 and prior-value preservation are explicit in the final canonical
consumer rules: complete paired observations and structure/selection checks
apply to hits and misses; changed verified observations reject admission;
initially unverified observations retain native semantics. Post-checks happen
before numerical cache admission and derived management publication. Reused
runtime-generated summary objects require particular regression coverage because
the existing lock does not roll back Python mutations. Legacy signatures miss
without migration; labels and current cell area are still applied by the caller.

RC-04 is resolved as a preimplementation budget decision. Independently read
[QA's review](raster_consumer_contract_qa.md), the raw
[interleaved controls](raster_management_interleaved_baseline.json) and
[native/composed measurements](raster_consumer_performance_baseline.json).
The real 41.43-MB TOPAZ/AAIGrid pair costs about 762 ms to recount, so preserving
its eligible cache is justified. Three alternating same-owner controls per phase
show complete validation of 50.67 ms for settled hits, 47.07 ms for settled
misses and 328.31 ms for helper-cold misses; added lock occupancy is
54.29/58.06/334.11 ms. Large SBS native summary costs 476.18 ms; its composed
settled hit costs 9.19 ms with zero payload digest reads. These are local means
on filesystem-warm disposable NFS copies. First-owner initialization is retained
separately, and the source-identity guards report named inputs unchanged.

Ratify the canonical limits: complete C03 validation <=75 ms settled and
<=400 ms cold/admission/evicted; whole management and actual lock added cost
<=100/450 ms respectively; C04 complete hit <=25 ms and native-miss added cost
<=50 ms. The earlier 50-ms validation and blanket 100-ms cold-overhead candidates
are superseded before implementation by real measurements. The prototype omits
the final authority checks and clears its hash cache instead of exercising actual
512-entry pressure. Therefore these results support targets, not implementation
conformance; repeat the full measurements with every final guard and actual
eviction. Do not weaken guards or silently change budgets after a miss.

Residual acceptance covers actual restored-time numerical changes, auxiliary
addition/removal, same-byte reuse, paired mutation on hits/misses, denied inputs,
native unverified compatibility, eight-entry numerical bounds, preserved prior
counts/objects/files on rejection and normal generated WEPP management
propagation. The retained QA composition preserves management/Parquet values but
does not yet compare final `wepp/runs/*.man` output. C01/C02/C05/C06 publication
scope, S01, production-equivalent runtime and whole-package acceptance stay open.

Reviewed final SHA-256 values match the independent security record:

```text
raster-dependency-freshness-contract.md bac31a24504998816ff8b160daa1a35a23887e521bf6a84447bf74130fb135e3
raster_cache_contract_decision.md 722cea5cfab1ce7ac87ed15fc74e1403c1a92b62c3744ccafe539c8c66c80217
```
