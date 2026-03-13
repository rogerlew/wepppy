# Incident Note: `forest` Dev-Server NFS Client Path Degradation
> Date: March 12, 2026 (America/Los_Angeles)  
> Scope: `forest` (`wc.bearhive.duckdns.org`) create/catalog latency against `/wc1`

## Summary
`forest` began returning `504` for `rq-engine/create/` and `/weppcloud/runs/catalog/` while the same codebase on `forest1` (`wc-prod.bearhive.duckdns.org`) could create runs normally.

The failure signature did **not** line up with PostgreSQL or a simple application regression. The dominant evidence pointed to the `/wc1` client path on `forest`: metadata-heavy NFS operations became extremely slow and, before reboot, could block in kernel RPC wait states.

After rebooting both `forest` and `forest1`, run creation recovered, but `forest` remained slower than the historical dev baseline. Follow-up testing did **not** support the direct `10.0.0.x` crossover leg as the primary cause. Current working hypothesis: `forest` NFS client-path instability on Broadcom/`bnx2x`, possibly aggravated by thermal conditions on HP 530T-class 10GbE adapters.

## Impact
- `rq-engine/create/` timed out behind the proxy instead of completing in a few seconds.
- `/weppcloud/runs/catalog/` also timed out.
- Operators could create runs on `forest1`, so the failure was environment-specific, not code-specific.

## Environment
- `forest` `/wc1`: `10.0.0.2:/` via `nfs4`
- `forest1` serves `10.0.0.2` locally and stores `/wc1` on `zfs_pool0`
- `forest` NFS client interface: `ens5f0`
- `forest1` NFS server interface: `enp131s0f0`
- Both NFS-facing adapters report Broadcom `bnx2x` on Linux `6.8.0-101-generic`

## Detection
Observed during triage:
- `POST https://wc.bearhive.duckdns.org/rq-engine/create/` returned `504`
- `GET https://wc.bearhive.duckdns.org/weppcloud/runs/catalog/` returned `504`
- Equivalent run creation on `forest1` succeeded

## Technical Findings
### 1) Pre-reboot `forest` NFS behavior was pathological
The historical benchmark from [ui-rcds-nfs-vs-dev-nfs.md](./ui-rcds-nfs-vs-dev-nfs.md) used:

```bash
python3 tools/benchmark_nfs_delete.py /wc1/benchmarks/delete-test /tmp/delete-test --fsync-files --fsync-dirs --sync
```

Before reboot, the benchmark on `forest` entered kernel wait states (`rpc_wait_bit_killable` / `nfs_wait_bit_killable`) and could stall for minutes.

Small-file probes on `/wc1` were also severely degraded:
- 10-second 4 KiB write probe without `fsync`: about `1.36 files/s`
- 4 KiB `write+fsync` microprobe mean: about `0.705s`
- 4 KiB read microprobe mean: about `0.750s`

Control results on `/tmp` were normal.

### 2) Reboot restored service, but not historical performance
After rebooting both hosts, `rq-engine/create/` succeeded again and the same benchmark completed:

```text
delete_benchmark_results
- root=/wc1/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=8.352 delete_s=0.949 rewrite_s=8.325 sync_s=0.156
- root=/tmp/delete-test files=3100 dirs=30 size_mb=12.11 create_s=0.599 delete_s=0.088 rewrite_s=4.635 sync_s=0.028

delete_benchmark_results
- root=/wc1/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=8.489 delete_s=0.904 rewrite_s=8.160 sync_s=0.067
- root=/tmp/delete-test files=3100 dirs=30 size_mb=12.11 create_s=0.601 delete_s=0.086 rewrite_s=3.463 sync_s=0.059
```

Historical dev baseline on `forest` (2026-01-31):

```text
- root=/wc1/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=6.185 delete_s=1.331 rewrite_s=4.742 sync_s=0.136
```

So the reboot cleared the hard stall, but `create_s` and especially `rewrite_s` remained worse than the previous baseline.

### 3) `forest1` local storage remained fast
The same benchmark on `forest1` local `/wc1` (`zfs`) completed much faster:

```text
- root=/wc1/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=1.400 delete_s=0.182 rewrite_s=1.389 sync_s=0.010
```

This argues against a code-path regression and against ZFS/local storage on `forest1` being the bottleneck.

### 4) Switching from the direct `10.0.0.x` leg to the `192.168.1.x` leg did not improve the result
For a clean comparison on `forest`, the same `/wc1` export was mounted twice temporarily with forced `nfs3` mounts:
- `10.0.0.2:/wc1`
- `192.168.1.108:/wc1`

Benchmark results:

```text
192.168.1.108 path:
- root=/mnt/wc1-nfs3-192test/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=8.285 delete_s=1.505 rewrite_s=8.016 sync_s=0.105

10.0.0.2 path:
- root=/mnt/wc1-nfs3-10test/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=7.608 delete_s=1.710 rewrite_s=6.539 sync_s=0.131
```

The switched `192.168.1.x` path was not materially better than the direct `10.0.0.x` path. That does **not** support the crossover/direct-link theory as the primary cause.

### 5) Network links were not obviously failing at the physical layer
Both relevant ports reported:
- `10000Mb/s`, full duplex
- `bnx2x` driver
- no CRC, carrier, or MAC errors on the NFS-facing interfaces during inspection

Ping was also clean:
- `forest -> 10.0.0.2`: `0%` loss, `0.239 ms` avg RTT
- `forest -> 192.168.1.108`: `0%` loss, `0.163 ms` avg RTT

NFS client retransmits on `forest` were essentially absent during inspection:

```text
Client rpc stats:
calls      retrans    authrefrsh
99941      1          99941
```

### 6) But the Broadcom paths still looked unhealthy under bulk TCP
`iperf3` across both `forest <-> forest1` paths was below expected 10GbE throughput and showed many retransmits:

```text
10.0.0.x path:  about 6.22 Gbit/s, 5826 retransmits in 10s
192.168.1.x path: about 6.01 Gbit/s, 4718 retransmits in 10s
```

This did **not** isolate the direct leg, because both legs behaved similarly. It does, however, reinforce that these Broadcom/`bnx2x` paths are not especially healthy.

## Assessment
Most likely:
- `forest`-side NFS client-path instability
- Broadcom `bnx2x` sensitivity on this kernel/platform
- thermal aggravation remains plausible

Less likely:
- PostgreSQL
- WEPPcloud application code
- the direct crossover leg specifically
- `forest1` local ZFS storage

Not proven:
- a hard NIC hardware fault
- a failing cable
- a storage-array fault

## Supporting External References
- HPE QuickSpecs for the 530T identify the adapter as Broadcom `BCM57810S` class hardware and list `0-55 C` operating temperature:
  - <https://www.hpe.com/psnow/doc/c04111407.pdf>
- Ubuntu regression tracking exists for BCM57800/57810-class `bnx2x` adapters on 6.8-era kernels:
  - <https://bugs.launchpad.net/ubuntu/+source/linux/+bug/2107347>
- Older `bnx2x` instability history is also documented in Ubuntu bug tracking:
  - <https://bugs.launchpad.net/ubuntu/+source/linux/+bug/1840789>

## Operational Outcome
- Rebooting both hosts restored project creation on `forest`
- No durable application-side fix was required to restore the working path
- The remaining risk is recurrence of client-path slowdown or stalls on `forest`

## Recommended Mitigations
1. Add point-source airflow over the HP 530T adapters on `forest` and `forest1`.
2. Track Ubuntu kernel updates that include the BCM57800/57810 `bnx2x` fixes and retest after upgrade.
3. If the issue recurs, capture the following immediately on `forest` before reboot:
   - `python3 tools/benchmark_nfs_delete.py /wc1/benchmarks/delete-test /tmp/delete-test --fsync-files --fsync-dirs --sync`
   - `nfsstat -rc`
   - `ethtool -S ens5f0`
   - `iperf3` against both `10.0.0.2` and `192.168.1.108`
4. If recurrence continues after cooling and kernel updates, replace or bypass the 530T/`bnx2x` client path for NFS traffic.

