# C08/C09 implementation security review

Independent reviewer: `freshness_security`, 2026-09-17 UTC. Reviewed the working
report implementation after `7d78e9810`, including the independently reviewed
relocation refinement `32c7bed70`, actual native/query readers, retained
correctness/QA evidence and filesystem probes. Only disposable probes and
artifacts were written by this reviewer.

## Findings and disposition

**Scoped PASS after the verified corrections below.** No unresolved medium/high
security finding remains in this bounded implementation. Runtime browse/download,
identity parity and wider package acceptance remain separate gates.

- **RP-SI01, Medium, closed: partial translator absence concealed read denial.**
  With a verified C08 cache, deleting one translator Parquet and removing read
  permission from the other returned historical rows. Both file orderings were
  independently reproduced using real chmod and the actual translator. The
  corrected missing-resource boundary inspects every surviving prerequisite
  before granting absence; both after-probes raise actual `PermissionError`.
- **RP-SI02, Medium, closed: historical C09 required a new catalog write.**
  With readable cache rows, all required tables removed, no catalog and run mode
  0555, the constructor failed trying to create `_query_engine`. It now observes
  that historical state without activation or writes. The after-probe returns
  the same historical rows and verifies the catalog directory remains absent.
- **RP-I02, Medium, independently verified closed: malformed proof bypass.**
  An invalid object-valued alias field was accepted as historical after the
  corresponding table/catalog entry disappeared. Complete accepted dependency
  validation now precedes missing-state comparison and historical path use.
  The same after-probe raises `ValueError`. This corroborates correctness's
  separately retained null-valued proof case.
- **RP-SI03, Medium, closed: rejected historical context blocked a valid build.**
  Removing the catalog and changing complete readable sources made the first
  rebuild fail with a false dependency-change error: unknown historical aliases
  were compared with newly activated aliases. The corrected path reacquires a
  normal context before production. It reuses only this call's earlier file
  observation when physical selection agrees, never the accepted cache hash;
  the post-query observation remains fresh. The actual after-probe returns the
  changed 900 mm result in one call, with `cache_status=built`.
- **RP-I01, High, independently verified closed: copied-run selection.**
  Correctness retained the original-project 100 mm result from a copy containing
  900 mm inputs. The reviewed refinement now normalizes one report-local context
  for both query SQL and observations. The independent absolute-path copy probe
  returns 900, binds the local file observation, preserves catalog bytes and
  leaves the original report unchanged. Existing parent/standalone, current
  absolute selection and escaping-path regressions also pass.

The native missing-translator spelling correction, proofless partial-history
parser validation and missing-catalog redirected-history correction are recorded
as RP-I04/RP-I03/RP-I05 in the correctness review. Their reviewed behavior is
consistent with the accepted contract. No generic parser, I/O, translator or
native-execution failure is converted into historical success.
The final low diagnostic precision is also closed: C08 historical logging now
distinguishes the missing selected source, missing translator prerequisites and
the specifically unavailable native API rather than logging only a generic
verification failure.

## Independent evidence and characterization limits

All commands use the canonical container and disposable inputs; permission
cases assert a non-root identity and provoke actual filesystem denial. Native
aggregation, Parquet readers and DuckDB results are real. Only controller
acquisition is isolated through a real Watershed object/translator. Publication
ENOSPC uses a bounded syscall fault seam; the maintained suite additionally
provokes actual directory-write denial.

| Retained artifact | Result |
| --- | --- |
| `reports_implementation_security_probe.py/.log` | 10 passed characterization/control cases, including both partial-denial defects and the original read-only historical failure. |
| `reports_proof_security_probe.py/.log` | 1 passed characterization of malformed alias proof accepted under absence. |
| `reports_implementation_security_after_probe.log` | 12 passed across the three named after-probe files: corrected denial/history/proof behavior, changed source IDs, restricted payloads and descriptor generation. |
| `reports_relocation_implementation_security_probe.log` | Original positive test fails on the false missing-catalog rebuild conflict; remaining cases were not run because of maxfail. |
| `reports_relocation_implementation_security_probe_revision2.log` | 5 passed after correction: one-call rebuild, copy/proof agreement, unrelated entry isolation, denied historical selection and rejected outside historical path. |

Two obsolete-ID characterization attempts did not reproduce the predicted old
failure: ID 2 remained a valid channel ID in the first fixture, and the revised
fixture ran while the source-first correction landed. Their failed assertions
remain in `reports_changed_ids_security_probe*.log`; they are not counted as
successful baseline reproductions. The positive after-probe verifies that a
changed source discovers its new native IDs, rebuilds valid rows and becomes
current. Likewise, `reports_unrelated_catalog_security_probe.log` ran after the
selected-entry restriction landed and returned correct rows; its old
expected-failure assertion is retained, not claimed as a reproduced runtime
failure. Positive after coverage verifies the required noninterference.

## Integrity and access boundaries verified

`_read_cache` obtains rows and embedded proof from one opened descriptor. The
independent replacement probe switches the canonical path after that open and
confirms the reader returns the complete old rows with old proof while the path
holds the new generation. Descriptor drift is rejected; ctime-only unlink
changes do not invalidate an intact older descriptor. The version-only sidecar
does not carry a mutable rows-to-source association.

New report payloads and status files under an existing 0600/0640 cache retain
those modes; attempts use 0700/0750 respectively, protecting native temporary
work. A publication failure preserves exact prior cache bytes and mode while
keeping native/query output, annotated candidate and failed status. C08 retains
its existing canonical nonregular/alias rejection; C09 keeps an allowed cache
symlink and atomically replaces its selected target after rechecking selection.
First creation retains worker umask semantics. No process identity, permission
policy or source repair is introduced.

Before/after dependency checks protect native and query publication; source-ID
reuse requires unchanged source bytes. Native H.wat remains streamed and only
the compact result is annotated. Scientific columns, calculations, effective
mapping precedence, Roads fallbacks and scope separation remain intact.
Concurrent complete candidates carry distinct matching provenance. Atomic
replacement is the commit point; late diagnostic failure is logged without
rolling back another writer or misreporting a committed generation as failed.

C09 context normalization touches only the three consumed catalog entries and
never rewrites the stored catalog. Existing resolver checks apply to ordinary,
rebased and historical selections. The independent forged outside-path proof
probe receives a containment `ValueError` before an unreadable outside file can
be read. A legitimately redirected historical input still raises permission
failure when denied. Historical paths are observations of prior inputs under
current authority; unknown catalog aliases prevent a currentness claim and do
not authorize a new query.

## Broader evidence and remaining acceptance

`reports_affected_final.log` records **87 passed** across the affected report
suite, including actual native/DuckDB source changes, real publication denial,
legacy native-unavailable compatibility, selected parent assets, deterministic
overlapping publications and canonical archive/restore. The archive test checks
members and restored cache/attempt bytes and reopens both reports at the same
root; separate copy tests cover relocation. Earlier failed collection/probe logs
remain retained. The broad-exception gate, stub completeness check and stubtest
for both public report modules pass.

QA's actual representative implementation benchmark records C08 build 1.574 s
with two full 81,150,978-byte hashes, one native ID scan and one summary; settled
complete construction averages 17.82 ms with persisted mapping and 32.52 ms with
Parquet mapping. C09 build is 51.48 ms with two hashes per input; settled complete
construction is 11.26 ms. Settled reads have no hash bytes or producer calls,
and actual 512-path eviction requires one source hash without rebuilding. These
meet the ratified local budgets. That snapshot predates the final small
historical/selected-entry corrections and is not an exact-revision timing claim.

The benchmark uses actual detached controller hydration with Redis disabled and
OS-warm storage. Live report URLs, restricted-attempt browse/download, Redis
singleton acquisition and production-equivalent identities/mounts remain runtime
work. Cross-filesystem cache destinations remain an explicitly unproven
acceptance risk; this review does not approve external staging or a new fallback.
The source observations do not promise arbitrary concurrent-writer isolation.
No deployment or package closeout is approved by this artifact.

Final reviewed SHA-256 values:

- `_cache_freshness.py`: `9b84e9c2ccf621976b1c7f47b762161a0d2bda5c15481a77437a6f967a4896c3`
- `hillslope_watbal.py`: `b3a14b6cbfa068207d5d0c459b36b3a67f196f505c86b6fbf60f8d0a96620d2d`
- `average_annuals_by_landuse.py`: `d8063ff1fbc9fba1f34e531c6788f3ffba0822feeb64dbe24f94a8b3900860ad`
