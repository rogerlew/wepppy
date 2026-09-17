# M1 security inventory

Reviewer: independent `freshness_security` agent, 2026-09-17 UTC. Baseline:
`adb4f9b004459fc578460a95f30ac01ae1421f36`. This is discovery evidence, not
implementation approval or the final dedicated security gate. No production
code, named project, cache, permission, or service was changed by this review.

## Findings first

| ID | Severity | Finding and execution path | Evidence | Required disposition |
| --- | --- | --- | --- | --- |
| SEC-M1-01 | Medium, confirmed integrity defect | `NoDbBase._hydrate_instance` and `load_detached` read generation A, then independently stat the pathname. A concurrent atomic replacement with B during decoding causes A to acquire B's signature. Cache validation then accepts stale A as current B; a later mutation can start from the wrong durable state. | `wepppy/nodb/base.py:1306`, `:1355`, `:1520`, `:1549`; retained real-filesystem probe below. | Bind loaded bytes and tracked version to one coherent read; preserve retry/error, locking, and post-commit contracts. Adding fields to the later pathname stat alone cannot fix this race. Carry as open until reproduced by regression and corrected. |
| SEC-M1-02 | Medium, confirmed freshness defect | Post-fire accepted source equality includes ctime, and accepted artifacts include mtime/ctime. A hard link, chmod, or byte-identical replacement can invalidate a result without a scientific change. The RQ download also rejects accepted unchanged bytes when timestamps differ. | `production.signature`, `sources`, `get_state`, `artifacts_current`; `postfire_debris_flow_routes.download`. Existing report restore regression demonstrates the independently correct size/hash policy. | Separate content equality from live object/race identity at the contract checkpoint, preserving source provenance and strict execution/publication guards. |

SEC-M1-01 is an application integrity race, not a demonstrated remote access
bypass. Its concurrent writer may be an ordinary cooperating producer; atomic
replacement prevents partial JSON but does not itself bind a separately read
payload and stat. No medium/high finding is waived by this inventory.

## Scope and threat model

Reviewed source and immediate consumers: post-fire production state/digests,
soil snapshot/preparation and activation, report attachments, RQ accepted-file
download, NoDb hydration/persistence, derived publication, runtime file reads and
WEPP hard-link materialization. Other repository consumers are assigned to the
main M1 inventory; this artifact does not claim repository-wide completeness.

Threats considered are concurrent cooperative writes, authorized run-file
replacement, restore/re-materialization, malformed persisted records, symlink
swaps, and modification by a process already able to write a run. Hashes do not
grant path authority, authenticate a source, or make a set of independently read
files a coherent generation. Privileged control of the kernel/filesystem or
simultaneous forgery of every trusted manifest is outside this review's claim.

Security impact remains **high**, and dedicated checkpoint/final reviews remain
mandatory under `docs/work-packages/README.md` and its security-review template.
Correctness/UX and QA are separate gates. Absence, populated legacy state,
byte-identical restore, read-only runs, and failed replacement are valid states
that security controls must preserve according to their owning contracts.

## Classified inventory

| Consumer / symbols | Producer and persisted identity | Classification and obligations |
| --- | --- | --- |
| `production.signature`, `sources`, `get_state` | `NoDb` accepted snapshots contain `[relative path, size, mtime_ns, ctime_ns]`; strong artifact records append SHA-256. Climate build and `_prep_channel_climate` alter the same source inode. | Scientific freshness currently conflates content and inode metadata. Keep relative source path, model/soil policy, settings, completion authority, engine and tool identity separate from content. Never infer a historical hash by hashing today's file. |
| `production.cached_digest`, `_digest_version`, `engine_identity` | LRU key is path plus device/inode/size/mtime/ctime, capacity 64; hashes code and WBT binary. | Cache hint, not accepted-content equality. Ctime protects equal-size/restored-mtime rewrites; device/inode catches replacement. A miss hashes a path after stat without a post-read identity check; require coherent admission before caching if extended to mutable run inputs. Metadata-only changes should cause rehash, then preserve an equal digest. No unlimited raster rehash on every poll. |
| `production.artifacts_current`, `reuse_predictors` | Accepted artifacts/predictors record optional fifth hash; strong checking only requests a hash when existing record length is 5. Reuse also verifies manifest source hashes, tool hash, engine identity and support policy. | Legacy four-field signatures lack content proof. Their present stat-only treatment must be explicit, not silently upgraded to content-current. Strict verification must still cover exact inventory and meaningful manifest/policy changes. |
| `production.execute_upload`, `execute_model`, `execute_m3` | Workers take source hashes, build into attempt directories, recheck sources, and publish under `PostfireDebrisFlow.change`; M3 also verifies soil snapshot. | Content, admission authority, and concurrent-publication guards. Preserve strict source snapshots inside execution, attempt identity checks, source-hash checks, retained failure artifacts and prior acceptance. Metadata equality alone is not permission to accept a mixed generation. |
| `soil_snapshot.source_state`, `_copy_source`, `snapshot_cache`, `verify_snapshot` | Source main/WAL/SHM identity is `[dev, ino, size, mtime_ns, ctime_ns]`; main and WAL are copied, then tables are read in a transaction; schema and sorted typed logical-table hashes are retained. | Object identity/read-coherence guards, plus persisted soil identity. Preserve `O_NOFOLLOW`, regular-file/size limits, all sidecar presence checks, rejection of rollback journals, before/after source checks and final recheck. Do not hash only the main DB or use immutable mode on a live WAL database. |
| `soil_inputs.dependency_state`, `_copy`, `prepare_soil` | Tracks present and absent sources, masks, metadata and original labels; source evidence and artifacts have hashes; post-copy verifies source and target. | Dependency closure and race guard. Content equivalence cannot erase THICK source ID/units/grid/bounds or explicit SSURGO collection evidence. Absent optional sources must remain usable, and an optional source appearing mid-build must reject publication. |
| `production_soils.inventory`, `verify_soil`, `activate_sources`; `source_preparation.prepare_local_sources`, `promote_local_sources` | `inventory` embeds filesystem dependency state and SQLite state into post-fire selections; promotion receipt binds grid/MUKEYs/cache identity/hashes plus previous manifest identity. | Metadata-only changes to soil sources can still mark accepted M3 stale. This needs its own content-versus-logical contract and evidence; do not remove identity checks from active preparation/promotion to fix it. Source-state comparison also binds the receipt to the authoritative basin and prevents stale promotion. |
| `report._artifact_record`, `open_assessment`, `Assessment.recheck`, `open_attachment` | Saved result requires a five-field artifact record with valid hash; result catalog is verified against accepted manifest hash. Download opens a bounded nonsymlink descriptor and hashes that descriptor. | Verified-safe content-equivalence pattern: persisted size/hash determine attachment identity; before/after descriptor size/mtime/ctime detect mutation during verification. Accepted assessment is rechecked; failure closes descriptor. Do not replace this with pathname hashing followed by reopening. |
| RQ `postfire_debris_flow_routes.context`, `download`, `DownloadResponse` | JWT `rq:export`, authorized run ID and config check precede accepted-attempt/file allowlist; download opens, stats and optionally hashes one handle. | Auth remains distinct from content. Current timestamp equality causes false rejection after restore. Four-field legacy records currently receive no hash check. Path opening uses `Path.open` after a path check and has no after-hash stat check; preserve or improve descriptor admission when changing this path. No outside-file disclosure was demonstrated. |
| `NoDbBase.getInstance`, `_cache_instance_matches_file_signature`, `_hydrate_instance`, `load_detached` | Writable singleton compares mtime/size strictly; Redis/detached cache uses 1 µs mtime tolerance; `.nodb` durable file is authoritative. | Cache optimization with integrity impact. Restored-mtime same-size replacement is invisible to these keys; the independent read/stat race is SEC-M1-01. Signature errors outside initial retry can leave an existing singleton reusable. Do not remove the scoped retry contract or make Redis authoritative. |
| `NoDbBase.dump` | Distributed ownership check; stale-write `(mtime,size)` comparison; temp write/fsync/replace; monotonic same-size mtime; post-commit Redis mirror. | Concurrency/version safety, not scientific content equivalence. Keep lock token, stale-write rejection, inode checks around forced utime, mode/umask, temp cleanup and committed-versus-failed distinction. A matching digest is not authorization to retry a stale whole-controller mutation. Cooperative locking explicitly does not fence out-of-band writers. |
| `_derived_build.file_signature`, `_identity`, `finalize`, `publish_files` | Input signature is resolved path/mtime/size. Rollback identity is dev/ino/mtime/size. Fresh durable hydration and lock cover publication; backups retain failed or unknown commits. | Input cache/freshness can miss equal-size/restored-mtime rewrite. Rollback identity is ownership of a particular publication: do not change to content-only or overwrite a concurrent same-byte replacement. Preserve containment, flat filenames, nonsymlink targets and unknown-commit recovery copies. |
| Runtime `fs._resolve_contained_path`, `stat`, `listdir`, `open_read` | Resolve path inside run/root; directory listing exposes size/mtime; `archive_fp` is always `None` in active directory mode. | Containment and display metadata, not proof of scientific freshness. Escape tests exist. Path resolution and later `open` are separate calls, so this is not a general adversarial descriptor-pinning primitive. Archive-native runtime access is retired. |
| Runtime `wepp_inputs.copy_input_file`, `materialize_input_file`; `Wepp._prep_channel_climate` | Canonical `climate/<cli_fn>` is materialized as `wepp/runs/pw0.cli` through `os.link`, falling back to copy after link failure. | Legitimate content-preserving producer causing source ctime drift. Keep hard-link behavior unless independent evidence warrants change. Relative normalization is not the stricter report no-symlink contract. Legacy archive/projection arguments are accepted but ignored; they do not activate an archive cache. |

## Canonical contract owners

- Post-fire `specification.md`, `docs/production_m1.md` (especially Publication
  verification and reuse), `docs/production_m3.md`, and `docs/model_selection.md`.
- `docs/ui-docs/contracts/postfire-debris-flow-report-contract.md` governs saved
  result validation, absent optional state, report/download behavior and restore.
- `docs/schemas/nodb-persistence-concurrency-contract.md` governs durable authority,
  cooperative locks, monotonic write versions, retries and stale-write handling.
- `docs/schemas/rq-response-contract.md` governs explicit worker/route errors.
- `docs/standards/artifact-observability-standard.md` governs retained attempt,
  source, incomplete, recheck and recovery evidence.

The old `docs/schemas/nodir_interface_spec.md` explicitly says it is retired;
it cannot authorize an archive-backed implementation in today's runtime helpers.

## Legacy, coherent-read and closure requirements for M2

1. Separate persisted content equality from transient generation identity. A
   ctime change may require revalidation; it must not become a universal content
   change. Keep strict execution/publication/read guards independently.
2. Enumerate four-field and five-field legacy artifact records, snapshots without
   input hashes, missing model (M1), older soil/support policies, absent optional
   soil sources, and absent optional post-fire controller. Never synthesize proof
   that today's bytes are the bytes an older result used.
3. Define cache-miss consistency against the actual opened descriptor and current
   pathname. A hash assembled while a file changes cannot be cached under an
   unrelated stat key. Multi-file reads also need source-set and absent-sidecar
   closure; single-file digest equality cannot provide that.
4. SQLite equivalence requires a consumer-specific choice. The existing typed
   logical hashes and schema are evidence, while WAL/SHM/main identities prevent
   mixed snapshots. Checkpoints may change files without changing relevant rows;
   no checkpoint, source mutation or SQLite recovery may occur during status
   inspection. This inventory does not ratify a new SQLite equivalence policy.
5. Preserve descriptor-based report validation and transfer. Accepted content
   remains readable after byte-identical restore; a new accepted attempt during
   a read yields the existing replacement error, not a mixed response.
6. Changed metadata cannot bypass access loss, symlink rejection, path authority,
   model/source provenance, or meaningful external `.msk` closure. Existing inert
   raster statistics exclusions are consumer-specific, not blanket sidecar
   exclusions.

## Evidence and validation

Searches used `rg -n` over the named paths for `signature`, `cached_digest`,
`st_ctime`, `st_mtime`, `st_ino`, `st_dev`, `sha256`, `symlink`, `resolve`,
`snapshot`, `WAL`, `journal`, and matching regression names. Read each matched
function with its writers/callers and applicable AGENTS/contracts. This security
subset is not the package's exhaustive search ledger.

The retained probe [m1_security_probe.py](m1_security_probe.py) ran with:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/m1_security_probe.py
```

Result (exit 0): both `hydrate` and `detached` returned `loaded_value=A`, with
`disk_value=B` and `stale_payload_matches_current_signature=true`. It invokes
unmodified hydration functions, disables Redis for the probe, and replaces a
real disposable file during a test decoder hook. It does not exercise a real
domain controller, NFS visibility, or a production distributed writer. The
assertion intentionally confirms the failing baseline, not corrected behavior.

Relevant existing regression evidence was inspected, not rerun by this review:

- `tests/nodb/mods/test_postfire_debris_flow_report.py`: byte-identical restore,
  symlink swap at open, descriptor mutation during hashing, replacement and
  currentness failure without loss of saved values.
- `tests/nodb/mods/test_postfire_debris_flow_production_soils.py`: committed WAL,
  concurrent snapshot change, no source writes/companions, rollback-journal
  spill rejection, symlink-swap copy rejection and retained incomplete attempts.
- `tests/nodb/mods/test_postfire_debris_flow_production.py`: source masks versus
  inert statistics and unrecorded external symlink exclusion.
- `tests/nodb/test_base_boundary_characterization.py`: cache mismatch, atomic
  replace contention, monotonic same-size write version, failed replace/retry,
  mode preservation and post-commit fsync semantics.
- `tests/runtime_paths/test_fs_parquet_contract.py`: escaping symlink/root
  rejection. `test_wepp_inputs_compat.py`: supported legacy arguments and
  hard-link failure copy fallback.
- `tests/microservices/test_rq_engine_postfire_debris_flow.py`: accepted/changed
  download, scopes/config/read-only, missing file, mask inventory and disconnect
  handle cleanup.

Local `.venv` import attempted Redis initialization without usable credentials
and logged authentication failures; it nevertheless imported. The actual probe
used the canonical container environment and isolated Redis. No credential was
read, printed or stored, and no import failure was hidden as a validation pass.

## Residual risk and gate status

Discovery complete for this assigned subset. SEC-M1-01 and SEC-M1-02 remain open
at this baseline. No remote exploitation, whole-repository security approval,
performance acceptance, restarted-stack result or final package closeout is
claimed. The final gate must review actual diffs after correctness/QA, close
medium/high findings, and verify both valid restore/link cases and hostile or
concurrent replacement cases under the real workflow identities and mounts.
