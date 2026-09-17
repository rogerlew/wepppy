# Freshness contract decision: post-fire first wave

Status: independent correctness/security checkpoint reviews passed; implementation not started.
Base: `adb4f9b004459fc578460a95f30ac01ae1421f36`.
Authority: owner instructed “execute docs/work-packages/20260916_file_dependency_freshness/”.
This executes the package's specified content-equivalence intent and checkpoint
commits, without production deployment or writes to named investigation runs.

## Scope and discrepancy

The real `copy_input_file` baseline changes ctime alone and makes post-fire
signature equality false. This is an intended contract refinement because the
current production contract explicitly uses stat identities for live readiness.
Adopt the proposed canonical file-dependency freshness contract in production
M1/M3 documentation. Keep strict worker publication comparisons, owner settings,
soil/SQLite snapshots and path policy. Other audited consumers require subsequent
coherent waves; do not claim the inventory or package complete with this fix.

## Compatibility and regression plan

Add `content_sha256` to new source snapshots, retain existing stat records and
artifact format. Compare accepted source content only with complete hashes on
both sides; legacy records retain exact-stat behavior. New malformed hashes fail
closed. Rollback readers conservatively treat new snapshots as stale. No state
migration, accepted-results rewrite, parameterization change or cache flush.
Engine fingerprint changes may independently stale historical results; preserve
that behavior and validate newly produced results on disposable projects.

Exercise real hard links, removal, touch, chmod, same-byte replace, changed bytes,
equal-size/restored-mtime rewrite, missing/empty inputs, legacy state, symlink
rejection and mutation during hashing. Test actual get_state/report/RQ downloads
and generated attempt files in addition to helper behavior. Downloads hash and
stream the same descriptor with before/after metadata guards. Preserve archive
payloads using canonical archive/restore and validate live UI/RQ/WEPP propagation.

## Performance decision

`digest_baseline.json` records 1.18 MB CLI (6.2 ms cold, 29 microseconds warm),
26.4 MB DEM (89 ms cold, 27 microseconds warm) and a 4 KB immutable SQLite snapshot
(2 ms cold, 30 microseconds warm), inside weppcloud. These are page-cache states,
not a claim of flushed disk-cache benchmarks or representative live WAL size.
First-wave acceptance: no content bytes read on 100 consecutive warm checks of
unchanged files; under 1 ms per warm file; single rehash after metadata change;
cold throughput no worse than 2x baseline on the same files (rerun if noisy).
The representative M3 source inventory contains 179 files totaling 68,689,513
bytes, plus 26 engine files and five result artifacts. The existing 64-entry
cache would thrash. Increase the existing bounded cache to 512 entries, enough
for two representative working sets without a new cache abstraction. Retain
counts and measure actual repeated state reads; multi-project eviction remains
bounded revalidation, not a correctness failure.
SQLite coherent-snapshot timing remains required for its later wave.

## Security and valid-state matrix

High impact as scoped by package. Preserve root containment, symlink rejection,
regular-file checks, owner authority, coherent descriptor identity and explicit
failure. Absent optional state stays absent; present-empty files retain a real
empty-byte digest; populated state preserves scientific values; legacy records
never acquire unproven acceptance hashes; malformed/hostile state cannot gain
currentness or stream unauthorized bytes. Review evidence must cover valid-state
noninterference and rejection independently.

## Review disposition

Independent reviews in `contract_correctness_review.md` and
`contract_security_review.md` pass the first-wave checkpoint. COR-01 cache
capacity and SEC-C01/C02 publication/descriptor precision are resolved in the
canonical text; COR-02 hashless-download test drift is classified below.
All runtime and full-package gates remain open. Commit this accepted checkpoint
as an ancestor before implementation.

## Review clarifications before implementation

The RQ hashless-download behavior is a conformance defect: production_m1 already
requires accepted-file SHA-256 verification, and production writers emit five
fields. The existing route test expects a four-field record to stream; replace
that mistaken fixture with a real strong signature and add a hashless-rejection
regression. This does not fabricate historical hashes or remove saved report
values. Hashless currentness retains documented strict metadata behavior.

Climate prerequisite readiness still compares CLI/parquet mtime. A touch can
therefore leave accepted content current while new-run readiness is false. Track
that as a separate open readiness consumer, not a first-wave acceptance claim.
The hard-link trigger leaves mtime unchanged and does not hit that boundary.
