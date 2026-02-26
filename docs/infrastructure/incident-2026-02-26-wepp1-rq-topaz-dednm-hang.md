# Incident Report: wepp1 Unresponsive During TOPAZ `dednm` Hang
> Date: February 26, 2026 (UTC)  
> Scope: WEPPcloud RQ execution on `wepp1` / `wepp2`

## Summary
On **February 26, 2026**, `wepp1` became intermittently unresponsive while long-running TOPAZ `dednm` processes consumed extreme CPU and memory in RQ workers.  
The proximate trigger was a TOPAZ pruning loop bug that can run indefinitely for specific channel-network states:

- `IF(X0001.GE.2)CYCLE J2` in TOPAZ `SUBROUTINE PRUNE`

This caused sustained worker pressure, abandoned RQ jobs, and degraded Redis/worker behavior. Service recovered after killing runaway processes and deploying a patched `dednm` binary.

## Impact
- Intermittent HTTP/HTTPS timeouts and degraded responsiveness from `wepp1`.
- RQ instability:
  - job abandonment (`AbandonedJobError`)
  - worker churn and dead worker processes
- High resource consumption:
  - `docker-rq-worker-1` peaked around ~`205.9 GiB` memory and very high CPU.
- Temporary operational mitigation included stopping WEPP RQ workers on `wepp2`.

## Detection
Observed symptoms during incident window:
- `wepp1` public endpoints timing out.
- `redis-cli` and Redis client pings timing out from peer hosts.
- Worker logs showing:
  - `Temporary failure in name resolution`
  - `Timeout reading from socket`
- Redis logs showing repeated:
  - `Asynchronous AOF fsync is taking too long (disk is busy?)`

## Timeline (UTC, February 26, 2026)
1. **15:01:58**  
   Job `de82d263-a7db-41ba-8868-24fd2ba39339` started:  
   `build_subcatchments_rq('childbearing-insemination', {})`
2. **15:04:17**  
   Job `a080435f-0561-4b48-b5a2-95f889b424d8` started:  
   `build_subcatchments_rq('lipophilic-legitimation', {})`
3. **18:45:57**  
   Multiple long-running subcatchment jobs moved to failed registry with `AbandonedJobError`, but corresponding compute processes persisted.
4. **18:54-19:10**  
   Redis repeatedly logged AOF fsync lag / disk-busy warnings.
5. **19:44-19:58**  
   Worker logs showed repeated DNS resolution failures for `redis` and socket timeouts, with worker deaths/restarts.
6. **~20:05 onward**  
   Host became responsive again; investigation confirmed stale high-memory worker trees still running.
7. **Post-incident remediation**  
   Runaway worker/process trees were terminated; TOPAZ source patch applied and binary rebuilt/deployed.

## Technical Findings
### 1) Stuck TOPAZ processes mapped to specific runs
Runaway `dednm` processes were traced to:
- `/wc1/runs/ch/childbearing-insemination/dem/topaz`
- `/wc1/runs/li/lipophilic-legitimation/dem/topaz`

These aligned with the long-running `build_subcatchments_rq` jobs above.

### 2) TOPAZ logic bug in `PRUNE`
In `/workdir/topaz/src/dednm.f90`:
- before: `IF(X0001.GE.2)CYCLE J2`
- after:  `IF(X0001.GE.2)EXIT J2`

The previous branch could re-enter `J2` without state progress, creating a non-terminating loop under qualifying network topology.

### 3) Infrastructure-level amplifiers
During compute saturation:
- Redis persistence lag increased latency.
- Worker DNS/socket errors increased worker churn and abandonment behavior.

These were significant amplifiers but not the primary algorithmic defect.

## Corrective Actions
1. Killed runaway high-memory RQ worker/process trees on `wepp1`.
2. Stopped WEPP RQ workers on `wepp2` during triage.
3. Patched TOPAZ source (`PRUNE` loop break condition).
4. Rebuilt `dednm`.
5. Deployed patched binary into WEPPpy runtime path:
   - `/workdir/wepppy/wepppy/topo/topaz/topaz_bin/dednm`

## Deployment Notes
First replacement binary was built on host and linked to a linuxbrew loader path, causing runtime `FileNotFoundError` in containerized subprocess execution (loader path not present in container).  
Final deployed binary was rebuilt inside `wepppy-rq-worker` to ensure container-compatible dynamic loader and verified via Python `subprocess.Popen`.

## Verification
- User verified `lipophilic-legitimation` workflow was functional after deployment.
- Container runtime check confirmed patched `dednm` launches successfully from WEPPpy execution environment.

## Related Commits
- TOPAZ source fix (`topaz` repo): `2503f1fbb8951afaea0b3fb63b50ccc6069a1e11`
- WEPPpy bundled binary update (`wepppy` repo): `8ba81eb317690336880d305ee6558fcada3843be`

## Follow-up Actions
1. Add CI/runtime check to verify ELF interpreter compatibility of bundled binaries in container context.
2. Add defensive loop-iteration guard/logging around legacy TOPAZ pruning loops.
3. Add an operator runbook entry for rapid triage of:
   - orphaned RQ worker trees
   - Redis fsync lag signatures
   - DNS resolution failures inside worker containers
4. Evaluate whether additional TOPAZ non-interactive safeguards are needed for outlet-prompt loops during automation.

