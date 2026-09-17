# Cache-admission amendment security review

## Findings and verdict

**PASS for the proposed amendment checkpoint. No unresolved medium/high
finding in this bounded design. No implementation or runtime approval.**

The observed same-key collision invalidates the immediate-cache assumption in
the first checkpoint. The proposed uncached observation interval addresses that
specific sequential rewrite failure without changing path authority, accepted
content semantics, legacy state, or scientific calculations. Implementation must
still pass the retained original real-clock reproduction and the acceptance
conditions below; a design review cannot close the confirmed code defect.

| ID | Severity | Finding / disposition | Status |
| --- | --- | --- | --- |
| SEC-I02 / FWC-01 | Medium, confirmed integrity defect in unreleased implementation | Retained probes show different six-byte contents with exactly equal device/inode/size/mtime/ctime and an old cached digest on overlay and repository filesystems. Immediate reuse is unsound for those operations. The amendment prescribes uncached observation, followed by fresh hashing at admission. | Contract remedy accepted; implementation closure pending. |
| SEC-I01 | Medium, availability in initial implementation | Cache-miss hashing read all 3,145,736 bytes after an 8-byte file grew. The ADR now requires captured-size-bounded reads. | Contract requirement accepted; implementation closure pending. |

No risk acceptance is recorded. The first-wave implementation remains held under
[its security review](first_wave_security_review.md), and NoDb mixed-generation
hydration remains a separate open package finding.

## Metadata and reviewed authority

- Reviewer: independent `freshness_security`, 2026-09-17 UTC.
- Existing ancestor: `43317704fd046faffac39e114634bb155213c547`.
- Reviewed proposal: `docs/adrs/20260917-file-digest-cache-admission.md`;
  `docs/schemas/file-dependency-freshness-contract.md`, Timestamp-quantum cache
  admission amendment; `artifacts/cache_admission_amendment.md`.
- Evidence inspected: `first_wave_ctime_collision_probe.py`,
  `first_wave_ctime_collision_probe.json`,
  `first_wave_ctime_collision_probe_nfs.json`,
  `first_wave_correctness_review.md`, and the reviewer's disposable growth probe.
- Security triage remains high because file-integrity/currentness checks are
  changing. This review covers the amendment strategy only, before its code.

The NFS probe reported zero collisions in its tested iterations. That is bounded
negative evidence, not proof that NFS cannot collide. Overlay/repository results
are sufficient counterexamples to immediate reuse without invoking hostile
timestamp manipulation, privileged metadata forgery or an external attacker.

## Why the bounded correction fits the evidence

A newly observed path/version receives a monotonic first-observation time.
During the next second every access hashes current bytes and does not reuse an
earlier digest for that key. Thus a second write inside the observed timestamp
quantum is read again even when the full stat tuple remains equal. Once the
interval elapses, admission requires another fresh read; no digest from the
observation window may be promoted without rereading.

This reasoning relies on the explicitly stated filesystem requirement: metadata
is coherent on open and the relevant timestamp collision quantum is no longer
than the observation interval. Monotonic elapsed time avoids comparing client
wall-clock age with server ctime. A filesystem outside these assumptions is not
made safe by elapsed time. The ADR appropriately requires retained evidence and
a revised contract before claiming coarser-quanta support.

The rule is a cache-reuse constraint, not a substitute for coherent acquisition.
It does not establish arbitrary concurrent multi-file snapshot consistency or
make metadata-only finalizer checks stronger. Descriptor/path before-and-after
checks, strict publication, uncached execution hashes, source inventory closure,
authorization, and soil/SQLite guards retain their existing obligations.

## Required implementation and noninterference evidence

1. During observation, two reads with the same stat key must consume current
   bytes separately. Retain the real-clock rapid-rewrite probe without sleeps
   that would conceal the original failure. Clock injection is appropriate only
   for deterministic admission branch coverage.
2. First admission after maturity must compute a fresh digest. An observation
   entry's eviction must restart the interval and must prevent reuse of any
   surviving digest entry for the same key. Test the interaction of both bounded
   caches, not merely their individual maximum sizes.
3. Bounded reads must reject growth promptly, reject truncation or identity
   changes explicitly, and never turn failed reads into reusable content proof.
   The implementation should use captured size plus bounded extra-byte growth
   detection; there is no need for a new global scientific-file size policy.
4. Warm hits still check present read permission and descriptor/path authority.
   Stable files preserve zero content reads over the settled warm-read gate.
   New/changed files can incur repeated cold work during observation; measure
   this across the representative working set and interleaved projects.
5. Absent optional inputs remain absent, empty files retain the empty-byte hash,
   legacy snapshots retain strict metadata semantics, and no acceptance-time
   hashes are fabricated. Metadata churn can restart observation without
   independently staling content-equivalent accepted outputs.
6. Authentication, no-follow project/download paths, fixed artifact inventories,
   strict finalizer ownership and immutable accepted values remain unchanged.
   Test changed content through state and actual artifact/download boundaries,
   along with valid hard links and restore operations.

## Process, observability and rollback

The implementation is unreleased. Commit the amended canonical contract, ADR
and independent review disposition before implementing this strategy. This
review neither waives the original independent correctness/QA requirements nor
the final security review after them. Retain failed probes, intermediate logs,
timing data and current code revisions as package evidence.

The prior automated-tool-failure report remains documented in
`first_wave_security_review.md`; it is not an approval or a reason to omit
findings. This review used only repository documents and retained local fixture
evidence. No production/named-project data, secrets or external targets changed.

Rollback must not restore known-unsound immediate reuse while retaining the new
content-currentness claim. If the real filesystem probes or measured budgets
fail, keep rollout held and revise the checkpoint. Rebuild/restart, disposable
UI/RQ/WEPP and archive/restore acceptance remain required and unreviewed.

Security reviewer sign-off: `freshness_security`, 2026-09-17 UTC, **amendment
checkpoint only**. Package owner acknowledgment and checkpoint revision remain
the main agent's responsibility; no package closeout is authorized here.
