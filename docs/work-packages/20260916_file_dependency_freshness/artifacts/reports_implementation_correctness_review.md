# C08/C09 implementation correctness review

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Scope: report
implementation after `7d78e9810`, with the separately reviewed relocation
refinement at `32c7bed70`. No production/test edits. **PASS for the bounded
implementation after the corrections below; no remaining major correctness
finding.** This is not package/runtime completion.

## Findings and retained direct evidence

**RP-I01 — High, resolved: relocated C09 selected the original project.**
`AverageAnnualsByLanduseReport._observe_inputs` initially passes persisted
`catalog.root` to resolution. Actual query planning also uses that root. In a
complete copied project with the original retained, local runoff changed from
100 to 900 cubic meters but the report returned 100 mm with `cache_status=built`.
With a partial copy and the original removed, it incorrectly reported all three
sources missing. A disposable catalog-root correction is a successful control.
Normalize one cloned context for both actual SQL and observations under the
reviewed relocation checkpoint; changing only hashes would prove the wrong files.
The corrected actual constructor returns local runoff 900 mm, and the partial
copy returns historical rows. Normalization now clones only consumed entries;
unrelated entries cannot reject this report. The maintained regressions cover
relative/absolute copies, inherited parent selection, standalone rejection,
current-root precedence and selected symlink escape. The catalog stays unchanged.

**RP-I02 — Medium, resolved: malformed proof bypassed validation on absence.**
`_cache_verdict` skipped validation when the observation was `None`. An invalid
C09 alias proof set to JSON null, with that source/catalog entry removed, was
accepted as historical. The correction validates the entire accepted dependency
set before comparison. The after-conformance probe now raises `ValueError` for
this same malformed alias, including the missing-source state.

**RP-I03 — Medium, resolved: proofless partial history hid malformed inputs.**
Legacy C09 rows plus one missing source and a remaining invalid-Parquet source
returned historical rows. Readable SHA-256 bytes did not establish that the
remaining prerequisite was parseable. The correction parses surviving tables
when using unverified legacy history. The actual after-probe now raises the
native `ArrowInvalid`, preserving the contracted distinction from archival
absence. Ordinary verified cache hits need no extra full-table parsing.

**RP-I04 — Medium, resolved: exact missing-translator error was misspelled.**
The initial catch compared `chns_ids`, while the actual translator error says
`chn_ids`. Missing translator parquet resources therefore bypassed historical
classification. The current actual report returns `historical_unverified` after
resource removal. The correction also inspects all surviving prerequisites
before classifying a missing peer, so denial/parser failure is not concealed.

**RP-I05 — Medium, resolved: missing catalog lost redirected history.**
After an actual C09 build with a catalog-selected alternate loss file, remove all
sources and the catalog. The empty-context fallback invents the logical default
path, treats its difference from the accepted alternate path as a known change,
and fails historical access. Restoring the same catalog restores historical rows.
Use fully validated accepted paths only as historical observations under current
allowed-root resolution; unknown aliases force historical status. Do not use
these paths for a new query, currentness claim or manufactured proof. Check any
surviving historical bytes and reject known changes/access failures. The final
actual probe now returns `historical_unverified` with the redirected source and
catalog removed. The maintained regression additionally leaves the redirected
file present, verifies historical access without catalog creation, then changes
its bytes and verifies rejection. Full dependency validation precedes path use;
the selected historical paths pass the current allowed-root resolver and do not
become query authority.

`reports_implementation_correctness_probe.py` runs actual native/DuckDB reports
on disposable projects; only Watershed acquisition is injected, retaining the
real translator. Initial and revision 2/3/4 JSON/logs preserve the discoveries;
`reports_implementation_correctness_probe_after_conformance.*` preserve resolved
malformed-proof/parser outcomes. Revision 4 retains redirected-history failure
and its successful catalog control. The after-relocation and after-final JSON/
logs retain the corrected local query, partial-copy and redirected-history
outcomes; earlier failures remain. Temporary projects were removed and named
runs were not changed. Relocation uses actual filesystem copies here; canonical
archive execution is covered separately in the maintained tests.

## Correct behavior and test evidence reviewed

`_read_cache` reads rows and embedded provenance from one descriptor and verifies
its before/after stat while allowing atomic path replacement to leave a complete
older descriptor generation valid. The version sidecar remains generation-free.
Native output stays streaming; only compact output is read into Arrow/pandas and
rewritten for annotation. Native and query output are retained separately from
annotated candidates and attempt status.

Source-first C08 comparison now discards obsolete source IDs after changed source
bytes, then discovers the new set natively. Effective mapping preserves in-memory
summary precedence, actual translator fallback, Roads targets and raw-ID logging.
C09 includes effective alias SQL as well as selected file identity, and its query
uses the captured context. Post-work observations reject drift before publishing.

`_CacheBuild` uses unique visible attempt paths, prepares the version sidecar and
ready status before atomic replacement, and immediately records the commit.
A postcommit diagnostic write failure is logged without rollback. Precommit
failure leaves the canonical cache intact and keeps candidate/native/query work.
C08 canonical destination checks remain distinct from C09 target-preserving file
symlink behavior. Existing modes and restricted attempt access are preserved.

The retained affected logs record 25 passes in revision 2, 35 in revision 3 and
**83 passes** across the report suite in `reports_affected_revision6.log`.
Reviewed actual source/mapping changes, partial history, metadata
churn, build-time mutation, concurrent native requests, symlink/mode behavior,
malformed metadata, missing translator, in-memory precedence, real permission
denial, legacy native-unavailable rules and postcommit status failure. The real
canonical archive test verifies members and restored cache/attempt bytes, then
reads both restored reports as current at the same root. It does not substitute
for the relocation cases above or browser access under production identities.
Deterministic concurrent publications now overlap at the ready boundary and
prove distinct attempts plus matching final provenance. Actual replacement
after cache open proves returned rows and metadata belong to the same complete
opened generation.

The independently retained `reports_implementation_performance_final.json`
uses an unmodified copied catalog, not the earlier catalog-root workaround.
C08 actual build is 1.574 seconds with two full source hashes, one ID scan and
one summary; settled construction averages 17.82 ms (persisted summaries) and
32.52 ms (Parquet fallback), with zero digest bytes/native calls. C09 build is
51.48 ms with two hashes per input; settled construction is 11.26 ms with zero
digest bytes/query calls. These meet the ratified local budgets. After pressure
from 512 other paths, each source is hashed once without producer work. Named
generations remain unchanged and report rows equal the retained baselines.

## Remaining acceptance limits

The representative benchmark uses detached actual controller hydration with
Redis disabled and OS-warm storage. It does not prove Redis-backed singleton
acquisition, cold/NFS storage timing or browser access. Its code snapshot precedes
the final missing-catalog/selected-entry restrictions; those affect historical
and relocation branches without adding source scans or producer work. Restricted
attempts must remain inspectable through normal authorized browse/download;
canonical archive/restore has direct test coverage. Cross-filesystem destinations,
live routes, arbitrary concurrent source producers and broader package inventory
remain separate acceptance work. No deployment or package closure is approved.
