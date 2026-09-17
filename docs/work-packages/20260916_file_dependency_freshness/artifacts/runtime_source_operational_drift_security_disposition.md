# Runtime source audit: bounded operational-file drift disposition

**PASS for the explicitly scoped RQ acceptance-audit exception below. Whole-tree
physical immutability failed and must not be claimed.** This authorizes no named
source write/repair, production guard change or baseline replacement. Reviewer:
`freshness_security`, 2026-09-17; independent read-only source/evidence review.

## Confirmed evidence

The direct Omni operation's original manifest reports a successful post-run
check of all3916 source files, hashing6,375,730,842bytes and requiring their
original physical versions, completed at08:21:04 UTC. Its SHA-256 is
`d23a24ae279544316ec2fbe22283dc3da97d20884ad099afab66f8cf2092a982`.
The immutable original copy manifest at
`/wc1/batch/qa-omni-native-20260917-a61f3e/copy-manifest.json` has SHA-256
`67986a74a89690f97a1a1e44c8c845740117a757a0f25bd6eb52ae47367447ee`.

The later live RQ driver's [first attempt log](runtime_omni_sbs_rq_initial.log)
fails `verify_source` with `Named source version changed: TTL`. The source
preflight is before Omni hydration, upload copying, RedisPrep lookup or enqueue
in that driver. The original failed attempt is valid evidence of the stricter
assertion's failure, not an Omni task failure or permission to repair the source.

[Correctness observations](runtime_omni_ttl_observations.json) identify four
changed source versions. Independent read-only inventory and verified reads now
confirm the same exact set, original modes and original byte digests in
[security observations](runtime_omni_operational_source_security_observations.json):

| Exact source-relative path | Physical difference | Current bytes/mode against original |
| --- | --- | --- |
| `TTL` | New inode, mtime and ctime;427bytes | Exact original SHA;0644 |
| `disturbed.log` | Same inode/size, new mtime and ctime;83255bytes | Exact original SHA;0644 |
| `ron.log` | Same inode/size, new mtime and ctime;237bytes | Exact original SHA;0644 |
| `watershed.log` | Same inode/size, new mtime and ctime;6488bytes | Exact original SHA;0644 |

File membership is unchanged and all other3912 files retain the original strict
device/inode/size/mtime/ctime tuple. The inventory rejects nonregular files and
nonordinary directories. The independent read used no source owner hydration;
the original manifest bytes remained unchanged. It rehashed only the four
operational files, not the full6.3GB source tree; the next final RQ audit must
still perform its full source byte check.

## Maintained writer trace and attribution limit

The retained scheduler log schedules `access_log_compile` at08:21:17 UTC.
[Batch worker evidence](runtime_omni_ttl_batch_logs.txt) records actual
`compile_dot_logs_rq` job `3f8a415d-e8dd-4469-b785-44fe335be797` running from
08:21:27 to08:21:35. The three logs changed around08:21:30 and TTL at08:21:34.

The maintained code explains precisely these same-byte physical writes:

- `wepppy/weppcloud/_scripts/compile_dot_logs.py:_load_run_metadata` hydrates
  Ron and Watershed and reads `ron.has_sbs`; `NoDbBase.has_sbs` hydrates Disturbed.
  `NoDbBase._init_logging` opens the component log and calls
  `Path(log_path).touch(exist_ok=True)`.
- The compilation loop calls `touch_ttl` with each retained access-log time.
  `run_ttl.touch_ttl` writes even when that time is not newer, and
  `_write_payload` replaces the file through a temporary path. TTL still records
  `last_touched_by=access_log` and the pre-runtime timestamp
  `2026-09-17T00:36:57.875513Z`; no newer access value is present.

This is strong matching temporal/code evidence for routine scheduler activity.
It is not process-level syscall attribution or proof that no other process
touched a file. Exact observed byte/mode equality, rather than that attribution,
is the acceptance condition. The audit must report actual metadata drift even
if the scheduler explains it.

## Smallest acceptable continuation

Use a new retained RQ attempt with an explicit audit-only allowlist for the four
exact relative paths above **on this same named source and original manifest**.
Do not modify the source, restore timestamps, rewrite the original baseline,
disable the scheduler or alter a production freshness predicate.

For each preflight/final audit:

1. Preserve the ordinary-file/directory and complete file-membership checks.
2. Keep the original strict physical version requirement for every other file;
   no wildcard `.log` exception or other missing/unreadable path is allowed.
3. For each of the four operational files whose physical version differs,
   perform the existing coherent descriptor/path verified read and require the
   exact original SHA, length and mode. Any changed bytes, mode, type or read
   error must fail. Record both versions and the verified original digest.
4. Preserve the full final byte audit of all3916 files and all existing
   disposable project, source selection, native/queue and module-version guards.
5. Record the four metadata exceptions separately. Report byte preservation
   and strict preservation of the other3912 file versions; set any claim of
   whole-source physical immutability to false. Retain the initial failure and
   original copy/direct manifests unchanged.

This is an evidence-backed distinction in a disposable runtime audit, not a
general permission to ignore operational writes or a security risk acceptance
for changed production code. It cannot waive scientific-file, NoDb, SQLite,
publication, authorization or membership invariants. A new unexplained path,
changed operational content or broader writer effect remains a blocker requiring
its own retained evidence and review. No source repair is requested or approved.

## Acceptance-harness conformance

The corrected `runtime_omni_sbs_rq_acceptance.py:verify_reviewed_source` was read
after this disposition. It uses an explicit
`--accept-reviewed-operational-metadata` flag and a separately named attempt;
the default still invokes the original strict verifier. Its changed-version
branch checks exact original SHA, byte length and mode, and performs a second
complete inventory/version/mode check after all reads. Final verification keeps
full hashing enabled. It records the observed exceptions and sets
`whole_tree_physical_identity_unchanged` false when present. This meets the
bounded conditions above. Actual queued/native execution and final source audit
results remain the correctness/runtime review's next evidence, not a result of
this static harness review.

## Final runtime result

`runtime_omni_sbs_rq_result.json` binds the successful revision2 manifest
SHA-256 `b3da2df3a743971a77a33206f677f5cb903d7cf698e704841c29c352e2049a75`;
independent readback matches. Its final audit rehashes all 3,916 original source
files and 6,375,730,842 bytes, records only the same four byte/length/mode-equal
operational physical differences, preserves the other strict versions and
membership, and explicitly reports whole-tree physical identity unchanged as
false. Both the four-job native tree and three-job consumed-source skip pass.
This supplies the previously pending actual runtime evidence for the narrow
exception; it does not extend its source scope or change the immutable baseline.
