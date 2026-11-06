# Preflight validation — 2026-11-06 UTC

Candidate base: `2111d0eb2`; only owned deployment prerequisites and documentation
will be committed. User-selected WEPP 261029 defaults remain unchanged.

- Actual shipped scheduler integration: failed on batch; passed after default
  repair (1 passed, 8.93 seconds). Checks real admission, receipt acknowledgment
  and generated catalog contents using disposable Redis.
- Catalog/scheduler/notifications focused set: 186 passed, 11 warnings, 39.39 seconds.
- Deployment contract/plan/execution set before probe repair: 72 passed, 34.06 seconds.
- RQ dependency graph: current.
- Frontend lint passed; Jest: 124 suites, 1067 tests passed. Production smoke
  harness supports separate evidence/credentials; independent review passed.
- Broad suite: running; no completion claim.
- Deployment registry probe: original get_job_ids performs cleanup on RQ 1.16.2.
  Initial cleanup=False attempt was rejected by independent inspection of the
  installed 1.16.2 signature. Final repair uses Redis ZCARD on registry.key;
  stale entries conservatively block deployment and are never cleaned by probes.
  Fresh deployment execution tests: 38 passed, 33.18 seconds. Extracted exact
  probe returns 0 on both wepp1/wepp2 installed 1.16.2 runtimes; independent
  review also verified installed forest 2.12.0.
- Private baseline configuration/container/source copies saved on all three hosts
  in `/var/tmp/wepppy-production-cutover-20261106` (directory mode 0700).
- Existing project image IDs tagged `wepppy-cutover-rollback-20261106:<digest-prefix>`
  on each host; no image/volume deletion.
- wepp1 account PostgreSQL custom-format backup SHA256:
  `b11bacd3c34ebb21bd3f819774d2144086b2732ad1e61bcceb00e55074eae24e`.
  Restored to owned `cutover_rehearsal_20261106`; guarded migration passed.
  User/run/runs_users/membership counts preserved: 5416/33444/9444/11.
  Target server `10.20.0.3/32`, revision f6b8d27a901c; both new tables empty.

Raw logs, configuration, database backups and credentials stay outside git.
The existing RQ dashboard 502 is baseline; no new service is introduced.

Production after rehearsal: e7a1c9d204bf, notification table absent, original
5416/33444/9444/11 counts unchanged. Live migration is still pending.
