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

