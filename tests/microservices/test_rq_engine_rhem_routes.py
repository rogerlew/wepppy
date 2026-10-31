import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import rhem_routes


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rhem_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(rhem_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> None:
    from wepppy.rq import submission_recovery
    class DummyLock:
        def acquire(self, **kwargs): return True
        def extend(self, *args, **kwargs): return True
        def release(self): return None
    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            self.connection = kwargs["connection"]

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def lock(self, *args, **kwargs): return DummyLock()
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(rhem_routes, "Queue", DummyQueue)
    monkeypatch.setattr(rhem_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: job_id)


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def get_rq_job_id(self, key): return None
        def remove_timestamp(self, *args, **kwargs) -> None:
            return None

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(rhem_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def test_run_rhem_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-99")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(rhem_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/run-rhem",
            json={"clean": True, "prep": False},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-99"


@pytest.mark.parametrize('payload', ['{', 'null', '[]', '{"clean":"bad"}', '{"clean":2}', '{"clean":[false]}', '{"clean":false,"clean_hillslopes":true}'])
def test_invalid_rhem_never_reaches_cleanup_or_timestamp(monkeypatch, tmp_path, payload):
    _stub_auth(monkeypatch)
    output = tmp_path / 'rhem' / 'output'
    output.mkdir(parents=True)
    sentinel = output / 'accepted.out'
    sentinel.write_text('accepted result')
    monkeypatch.setattr(rhem_routes, 'get_wd', lambda runid: str(tmp_path))
    def forbidden(*args, **kwargs):
        pytest.fail('invalid request reached a business side effect')
    monkeypatch.setattr(rhem_routes.RedisPrep, 'getInstance', forbidden)
    monkeypatch.setattr(rhem_routes, 'enqueue_tracked_rq_job', forbidden)
    with TestClient(rq_engine.app) as client:
        response = client.post('/api/runs/run-1/cfg/run-rhem', content=payload, headers={'Content-Type':'application/json'})
    assert response.status_code == 400, response.text
    assert response.json()['error']['code'] == 'invalid_request'
    assert sentinel.read_text() == 'accepted result'


@pytest.mark.parametrize('payload,clean', [({}, True), ({'clean': False}, False), ({'clean': None}, True), ({'clean_hillslopes': False}, False)])
def test_rhem_valid_defaults_and_false_reach_real_cleanup_boundary(monkeypatch, tmp_path, payload, clean):
    from types import SimpleNamespace
    from wepppy.rq import project_rq
    from wepppy.nodb.mods.rhem import Rhem
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    _stub_queue(monkeypatch)
    runs=tmp_path/'runs'; output=tmp_path/'output'
    runs.mkdir(); output.mkdir()
    sentinel=output/'accepted.out'; sentinel.write_text('accepted')
    model=SimpleNamespace(runs_dir=str(runs),output_dir=str(output), prep_hillslopes=lambda:None, run_hillslopes=lambda:None)
    model.clean=lambda:Rhem.clean(model)
    monkeypatch.setattr(project_rq.Rhem,'getInstance',lambda wd:model)
    monkeypatch.setattr(project_rq,'get_wd',lambda runid:str(tmp_path))
    monkeypatch.setattr(rhem_routes,'get_wd',lambda runid:str(tmp_path))
    monkeypatch.setattr(project_rq,'get_current_job',lambda:SimpleNamespace(id='controlled'))
    monkeypatch.setattr(project_rq.StatusMessenger,'publish',lambda *args:None)
    monkeypatch.setattr(project_rq.RedisPrep,'getInstance',lambda wd:SimpleNamespace(remove_timestamp=lambda *a:None,timestamp=lambda *a:None))
    def execute(queue, function, **kwargs):
        function(*kwargs['args'], **(kwargs.get('kwargs') or {}))
        return SimpleNamespace(id='controlled')
    monkeypatch.setattr(rhem_routes,'enqueue_tracked_rq_job',execute)
    with TestClient(rq_engine.app) as client:
        response=client.post('/api/runs/run-1/cfg/run-rhem',json=payload)
    assert response.status_code == 200, response.text
    assert sentinel.exists() is (not clean)
