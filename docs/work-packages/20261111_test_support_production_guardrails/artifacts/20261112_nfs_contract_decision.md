# NFS run-log lifecycle repair checkpoint

Starting revision: `06cd266a10a0d48e66bae861b724c79ab7b8bc98`. Implementation pending.

Roger approved the NFS recommendation, forest live browser acceptance, and F6
through M4 on 2026-11-12. This supersedes F7's cleanup exclusion and forest hold
only for the bounded acceptance workflow. Production activation is excluded.

## Decision and rationale

NoDb keeps run FileHandlers on component loggers beyond requests, including
direct constructor objects outside its instance cache. Other web processes hold
independent handlers. Cache cleanup cannot release those descriptors. The real
NFS acceptance returned delete 200 with a remaining directory; process exit
released the handles. Prior query-access forest acceptance reproduced the same
class. Use append-only per-record file lifetime under the existing logging
handler lock, preserving asynchronous QueueListener/Redis/console delivery.
Preserve eager constructor path validation/empty-file creation, releasing that
stream immediately. Late records after deletion report a static sanitized sink
failure and preserve other sinks; never print raw record arguments. Distinguish
stream release from final Handler.close so repeated writes remain supported.
No new queue, registry, daemon or deletion coordination protocol is introduced.

Affected canonical contracts are the test-support contract and NoDb persistence
contract. F5 safe-traceback sanitation remains unchanged and applies to file
I/O diagnostics. The new helper belongs in `wepppy/observability/`; NoDb, RQ
worker, and migration run-file sinks consume it. Batch parent logs are assessed
separately from child run deletion. General deletion workers are excluded.

Support delete returns its existing 200 payload only after actual path absence.
OSError or retained path returns 500 with `{"error":"Run cleanup failed"}`;
server diagnostics stay sanitized. A missing run still returns 404. Failed
creation cleanup must also surface incomplete cleanup rather than hide it.
Authentication and containment remain unchanged. No persisted schema changes.

## Failure class and regression plan

| Consumer/state | Evidence or required check | Disposition |
| --- | --- | --- |
| NoDb direct/cached controllers | Logger retains FileHandler across requests and processes | Confirmed; repair |
| RQ worker run log | Handler removed without close | Confirmed; repair |
| Migration run log | Global logger retains handler; replacement clears without close | Confirmed; repair |
| Batch child run | Batch log lives under parent logs directory | Outside child-run deletion; assess parent lifetime |
| Security audit log | Separate service log, not inside run directory | Outside run lifecycle |
| Empty/populated run | Real filesystem removal; success requires absence | Required |
| Missing run | Existing 404 preserved | Required |
| Invalid bearer | No filesystem side effects | Required |
| Retained/active external writer | Explicit failure; never claim globally serialized deletion | Required |
| Late log after deletion | No directory recreation; file error must not kill listener or other sinks | Required |
| Threaded writes | Complete formatted append records; no idle descriptors | Required |

Benchmark representative queued writes on forest NFS and compare existing
FileHandler; retain measured cost. Test formatting, Unicode, sanitation, close
on failure and shutdown. Run actual multi-process NFS logging/deletion and
browser create/load/delete, read path absence, and scan exact-token retention.
Fresh focused/broad regression and independent correctness/security reviews
remain required. No unsupported concurrent-deletion guarantee is introduced.

## Review disposition

Two independent design reviews support per-record lifetime over cache teardown.
They require explicit active-writer limitations, retained-path failure, migration
coverage, and survival of missing-parent file errors. These requirements are
incorporated above. Independent correctness (`contract_correctness`) and
security (`contract_security`) reviewers approved the exact canonical delta on
2026-11-12 before implementation, with no open medium/high findings. Approval
is for the checkpoint, not runtime acceptance or production activation.
