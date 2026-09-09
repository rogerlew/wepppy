"""Bounded wepp1 repair; dry-run by default, run inside the production container."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import redis
import rq
from rq import Queue
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import clear_nodb_file_cache
from wepppy.nodb.core.climate import Climate
from wepppy.weppcloud.app import Run, app


RUNIDS = (
    "under-fecundity", "seductive-sabra", "warming-championship", "asteroid-hindrance",
)
EXPECTED = "/geodata/extended_mods_data/wepppy-locations-portland/daymet_scale.tif"


def generated_samples(wd, climate):
    paths = []
    if climate.cli_fn:
        paths.append(Path(climate.cli_dir) / climate.cli_fn)
    runs = wd / "wepp/runs"
    if runs.is_dir():
        paths.extend(sorted(runs.glob("*.cli"))[:1])
    return {
        str(path.relative_to(wd)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths if path.is_file()
    }


def assert_no_target_jobs(connection):
    assert rq.__version__ == "1.16.2", "Recheck registry encoding before repair"
    for name in ("default", "batch", "fork-archive"):
        queue = Queue(name, connection=connection)
        started = connection.zrange(queue.started_job_registry.key, 0, -1)
        ids = {value.decode() for value in started} | set(queue.job_ids)
        for job in Job.fetch_many(sorted(ids), connection=connection):
            if job is not None and any(runid in repr((job.args, job.kwargs)) for runid in RUNIDS):
                raise RuntimeError(f"Target run has queued/active job {job.id}; defer repair")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert (os.getuid(), os.getgid()) == (1002, 130), "Unexpected production identity"
    connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    assert_no_target_jobs(connection)
    with app.app_context():
        owned = Run.query.filter(
            Run.owner_id == "1810", Run.config == "portland-10-mofe", Run.runid.in_(RUNIDS),
        ).all()
        assert {run.runid for run in owned} == set(RUNIDS), "Ownership/config scope changed"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path("/wc1/.incident-backups") / f"climate-scale-map-{stamp}"
    if args.apply:
        backup_root.mkdir(parents=True, mode=0o700)
        backup_root.chmod(0o700)

    records = []
    for runid in RUNIDS:
        wd = Path("/wc1/runs") / runid[:2] / runid
        assert wd.resolve() == wd, "Unexpected run symlink"
        clear_nodb_file_cache(runid, pup_relpath="climate.nodb")
        climate = Climate.getInstance(str(wd))
        expected = climate.config_get_path("climate", "daymet_precip_scale_factor_map", None)
        assert expected == EXPECTED and Path(expected).is_file()
        if not args.apply:
            record = {"runid": runid, "stored": climate._precip_scale_factor_map,
                      "expected": expected, "samples": generated_samples(wd, climate)}
            print(json.dumps(record), flush=True)
            continue

        climate.lock()
        try:
            assert_no_target_jobs(connection)
            # Local lock tokens live in a WeakKeyDictionary keyed by this object,
            # so refresh its durable attributes without replacing its identity.
            clear_nodb_file_cache(runid, pup_relpath="climate.nodb")
            fresh = Climate.getInstance(str(wd), ignore_lock=True)
            climate.__dict__.clear()
            climate.__dict__.update(fresh.__dict__)
            expected = climate.config_get_path("climate", "daymet_precip_scale_factor_map", None)
            assert expected == EXPECTED and Path(expected).is_file()
            if climate._precip_scale_factor_map == expected:
                print(json.dumps({"runid": runid, "status": "already correct; unchanged"}), flush=True)
                continue
            path = wd / "climate.nodb"
            original = path.read_bytes()
            backup = backup_root / f"{runid}.climate.nodb"
            with backup.open("xb") as handle:
                handle.write(original)
                handle.flush()
                os.fsync(handle.fileno())
            before = climate.__getstate__()
            samples = generated_samples(wd, climate)
            climate._precip_scale_factor_map = expected
            after = climate.__getstate__()
            changed = {
                key for key in before.keys() | after.keys()
                if before.get(key) is not after.get(key) and before.get(key) != after.get(key)
            }
            assert changed <= {"_precip_scale_factor_map"}, changed
            climate.dump()
        finally:
            climate.unlock()

        disk = json.loads(path.read_text())["py/state"]
        assert disk["_precip_scale_factor_map"] == expected
        reloaded = Climate.getInstance(str(wd), ignore_lock=True)
        assert reloaded._precip_scale_factor_map == expected
        assert generated_samples(wd, reloaded) == samples
        record = {"runid": runid, "before": before.get("_precip_scale_factor_map"),
                  "after": expected, "backup": str(backup), "samples": samples,
                  "before_sha256": hashlib.sha256(original).hexdigest(),
                  "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        records.append(record)
        (backup_root / "manifest.json").write_text(json.dumps(records, indent=2) + "\n")
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
