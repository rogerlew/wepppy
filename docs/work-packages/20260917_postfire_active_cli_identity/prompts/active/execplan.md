# Repair active post-fire CLI identity

Follow docs/prompt_templates/codex_exec_plans.md. Owner requested the fix.

## Purpose / Big Picture


Normal WEPP hard-link creation during an M3 run must not discard unchanged
scientific inputs. Real changes must still prevent stale publication.

## Progress


- [x] Cause identified: only active CLI ctime differs, content identical.
- [ ] Contract/checkpoint independent reviews.
- [ ] Failing baseline and bounded implementation with regression.
- [ ] Full applicable tests, independent reviews and restarted-worker acceptance.
- [ ] Named run recovery, durable docs, evidence and closeout.

## Surprises & Discoveries


The prior contract intentionally retained strict active-worker metadata equality,
even after accepted-result content comparison was repaired. User's overlapping
WEPP/M3 run exposed this missed valid workflow.

## Decision Log


2026-09-17 UTC: narrow exception only for active_cli ctime drift, with unchanged
path/size/mtime, explicit admission-time digest and fresh coherent uncached hash.
Other source metadata, selections, legacy snapshots and artifact guards retain
strict checks. No acceptance-time hash is fabricated.

## Outcomes & Retrospective


Pending implementation and actual runtime verification.

## Context and Plan of Work


Repository /home/workdir/wepppy. Edit production.py and run_preparation.py under
wepppy/nodb/mods/postfire_debris_flow after contract checkpoint. Add one worker
snapshot comparator used at admission, authority checks and preparation rebasing.
Verify changed active CLI through strong signature's descriptor-bound hash;
require observed signature remains equal to current snapshot. Do not reuse the
permissive accepted-result comparator for other source files. Extend real NoDb/
native M3 tests; add adversarial helper tests as needed. Independent reviewers
verify race handling and absence of a general metadata waiver.

## Concrete Steps and Validation


Run wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_runtime_m3.py during
iteration, affected post-fire suites, then wctl run-pytest tests --maxfail=1.
Inspect Docker instructions and canonical deployment entry before restarting
web/rq-worker. Retain actual source-prepared worker run with deliberate normal
WEPP climate materialization overlapping execution on a disposable clone, plus
real-content invalidation. Use normal UI/RQ to recover thespian-cleanness only
after confirmed fixes, protecting earlier acceptance and other project inputs.

## Idempotence and Recovery


Retain failed artifacts and previous accepted records. No new schema or run-wide
cache clear. No rollback requires deleting scientific data. Stop stale candidates
rather than publishing when hash, path or generation verification fails.

## Artifacts and Interfaces


Records under artifacts; project outputs remain in normal browsable attempt
paths and archives. No public API/schema changes. Final docs describe behavior,
limits and exact runtime evidence. Independent review/checkpoint precedes code.
