# SURF-04A NFS Transaction Validation

**Date**: 2026-08-02
**Result**: pass

## Backing Filesystem

The focused integration test ran inside the WEPPcloud development container on
the actual `/wc1` NFSv4.2 mount, not ext4 or tmpfs:

```text
TARGET SOURCE     FSTYPE OPTIONS
/wc1   10.0.0.2:/ nfs4   rw,noatime,vers=4.2,rsize=32768,wsize=32768,
                       soft,proto=tcp,timeo=600,retrans=2,local_lock=none
```

## Command and Result

```bash
wctl docker compose exec \
  -e WEPPPY_NFS_TEST_ROOT=/wc1/benchmarks/omni-fork-nfs-parity \
  weppcloud bash -lc 'cd /workdir/wepppy && \
    PYTHONPATH=/workdir/wepppy /opt/venv/bin/pytest \
    tests/rq/test_project_rq_fork_nfs.py -m integration -vv'
```

Final result: `3 passed` in `8.28s`, including deterministic
symlink-to-regular and symlink-to-directory swaps on the same NFS mount.

The test refused non-NFS roots and proved:

- descriptor-relative cross-directory rename of a symlink into quarantine;
- raw link text plus device/inode identity after capture;
- hard-link restoration of the symlink object with
  `follow_symlinks=False`;
- identical device/inode and raw text after restoration;
- `EEXIST` collision refusal without overwriting foreign bytes;
- quarantine retention on collision; and
- exact temporary workspace cleanup (no `surf04a-*` residue).

The NFS suite and unit suite both cover deterministic symlink-to-regular
restoration and symlink-to-directory confinement/fail-closed behavior.

## Live rq-engine End-to-End Validation

After restarting the development stack, a run-scoped service JWT minted by the
same WEPPcloud instance was used against the proxied rq-engine API.

- `POST /rq-engine/api/runs/assisted-weakness/disturbed9002_wbt/fork`
  returned job `adf8f474-4c2e-426c-9f71-ba73bf89a481` and target
  `canine-liar`.
- The fork reached `finished` in `14.8065` seconds with no exception.
- The fork contains 63 Omni symlinks. All resolve, none point into the source
  run, and the normalized targets are relative to the fork root.
- `POST /rq-engine/api/runs/assisted-weakness/disturbed9002_wbt/archive`
  returned job `005bd8bd-2d4f-4f73-b902-bf4d7e8c8a6c`.
- The archive reached `finished` in `103.636748` seconds with no exception and
  produced `archives/assisted-weakness.20260802T201438Z.zip` (281,998,224
  bytes).

An older token minted before the stack restart failed with a signature
mismatch. A token minted after restart validated in both the WEPPcloud and
rq-engine containers. Both containers reported the same active-secret
fingerprint and two validation keys, consistent with a stale pre-restart token
crossing a local secret-file/cache rotation boundary rather than an ongoing
service configuration mismatch.
