# UI RCDS NFS vs Dev NFS: Delete/Recreate Benchmark

This note captures `tools/benchmark_nfs_delete.py` results for a metadata-heavy workload (many small files), used to approximate UI RCDS run-tree cleanup pain (create/unlink/rmdir + `fsync` pressure).

## Workload

Defaults (as-run in the captured outputs):

- Tree shape: `--dir-width=5 --dir-depth=2` → `31` directories total (`dirs=30` excludes the root)
- Files: `--files-per-dir=100` → `3100` files total
- File size: `--file-size=4096` → `12.11 MiB` total payload (`3100 * 4096`)
- Flush flags: `--fsync-files --fsync-dirs --sync`

Timings:

- `create_s`: initial create pass (no fsync)
- `delete_s`: delete the tree (`shutil.rmtree`)
- `rewrite_s`: recreate the tree (with `--fsync-*` behavior)
- `sync_s`: `os.sync` wall time (system-wide flush; very sensitive to unrelated IO)

## Results

### Production (WEPPcloud, historical baseline)

Captured output (all flush options enabled):

```
delete_benchmark_results
root=/geodata/wc1/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=30.376 delete_s=4.980 rewrite_s=34.456 sync_s=1.235
root=/tmp/delete-test files=3100 dirs=30 size_mb=12.11 create_s=0.675 delete_s=0.090 rewrite_s=6.749 sync_s=0.906
```

### Dev host NFS (forest.local, `/wc1`)

Mount (forest.local snapshot):

```
10.0.0.2:/ on /wc1 type nfs4 (rw,noatime,vers=4.2,rsize=32768,wsize=32768,...,soft,...)
```

Rerun output (2026-01-31, all flush options enabled):

```
delete_benchmark_results
- root=/wc1/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=6.185 delete_s=1.331 rewrite_s=4.742 sync_s=0.136
- root=/tmp/delete-test files=3100 dirs=30 size_mb=12.11 create_s=0.576 delete_s=0.095 rewrite_s=4.077 sync_s=0.069
```

### WEPP2 (production NAS remounted as NFSv4.2)

Mount (wepp2.tail305ec9.ts.net):

```
nas.rocket.net:/wepp on /geodata type nfs4 (rw,noatime,vers=4.2,rsize=32768,wsize=32768,...,soft,...)
```

Rerun output (2026-01-31, all flush options enabled):

```
delete_benchmark_results
- root=/geodata/wc1/benchmarks/delete-test files=3100 dirs=30 size_mb=12.11 create_s=27.340 delete_s=2.755 rewrite_s=26.364 sync_s=0.004
- root=/tmp/delete-test files=3100 dirs=30 size_mb=12.11 create_s=0.461 delete_s=0.082 rewrite_s=4.847 sync_s=0.003
```

## Comparison (baseline production / forest.local dev)

Ratios (production time ÷ forest.local time):

- NFS `create_s`: `30.376 / 6.185` = `4.9x`
- NFS `delete_s`: `4.980 / 1.331` = `3.7x`
- NFS `rewrite_s`: `34.456 / 4.742` = `7.3x`
- NFS `sync_s`: `1.235 / 0.136` = `9.1x` (not stable; `os.sync` is system-wide)
- `/tmp create_s`: `0.675 / 0.576` = `1.2x`
- `/tmp delete_s`: `0.090 / 0.095` = `0.9x` (effectively the same)
- `/tmp rewrite_s`: `6.749 / 4.077` = `1.7x`
- `/tmp sync_s`: `0.906 / 0.069` = `13.1x` (not stable; `os.sync` is system-wide)

## Comparison (baseline production / wepp2 NFSv4.2 remount)

Ratios (production time ÷ wepp2 time):

- NFS `create_s`: `30.376 / 27.340` = `1.1x`
- NFS `delete_s`: `4.980 / 2.755` = `1.8x`
- NFS `rewrite_s`: `34.456 / 26.364` = `1.3x`
- NFS `sync_s`: `1.235 / 0.004` = `308.8x` (not stable; `os.sync` is system-wide)
- `/tmp create_s`: `0.675 / 0.461` = `1.5x`
- `/tmp delete_s`: `0.090 / 0.082` = `1.1x`
- `/tmp rewrite_s`: `6.749 / 4.847` = `1.4x`
- `/tmp sync_s`: `0.906 / 0.003` = `302.0x` (not stable; `os.sync` is system-wide)

## Notes / Takeaways

- This benchmark is dominated by metadata ops and stable-write latency (especially with `--fsync-files` / `--fsync-dirs`), not bandwidth; 10 GbE does not guarantee good small-file performance.
- Treat `sync_s` as a “system dirtiness / background IO” indicator, not a per-path metric.
- For a heavier profile, bump `--files-per-dir` and/or `--dir-depth` (expect NFS to degrade faster than local FS).

## Small-File Read/Write/Delete + Metadata Microbench (2026-02-10)

This is a lightweight microbench intended to approximate UI pain on metadata-heavy paths (many small files).

Scope:
- Files: `2000`
- File size: `4096` bytes (payload `8192000` bytes, `7.8125 MiB`)
- Directory: single directory under `/wc1/benchmarks/meta-rwdel/`
- Work units:
  - `write`: create + write all files
  - `stat`: `stat()` all files (via `Path.iterdir()` loop)
  - `listdir`: enumerate directory entries once
  - `read`: read all files (shuffled order)
  - `delete`: `shutil.rmtree()` cleanup

Important caveats:
- This does not drop page cache and is not a disk bandwidth test; it is oriented toward small-file create/open/stat/unlink pressure.
- Read timings may be influenced by cache effects from the preceding write phase.

### wepp1 (production NAS, container `/wc1`)

Mount inside `weppcloud` container:

```
/wc1 nas.rocket.net:/wepp/wc1 nfs4 ... rsize=65536,wsize=65536,...,hard,...,acdirmin=5,...,addr=192.168.100.102
```

Timings:

```
files=2000 size=4096
write_s=14.742265
stat_s=0.099181
listdir_s=0.011301
read_s=5.689536
delete_s=2.322614
```

Derived rates:
- write: `135.7` files/s
- stat: `20165.1` files/s
- read: `1.373` MiB/s
- delete: `861.1` files/s

### forest.local dev NFS (container `/wc1`)

Mount inside `weppcloud` container:

```
/wc1 10.0.0.2:/ nfs4 ... rsize=32768,wsize=32768,...,soft,...,addr=10.0.0.2
```

Timings:

```
files=2000 size=4096
write_s=1.815811
stat_s=0.036887
listdir_s=0.008193
read_s=0.876737
delete_s=0.985464
```

Derived rates:
- write: `1101.4` files/s
- stat: `54219.5` files/s
- read: `8.911` MiB/s
- delete: `2029.5` files/s

### Ratios (wepp1 ÷ forest.local)

- write time: `14.742 / 1.816` = `8.1x` slower
- stat time: `0.0992 / 0.0369` = `2.7x` slower
- read time: `5.690 / 0.877` = `6.5x` slower
- delete time: `2.323 / 0.985` = `2.4x` slower

### Replication

Run inside the appropriate `weppcloud` container:

```bash
python - <<'PY'
import random
import shutil
import time
from pathlib import Path

root = Path('/wc1/benchmarks/meta-rwdel') / f"smallfiles_{int(time.time())}"
files = 2000
size = 4096

def write_files(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=False)
    data = b'x' * size
    for i in range(files):
        with open(p / f"f{i:05d}.bin", 'wb', buffering=0) as fp:
            fp.write(data)

def stat_all(p: Path) -> int:
    total = 0
    for f in p.iterdir():
        total += f.stat().st_size
    return total

def read_all(p: Path) -> int:
    paths = list(p.iterdir())
    random.shuffle(paths)
    total = 0
    for f in paths:
        with open(f, 'rb', buffering=0) as fp:
            total += len(fp.read())
    return total

def delete_all(p: Path) -> None:
    shutil.rmtree(p)

def timed(label, fn):
    t0 = time.perf_counter()
    res = fn()
    dt = time.perf_counter() - t0
    print(f"{label}_s={dt:.6f}")
    return res, dt

print('bench_root', str(root))
print('params', {'files': files, 'size': size})
_, t_write = timed('write', lambda: write_files(root))
(total_stat, t_stat) = timed('stat', lambda: stat_all(root))
(total_ls, t_ls) = timed('listdir', lambda: len(list(root.iterdir())))
(total_read, t_read) = timed('read', lambda: read_all(root))
_, t_del = timed('delete', lambda: delete_all(root))
print('totals', {'stat_bytes': total_stat, 'read_bytes': total_read, 'listdir_n': total_ls})
print('rates', {
    'write_files_per_s': files / t_write,
    'stat_files_per_s': files / t_stat,
    'read_mib_per_s': (total_read / (1024*1024)) / t_read,
    'delete_files_per_s': files / t_del,
})
PY

findmnt -T /wc1 -o TARGET,SOURCE,FSTYPE,OPTIONS
```

## nfsiostat Per-Op Latency + Concurrent stat() (2026-02-10)

This run captures per-operation RTT/EXE from `nfsiostat` during the same "many small files" workload, and pairs it with a multi-threaded `stat()` throughput run.

Tooling:
- Microbench helper: `tools/benchmarks/bench_nfs_smallfiles.py`
- Parameters: `--files 2000 --file-size 4096`
- Notes:
  - `nfsiostat` prints the first report as "since mount"; the capture pattern below sleeps before/after the phase so we can pull an interval report that corresponds to the benchmark activity.
  - `avg RTT` and `avg exe` are from `nfsiostat`'s "peak ops/s interval" for the given op.

### Setup Commands

Forest (dev NFS, mountpoint `/wc1`):

```bash
ROOT=/wc1/benchmarks/nfsiostat-oplat/forest_$(date +%s)
python3 tools/benchmarks/bench_nfs_smallfiles.py write --root "$ROOT" --files 2000 --file-size 4096

# READDIR/LOOKUP latency while repeatedly listing the same directory.
nfsiostat 1 999 -d /wc1 > /tmp/nfsiostat_forest_dir.txt & pid=$!
sleep 2
python3 tools/benchmarks/bench_nfs_smallfiles.py listdir --root "$ROOT" --files 2000 --file-size 4096 --repeat 1000
sleep 2
kill $pid; wait $pid || true

# GETATTR latency while forcing repeated stat()s by pathname.
nfsiostat 1 999 -a /wc1 > /tmp/nfsiostat_forest_attr.txt & pid=$!
sleep 2
python3 tools/benchmarks/bench_nfs_smallfiles.py stat-seq --root "$ROOT" --files 2000 --file-size 4096 --repeat 50
sleep 2
kill $pid; wait $pid || true

python3 tools/benchmarks/bench_nfs_smallfiles.py concurrent-stat --root "$ROOT" --files 2000 --file-size 4096 --threads 128 --repeats 10
python3 tools/benchmarks/bench_nfs_smallfiles.py delete --root "$ROOT" --files 2000 --file-size 4096
```

WEPP1 (production NAS, mountpoint `/geodata`):

```bash
ROOT=/geodata/wc1/benchmarks/nfsiostat-oplat/wepp1_$(date +%s)
python3 tools/benchmarks/bench_nfs_smallfiles.py write --root "$ROOT" --files 2000 --file-size 4096

nfsiostat 1 999 -d /geodata > /tmp/nfsiostat_wepp1_dir.txt & pid=$!
sleep 2
python3 tools/benchmarks/bench_nfs_smallfiles.py listdir --root "$ROOT" --files 2000 --file-size 4096 --repeat 1000
sleep 2
kill $pid; wait $pid || true

nfsiostat 1 999 -a /geodata > /tmp/nfsiostat_wepp1_attr.txt & pid=$!
sleep 2
python3 tools/benchmarks/bench_nfs_smallfiles.py stat-seq --root "$ROOT" --files 2000 --file-size 4096 --repeat 50
sleep 2
kill $pid; wait $pid || true

python3 tools/benchmarks/bench_nfs_smallfiles.py concurrent-stat --root "$ROOT" --files 2000 --file-size 4096 --threads 128 --repeats 10
python3 tools/benchmarks/bench_nfs_smallfiles.py delete --root "$ROOT" --files 2000 --file-size 4096
```

### Results

Mount snapshots:

```text
forest.local: /wc1   10.0.0.2:/              nfs4 ... soft ... rsize=32768,wsize=32768 ...
wepp1:        /geodata nas.rocket.net:/wepp   nfs4 ... hard ... rsize=65536,wsize=65536 ... acregmax=30,acdirmin=5 ...
```

Timing summary:

```text
forest.local:
- write (2000 x 4 KiB):  1.891 s
- listdir repeat=1000:   0.897 s
- stat-seq repeat=50:    2.769 s  (36.1k stats/s)
- concurrent stat 128t:  median 17.7k stats/s  (10 repeats)
- delete:                0.858 s

wepp1:
- write (2000 x 4 KiB):  14.865 s
- listdir repeat=1000:   1.125 s
- stat-seq repeat=50:    2.607 s  (38.4k stats/s)
- concurrent stat 128t:  median 12.9k stats/s  (10 repeats)
- delete:                2.498 s
```

`nfsiostat` peak-interval per-op latency (RTT/EXE):

```text
forest.local:
- READDIR: ops/s=7      avg_RTT_ms=1.714  avg_exe_ms=1.857
- GETATTR: ops/s=2000   avg_RTT_ms=0.160  avg_exe_ms=0.174

wepp1:
- READDIR: ops/s=15     avg_RTT_ms=2.333  avg_exe_ms=2.333
- GETATTR: ops/s=1289   avg_RTT_ms=0.320  avg_exe_ms=0.346
```

### Takeaways

- For this workload, WEPP1's metadata ops (READDIR/GETATTR) are only modestly slower than forest.local, but small-file create/write and delete are much slower.
- If a "loading a run" path performs many tiny writes (cache artifacts, log fan-out, JSON rewrites) in addition to metadata traversal, the write amplification on the NAS-backed NFS mount can dominate the wall time even when `stat()`/`readdir()` look reasonable.

## Run-Tree Inode + `stat()` Pressure (Why NoDir)

In addition to latency, the production NAS-backed NFS mount is consuming inodes at scale:

```text
Filesystem              Inodes     IUsed     IFree IUse% Mounted on
nas.rocket.net:/wepp 249999994 149273382 100726612   60% /geodata
```

WEPPcloud project runs create `landuse/`, `soils/`, `climate/`, and `watershed/` trees that can include per-hillslope files (often multiple files per hillslope). As the rest of the stack gets faster and supports larger watersheds, it is normal to see 10k+ hillslopes, which turns these directories into tens of thousands of small files.

The browse service needs per-entry metadata (name/mtime/size and directory child counts) to render the run file tree, which amplifies NFS metadata RTT (`stat()`/`readdir()` costs) even when total bytes are small.

Direction:
- Archive `landuse/`, `soils/`, `climate/`, and `watershed/` as `.nodir` artifacts (zip container, differentiated from generic/user `.zip` files).
- Keep `wepp/` as a real directory (WEPP executables require filesystem paths).
- Treat archive-backed trees as “directory-like” in browse and internal code.

See:
- Work package: [`docs/work-packages/20260214_nodir_archives/package.md`](../work-packages/20260214_nodir_archives/package.md)
- Contract: [`docs/schemas/nodir-contract-spec.md`](../schemas/nodir-contract-spec.md)
