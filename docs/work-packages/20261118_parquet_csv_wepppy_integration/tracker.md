# Parquet CSV integration tracker

**Started / updated**: 2026-11-18 UTC
**Phase**: M1/M2 implemented; focused validation and image build in progress
**Branch**: `codex/parquet-csv-cli-package`
**Security impact**: high; dedicated reviews required, not yet performed
**Plan**: [implementation_execplan.md](prompts/active/implementation_execplan.md)

## Progress

- [x] Inspect accepted standalone evaluation and current download branches/contracts.
- [x] Scaffold package, draft durable contract, checkpoint and active ExecPlan.
- [x] Record immediate cutover, no environment-facing configuration and no Python fallback.
- [x] M0: Resolve compatibility, filter/environment contract changes, fixed settings and HTTP errors.
- [x] M0: Independent contract reviews and checkpoint ancestor commit.
- [ ] M1: Promote/package native CLI and harness; close required compatibility gaps.
- [ ] M2: Wire all covered CSV routes, response ownership and shared admission; remove old path.
- [ ] M3: Exact-image workflow/resource/security validation; broad tests after wiring.
- [ ] M4: Final reviews, documentation, release/rollback handoff and evidence-based closeout.

## Decisions and rationale

2026-11-18, operator: immediate native cutover, no environment-variable-facing
configuration and no Python fallback. A single release path avoids retaining the
old resource-heavy implementation as a hidden failure mode. Exact wording is in
[integration contract: Authority and cutover policy](../../schemas/parquet-csv-integration-contract.md#authority-and-cutover-policy)
and [Configuration ownership](../../schemas/parquet-csv-integration-contract.md#configuration-ownership).

Prior operator decision retained: broad repository tests wait until integration
is wired. This scaffold receives documentation checks only. Scaffold work does
not authorize deployment. No runtime changes or changes to the closed evaluation.

## Discovery and open M0 work

`_download.py` has unfiltered, filtered and file-like/NoDir CSV branches. Confirm
which virtual paths remain reachable under retirement policy. The active filter
contract currently references environment-backed enablement and row caps; the CSV
surface needs an explicit amendment, with other consumers preserved.
The wepp1 overlay uses eight browse workers and a 120-second Gunicorn setting;
the standalone harness has 180-second staging/conversion ceilings. Verify actual
ASGI/proxy timeout semantics and resource budgets rather than copying defaults.
Standalone unsupported schemas/codecs are release blockers where currently valid.

## Validation and handoff

Scaffold validation: six Markdown files passed lint with zero errors/warnings;
spelling previews and whitespace checks passed.
Runtime tests, independent reviews, binary/image builds and deployment: not run.
Next: execute M0 of the active plan when implementation is requested. Retain exact
contract/binary/source identities, generated HTTP byte readback, no-fallback proof,
shared-worker admission and crash/disconnect evidence before any cutover claim.

## Execution updates

2026-11-18 UTC: operator authorized execution. Retained an inventory of 156 real
files, including climate timestamps, null columns, Zstandard and GeoParquet WKB.
Independent read-only contract reviews are in progress. No implementation changes
or broad tests yet.

Operator approved temporary conversion storage, with original Parquet and
correlated service diagnostics retained. Exact rationale: "the .csv could become
stale but users wouldn't realize it". A CSV is generated freshly per request,
never retained as a potentially misleading project output or reused as a cache.

Additional operator rationale: retained CSVs suggest automatic model generation;
users would interpret absence as missing output. Keep CSV explicitly on demand.

Operator explicitly approved rejecting invalid UTF-8 metadata, preserving raw
Parquet access. The canonical contract records the bounded exception. Security
checkpoint approved; final correctness confirmation pending after dispositions.

M0: both independent reviews approve the final contract; all medium/high findings
closed. Documentation checks pass. The next commit is the required standalone
checkpoint ancestor; its full SHA will be recorded before production edits.

Checkpoint ancestor: `a1f40de48bce439520fd47bb5e8d3f9ae0167bd0`.


2026-11-18 UTC implementation: promoted the single supervisor into production,
wired all CSV routes, removed production Python CSV serialization and retained a
test-only oracle. Added protocolv2, native filters and required compatibility,
shared inherited leases, wall/parent-death termination, stream/disconnect cleanup,
fixed image packaging and a canonical deployment preflight. No live service changed.

Focused runs progressed through113,178 and186 passing checks while identifying
and closing compatibility/test-fixture issues. Six real compatibility files match
oracle bytes (initial evidence at /tmp/csv-v2-real-readback.json). Independent
read-only implementation review is active. Final focused run, exact image,
full corpus/resource evidence and broad suite remain open; no completion claim.

Dictionary amendment ancestor: `3fefd089d`; both reviewers approved before source
threshold edit. Exact 131,072/131,073 boundary and real-file parity are next.

Focused acceptance: 208 native/route/lifecycle checks passed (receipt
`2f719ee5ef6a476fa144608e9c507f91`); 152 adjacent filter/auth/security checks passed
(receipt `8f88d21621874924a12c1cfb6162687b`). Rust: 13 passed, including amended
dictionary boundary. M1/M2 implemented and wired. M3 exact-image/corpus/broad
acceptance and M4 final reviews remain in progress.

Column amendment ancestor: `9a4642a01793922c80b4f399cf30d8cd83e94837`; threshold
edits followed independent approvals. Final native source plus whitespace cast
regression and successful-outcome log retention committed in `c433c6ee3`.
Final focused run: 213 passed; all 46 selected real files match legacy bytes.
Exact-image identity/negative/readback checks and broad acceptance remain open.
