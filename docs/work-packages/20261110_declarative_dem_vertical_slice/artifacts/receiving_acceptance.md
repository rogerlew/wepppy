# Receiving acceptance — 2026-11-11 UTC

Roger authorized executing the deployment handoff and a proper deployment with
its table migrations. Receiving evidence is retained in
[open-wepp-org](https://github.com/rogerlew/open-wepp-org/tree/main/docs/work-packages/20261110-declarative-dem-canary).
Production Compose on wepp1/wepp2/wepp3 was untouched.

## Deployment and correction

- Source `f02e78cc083322a387a9415f120b4ede5911c935`, image workflow
  [42925712492](https://github.com/rogerlew/wepppy/actions/runs/42925712492).
- Linux/amd64 child `sha256:fdcd5d44bd0332ad7ec8575602efffced804d5f9c8c669a21162ecabe4e11dd4`.
- Fresh encrypted backup `20261108-032445F_20261110-151938D`; transactional
  Alembic upgrade `e7a1c9d204bf` → `f6b8d27a901c`, both notification tables verified.
- First image exposed NFS redundant-attribute writes and RQ rejection of
  `__main__` function objects from the real CLI. Corrected source preserves exact
  access metadata and uses canonical fixed task names. Original failed project
  and uncertain finalization intent are retained, never replayed.
- Actual-image NFS Ron initialization and repeated snapshots pass under UID 1000,
  GID/groups 993, umask 0022, exact mode 0644 and unchanged ACL/SELinux attributes.
  Native imports and exact runtime image IDs pass. No privilege/storage change.

## Live acceptance

Successful public fixture `declarative-420b71117ee9447fac8692369ef6f410`:
science `a5114747-641c-4dd1-944b-df665c4481ad`, finalizer
`70e6cf98-f3ef-4ba4-a0cb-add6d494b0d0`, Pod UID
`89be98a3-38da-4d02-8af4-b17cad049e33`, node `worker-dell-02`.
Both jobs finished; durable READONLY and verified completion, real Git checkpoints.
Raster: EPSG:32611, 37×26, 962 valid cells, 30 m, SHA-256
`10b6b95c574f8a90e6fe5ebed0a56ae68f90f38129cd434c8d7cb04302698134`.
Acquisition 1.8468 s; hash/readback 0.0723 s. These do not bound large DEM costs.

Authenticated actual HTTP page, elevation (1032.540283 m), browse/download,
mutation refusal and archive/restore pass. The 16-file protected manifest,
provenance and history stay unchanged. Bootstrap enable/checkout/no-prep routes
return explicit protection 409. A fresh real queued mutation is refused by the
custom worker before task invocation, preserving original jobs/fingerprints.

Seven sequential owned projects retain initial failure, success, induced source
failure, checkpoint failure, finalizer failure, running cancellation and worker
loss. Failed science stays false/read-only after settled finalization; failed
protection stays false and repeat finalize never retries. Invalid source and
wrong/missing runtime evidence reject before writes; duplicate admission preserves
job IDs/state. Duplicate queue delivery remains covered by real-RQ source tests;
original live job IDs were not overwritten to manufacture duplicate evidence.

Cancellation observed actual STARTED execution, stopped workhorse, complete lock
cleanup and no executions before canceled/read-only finalization. Worker loss
observed STARTED, pinned and stopped only its real workhorse, then UID-bound Pod
deletion. Fast GC defeated terminal-row polling; exact-ID Talos CRI events prove
exit 137 before removal. Application cleanup remains not_requested, state remains
incomplete/unverified, and no finalizer/replay was attempted. Observer identity
is explicitly separate from the lost executor.

## Validation and operational closeout

- Corrected boundary suite: 106 passed, zero skips, real disposable Redis.
- Corrected NoDb/RQ broad run: 5586 passed, 182 skipped, 5466 warnings, 2469.09 s.
  Skips include opt-in/live fixtures, absent datasets and separate fixtures that
  require container redis-server. Do not call this a zero-skip full suite.
- RQ graph and changed-doc lint pass. Original full-suite continuation ledger
  retains 6401 unique passes/241 skips and the reproduced unrelated TTL-help
  assertion; original frontend 1069 passed. No clean current full-suite claim.
- Prior broad-run forest test overlay was hash-checked then restored to its initial
  commit for exactly seven files; unrelated preexisting edits were preserved.
- PR217 (`6070ff1cad9e96a4806bcacbd09bc7fa0f1d13eb`) removed the last dedicated
  overlay; app Flux resumed. All 18 nodes Ready, all desired consumers healthy
  at the exact image, 15 ordinary workers idle, normal queue counts unchanged,
  public health OK, migrated schema verified. All projects/evidence retained.

Large-DEM observation cost, private elevation authorization, general workflows,
Bootstrap, automatic replay and compatibility shims remain excluded/deferred.
Recovery must preserve guards and working NFS snapshots; keep additive schema.
Final independent review is recorded in receiving `artifacts/security-review.md`.

The optional ordinary climate report returned HTTP200 HTML on this DEM-only
project, with protected fingerprints unchanged. An initial test assumption that
this report must fail was disproved; no compatibility failure is claimed.
The final whole-suite invocation on four exact f02 production/test overlay files
is complete as an invocation:13793 collected, failed-first/no exclusions, stopped
on the identical known TTL-help baseline assertion (1failed/1skip). It does not
claim exhaustive execution. See final_full_suite.txt and actual failure artifact.
All four final overlays were hash-checked and restored after the terminal result.
