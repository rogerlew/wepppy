# Live cutover checkpoint

2026-11-06 06:34 UTC. Private evidence directory on each host:
`/var/tmp/wepppy-production-cutover-20261106`.

- Candidate: `8d079b41db466fda5235a599c151324190393e9d`.
- Eight original application/worker containers verified exited, PID zero.
- PostgreSQL `accounts-quiescent.dump` SHA256:
  `2ed9d243168dd247f69048b4db156dcaa8012a9db37e4815207644df584b492f`.
- Redis `redis-quiescent.rdb` SHA256:
  `ccb82587b264a8a652fee9217569878d3777d1bd0df95924a9962e2e51421756`.
  All-database snapshot size: 1,366,035,866 bytes.
- `permit-retirement.log`: exactly two reviewed completed permits removed;
  remaining ledger metadata and historical pilot bytes preserved.
- `live-migration.log`: production head f6b8d27a901c, 5,416 users, 33,444 runs,
  9,444 ownership rows and 11 feature memberships unchanged; new tables empty.
- `deploy-live.log`: canonical wepp1 deployment running.

No feature activation or final deployment acceptance is claimed by this checkpoint.
The first database dump attempt used an absent postgres role and failed before
reading data; the successful dump used the container's configured POSTGRES_USER.
