# Active CLI identity implementation security review

Independent reviewer: `active_cli_security`, 2026-09-17 UTC. No production or
test files edited by this reviewer.

## Findings and gate status

**Final security gate: PASS, 2026-09-17 19:15 UTC. No open medium/high findings.**
Final reviewed production revision: `1003fe9addfcfc308ecdfdce56a3f36011845536`.
This security gate covers the scoped repair; overall package closure also owns
the final correctness/QA disposition and documentation.

- **SEC-01, medium contract conflict, closed:** the checkpoint's shared and
  domain amendments explicitly bound the worker exception; see the separate
  contract security review.
- **SEC-02, low test-evidence defect, corrected:** the first
  `after_read` injection made another hard link before the strong signature.
  Adjacent link operations could share a ctime value while bytes remained
  unchanged, so the expected rejection was not guaranteed. The independent
  run retained in `security_focused.log` reproduced this. The amended test
  injects a real observable mtime change between snapshot and verification;
  the byte-change/restored-mtime and stale-cache regressions remain separate.
  `focused_final.log` now passes all 153 selected tests, closing this evidence
  defect. The test is named for its snapshot-to-verification boundary.
- **SEC-03, medium, closed: source preparation upgrades legacy hash authority.**
  In `run_preparation.py:59`, `rebase` assigned the full newly observed `snapshot`
  to the attempt after `_worker_source_snapshots_current` accepted a hashless
  admission by exact stat equality. `sources(content=True)` includes fresh
  hashes, so subsequent CLI ctime churn can use a digest absent at admission.
  An absent-source legacy attempt therefore gains content-equivalence authority
  that the active CLI contract explicitly withholds from legacy snapshots.
  The correction preserves absence of `content_sha256` in rebased inputs when
  original admitted inputs lack it, after validating the complete fresh map.
  Promoted source metadata and hashed admissions retain their behavior. The real
  native regression fails before the patch (`legacy_baseline.log`); both
  watershed fixtures now succeed without churn while retaining hashless
  acceptance and reject later link churn without replacing that acceptance.
  `legacy_final.log`: 21 preparation/legacy regressions passed, 55 deselected,
  115.04 seconds. Independent code and evidence inspection closes this finding.

## Reviewed implementation and ancestry

The standalone contract checkpoint is `567eacf7d`, parent
`0b5d063d3947e8a2ed56f7d9b3f73a7fd6ac7cc5`. It includes both independent contract
reviews and promoted amendments, without production code. The inspected
implementation is committed as `2b00c4165`; subsequent bounded legacy and
malformed-shape corrections are committed as `1003fe9ad`, descended from that
checkpoint and confined to `production.py` and `run_preparation.py`.

`_worker_source_snapshots_current` validates any present content maps, requires
their equality when both exist, then compares all remaining snapshot fields.
The only normalized field is the active CLI's ctime. Its path, size and mtime
must match, and the admission hash must already be valid. A changed other-file
ctime, source inventory or selection cannot use the exception. A hashless
admission retains strict equality. Explicit dictionary/source-inventory shape
checks preserve stable rejection of malformed inputs without a TypeError;
they do not admit new source states or alter the no-follow/hash boundary.

The exceptional path calls `signature(..., strong=True)`, retaining the existing
uncached descriptor-bound hash, component-wise no-follow regular-file opener,
full descriptor/path generation checks and byte-count limits. Its returned
four-field stat record must equal the current source observation and its digest
must equal the admission digest. This prevents a stale cache or a newer observed
path generation from authorizing the ctime waiver. Exceptions remain explicit.

Both M1/M3 admission paths retain a deep copy of admitted authority and exact
outer snapshot fields. M1 strict attempt/dNBR checks continue to use that
authority. M3 source preparation applies the comparator only after the existing
owned pointer/receipt exclusions; complete present hash maps must still match
before rebasing. The rebase cannot bless changed climate bytes. Shared
pre-publication and locked authority checks use the helper, while all existing
result, predictor, uploaded-artifact and SQLite/soil checks stay strict.

No authorization, CSRF/session/token handling, routes, queue dependencies,
subprocess construction, network destinations, secrets or persisted schema
changed. The security impact is bounded scientific-input integrity and valid
workflow availability, not a new external attack surface.

## Evidence inspected and remaining gates

`focused_final.log` records 153 passing tests in 345.97 seconds, including 24
native M3 link/unlink/rematerialization cases at queued admission, absent-source
preparation, result completion and locked publication across two native
soil/terrain fixtures, plus all three M1 stages. The actual WEPP input
materializer, native raster/model work, fresh owner state and publication run;
only the source-acquisition seam supplies local prepared source data.

New adversarial helper tests exercise changed bytes with restored mtime,
changed path/mtime/selection/other-source ctime, malformed or missing admitted
hashes, mismatched current hashes, poisoned cached digest, symlink replacement,
descriptor/path replacement and read-time generation drift. The independent
initial run passed 16 such/valid cases and exposed SEC-02. Existing tests retain
strict artifact, live SQLite/WAL, newer-attempt and failed-replacement protection.

Restarted-worker overlap `fa299be5-45b0-448b-b1d1-718445c1529a` finished and
published accepted attempt `68186dc8d0d74673a04be41ca9767853`. Independently
verified that ordinary WEPP materialization ran 7.46 seconds after the worker
started and before it ended. The raw nanosecond identity proof retains unchanged
device/inode/size/mtime and SHA-256 with changed ctime. Browser state and report
were current. Runtime identity was uid1000/gid993, group993, umask0022 on the
actual forest mounts. The 1,151,532-byte CLI strong signature took 9.48 ms.

The real equal-size/restored-mtime edit in job
`5bff6acb-16ad-4252-aeae-f3668c4e3509` produced a different digest and was
rejected as `superseded`. Accepted attempt `68186dc8d0d74673a04be41ca9767853`
remained retained. Restoring the exact original CLI bytes restored currentness.
`browser_clone_records.log` confirms ordinary browse HTTP200 access to the
failed attempt directory, status, error log and accepted result directory.
The canonical archive regression passed (one test, 24 deselected); this is
archive-code regression evidence, not a new full live-run archive/restore.

`security_runtime_verification.json` records independent read-only rehashes of
the five browser-downloaded result artifacts against their retained disk files,
the restored CLI digest, exact admitted/mutated raw identity assertions and
the changed source modules' hashes matching the actual runtime snapshot.
The browser's JavaScript integers round nanosecond timestamps; comparisons use
the separately retained Python/raw JSON records, not those rounded numbers.
`source_copy_verification.json` also reports the original 6,840,257,872-byte
source inventory unchanged during disposable-copy setup.

Normal named-run recovery subsequently passed as job
`0fd409ce-8e3c-480a-af2c-8a5fd571c7f8`, accepted attempt
`0c7899f7ac6f464e80e3f873a4c75fe1`. The identity record confirms unchanged
original CLI bytes/size/mtime/ctime and unchanged admitted source hashes; only
engine identity differs from the original failed attempt. Browser verification
shows currentness and HTTP200 access to original failure and new result records.
Earlier transient submission failures remain retained as unsuccessful attempts.

The initial overlap/negative runtime evidence covers `2b00c4165`, before the
bounded SEC-03 and malformed-shape corrections. After freezing `1003fe9ad`, web,
rq-engine and rq-worker were restarted again. A normal named Run then completed
job `0c3bb451-0e7a-4814-95f5-3f1d2f219d49`, accepted attempt
`8190121c8a4b45e1952861e74d909693`. `browser_named_final.log` verifies currentness
after reload and all five downloadable artifacts. Independent raw NoDb readback,
code hashes and original CLI signature/digest checks are retained in
`security_final_runtime_verification.json`; both final production modules match
the accepted engine fingerprint and the frozen commit. Original failed and
previously accepted attempt files remain present. Independent rehashes confirm
the final five downloads match their disk artifacts and seven original failure/
accepted-result records match their pre-repair hashes. The final named browser
record check also passes: original failure directory/status/error and current
result directory remain available through ordinary browse (HTTP200).

Validation scope is explicit: the full-suite run began against the main repair
and finished with 8,971 passing tests and 99 skips in 1,401.59 seconds. It is not
represented as a clean full-suite run begun after the final corrections. Those
corrections have 107 passing boundary tests (`final_boundary_pass.log`), 21
passing legacy/preparation tests, and a final frozen-code run of both native
legacy fixtures (`final_native_legacy.log`, two passed in 36.99 seconds). This
combination, the unchanged narrow modern-attempt exception and final restarted
named-run evidence meet the scoped security gate. Broad QA disposition remains
the package owner's separate responsibility.

## Residual risk

This remains bounded before/after source observation under normal filesystem
metadata semantics. It is not arbitrary-writer snapshot isolation. Churn during
the coherent read can still fail explicitly; stable same-byte link churn outside
the read must pass. The unchanged strict fast path does not acquire a new general
content-verification policy. No additional cache bypass, retry or relaxed source
identity is authorized beyond the active CLI exception.
