# Raster dependency freshness

Status: implemented bounded C03/C04 behavior; independent reviews and measured performance gates pass.

## Scope and native authority

Landuse MOFE pair-count reuse and SBS native-summary reuse require current
content of their effective raster dependencies. Preserve native calculations,
accepted input paths, reader options, source symlink support, and native error
boundaries. Metadata-only changes cannot change numerical identity. A changed
required dependency must prevent reuse, including equal-size/restored-mtime
writes and added or removed auxiliary files.

Use the existing installed GDAL to discover dependencies and the verified
ordinary-file digest implementation to observe bytes. This is dependency
inspection, not a second raster computation. No new dependency, native decoder,
remote transport, process-wide dataset handle cache or aggregate digest cache is
authorized. Discovery must not update datasets or write auxiliary metadata.

Verified reuse coverage is bounded to local GTiff/AAIGrid datasets and verified local
auxiliary dependencies. Recognize the installed driver, not the filename suffix.
VRT, Zarr, VSI and unproven auxiliary relationships are explicitly unverified
before opening them for discovery. Preserve these accepted inputs by invoking
the same native operation uncached. This fixes numerical reuse without claiming
universal GDAL dependency closure or introducing a VRT preflight framework.
The representative expensive SBS workload is GTiff; a maintained large TOPAZ
MOFE workload uses AAIGrid plus GTiff. Both require measured whole-consumer
acceptance; neither justifies a general recursive VRT/Zarr framework.

## Dependency observation

Rediscover local dataset membership on every attempted reuse. Include native
reported masks, world files, PAM metadata and overviews. Hash every reported
ordinary auxiliary file; do not certify an auxiliary raster from its suffix.
Selected/resolved source and auxiliary paths and verified byte digests form a
deterministic identity. Source links remain supported under the caller's existing
authority. Metadata is a cache hint/read guard, not numerical content identity.

Before native open/list discovery, preflight companion candidates at both the
full source filename and extension-replaced stem, including case variants. Opaque
`.aux`/`.aux.xml` layouts are unverified. `.msk`/`.ovr` companion datasets must
recursively satisfy the same local driver/companion eligibility; unknown, denied
or cyclic relationships are unverified. Driver identification alone does not
authorize an arbitrary dataset open. Preserve selected/resolved observations for
source and companion symlinks. Check effective GDAL configuration, including
thread-local values, rather than only environment variables. Initial verified
settings are: GDAL_PAM_PROXY_DIR unset, GDAL_PAM_ENABLED YES,
GDAL_DISABLE_READDIR_ON_OPEN FALSE, GDAL_READDIR_LIMIT_ON_OPEN1000,
GDAL_GEOREF_SOURCES unset/default, USE_RRD NO and TIFF_USE_OVR FALSE. Unknown or
nondefault values make coverage unverified; never set or clear them. Compare
configuration eligibility again after observation. These are the existing native
defaults, not changes to native settings or scientific parameters.

Open eligible datasets read-only with allowed drivers restricted to GTiff and
AAIGrid. Discovery supplies an explicit sibling list containing the source
basename and preflight ordinary companions only. World-file candidates include
`.wld`, the source extension plus `w` (for example `.tiffw`) and its first/last
letters plus `w`, with case variants, independent of the identified driver.
Reject opaque RPC/IMD/RRD sidecar layouts before restricted discovery rather
than silently hiding them; they are outside verified coverage. Exclude opaque metadata,
masks and overviews from automatic sibling reopening. Inspect each eligible
mask/overview separately with the same restricted discovery options, and retain
those explicit companion edges and digests in the composed proof even when the
root file list omits them. Actual GTiff/AAIGrid replacement probes show this
prevents GetFileList from opening a newly replaced WarpedVRT auxiliary; a final
stat check alone cannot undo its remote requests. Recheck versions/membership
on failed inspection too: observed drift raises source-change instead of being
reclassified as initially unverified. Discovery options apply only to inspection;
the original numerical native operation receives its unchanged path/options.
Before GetFileList, reject reuse coverage for a nonempty OVERVIEWS or
other unproven external-dataset metadata relationship. Actual probes show a true
TIFF can encode a remote OVERVIEW_FILE internally without any sibling sidecar;
metadata inspection itself makes no request but GetFileList fetches it. A local
WarpedVRT disguised as `.msk` or `.ovr` also fetches during root inventory. These
preconditions prevent the proven eager cases without adding a URI/XML parser.
Any reported member outside the proven ordinary local/auxiliary closure makes
the observation unverified. Recheck companion membership and selected identities
before accepting it; a changed eligibility decision cannot bless an old graph.

Unverified inputs are passed unchanged to the original native operation. Do not
change process-wide GDAL options, prohibit native formats or introduce remote
validators. This bounded observer does not claim to certify every GDAL option or
auxiliary mechanism. New coverage requires retained native read-set, authority
and timing evidence before adding it.

Missing, denied, malformed or unavailable dependencies cannot authorize a prior
cache hit. When inspection cannot establish proof, record an explicit reason and
run the existing native operation uncached, preserving its success/error boundary.
Never turn a native dependency exception into a reusable missing-file sentinel.

Recheck membership and file versions during observation; reject an observably
mixed observation. Retain each observation's physical file versions, selected/resolved identities,
companion-parent directory versions and effective configuration as a separate
read guard across the whole native/reuse interval. Do not put this guard into
numerical identity: metadata-only changes between completed calls still reuse
content. Comparing only pre/post hashes is insufficient when a writer changes
pixels during native computation and restores the original bytes afterward.
After native materialization or cache-hit selection, repeat
the complete observation and compare both content and the captured read guard
before admitting/returning its result. A verified
pre-observation becoming changed or unverified rejects admission and derived
publication with an explicit source-change error. The bounded summary cache
must admit only after a matching post-check, not cache a raw result and raise
outside the cached function. Initially unverified input preserves native success
without claiming this coherence proof. No isolation from arbitrary writes after
final validation is promised.

## Consumer rules and compatibility

C03 includes both subwatershed and MOFE rasters plus the existing MOFE structure
identity. Mapping labels remain outside the pair-count identity because the
caller applies them after counting. Legacy persisted signatures conservatively
miss; the next normal management build establishes the new signature. Keep the
existing cache fields, locking, management values and generated WEPP formats.
A miss must reach actual native counting and updated management areas. On both
hits and misses, observe the complete two-raster set before and after counting
or reuse, and recheck MOFE structure/source selection before installing counts
or publishing derived management areas. Rejection must preserve prior management
values/files and their cache association, including reused runtime-generated
management summaries. Individually valid sequential raster
observations are insufficient proof of a coherent pair.

C04 retains the bounded eight-entry summary cache, but its key includes verified
raster dependency identity. The native summary executes only on a miss or an
unverified observation. Recheck even a cache hit before returning it. Native
absence, invalid-input exceptions and optional summary semantics remain intact;
no Python raster summary fallback is permitted. The packaged color-map resource
retains its existing code/version ownership, outside this runtime-file scope.

This contract does not yet change C01 outside-lock finalization, C02 mixed
feature-export inputs, C05 Geneva geometry or C06 aligned burn artifacts. Their
publication and provenance boundaries require separate checkpoints. Bypassing a
numerical cache is not evidence of safe outside-lock publication.

## Validation and cost

Exercise absent, empty, populated, legacy, malformed and denied inputs; same-byte
metadata operations; same-size content changes; masks/world files/overviews;
non-GTiff auxiliary datasets; and source changes during observation/native work.
VRT, Zarr and local ZIP cases exercise unchanged uncached native behavior,
including real source rewrites, rather than claiming complete graph discovery. Use actual native
results and generated management artifacts, not only digest comparisons. Explicit
unverified cases must still reach the original native success/error boundary.

Representative acceptance uses disposable copied GTiff SBS inputs and both
small WBT and large TOPAZ/AAIGrid MOFE owners on warm NFS. Complete C04 summary
hit mean must be <=25ms; native-miss added mean <=50ms. Complete paired C03
validation, including structure, eligibility, discovery, digest and coherence
checks, must be <=75ms settled and <=400ms with cold/evicted digests. Both whole
management elapsed time and actual lock occupancy may add <=100ms settled or
<=450ms cold/evicted against paired controls on the same owner. Include normal
NoDb persistence, management Parquet output and completion hooks in whole times.
Retain first-owner initialization separately; do not call warmed-owner evidence
a cold-process or cold-storage guarantee.

Measured interleaved large-case baseline/composed means are894/945ms for a hit,
1604/1661ms for a settled miss and1580/1916ms for a cold-digest miss. Complete
paired observation adds47–51ms settled and328ms cold; lock additions are54–58ms
and334ms. Native counting alone costs~762ms, establishing that dropping AAIGrid
reuse would violate the intended settled budget. Large SBS native summary costs
~476ms; composed guarded hit is~9ms. These measured compositions support the
budgets but do not prove final implementation conformance. Repeat with all final
companion/configuration/metadata guards and actual512-entry eviction pressure.

Settled representative hits must perform no native numerical work or full
payload digest rereads. The ordinary digest cache remains512entries; initial
admission and eviction may rehash. Unverified layouts always perform their
existing native work, with that explicit compatibility cost recorded. No
representative VRT/Zarr/ZIP workload currently establishes a need to extend
verified coverage. The synthetic580-member Zarr pressure case is not authority
for a new aggregate cache or recursive framework.
