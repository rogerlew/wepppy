import copy
from contextlib import contextmanager
import json
from io import BytesIO
from pathlib import Path
import zipfile

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import landuse_routes
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        landuse_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"token_class": "service", "scope": "rq:enqueue rq:read"},
    )
    monkeypatch.setattr(landuse_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> None:
    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def fetch_job(self, job_id):
            return None

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(landuse_routes, "Queue", DummyQueue)
    monkeypatch.setattr(landuse_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    state: dict[str, list[object]] = {"removed": [], "jobs": []}

    class DummyPrep:
        def remove_timestamp(self, task, *args, **kwargs) -> None:
            state["removed"].append(task)

        def set_rq_job_id(self, key, job_id, *args, **kwargs) -> None:
            state["jobs"].append((key, job_id))

        def get_rq_job_id(self, *args, **kwargs):
            return None

    monkeypatch.setattr(landuse_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())
    return state


def test_build_landuse_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-42")
    prep_state = _stub_prep(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-42"
    assert prep_state["removed"] == [
        landuse_routes.TaskEnum.build_landuse,
        landuse_routes.TaskEnum.run_geneva,
    ]
    assert prep_state["jobs"] == [("build_landuse_rq", "job-42")]


def test_build_landuse_rejects_single_mode_for_mofe(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.Single
        multi_ofe = True
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def __init__(self) -> None:
            self.parse_inputs_calls: list[object] = []

        def parse_inputs(self, payload) -> None:
            self.parse_inputs_calls.append(payload)

    controller = DummyLanduse()
    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: controller,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_landuse_mode"
    assert "MOFE projects require a gridded landuse map" in payload["error"]["message"]
    assert controller.parse_inputs_calls == []


def test_build_landuse_rejects_invalid_custom_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-42")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

        def get_mapping_dict(self):
            raise landuse_routes.LanduseCustomMappingError(
                "Configured landuse custom mapping file is missing: landuse/landuse_user_defined_mapping.json",
                code="LANDUSE_CUSTOM_MAP_MISSING",
                details={"custom_mapping_relpath": "landuse/landuse_user_defined_mapping.json"},
            )

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "LANDUSE_CUSTOM_MAP_MISSING"
    assert "custom mapping file is missing" in payload["error"]["message"].lower()


def test_build_landuse_disturbed_uses_grouped_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "batch"
        mods = {"disturbed"}
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

    class DummyDisturbed:
        def __init__(self) -> None:
            self.grouped_update_calls: list[dict[str, bool]] = []

        @property
        def burn_shrubs(self) -> bool:
            return True

        @burn_shrubs.setter
        def burn_shrubs(self, _value: bool) -> None:
            raise AssertionError("build-landuse should not set burn_shrubs directly")

        @property
        def burn_grass(self) -> bool:
            return False

        @burn_grass.setter
        def burn_grass(self, _value: bool) -> None:
            raise AssertionError("build-landuse should not set burn_grass directly")

        def apply_build_landuse_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    disturbed = DummyDisturbed()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(landuse_routes.Disturbed, "getInstance", lambda wd: disturbed)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            json={"checkbox_burn_shrubs": True, "checkbox_burn_grass": False},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Set landuse inputs for batch processing"
    assert disturbed.grouped_update_calls == [{"burn_shrubs": True, "burn_grass": False}]


def test_build_landuse_disturbed_omitted_burn_fields_forwards_false_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "batch"
        mods = {"disturbed"}
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

    class DummyDisturbed:
        def __init__(self) -> None:
            self.grouped_update_calls: list[dict[str, bool]] = []

        def apply_build_landuse_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    disturbed = DummyDisturbed()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(landuse_routes.Disturbed, "getInstance", lambda wd: disturbed)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 200
    assert response.json() == {"message": "Set landuse inputs for batch processing"}
    assert disturbed.grouped_update_calls == [{"burn_shrubs": False, "burn_grass": False}]


def test_build_landuse_maps_nodb_lock_conflict_from_parse_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            raise NoDbAlreadyLockedError("already locked owner=alice token=secret-token")

    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(landuse_routes.Watershed, "getInstance", lambda wd: object())
    warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        landuse_routes.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            json={"mofe_buffer_selection": 42},
        )

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "conflict"
    assert payload["error"]["message"] == landuse_routes.NODB_LOCK_CONFLICT_CLIENT_MESSAGE
    assert "owner=alice" not in payload["error"]["message"]
    assert "secret-token" not in payload["error"]["message"]
    assert len(warning_calls) == 1
    warning_args, _warning_kwargs = warning_calls[0]
    warning_args_text = " ".join(str(arg) for arg in warning_args)
    assert "owner=" not in warning_args_text
    assert "token=" not in warning_args_text


def test_set_landuse_mode_updates_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    class DummyLanduse:
        def __init__(self) -> None:
            self.mode = landuse_routes.LanduseMode.Gridded
            self.single_selection = None
            self.grouped_update_calls: list[dict[str, object]] = []

        def apply_set_landuse_mode_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)
            self.mode = kwargs["mode"]
            self.single_selection = kwargs["single_selection"]

    controller = DummyLanduse()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: controller)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-mode",
            json={"mode": int(landuse_routes.LanduseMode.UserDefined), "landuse_single_selection": "forest"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Landuse mode updated"
    assert controller.grouped_update_calls == [
        {"mode": landuse_routes.LanduseMode.UserDefined, "single_selection": "forest"}
    ]
    assert controller.mode == landuse_routes.LanduseMode.UserDefined
    assert controller.single_selection == "forest"


@pytest.mark.parametrize("include_selection", [False, True])
def test_set_landuse_mode_rejects_single_mode_for_mofe(
    monkeypatch: pytest.MonkeyPatch,
    include_selection: bool,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    class DummyLanduse:
        multi_ofe = True

        def __init__(self) -> None:
            self.grouped_update_calls: list[dict[str, object]] = []

        def apply_set_landuse_mode_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    controller = DummyLanduse()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: controller)

    with TestClient(rq_engine.app) as client:
        body = {"mode": int(landuse_routes.LanduseMode.Single)}
        if include_selection:
            body["landuse_single_selection"] = "42"
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-mode",
            json=body,
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_landuse_mode"
    assert "MOFE projects require a gridded landuse map" in payload["error"]["message"]
    assert controller.grouped_update_calls == []


def test_set_landuse_mode_requires_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: object())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-mode",
            json={"landuse_single_selection": "forest"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "mode and landuse_single_selection must be provided"


def test_set_landuse_mode_updates_non_single_mode_when_selection_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    class DummyLanduse:
        def __init__(self) -> None:
            self.grouped_update_calls: list[dict[str, object]] = []

        def apply_set_landuse_mode_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    controller = DummyLanduse()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: controller)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-mode",
            json={"mode": int(landuse_routes.LanduseMode.UserDefined)},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Landuse mode updated"
    assert controller.grouped_update_calls == [
        {"mode": landuse_routes.LanduseMode.UserDefined, "single_selection": None}
    ]


def test_set_landuse_mode_requires_selection_for_single_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    class DummyLanduse:
        multi_ofe = False

        def __init__(self) -> None:
            self.grouped_update_calls: list[dict[str, object]] = []

        def apply_set_landuse_mode_updates(self, **kwargs) -> None:
            self.grouped_update_calls.append(kwargs)

    controller = DummyLanduse()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: controller)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-mode",
            json={"mode": int(landuse_routes.LanduseMode.Single)},
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "mode and landuse_single_selection must be provided"
    assert controller.grouped_update_calls == []


def test_set_landuse_db_updates_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    class DummyLanduse:
        nlcd_db = None

    controller = DummyLanduse()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: controller)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-db",
            json={"landuse_db": "nlcd"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Landuse database updated"
    assert controller.nlcd_db == "nlcd"


def test_set_landuse_db_maps_nodb_lock_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    class DummyLanduse:
        @property
        def nlcd_db(self):  # pragma: no cover - setter path only
            return None

        @nlcd_db.setter
        def nlcd_db(self, _value) -> None:
            raise NoDbAlreadyLockedError("already locked owner=alice token=secret-token")

    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())
    warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        landuse_routes.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-db",
            json={"landuse_db": "nlcd"},
        )

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "conflict"
    assert payload["error"]["message"] == landuse_routes.NODB_LOCK_CONFLICT_CLIENT_MESSAGE
    assert "owner=alice" not in payload["error"]["message"]
    assert "secret-token" not in payload["error"]["message"]
    assert len(warning_calls) == 1
    warning_args, _warning_kwargs = warning_calls[0]
    warning_args_text = " ".join(str(arg) for arg in warning_args)
    assert "owner=" not in warning_args_text
    assert "token=" not in warning_args_text


def test_set_landuse_db_resolves_pup_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_auth(monkeypatch)
    run_root = tmp_path / "run-1"
    pup_root = run_root / "_pups" / "scenario-a"
    pup_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        landuse_routes,
        "get_wd",
        lambda runid, prefer_active=False: str(run_root),
    )
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    captured: dict[str, str] = {}

    class DummyLanduse:
        nlcd_db = None

    def _get_instance(wd: str) -> DummyLanduse:
        captured["wd"] = wd
        return DummyLanduse()

    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", _get_instance)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-db?pup=scenario-a",
            json={"landuse_db": "nlcd"},
        )

    assert response.status_code == 200
    assert captured["wd"] == str(pup_root.resolve())


def test_set_landuse_db_rejects_unknown_pup_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_auth(monkeypatch)
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "_pups").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: object())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-db?pup=missing-project",
            json={"landuse_db": "nlcd"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Unknown pup project"


def test_set_landuse_db_rejects_pup_traversal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_auth(monkeypatch)
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "_pups" / "scenario-a").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: object())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-db?pup=../scenario-a",
            json={"landuse_db": "nlcd"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Unknown pup project"


def test_set_landuse_db_rejects_pup_when_pups_root_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_auth(monkeypatch)
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: object())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-db?pup=scenario-a",
            json={"landuse_db": "nlcd"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Unknown pup project"


def test_modify_landuse_coverage_updates_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)

    class DummyLanduse:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, float]] = []

        def modify_coverage(self, dom: str, cover: str, value: float) -> None:
            self.calls.append((dom, cover, value))

    controller = DummyLanduse()
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: controller)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-coverage",
            json={"dom": "1", "cover": "forest", "value": "75"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Landuse coverage updated"
    assert controller.calls == [("1", "forest", 75.0)]


def test_landuse_state_rejects_missing_read_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        landuse_routes,
        "require_jwt",
        lambda request: {"token_class": "service", "scope": "rq:enqueue"},
    )
    monkeypatch.setattr(landuse_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: object())

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/controllers/landuse/state")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert "rq:read" in payload["error"]["message"]
    assert "rq:status" in payload["error"]["message"]


def test_landuse_state_returns_controller_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        landuse_routes,
        "require_jwt",
        lambda request: {"token_class": "service", "scope": "rq:read"},
    )
    monkeypatch.setattr(landuse_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")

    class DummyLanduse:
        mode = landuse_routes.LanduseMode.Gridded
        single_selection = "101"
        nlcd_db = "nlcd"
        mapping = "disturbed"
        custom_mapping_relpath = None
        has_landuse = True
        domlc_d = {"1": "42", "2": "91"}

    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/controllers/landuse/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["controller"] == "landuse"
    assert payload["runid"] == "run-1"
    assert payload["config"] == "cfg"
    assert payload["run_state_domain"] == "metadata"
    assert payload["state"]["mode_name"] == "gridded"
    assert payload["state"]["dominant_landcover_count"] == 2
    assert payload["state"]["landuse_db"] == "nlcd"


def test_phase1_mutators_reject_unknown_token_class(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        landuse_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"token_class": "unknown", "scope": "rq:enqueue"},
    )
    monkeypatch.setattr(landuse_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(landuse_routes, "_preflight_landuse_mutation_root", lambda wd: None)
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: object())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/set-landuse-db",
            json={"landuse_db": "nlcd"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_modify_landuse_mapping_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    captured: dict[str, object] = {}

    class DummyJob:
        id = "job-map-42"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, func, args, timeout=None, **kwargs):
            captured["func"] = func
            captured["args"] = args
            captured["timeout"] = timeout
            captured["kwargs"] = kwargs
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(landuse_routes, "Queue", DummyQueue)
    monkeypatch.setattr(landuse_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"mappings": [{"dom": "44", "newdom": "71"}]},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-map-42"
    assert response.json()["mapping_count"] == 1
    assert captured["func"] is landuse_routes.modify_landuse_mapping_rq
    assert captured["args"] == ("run-1", [{"dom": "44", "newdom": "71"}])
    assert "depends_on" not in captured["kwargs"]


def test_modify_landuse_mapping_requires_payload_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"dom": "44"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "mappings or dom/newdom must be provided"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"mappings": [{"dom": None, "newdom": "71"}]}, "mappings[0].dom must be provided"),
        ({"mappings": [{"dom": "44", "newdom": None}]}, "mappings[0].newdom must be provided"),
    ],
)
def test_modify_landuse_mapping_rejects_null_mapping_keys(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    message: str,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json=payload,
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == message


def test_modify_landuse_mapping_accepts_legacy_dom_newdom_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    captured: dict[str, object] = {}

    class DummyJob:
        id = "job-map-legacy"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, func, args, timeout=None, **kwargs):
            captured["func"] = func
            captured["args"] = args
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(landuse_routes, "Queue", DummyQueue)
    monkeypatch.setattr(landuse_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"dom": "44", "newdom": "71"},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-map-legacy"
    assert response.json()["mapping_count"] == 1
    assert captured["func"] is landuse_routes.modify_landuse_mapping_rq
    assert captured["args"] == ("run-1", [{"dom": "44", "newdom": "71"}])


def test_modify_landuse_mapping_rejects_blank_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"mappings": [{"dom": "   ", "newdom": "  "}]},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "dom and newdom must be provided"


def test_modify_landuse_mapping_rejects_control_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"mappings": [{"dom": "4\t4", "newdom": "71"}]},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "mappings[0].dom contains unsupported control characters"


def test_modify_landuse_mapping_deduplicates_dom_updates_last_write_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    captured: dict[str, object] = {}

    class DummyJob:
        id = "job-map-dedupe"

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, func, args, timeout=None, **kwargs):
            captured["func"] = func
            captured["args"] = args
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(landuse_routes, "Queue", DummyQueue)
    monkeypatch.setattr(landuse_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={
                "mappings": [
                    {"dom": "44", "newdom": "71"},
                    {"dom": "55", "newdom": "91"},
                    {"dom": "44", "newdom": "42"},
                ]
            },
        )

    assert response.status_code == 200
    assert response.json()["mapping_count"] == 2
    assert captured["func"] is landuse_routes.modify_landuse_mapping_rq
    assert captured["args"] == (
        "run-1",
        [
            {"dom": "44", "newdom": "42"},
            {"dom": "55", "newdom": "91"},
        ],
    )


def test_modify_landuse_mapping_enforces_batch_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    edits = [
        {"dom": str(idx), "newdom": "71"}
        for idx in range(landuse_routes.LANDUSE_MAPPING_BATCH_MAX_EDITS + 1)
    ]

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"mappings": edits},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == (
        f"mappings exceeds {landuse_routes.LANDUSE_MAPPING_BATCH_MAX_EDITS} edits"
    )


def test_modify_landuse_mapping_propagates_nodir_preflight_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _rel: str, *, view: str = "effective"):
        raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")

    monkeypatch.setattr(landuse_routes, "nodir_resolve", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"mappings": [{"dom": "44", "newdom": "71"}]},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_MIXED_STATE"


def test_modify_landuse_mapping_returns_500_when_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_prep(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            raise RuntimeError("queue down")

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(landuse_routes, "Queue", DummyQueue)
    monkeypatch.setattr(landuse_routes.redis, "Redis", lambda **kwargs: DummyRedis())

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/modify-landuse-mapping",
            json={"mappings": [{"dom": "44", "newdom": "71"}]},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Failed to modify landuse mapping"


def test_build_landuse_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.Gridded
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            raise ValueError("bad payload")

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "bad payload"


def test_build_landuse_requires_mapping_for_user_defined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "landuse_management_mapping_selection must be provided"


def test_build_landuse_rejects_path_like_mapping_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            json={"landuse_management_mapping_selection": "../secret/custom_map.json"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_mapping_selection"
    assert "supported mapping keys" in payload["error"]["message"]


def test_build_landuse_propagates_nodir_preflight_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    def _raise_nodir(_wd: str, _rel: str, *, view: str = "effective"):
        raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")

    monkeypatch.setattr(landuse_routes, "nodir_resolve", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/build-landuse", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODIR_MIXED_STATE"


def test_build_landuse_user_defined_propagates_mutation_nodir_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: "/tmp/run")

    class DummyLanduse:
        run_group = "default"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = "/tmp"
        lc_fn = "/tmp/lc.tif"
        mapping = None
        user_defined_landcover_fn = "existing.tif"

        def parse_inputs(self, payload) -> None:
            return None

    monkeypatch.setattr(
        landuse_routes.Landuse,
        "getInstance",
        lambda wd: DummyLanduse(),
    )
    monkeypatch.setattr(
        landuse_routes.Watershed,
        "getInstance",
        lambda wd: object(),
    )

    def _raise_nodir(
        wd: str,
        root: str,
        callback,
        *,
        purpose: str = "nodir-mutation",
    ):
        raise NoDirError(http_status=503, code="NODIR_LOCKED", message="locked")

    monkeypatch.setattr(landuse_routes, "mutate_root", _raise_nodir)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            json={"landuse_management_mapping_selection": "disturbed"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "NODIR_LOCKED"


def test_build_landuse_user_defined_rejects_invalid_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: str(tmp_path))

    class DummyLanduse:
        run_group = "batch"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = str(tmp_path / "landuse")
        lc_fn = str(tmp_path / "landuse" / "lc.tif")
        mapping = None
        user_defined_landcover_fn = None

        def parse_inputs(self, payload) -> None:
            return None

    class DummyWatershed:
        subwta = str(tmp_path / "subwta.tif")

    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(landuse_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(landuse_routes, "mutate_root", lambda wd, root, callback, purpose="x": callback())

    import wepppy.all_your_base.geo as geo_module

    monkeypatch.setattr(
        geo_module,
        "raster_stacker",
        lambda _src, _subwta, out: Path(out).write_bytes(b"lc"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            data={"landuse_management_mapping_selection": "disturbed"},
            files={"input_upload_landuse": ("bad.exe", b"data")},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"].startswith("Invalid file extension.")
    assert payload["error"]["details"].startswith("Invalid file extension.")
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]


def test_build_landuse_user_defined_rejects_oversize_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: str(tmp_path))
    monkeypatch.setattr(landuse_routes, "LANDUSE_USER_DEFINED_MAX_BYTES", 4)

    class DummyLanduse:
        run_group = "batch"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = str(tmp_path / "landuse")
        lc_fn = str(tmp_path / "landuse" / "lc.tif")
        mapping = None
        user_defined_landcover_fn = None

        def parse_inputs(self, payload) -> None:
            return None

    class DummyWatershed:
        subwta = str(tmp_path / "subwta.tif")

    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(landuse_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(landuse_routes, "mutate_root", lambda wd, root, callback, purpose="x": callback())

    import wepppy.all_your_base.geo as geo_module

    monkeypatch.setattr(
        geo_module,
        "raster_stacker",
        lambda _src, _subwta, out: Path(out).write_bytes(b"lc"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            data={"landuse_management_mapping_selection": "disturbed"},
            files={"input_upload_landuse": ("landuse.tif", b"abcdef")},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["error"]["message"] == "File exceeds maximum allowed size"
    assert payload["error"]["details"] == "File exceeds maximum allowed size"
    assert payload["error"]["code"] == "payload_too_large"
    assert payload["error_id"]


def test_build_landuse_user_defined_requires_upload_when_no_existing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid: str(tmp_path))

    class DummyLanduse:
        run_group = "batch"
        mods: set[str] = set()
        mode = landuse_routes.LanduseMode.UserDefined
        lc_dir = str(tmp_path / "landuse")
        lc_fn = str(tmp_path / "landuse" / "lc.tif")
        mapping = None
        user_defined_landcover_fn = None

        def parse_inputs(self, payload) -> None:
            return None

    class DummyWatershed:
        subwta = str(tmp_path / "subwta.tif")

    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(landuse_routes.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(landuse_routes, "mutate_root", lambda wd, root, callback, purpose="x": callback())

    import wepppy.all_your_base.geo as geo_module

    monkeypatch.setattr(
        geo_module,
        "raster_stacker",
        lambda _src, _subwta, out: Path(out).write_bytes(b"lc"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/build-landuse",
            data={"landuse_management_mapping_selection": "disturbed"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert (
        payload["error"]["message"]
        == "input_upload_landuse is required when no existing user-defined landuse file is available."
    )
    assert payload["error"]["details"] == payload["error"]["message"]
    assert payload["error"]["code"] == "validation_error"
    assert payload["error_id"]


class _DummyLandusePhase3:
    def __init__(self, wd: str) -> None:
        self.wd = wd
        self.mapping = "disturbed"
        self._custom_mapping_relpath: str | None = None
        self.build_managements_calls = 0
        self.modify_calls: list[tuple[list[str], str]] = []
        self.raise_on_build = False

    @contextmanager
    def locked(self):
        yield

    def _resolve_effective_mapping_reference(self, mapping_reference: str | None = None):
        return mapping_reference

    @property
    def custom_mapping_relpath(self) -> str | None:
        return self._custom_mapping_relpath

    @custom_mapping_relpath.setter
    def custom_mapping_relpath(self, value: str | None) -> None:
        self._custom_mapping_relpath = value

    def build_managements(self) -> None:
        self.build_managements_calls += 1
        if self.raise_on_build:
            raise RuntimeError("boom")

    def modify(self, topaz_ids: list[str], lccode: str) -> None:
        self.modify_calls.append((topaz_ids, lccode))


def _stub_landuse_phase3_common(
    monkeypatch: pytest.MonkeyPatch,
    run_root: Path,
    landuse: _DummyLandusePhase3,
) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: landuse)
    monkeypatch.setattr(
        landuse_routes.landuse_flask.Landuse,
        "getInstance",
        lambda wd: landuse,
    )


def test_landuse_phase3_catalog_upload_update_delete_via_rq_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    source_man = Path("wepppy/wepp/management/data/Tahoe/Tahoe_Old_Forest.man")
    assert source_man.exists()

    with TestClient(rq_engine.app) as client:
        with source_man.open("rb") as handle:
            upload = client.post(
                "/api/runs/run-1/cfg/landuse-user-defined/upload",
                files={"management_upload": ("custom_entry.man", handle.read())},
            )
        assert upload.status_code == 200
        assert upload.json()["imported_files"] == ["custom_entry.man"]

        listed = client.get("/api/runs/run-1/cfg/landuse-user-defined/catalog")
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert [item["filename"] for item in items] == ["custom_entry.man"]
        assert listed.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"

        updated = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/update-description",
            json={"filename": "custom_entry.man", "description": "Custom Forest"},
        )
        assert updated.status_code == 200
        item = next(entry for entry in updated.json()["items"] if entry["filename"] == "custom_entry.man")
        assert item["description"] == "Custom Forest"

        deleted = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/delete",
            json={"filename": "custom_entry.man"},
        )
        assert deleted.status_code == 200
        assert deleted.json()["items"] == []

    assert not (run_root / "landuse" / "user-defined" / "custom_entry.man").exists()


def test_landuse_phase3_upload_rejects_zip_with_non_man_members(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("bad.txt", "not a management file")
    archive_buffer.seek(0)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("invalid.zip", archive_buffer.read())},
        )

    assert response.status_code == 400
    payload = response.json()
    assert ".man extension" in payload["error"]["message"].lower()


def test_landuse_phase3_upload_accepts_zip_with_finder_metadata_sidecars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    source_man = Path("wepppy/wepp/management/data/Tahoe/Tahoe_Old_Forest.man")
    with source_man.open("rb") as handle:
        man_payload = handle.read()

    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("custom_entry.man", man_payload)
        archive.writestr("__MACOSX/._custom_entry.man", b"resource-fork")
        archive.writestr(".DS_Store", b"finder-metadata")
    archive_buffer.seek(0)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("finder.zip", archive_buffer.read())},
        )

    assert response.status_code == 200
    assert response.json()["imported_files"] == ["custom_entry.man"]


def test_landuse_phase3_upload_rejects_zip_with_nested_man_members(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    source_man = Path("wepppy/wepp/management/data/Tahoe/Tahoe_Old_Forest.man")
    with source_man.open("rb") as handle:
        man_payload = handle.read()

    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("nested/custom_entry.man", man_payload)
    archive_buffer.seek(0)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("nested.zip", archive_buffer.read())},
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Archive members must be at the archive root."


def test_landuse_phase3_upload_rejects_symlink_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    escaped_target = tmp_path / "escaped-target"
    escaped_target.mkdir(parents=True, exist_ok=True)
    catalog_link = run_root / "landuse" / "user-defined"
    catalog_link.parent.mkdir(parents=True, exist_ok=True)
    catalog_link.symlink_to(escaped_target, target_is_directory=True)

    source_man = Path("wepppy/wepp/management/data/Tahoe/Tahoe_Old_Forest.man")
    with source_man.open("rb") as handle:
        payload_bytes = handle.read()

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("custom_entry.man", payload_bytes)},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RUN_PATH"


def test_landuse_phase3_upload_enforces_max_bytes_and_conflict_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)
    monkeypatch.setattr(landuse_routes.landuse_flask, "_LANDUSE_MAN_UPLOAD_MAX_BYTES", 4)

    with TestClient(rq_engine.app) as client:
        oversize = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("custom_entry.man", b"abcdef")},
        )
        assert oversize.status_code == 413

    monkeypatch.setattr(landuse_routes.landuse_flask, "_LANDUSE_MAN_UPLOAD_MAX_BYTES", 5 * 1024 * 1024)
    source_man = Path("wepppy/wepp/management/data/Tahoe/Tahoe_Old_Forest.man")
    with source_man.open("rb") as handle:
        payload_bytes = handle.read()

    with TestClient(rq_engine.app) as client:
        first = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("custom_entry.man", payload_bytes)},
        )
        assert first.status_code == 200

        conflict = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("custom_entry.man", payload_bytes)},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "CATALOG_CONFLICT"


def test_landuse_phase3_upload_replace_true_overwrites_existing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    source_man = Path("wepppy/wepp/management/data/Tahoe/Tahoe_Old_Forest.man")
    with source_man.open("rb") as handle:
        original_payload = handle.read()
    replacement_payload = original_payload.replace(b"Old Forest", b"Old Forest (Replacement)")

    with TestClient(rq_engine.app) as client:
        first = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            files={"management_upload": ("custom_entry.man", original_payload)},
        )
        assert first.status_code == 200

        replaced = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/upload",
            data={"replace": "true"},
            files={"management_upload": ("custom_entry.man", replacement_payload)},
        )
        assert replaced.status_code == 200
        assert replaced.json()["replace"] is True

    installed_path = run_root / "landuse" / "user-defined" / "custom_entry.man"
    assert installed_path.read_bytes() == replacement_payload


def test_landuse_phase3_map_snapshot_and_save(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    mapping_payload = {
        "21": {
            "Key": 21,
            "Description": "Low Intensity Residential",
            "DisturbedClass": "developed low intensity",
            "ManagementFile": "Developed_Low_Intensity.man",
            "ManagementDir": "/maps",
            "SoilFile": "Developed_Low_Intensity.sol",
            "Color": [221, 201, 201, 255],
        },
        "22": {
            "Key": 22,
            "Description": "High Intensity Residential",
            "DisturbedClass": "developed moderate intensity",
            "ManagementFile": "Developed_Moderate_Intensity.man",
            "ManagementDir": "/maps",
            "SoilFile": "Developed_Moderate_Intensity.sol",
            "Color": [216, 147, 130, 255],
        },
    }
    monkeypatch.setattr(landuse_routes.landuse_flask, "load_map", lambda _mapping: copy.deepcopy(mapping_payload))

    class DummyPrep:
        def timestamp(self, _task: object) -> None:
            return None

    monkeypatch.setattr(landuse_routes.RedisPrep, "getInstance", lambda _wd: DummyPrep())

    with TestClient(rq_engine.app) as client:
        snapshot = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")
        assert snapshot.status_code == 200
        assert snapshot.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
        snapshot_payload = snapshot.json()
        assert len(snapshot_payload["rows"]) == 2
        assert snapshot_payload["lookup_sha256"]

        save = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": snapshot_payload["lookup_sha256"],
                "rows": [
                    {"key": "21", "management_file": "Developed_Moderate_Intensity.man"},
                    {
                        "key": "22",
                        "management_file": "Developed_Moderate_Intensity.man",
                        "description": "High Intensity Residential (Edited)",
                    },
                ],
            },
        )
        assert save.status_code == 200
        assert save.json()["message"] == "Landuse map saved"

    assert landuse.build_managements_calls == 0
    assert landuse.custom_mapping_relpath == "landuse/landuse_user_defined_mapping.json"
    override_path = run_root / "landuse" / "landuse_user_defined_mapping.json"
    assert override_path.exists()
    override_payload = json.loads(override_path.read_text(encoding="utf-8"))
    assert override_payload["21"]["ManagementFile"] == "Developed_Moderate_Intensity.man"
    assert override_payload["21"]["Description"] == "Developed Moderate Intensity"
    assert override_payload["22"]["ManagementFile"] == "Developed_Moderate_Intensity.man"
    assert override_payload["22"]["Description"] == "High Intensity Residential (Edited)"


def test_landuse_phase3_map_save_requires_precondition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)
    monkeypatch.setattr(
        landuse_routes.landuse_flask,
        "load_map",
        lambda _mapping: {
            "21": {
                "Key": 21,
                "Description": "Low Intensity Residential",
                "DisturbedClass": "developed low intensity",
                "ManagementFile": "Developed_Low_Intensity.man",
                "ManagementDir": "/maps",
            }
        },
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={"rows": [{"key": "21", "management_file": "Developed_Low_Intensity.man"}]},
        )

    assert response.status_code == 428
    assert response.json()["error"]["code"] == "PRECONDITION_REQUIRED"


def test_landuse_phase3_map_save_accepts_header_precondition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)
    monkeypatch.setattr(
        landuse_routes.landuse_flask,
        "load_map",
        lambda _mapping: {
            "21": {
                "Key": 21,
                "Description": "Low Intensity Residential",
                "DisturbedClass": "developed low intensity",
                "ManagementFile": "Developed_Low_Intensity.man",
                "ManagementDir": "/maps",
            }
        },
    )

    with TestClient(rq_engine.app) as client:
        snapshot = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")
        assert snapshot.status_code == 200
        precondition = snapshot.json()["lookup_sha256"]

        save = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            headers={"X-If-Match-Sha256": precondition},
            json={"rows": [{"key": "21", "management_file": "Developed_Low_Intensity.man"}]},
        )

    assert save.status_code == 200
    assert save.json()["message"] == "Landuse map saved"


def test_landuse_phase3_map_save_rejects_stale_hash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    initial_mapping = {
        "21": {
            "Key": 21,
            "Description": "Low Intensity Residential",
            "DisturbedClass": "developed low intensity",
            "ManagementFile": "Developed_Low_Intensity.man",
            "ManagementDir": "/maps",
            "Color": [221, 201, 201, 255],
        }
    }
    updated_mapping = copy.deepcopy(initial_mapping)
    updated_mapping["21"]["ManagementFile"] = "Developed_Moderate_Intensity.man"

    monkeypatch.setattr(landuse_routes.landuse_flask, "load_map", lambda _mapping: copy.deepcopy(initial_mapping))

    with TestClient(rq_engine.app) as client:
        snapshot = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")
        assert snapshot.status_code == 200
        stale_sha = snapshot.json()["lookup_sha256"]

        monkeypatch.setattr(landuse_routes.landuse_flask, "load_map", lambda _mapping: copy.deepcopy(updated_mapping))
        save = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": stale_sha,
                "rows": [{"key": "21", "management_file": "Developed_Moderate_Intensity.man"}],
            },
        )

    assert save.status_code == 409
    payload = save.json()
    assert payload["error"]["code"] == "STALE_LOOKUP"
    assert payload["error"]["details"]["expected_sha256"] == stale_sha


def test_landuse_phase3_map_save_validates_rows_and_saves_without_building_managements(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    mapping_payload = {
        "21": {
            "Key": 21,
            "Description": "Low Intensity Residential",
            "DisturbedClass": "developed low intensity",
            "ManagementFile": "Developed_Low_Intensity.man",
            "ManagementDir": "/maps",
            "Color": [221, 201, 201, 255],
        },
        "22": {
            "Key": 22,
            "Description": "High Intensity Residential",
            "DisturbedClass": "developed moderate intensity",
            "ManagementFile": "Developed_Moderate_Intensity.man",
            "ManagementDir": "/maps",
            "Color": [216, 147, 130, 255],
        },
    }
    monkeypatch.setattr(landuse_routes.landuse_flask, "load_map", lambda _mapping: copy.deepcopy(mapping_payload))

    override_path = run_root / "landuse" / "landuse_user_defined_mapping.json"
    override_path.parent.mkdir(parents=True, exist_ok=True)
    prior_payload = {"21": {"ManagementFile": "Developed_Low_Intensity.man"}}
    override_path.write_text(json.dumps(prior_payload), encoding="utf-8")
    landuse.custom_mapping_relpath = "landuse/landuse_user_defined_mapping.json"

    class DummyPrep:
        def timestamp(self, _task: object) -> None:
            return None

    monkeypatch.setattr(landuse_routes.RedisPrep, "getInstance", lambda _wd: DummyPrep())

    with TestClient(rq_engine.app) as client:
        snapshot = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")
        assert snapshot.status_code == 200
        lookup_sha = snapshot.json()["lookup_sha256"]

        invalid = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": lookup_sha,
                "rows": [
                    {"key": "21", "management_file": "Developed_Low_Intensity.man"},
                    {"key": "21", "management_file": "Developed_Moderate_Intensity.man"},
                ],
            },
        )
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "invalid_rows_payload"

        save = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": lookup_sha,
                "rows": [
                    {"key": "21", "management_file": "Developed_Low_Intensity.man"},
                    {"key": "22", "management_file": "Developed_Moderate_Intensity.man"},
                ],
            },
        )

    assert save.status_code == 200
    saved_payload = json.loads(override_path.read_text(encoding="utf-8"))
    assert saved_payload["21"]["ManagementFile"] == "Developed_Low_Intensity.man"
    assert saved_payload["22"]["ManagementFile"] == "Developed_Moderate_Intensity.man"
    assert landuse.custom_mapping_relpath == "landuse/landuse_user_defined_mapping.json"
    assert landuse.build_managements_calls == 0


def test_landuse_phase3_map_save_rejects_missing_extra_and_unknown_management_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    mapping_payload = {
        "21": {
            "Key": 21,
            "Description": "Low Intensity Residential",
            "DisturbedClass": "developed low intensity",
            "ManagementFile": "Developed_Low_Intensity.man",
            "ManagementDir": "/maps",
            "Color": [221, 201, 201, 255],
        },
        "22": {
            "Key": 22,
            "Description": "High Intensity Residential",
            "DisturbedClass": "developed moderate intensity",
            "ManagementFile": "Developed_Moderate_Intensity.man",
            "ManagementDir": "/maps",
            "Color": [216, 147, 130, 255],
        },
    }
    monkeypatch.setattr(landuse_routes.landuse_flask, "load_map", lambda _mapping: copy.deepcopy(mapping_payload))

    with TestClient(rq_engine.app) as client:
        snapshot = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")
        assert snapshot.status_code == 200
        lookup_sha = snapshot.json()["lookup_sha256"]

        missing = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": lookup_sha,
                "rows": [{"key": "21", "management_file": "Developed_Low_Intensity.man"}],
            },
        )
        assert missing.status_code == 400
        assert missing.json()["error"]["code"] == "invalid_rows_payload"
        assert "missing=['22']" in missing.json()["error"]["message"]

        extra = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": lookup_sha,
                "rows": [
                    {"key": "21", "management_file": "Developed_Low_Intensity.man"},
                    {"key": "22", "management_file": "Developed_Moderate_Intensity.man"},
                    {"key": "999", "management_file": "Developed_Moderate_Intensity.man"},
                ],
            },
        )
        assert extra.status_code == 400
        assert extra.json()["error"]["code"] == "invalid_rows_payload"
        assert "extra=['999']" in extra.json()["error"]["message"]

        unknown = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": lookup_sha,
                "rows": [
                    {"key": "21", "management_file": "Unknown_File.man"},
                    {"key": "22", "management_file": "Developed_Moderate_Intensity.man"},
                ],
            },
        )
        assert unknown.status_code == 400
        assert unknown.json()["error"]["code"] == "invalid_rows_payload"
        assert "Unknown management_file 'Unknown_File.man'" in unknown.json()["error"]["message"]

        too_long_description = "x" * (landuse_routes.landuse_flask._LANDUSE_MAP_DESCRIPTION_MAX_LENGTH + 1)
        invalid_description = client.post(
            "/api/runs/run-1/cfg/landuse-map/save",
            json={
                "if_match_sha256": lookup_sha,
                "rows": [
                    {
                        "key": "21",
                        "management_file": "Developed_Low_Intensity.man",
                        "description": too_long_description,
                    },
                    {"key": "22", "management_file": "Developed_Moderate_Intensity.man"},
                ],
            },
        )
        assert invalid_description.status_code == 400
        assert invalid_description.json()["error"]["code"] == "invalid_rows_payload"
        assert "rows[0].description exceeds" in invalid_description.json()["error"]["message"]


def test_landuse_phase3_clear_override_clears_path_and_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    landuse.custom_mapping_relpath = "landuse/landuse_user_defined_mapping.json"
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    override_path = run_root / "landuse" / "landuse_user_defined_mapping.json"
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text("{}", encoding="utf-8")

    class DummyPrep:
        def timestamp(self, _task: object) -> None:
            return None

    monkeypatch.setattr(landuse_routes.RedisPrep, "getInstance", lambda _wd: DummyPrep())

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/landuse-map/clear-override", json={})

    assert response.status_code == 200
    assert response.json()["message"] == "Landuse map override cleared"
    assert landuse.custom_mapping_relpath is None
    assert landuse.build_managements_calls == 1
    assert not override_path.exists()


def test_landuse_phase3_modify_landuse_strict_input_and_auth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    with TestClient(rq_engine.app) as client:
        success = client.post(
            "/api/runs/run-1/cfg/modify-landuse",
            json={"topaz_ids": [1, "2", " 3 "], "landuse": 7},
        )
        assert success.status_code == 200
        assert success.json()["topaz_count"] == 3
        assert landuse.modify_calls == [(["1", "2", "3"], "7")]

        invalid = client.post(
            "/api/runs/run-1/cfg/modify-landuse",
            json={"topaz_ids": ["abc"], "landuse": 7},
        )
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "validation_error"

    monkeypatch.setattr(
        landuse_routes,
        "require_jwt",
        lambda request, required_scopes=None: {"token_class": "unknown", "scope": "rq:enqueue"},
    )
    monkeypatch.setattr(landuse_routes, "authorize_run_access", lambda claims, runid: None)
    with TestClient(rq_engine.app) as client:
        forbidden = client.post(
            "/api/runs/run-1/cfg/landuse-user-defined/delete",
            json={"filename": "x.man"},
        )

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"


def test_landuse_phase3_read_routes_require_read_scope(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    monkeypatch.setattr(
        landuse_routes,
        "require_jwt",
        lambda request: {"token_class": "service", "scope": "rq:enqueue"},
    )
    monkeypatch.setattr(landuse_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: landuse)

    with TestClient(rq_engine.app) as client:
        catalog = client.get("/api/runs/run-1/cfg/landuse-user-defined/catalog")
        snapshot = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")

    assert catalog.status_code == 403
    assert snapshot.status_code == 403


def test_landuse_phase3_read_routes_reject_unknown_token_class(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    monkeypatch.setattr(
        landuse_routes,
        "require_jwt",
        lambda request: {"token_class": "unknown", "scope": "rq:read"},
    )
    monkeypatch.setattr(landuse_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(landuse_routes.Landuse, "getInstance", lambda wd: landuse)

    with TestClient(rq_engine.app) as client:
        catalog = client.get("/api/runs/run-1/cfg/landuse-user-defined/catalog")
        snapshot = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")

    assert catalog.status_code == 403
    assert catalog.json()["error"]["code"] == "forbidden"
    assert snapshot.status_code == 403
    assert snapshot.json()["error"]["code"] == "forbidden"


def test_landuse_phase3_map_snapshot_redacts_map_path_in_error_details(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-1"
    run_root.mkdir(parents=True, exist_ok=True)
    landuse = _DummyLandusePhase3(str(run_root))
    _stub_landuse_phase3_common(monkeypatch, run_root, landuse)

    def _raise_mapping_error(_landuse: object, _wd: str):
        raise landuse_routes.ManagementMapLoadError(
            "Management map file does not exist: /tmp/run-1/landuse/custom-map.json",
            code="management_map_missing",
            map_path="/tmp/run-1/landuse/custom-map.json",
        )

    monkeypatch.setattr(landuse_routes.landuse_flask, "_build_landuse_map_snapshot_payload", _raise_mapping_error)

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/landuse-map/snapshot")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "management_map_missing"
    assert payload["error"]["message"] == "Management map file does not exist"
    details = payload["error"].get("details")
    assert not details or "map_path" not in details
