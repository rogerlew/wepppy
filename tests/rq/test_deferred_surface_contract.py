from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from redis.exceptions import RedisError

from wepppy.rq import submission_recovery

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def isolated_lifecycle_locks(tmp_path, monkeypatch):
    monkeypatch.setattr(submission_recovery, "_LIFECYCLE_LOCK_DIR", str(tmp_path))


@dataclass(frozen=True)
class SurfaceCase:
    name: str
    source: str
    job_key: str


@dataclass(frozen=True)
class ProductionPolicy:
    func_name: str
    origin: str
    conflict_keys: tuple[str, ...]
    root_func_names: tuple[str, ...]
    workflow_func_names: tuple[str, ...]
    workflow_modules: tuple[str, ...]


SURFACES = (
    SurfaceCase("climate-upload", "wepppy/microservices/rq_engine/upload_climate_routes.py", "upload_cli_rq"),
    SurfaceCase("rhem", "wepppy/microservices/rq_engine/rhem_routes.py", "run_rhem_rq"),
    SurfaceCase("climate-build", "wepppy/microservices/rq_engine/climate_routes.py", "build_climate_rq"),
    SurfaceCase("openet", "wepppy/microservices/rq_engine/openet_ts_routes.py", "fetch_and_analyze_openet_ts_rq"),
    SurfaceCase("watershed-channels", "wepppy/microservices/rq_engine/watershed_routes.py", "fetch_dem_and_build_channels_rq"),
    SurfaceCase("watershed-outlet", "wepppy/microservices/rq_engine/watershed_routes.py", "set_outlet_rq"),
    SurfaceCase("watershed-subcatchments", "wepppy/microservices/rq_engine/watershed_routes.py", "build_subcatchments_and_abstract_watershed_rq"),
    SurfaceCase("treatments", "wepppy/microservices/rq_engine/treatments_routes.py", "build_treatments_rq"),
    SurfaceCase("rusle", "wepppy/microservices/rq_engine/rusle_routes.py", "build_rusle_rq"),
    SurfaceCase("dss-export", "wepppy/microservices/rq_engine/dss_export_routes.py", "post_dss_export_rq"),
    SurfaceCase("omni-scenarios", "wepppy/microservices/rq_engine/omni_routes.py", "run_omni_rq"),
    SurfaceCase("omni-contrasts", "wepppy/microservices/rq_engine/omni_routes.py", "run_omni_contrasts_rq"),
    SurfaceCase("omni-delete", "wepppy/microservices/rq_engine/omni_routes.py", "delete_omni_contrasts_rq"),
    SurfaceCase("polaris", "wepppy/microservices/rq_engine/polaris_routes.py", "fetch_and_align_polaris_rq"),
    SurfaceCase("rap", "wepppy/microservices/rq_engine/rap_ts_routes.py", "fetch_and_analyze_rap_ts_rq"),
    SurfaceCase("landuse-build", "wepppy/microservices/rq_engine/landuse_routes.py", "build_landuse_rq"),
    SurfaceCase("landuse-modify", "wepppy/microservices/rq_engine/landuse_routes.py", "modify_landuse_mapping_rq"),
    SurfaceCase("ash", "wepppy/microservices/rq_engine/ash_routes.py", "run_ash_rq"),
    SurfaceCase("soils", "wepppy/microservices/rq_engine/soils_routes.py", "build_soils_rq"),
    SurfaceCase("ermit-export", "wepppy/microservices/rq_engine/export_routes.py", "ermit_export"),
    SurfaceCase("features-export", "wepppy/microservices/rq_engine/export_routes.py", "features_export"),
    SurfaceCase("debris-flow", "wepppy/microservices/rq_engine/debris_flow_routes.py", "run_debris_flow_rq"),
    SurfaceCase("rangeland", "wepppy/weppcloud/routes/nodb_api/rangeland_bp.py", "build_rangeland_cover_rq"),
    SurfaceCase("project-delete", "wepppy/weppcloud/routes/nodb_api/project_bp.py", "delete_run_rq"),
    SurfaceCase("project-readonly", "wepppy/weppcloud/routes/nodb_api/project_bp.py", "set_readonly"),
    SurfaceCase("interchange", "wepppy/weppcloud/routes/nodb_api/interchange_bp.py", "run_interchange_migration"),
)

EXPECTED_SPECIAL_POLICIES = {
    "climate-upload": {
        "conflict_keys": ("build_climate_rq", "upload_cli_rq"),
        "root_suffixes": ("build_climate_rq", "upload_cli_rq"),
    },
    "climate-build": {
        "conflict_keys": ("build_climate_rq", "upload_cli_rq"),
        "root_suffixes": ("build_climate_rq", "upload_cli_rq"),
    },
    "omni-scenarios": {
        "workflow_suffixes": (
            "run_omni_scenario_rq",
            "_compile_hillslope_summaries_rq",
            "_finalize_omni_scenarios_rq",
        ),
    },
    "omni-contrasts": {
        "conflict_keys": ("run_omni_contrasts_rq", "delete_omni_contrasts_rq"),
        "root_suffixes": ("run_omni_contrasts_rq", "delete_omni_contrasts_rq"),
        "workflow_suffixes": ("run_omni_contrast_rq", "_finalize_omni_contrasts_rq"),
    },
    "omni-delete": {
        "conflict_keys": ("run_omni_contrasts_rq", "delete_omni_contrasts_rq"),
        "root_suffixes": ("run_omni_contrasts_rq", "delete_omni_contrasts_rq"),
        "workflow_suffixes": ("run_omni_contrast_rq", "_finalize_omni_contrasts_rq"),
    },
    "watershed-subcatchments": {
        "workflow_suffixes": ("build_subcatchments_rq", "abstract_watershed_rq"),
    },
    "watershed-channels": {
        "workflow_suffixes": ("fetch_dem_rq", "build_channels_rq"),
    },
}


class PrepStub:
    def __init__(self, *, fail_save: bool = False) -> None:
        self.job_ids = {case.job_key: "old-job" for case in SURFACES}
        self.fail_save = fail_save

    def get_rq_job_id(self, job_key: str) -> str | None:
        return self.job_ids.get(job_key)

    def set_rq_job_id(self, job_key: str, job_id: str) -> None:
        if self.fail_save:
            raise OSError("durable receipt save failed")
        self.job_ids[job_key] = job_id


class ConnectionStub:
    def hget(self, *_args):
        return None

    def lock(self, *_args, **_kwargs):
        return SimpleNamespace(
            acquire=lambda **_kwargs: True,
            extend=lambda *_args, **_kwargs: True,
            release=lambda: None,
        )


class QueueStub:
    name = "default"

    def __init__(self, *, fail_enqueue: bool = False) -> None:
        self.connection = ConnectionStub()
        self.fail_enqueue = fail_enqueue
        self.calls: list[dict] = []

    def enqueue_call(self, _func, **kwargs):
        self.calls.append(kwargs)
        if self.fail_enqueue:
            raise RedisError("enqueue failed before commit")
        return SimpleNamespace(id=kwargs["job_id"])


def _surface_func(runid: str) -> None:
    del runid


def _import_names(tree: ast.AST) -> dict[str, str]:
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return names


def _names_from_expr(expr: ast.AST | None, imports: dict[str, str]) -> tuple[str, ...]:
    if expr is None:
        return ()
    nodes = expr.elts if isinstance(expr, (ast.Tuple, ast.List)) else (expr,)
    return tuple(imports.get(node.id, node.id) for node in nodes if isinstance(node, ast.Name))


def _production_policy(case: SurfaceCase) -> ProductionPolicy:
    repo_root = Path(__file__).resolve().parents[2]
    tree = ast.parse((repo_root / case.source).read_text(encoding="utf-8"))
    imports = _import_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", None) != "enqueue_tracked_rq_job":
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        if ast.literal_eval(keywords["job_key"]) != case.job_key:
            continue
        root_names = _names_from_expr(keywords.get("allowed_root_funcs"), imports)
        func_expr = node.args[1]
        func_name = imports.get(func_expr.id, func_expr.id) if isinstance(func_expr, ast.Name) else ast.unparse(func_expr)
        if func_name == "target_func":
            func_name = root_names[0]
        conflicts_expr = keywords.get("conflict_keys")
        conflict_keys = (
            tuple(ast.literal_eval(conflicts_expr))
            if conflicts_expr is not None
            else (case.job_key,)
        )
        origins_expr = keywords.get("allowed_origins")
        origins = tuple(ast.literal_eval(origins_expr)) if origins_expr is not None else ("default",)
        modules_expr = keywords.get("allowed_workflow_modules")
        modules = tuple(ast.literal_eval(modules_expr)) if modules_expr is not None else ()
        return ProductionPolicy(
            func_name=func_name,
            origin=origins[0],
            conflict_keys=conflict_keys,
            root_func_names=root_names or (func_name,),
            workflow_func_names=_names_from_expr(keywords.get("allowed_workflow_funcs"), imports),
            workflow_modules=modules,
        )
    raise AssertionError(f"No production admission call for {case.name}")


def _fake_func(func_name: str):
    module, _, qualname = func_name.rpartition(".")
    func = lambda *_args, **_kwargs: None
    func.__module__ = module
    func.__qualname__ = qualname
    return func


def _submit(case: SurfaceCase, prep: PrepStub, queue: QueueStub):
    policy = _production_policy(case)
    return submission_recovery.enqueue_tracked_rq_job(
        queue,
        _fake_func(policy.func_name),
        prep=prep,
        job_key=case.job_key,
        runid="run-1",
        args=("run-1",),
        conflict_keys=policy.conflict_keys,
        allowed_origins=(policy.origin,),
        allowed_root_funcs=tuple(_fake_func(name) for name in policy.root_func_names),
        allowed_workflow_funcs=tuple(_fake_func(name) for name in policy.workflow_func_names),
        allowed_workflow_modules=policy.workflow_modules,
    )


@pytest.mark.parametrize("case", SURFACES, ids=lambda case: case.name)
def test_surface_manifest_matches_a_real_generic_admission_call(case: SurfaceCase) -> None:
    policy = _production_policy(case)
    assert policy.func_name
    assert policy.origin in {"default", "batch"}
    assert case.job_key in policy.conflict_keys
    assert policy.func_name in policy.root_func_names
    expected = EXPECTED_SPECIAL_POLICIES.get(case.name, {})
    if "conflict_keys" in expected:
        assert policy.conflict_keys == expected["conflict_keys"]
    if "root_suffixes" in expected:
        assert tuple(name.rpartition(".")[2] for name in policy.root_func_names) == expected["root_suffixes"]
    if "workflow_suffixes" in expected:
        assert tuple(name.rpartition(".")[2] for name in policy.workflow_func_names) == expected["workflow_suffixes"]


def _foreign_func(policy: ProductionPolicy, *, child: bool) -> str:
    for other_case in SURFACES:
        other = _production_policy(other_case)
        names = other.workflow_func_names if child else other.root_func_names
        for name in names:
            if name not in policy.root_func_names and name not in policy.workflow_func_names:
                return name
    raise AssertionError("surface inventory has no distinct foreign function")


def _candidate(policy: ProductionPolicy, mismatch: str | None = None, *, func_name: str | None = None):
    func_name = func_name or policy.func_name
    origin = policy.origin
    args = ("run-1",)
    meta = {"runid": "run-1"}
    if mismatch == "cross-run":
        args = ("other-run",)
        meta = {"runid": "other-run"}
    elif mismatch == "wrong-operation":
        func_name = _foreign_func(policy, child=False)
    elif mismatch == "hostile-lineage":
        func_name = _foreign_func(policy, child=True)
    elif mismatch == "wrong-origin":
        origin = "hostile-queue"
    return SimpleNamespace(func_name=func_name, origin=origin, args=args, meta=meta)


def _assert_declared_descendants(association, root_association, policy: ProductionPolicy) -> None:
    for func_name in policy.root_func_names:
        candidate = _candidate(policy, func_name=func_name)
        assert association(candidate) is True
        assert root_association(candidate) is True
    for func_name in policy.workflow_func_names:
        candidate = _candidate(policy, func_name=func_name)
        assert association(candidate) is True
        if func_name not in policy.root_func_names:
            assert root_association(candidate) is False
    for module_name in policy.workflow_modules:
        candidate = _candidate(
            policy, func_name=f"{module_name}.representative_child_rq"
        )
        assert association(candidate) is True
        assert root_association(candidate) is False


@pytest.mark.parametrize("case", SURFACES, ids=lambda case: case.name)
def test_surface_replaces_deferred_with_one_exact_receipt(
    case: SurfaceCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = PrepStub()
    queue = QueueStub()
    policy = _production_policy(case)
    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: "replacement-job")
    monkeypatch.setattr(
        submission_recovery,
        "reconcile_deferred_workflow",
        lambda *_args, **kwargs: (
            _assert_declared_descendants(
                kwargs["association"], kwargs["root_association"], policy
            )
            or (
                pytest.fail("production association rejected its own root")
                if not kwargs["association"](_candidate(policy))
                else SimpleNamespace(state="canceled", job_ids=("old-job",))
            )
        ),
    )

    job = _submit(case, prep, queue)

    assert job.id == "replacement-job"
    assert prep.job_ids[case.job_key] == "replacement-job"
    assert queue.calls[0]["job_id"] == "replacement-job"


@pytest.mark.parametrize("status", ("queued", "started", "scheduled"))
@pytest.mark.parametrize("case", SURFACES, ids=lambda case: case.name)
def test_surface_preserves_active_duplicate_protection(
    case: SurfaceCase, status: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = PrepStub()
    queue = QueueStub()
    policy = _production_policy(case)
    monkeypatch.setattr(
        submission_recovery,
        "reconcile_deferred_workflow",
        lambda *_args, **kwargs: (
            pytest.fail("production association rejected its own active root")
            if not kwargs["association"](_candidate(policy))
            else SimpleNamespace(state="active", job_ids=(f"old-{status}",))
        ),
    )

    with pytest.raises(submission_recovery.RqSubmissionConflict, match="still active"):
        _submit(case, prep, queue)

    assert prep.job_ids[case.job_key] == "old-job"
    assert queue.calls == []


@pytest.mark.parametrize("mismatch", ("cross-run", "wrong-operation", "wrong-origin", "hostile-lineage"))
@pytest.mark.parametrize("case", SURFACES, ids=lambda case: case.name)
def test_surface_contains_unverified_workflow(
    case: SurfaceCase, mismatch: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = PrepStub()
    queue = QueueStub()
    policy = _production_policy(case)
    monkeypatch.setattr(
        submission_recovery,
        "reconcile_deferred_workflow",
        lambda *_args, **kwargs: (
            pytest.fail(f"production association accepted {mismatch}")
            if kwargs["association"](_candidate(policy, mismatch))
            else SimpleNamespace(state="mismatch", job_ids=(mismatch,))
        ),
    )

    with pytest.raises(submission_recovery.RqSubmissionConflict, match="could not be verified"):
        _submit(case, prep, queue)

    assert prep.job_ids[case.job_key] == "old-job"
    assert queue.calls == []


@pytest.mark.parametrize("failure", ("cleanup", "hint-save", "enqueue"))
@pytest.mark.parametrize("case", SURFACES, ids=lambda case: case.name)
def test_surface_partial_failure_never_enqueues_an_untracked_job(
    case: SurfaceCase, failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = PrepStub(fail_save=failure == "hint-save")
    queue = QueueStub(fail_enqueue=failure == "enqueue")
    policy = _production_policy(case)
    monkeypatch.setattr(submission_recovery, "new_rq_job_id", lambda: "replacement-job")
    if failure == "cleanup":
        monkeypatch.setattr(
            submission_recovery,
            "reconcile_deferred_workflow",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RedisError("cleanup failed")),
        )
    else:
        monkeypatch.setattr(
            submission_recovery,
            "reconcile_deferred_workflow",
            lambda *_args, **kwargs: (
                pytest.fail("production association rejected its own root")
                if not kwargs["association"](_candidate(policy))
                else SimpleNamespace(state="canceled", job_ids=("old-job",))
            ),
        )
    monkeypatch.setattr(submission_recovery, "recover_committed_enqueue", lambda *_args, **_kwargs: None)

    with pytest.raises((OSError, RedisError)):
        _submit(case, prep, queue)

    if failure in {"cleanup", "hint-save"}:
        assert queue.calls == []
    if failure == "cleanup":
        assert prep.job_ids[case.job_key] == "old-job"
    elif failure == "enqueue":
        assert prep.job_ids[case.job_key] == "replacement-job"
