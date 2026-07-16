# Paired WEPPpy / WEPPpyo3 rollback runbook

This change is a paired Python/native ABI deployment. Never restore only the
shared object while the new WEPPpy orchestrator is importable, and never run the
new native wrapper against the old shared object.

## Frozen revisions

| Component | Pre-change revision | Deployment revision |
| --- | --- | --- |
| WEPPpy | `9baacc49c2098229838e130744939ef60671f5b0` | `ec4b26e35` |
| WEPPpyo3 | `4d3c060a27133b9bd7335de3e1dee4d680db0fcf` | `2020fdcb7e6f2317d1e397bd7b19866544e9ee07` |
| Native release SHA-256 | `7419203c8b91db1b595590b7c9a28040662d5fad9fdf8b182a17c85a76d518e4` | `8c42edd0a8e1b03bdaf423355a12414180c709efaac3e379e5dd23e6cc77214e` |

The runtime artifact is
`/home/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so`.

## Rollback procedure

1. Confirm `wctl rq-info` reports zero queued/executing jobs. Do not interrupt a
   model or publication job merely to shorten rollback time.
2. Stop every long-lived importer together:

   ```sh
   PATH=/home/workdir/wepppy/.venv/bin:$PATH \
     wctl docker compose stop \
       weppcloud query-engine rq-engine rq-worker rq-worker-batch scheduler
   ```

3. Create normal revert commits in both repositories:

   ```sh
   git -C /home/workdir/wepppy revert --no-edit ec4b26e35
   git -C /home/workdir/wepppyo3 revert --no-edit 2020fdcb7e6f2317d1e397bd7b19866544e9ee07
   ```

4. Before restart, require the old artifact hash:

   ```sh
   sha256sum /home/workdir/wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so
   ```

   Expected:
   `7419203c8b91db1b595590b7c9a28040662d5fad9fdf8b182a17c85a76d518e4`.

5. Recreate all importers from the paired checkout:

   ```sh
   PATH=/home/workdir/wepppy/.venv/bin:$PATH \
     wctl docker compose up -d --no-deps --force-recreate \
       weppcloud query-engine rq-engine rq-worker rq-worker-batch scheduler
   ```

6. Verify each process imports the canonical release path and old SHA, then run
   `wctl rq-info`, the ordinary interchange import smoke, and an authenticated
   read-only AgFields state request before accepting traffic.

## Data behavior

Rollback does not delete or rewrite raw `H*.dat` reports. Leave the specialized
`wepp/ag_fields/output/interchange/` directory in place: the pre-change runtime
does not consume it, and retaining it preserves forensic/recovery evidence.
No watershed scheme, ordinary interchange, or source mapping artifact needs to
be restored.

To roll forward after diagnosis, revert the two rollback commits as another
paired change, recreate the same importer set, and repeat the canonical
path/SHA/signature checks.
