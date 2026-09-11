# Validation

Contract ancestor: `6e4c4710a`. Independent contract and source reviews accepted;
correctness requested recovery-dump persistence and rejection of nonpositive
upstream timestamps, both implemented. Security requested actual Redis and live
WebSocket validation, both passed.

- Production tests: 43 passed after adapter extraction; final 8 preflight cases
  passed after recovery-dump change. Prior 35 production cases unchanged.
- Frontend: 863 tests / 111 suites passed; lint passed.
- Go: all preflight packages passed; Redis/WebSocket server integration passed.
- Stubtest: passed after synchronizing six existing missing TaskEnum declarations
  along with the new task; check-test-stubs passed.
- Real Redis/NoDb probe: [script](redis_boundary.py), [output](redis_boundary.log).
  Publication, replacement clearing, lock/pipeline, and redisprep.dump restoration
  verified on a disposable project under the dev container identity.
- Live `addicted-reservist`: authenticated state remained current, partial=true,
  accepted publication `a366dd8557a249aab845905defb5658b`, original completion
  `2026-09-11T02:34:06.048757+00:00`. Explicit reconciliation recorded timestamp
  `1789094046`; no model job or artifact rewrite was performed.
- Rebuilt/recreated dev preflight and reloaded the actual web master PID 6.
  Live WebSocket returned postfire_debris_flow=true, with only the existing
  type/checklist/lock_statuses/last_modified envelope.
- Browser navigation/reload check passed: 🌋, unchanged label, placement after
  Gridded RUSLE, correct latest job ID, and indicator retained after reload.
  [Script](browser.cjs), [output](browser.log).
- Docs and diff checks passed; changed broad-exception delta is zero.
- Full Python suite remains on operator hold. No production fleet deployment.

The notification adapter is separate from production.py because that source file
is included in existing scientific engine fingerprints. Its pre-task bytes are
preserved; no fingerprint bypass, legacy artifact migration or implicit GET
mutation was introduced. The retained old production.notify helper is left in
place for fingerprint compatibility; the facade now uses preflight.notify.
