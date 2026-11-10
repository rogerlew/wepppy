"""Real record/Git/raster boundaries for the bounded declarative protocol."""

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import zipfile

import pytest

from wepppy.declarative import policy, records, schema

pytestmark = pytest.mark.unit


@pytest.fixture
def definition():
    return {"schema": "dem-v1", "image": "ghcr.io/rogerlew/wepppy@sha256:" + "a" * 64,
            "submission_id": str(uuid4()), "extent": [-116.10, 46.70, -116.09, 46.71],
            "source": "ned1/2024", "product": "dem", "visibility": "public"}


@pytest.fixture
def approval(definition):
    return {definition["image"]: {"schema": "dem-v1", "protocol": "dem-engine-v1",
                                 "platform": "linux/amd64", "operation": "fetch_dem_rq"}}


@pytest.fixture
def project(tmp_path, definition):
    runid, queue = schema.identities(definition["submission_id"])
    wd = tmp_path / runid
    wd.mkdir()
    admission = {"schema": schema.SCHEMA, "runid": runid, "queue": queue,
                 "definition": definition, "owner_id": 1,
                 "attempt_id": str(uuid4()), "finalizer_id": str(uuid4())}
    with records.guard(wd):
        records.write(wd, "provenance/declarative.json", admission, exclusive=True)
        records.write(wd, "provenance/build.json", {"processing": "admitted", "protection": "pending"})
    return wd, admission


def test_valid_definition(definition, approval):
    assert schema.validate(definition, approval) == definition


@pytest.mark.parametrize("field,value", [("visibility", "private"), ("extent", [True, 1, 2, 3]),
                                        ("extent", [0, 0, 10, 10]), ("source", "https://example.org"),
                                        ("submission_id", "../escape"), ("image", "latest")])
def test_reject_definition(definition, approval, field, value):
    definition[field] = value
    with pytest.raises(schema.AdmissionError):
        schema.validate(definition, approval)


def test_unknown_and_duplicate_fields(definition, approval):
    definition["command"] = "touch /tmp/escape"
    with pytest.raises(schema.AdmissionError):
        schema.validate(definition, approval)
    with pytest.raises(schema.AdmissionError):
        schema.loads('{"schema":1,"schema":2}')
    with pytest.raises(schema.AdmissionError):
        schema.loads('{"extent":NaN}')


def test_ordinary_empty_and_invalid_states(tmp_path):
    policy.reject_mutation(tmp_path)
    (tmp_path / "provenance").mkdir()
    policy.reject_mutation(tmp_path)
    (tmp_path / "provenance/declarative.json").write_text("")
    with pytest.raises(records.ProtectedProjectError):
        policy.reject_mutation(tmp_path)


def test_symlinked_record_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    wd = tmp_path / "project"
    wd.mkdir()
    (wd / "provenance").symlink_to(outside, target_is_directory=True)
    with pytest.raises(records.ProtectedProjectError):
        records.marker(wd)
    assert not list(outside.iterdir())


def test_exact_git_checkpoint_and_duplicate_claim(project):
    wd, admission = project
    attempt = admission["attempt_id"]
    with records.guard(wd):
        records.write(wd, f"provenance/claims/{attempt}.json", {"claimed": True}, exclusive=True)
        with pytest.raises(FileExistsError):
            records.write(wd, f"provenance/claims/{attempt}.json", {"claimed": False}, exclusive=True)
        records.write(wd, f"provenance/attempts/{attempt}.json", {"outcome": "failed"}, exclusive=True)
        (wd / "provenance/not-tracked.txt").write_text("not checkpoint input")
        commit = records.checkpoint(wd, attempt, ["declarative.json", f"attempts/{attempt}.json"])
        assert records.checkpoint(wd, attempt, [f"attempts/{attempt}.json"]) == commit
        tracked = records._git(wd / "provenance", "ls-tree", "-r", "--name-only", commit)
        assert set(tracked.splitlines()) == {"declarative.json", f"attempts/{attempt}.json"}
        assert records.read(wd, f"provenance/claims/{attempt}.json") == {"claimed": True}
        with pytest.raises(records.ProtectedProjectError):
            records.checkpoint(wd, str(uuid4()), ["not-tracked.txt"])


def test_bound_task_authority(project):
    wd, admission = project
    job = SimpleNamespace(id=admission["attempt_id"], origin=admission["queue"])
    with pytest.raises(records.ProtectedProjectError):
        policy.require_task(wd, "fetch_dem_rq")
    with policy.attempt_authority(wd, job):
        policy.require_task(wd, "fetch_dem_rq")
        policy.require_controller_mutation(wd)
        with pytest.raises(records.ProtectedProjectError):
            policy.require_task(wd, "set_run_readonly_rq")
    with pytest.raises(records.ProtectedProjectError):
        policy.require_controller_mutation(wd)
    with pytest.raises(records.ProtectedProjectError):
        policy.require_settled(wd)


def test_protected_manifest_detects_content_drift(project):
    wd, _ = project
    (wd / "ron.nodb").write_text("config")
    (wd / "dem").mkdir()
    (wd / "dem/dem.tif").write_bytes(b"raster")
    with records.guard(wd):
        records.write(wd, "provenance/protected.json", records.protected_manifest(wd))
    records.verify_protected(wd)
    (wd / "dem/dem.tif").write_bytes(b"changed")
    with pytest.raises(records.ProtectedProjectError):
        records.verify_protected(wd)


def test_real_raster_and_zero_write_consumer(project):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from wepppy.declarative.observations import raster_summary
    from wepppy.microservices.elevationquery import _sample_dem
    wd, _ = project
    (wd / "dem").mkdir()
    path = wd / "dem/dem.tif"
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1,
                       dtype="float32", crs="EPSG:4326", transform=from_origin(-116.1, 46.71, .005, .005)) as ds:
        ds.write(np.array([[100, 200], [300, 400]], dtype="float32"), 1)
    (wd / "READONLY").touch()
    before = records.protected_manifest(wd)
    assert _sample_dem(path, -116.0975, 46.7075) == 100
    summary = raster_summary(path)
    assert summary["valid_cells"] == 4
    assert summary["minimum"] == 100
    assert summary["shape"] == [2, 2]
    assert before == records.protected_manifest(wd)


def test_exception_guard_binds_named_runid(monkeypatch, tmp_path):
    from wepppy.rq import exception_logging
    seen = []
    monkeypatch.setattr(exception_logging, 'get_wd', lambda runid: seen.append(runid) or str(tmp_path))
    @exception_logging.with_exception_logging
    def migration(wd, runid):
        return wd
    @exception_logging.with_exception_logging
    def gc(root):
        return root
    assert migration('/wc1/runs/aa/example', 'example') == '/wc1/runs/aa/example'
    assert gc('/wc1/runs') == '/wc1/runs'
    assert seen == ['example']


def test_observation_refuses_replaced_project(tmp_path):
    from wepppy.declarative.observations import DemObservation
    metadata = tmp_path / '_query_engine/refresh'
    metadata.mkdir(parents=True)
    incarnation = metadata / 'incarnation.json'
    incarnation.write_text('{"incarnation":"before"}')
    ron = SimpleNamespace(wd=str(tmp_path), runid='ordinary', dem_db='ned1/2024',
                          map=SimpleNamespace(extent=[1, 2, 3, 4], center=[2, 3], zoom=12, cellsize=30))
    observation = DemObservation(ron, None)
    incarnation.write_text('{"incarnation":"after"}')
    assert observation.finish(ron, succeeded=False) is None
    assert not (tmp_path / f'provenance/attempts/{observation.attempt_id}.json').exists()


def test_science_boundary_rejects_changed_dem_and_alternate_viewer(project, monkeypatch):
    from wepppy.declarative.adapter import _verify_science_boundary
    from wepppy.nodb.core import Ron
    wd, admission = project
    (wd / 'dem').mkdir()
    dem = wd / 'dem/dem.tif'
    dem.write_bytes(b'acquired raster')
    inputs = {'source': 'ned1/2024', 'extent': [1, 2, 3, 4], 'cellsize': 30}
    ron = SimpleNamespace(dem_fn=str(dem), dem_db=inputs['source'],
                          map=SimpleNamespace(extent=inputs['extent'], cellsize=30))
    monkeypatch.setattr(Ron, 'load_detached', lambda wd: ron)
    attempt = admission['attempt_id']
    with records.guard(wd):
        records.write(wd, f'provenance/attempts/{attempt}.json', {
            'attempt_id': attempt, 'outcome': 'succeeded', 'inputs': inputs,
            'output': {'sha256': records.digest(dem)},
        })
        commit = records.checkpoint(wd, attempt, [f'attempts/{attempt}.json'])
        records.write(wd, 'provenance/build.json', {'checkpoint': commit})
    _verify_science_boundary(wd, admission)
    dem.write_bytes(b'replaced raster')
    with pytest.raises(schema.AdmissionError):
        _verify_science_boundary(wd, admission)
    dem.write_bytes(b'acquired raster')
    (wd / 'dem/dem.vrt').write_text('alternate consumer')
    with pytest.raises(schema.AdmissionError):
        _verify_science_boundary(wd, admission)


def test_runtime_rejects_changes_and_unapproved_exec_hooks(definition):
    from copy import deepcopy
    from tools.declarative_dem import observe
    spec = {'automountServiceAccountToken': False, 'nodeName': 'worker-dell-01',
            'nodeSelector': {'kubernetes.io/hostname': 'worker-dell-01'},
            'containers': [{'name': 'worker', 'image': definition['image'], 'args': ['worker']}]}
    pod = {'metadata': {'namespace': 'weppcloud', 'name': 'slice', 'uid': 'pod-uid'},
           'spec': spec, 'status': {'phase': 'Running', 'containerStatuses': [
               {'name': 'worker', 'ready': True, 'containerID': 'containerd://123',
                'imageID': definition['image'], 'restartCount': 0}]}}
    node = {'metadata': {'name': 'worker-dell-01', 'labels': {'kubernetes.io/hostname': 'worker-dell-01'}},
            'status': {'nodeInfo': {'operatingSystem': 'linux', 'architecture': 'amd64'}}}
    template = {'spec': deepcopy(spec)}
    before = observe(pod, node, template, definition)
    assert schema.verify_evidence(definition, before, before) == before
    for field in ('lifecycle', 'startupProbe', 'livenessProbe', 'readinessProbe', 'resources'):
        changed = deepcopy(pod)
        changed['spec']['containers'][0][field] = {'exec': {'command': ['unreviewed']}}
        with pytest.raises(schema.AdmissionError):
            observe(changed, node, template, definition)
    changed = deepcopy(node)
    changed['metadata']['labels']['kubernetes.io/hostname'] = 'worker-frontend-01'
    with pytest.raises(schema.AdmissionError):
        observe(pod, changed, template, definition)
    changed = dict(before, container_id='containerd://replacement')
    with pytest.raises(schema.AdmissionError):
        schema.verify_evidence(definition, changed, before)


@pytest.mark.parametrize('command', ['status', 'cancel'])
def test_revoked_approval_does_not_block_existing_control(tmp_path, definition, monkeypatch, command):
    import sys
    from tools import declarative_dem
    path = tmp_path / 'definition.json'
    path.write_text(json.dumps(definition))
    template = tmp_path / 'pod.json'
    template.write_text('{}')
    monkeypatch.setattr(sys, 'argv', ['engine', command, '--definition', str(path),
        '--approvals', str(tmp_path / 'removed-approvals.json'), '--template', str(template),
        '--context', 'fixture', '--pod', 'fixture'])
    monkeypatch.setattr(declarative_dem.Client, 'run', lambda self: {
        'verified': False, 'processing': 'canceled', 'protection': 'readonly', 'error': None})
    assert declarative_dem.main() == 0
    with pytest.raises(schema.AdmissionError):
        schema.validate(definition, {})


def test_direct_nodb_bootstrap_and_science_mutations_rejected(project, monkeypatch):
    from wepppy.nodb.base import NoDbBase
    from wepppy.nodb.core.wepp_bootstrap_service import WeppBootstrapService
    from wepppy.nodb.core import Ron
    from wepppy.rq import project_rq, wepp_rq_stage_post
    wd, admission = project
    (wd / 'READONLY').write_text('protected')
    controller = object.__new__(NoDbBase)
    controller.wd = str(wd)
    with pytest.raises(records.ProtectedProjectError):
        controller.readonly = False
    with pytest.raises(records.ProtectedProjectError):
        controller.public = False
    ron = object.__new__(Ron)
    ron.wd = str(wd)
    with pytest.raises(records.ProtectedProjectError):
        ron.fetch_dem()
    with pytest.raises(records.ProtectedProjectError):
        WeppBootstrapService().init_bootstrap(SimpleNamespace(wd=str(wd)))
    for module, function in [(project_rq, project_rq.build_subcatchments_rq),
                             (wepp_rq_stage_post, wepp_rq_stage_post._post_run_cleanup_out_rq)]:
        monkeypatch.setattr(module, 'get_wd', lambda runid: str(wd))
        with pytest.raises(records.ProtectedProjectError):
            function(admission['runid'])
    assert (wd / 'READONLY').read_text() == 'protected'
    assert not (wd / '.git').exists()


def test_flask_mutation_guard_precedes_route_side_effects(project, monkeypatch):
    from wepppy.weppcloud.app import app, _protect_declarative_project
    from wepppy.weppcloud.utils import helpers
    wd, admission = project
    monkeypatch.setattr('wepppy.weppcloud.app.get_wd', lambda runid: str(wd))
    monkeypatch.setattr(helpers, 'authorize', lambda runid, config: None)
    with app.test_request_context('/runs/example/disturbed9002/tasks/set-readonly', method='POST'):
        from flask import request
        request.view_args = {'runid': admission['runid'], 'config': 'disturbed9002'}
        response, code = _protect_declarative_project()
        assert code == 409
        assert response.json['error']['code'] == 'declarative_protected'
    with app.test_request_context('/runs/example/disturbed9002/', method='GET'):
        from flask import request
        request.view_args = {'runid': admission['runid'], 'config': 'disturbed9002'}
        assert _protect_declarative_project() is None


def test_empty_adapter_response_is_a_sanitized_admission_error(monkeypatch, definition):
    from tools.declarative_dem import Client
    import subprocess
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout='', stderr='sensitive internal detail'))
    client = Client(SimpleNamespace(context='fixture'), definition, {})
    with pytest.raises(schema.AdmissionError, match='no protocol response'):
        client.kubectl('exec')
