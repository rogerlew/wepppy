"""Remove only the recorded disposable runs after rq-engine releases log handles."""
import json
from pathlib import Path
import stat

from wepppy.weppcloud.app import app, db, Run, User
from wepppy.weppcloud.user_preferences import cleanup_new_run_directory, delete_registered_run, RunRegistrationReceipt
from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.microservices.rq_engine.project_routes import _creation_idempotency_client

root = Path(__file__).parent
runids = json.loads((root / "20260907_canary_run_ids.json").read_text())
results = []
for runid in runids:
    wd = get_wd(runid)
    assert Path(wd).name == runid and Path(wd).is_relative_to("/wc1/runs")
    result = {"runid": runid, "path": wd}
    if Path(wd).exists():
        info = Path(wd).stat()
        result["directory_identity"] = {"uid": info.st_uid, "gid": info.st_gid, "mode": oct(stat.S_IMODE(info.st_mode))}
    with app.app_context():
        record = Run.query.filter_by(runid=runid).first()
        if record is not None:
            agent = User.query.filter_by(email="dev-agent@example.com").one()
            assert str(record.owner_id) == str(agent.id)
            receipt = RunRegistrationReceipt(run_pk=record.id, runid=runid, config=record.config, user_id=agent.id)
        else:
            receipt = None
    if receipt:
        delete_registered_run(receipt)
    if Path(wd).exists():
        cleanup_new_run_directory(runid, wd)
    assert not Path(wd).exists()
    with app.app_context():
        assert Run.query.filter_by(runid=runid).first() is None
    result["removed"] = True
    results.append(result)
client = _creation_idempotency_client()
removed_keys = 0
for key in client.scan_iter(match="project-create:idempotency:v1:*"):
    raw = client.get(key)
    if raw is not None and json.loads(raw).get("run_id") in runids:
        removed_keys += client.delete(key)
print(json.dumps({"runs": results, "remaining_canary_idempotency_keys_removed": removed_keys}, indent=2))
