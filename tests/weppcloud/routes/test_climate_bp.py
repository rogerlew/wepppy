from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import threading

import pytest

pytest.importorskip("flask")
from flask import Flask

from wepppy.nodb.project_config_capabilities import resolve_run_capability_authority
from wepppy.nodb.project_config_reader import ProjectConfigStatus
from wepppy.nodb.project_config_snapshot import (
    materialize_preset_snapshot,
    resolve_preset_snapshot,
)
from wepppy.project_config_serialization import parse_config_text

try:
    import wepppy.weppcloud.routes.nodb_api.climate_bp as climate_module
    from wepppy.nodb.core.climate import ClimateMode
except ImportError:
    pytest.skip("Climate blueprint dependencies missing", allow_module_level=True)

RUN_ID = "test-run"
CONFIG = "main"
pytestmark = pytest.mark.routes


def _eu_preset_authority(root: Path):
    candidate = resolve_preset_snapshot(
        "eu-disturbed",
        {},
        source_revision="test-revision",
    )
    materialize_preset_snapshot(root, candidate)
    values = parse_config_text(candidate.config_bytes.decode("utf-8"))
    config = SimpleNamespace(
        project_config_status=ProjectConfigStatus(
            "flattened",
            str(root),
            "eu-disturbed.cfg",
            True,
            True,
            config_sha256=hashlib.sha256(candidate.config_bytes).hexdigest(),
        ),
        config_get_raw=lambda section, option, default=None: values.get(
            section, {}
        ).get(option, default),
        config_get_list=lambda section, option, default=None: values.get(
            section, {}
        ).get(option, default),
    )
    return resolve_run_capability_authority(config)


@pytest.fixture()
def climate_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Provide a Flask test client with the climate blueprint registered."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(climate_module.climate_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    cli_dir = run_dir / "cli"
    cli_dir.mkdir()

    def fake_get_wd(runid: str) -> str:
        assert runid == RUN_ID
        return str(run_dir)

    monkeypatch.setattr(climate_module, "get_wd", fake_get_wd)

    class DummyClimate:
        _instances: dict[str, "DummyClimate"] = {}

        def __init__(self, wd: str) -> None:
            self._mutation_lock = threading.Lock()
            self.fail_next_catalog_assignment = False
            self.fail_catalog_thread: str | None = None
            self._block_pair_thread: str | None = None
            self.first_mode_written = threading.Event()
            self.second_lock_attempt = threading.Event()
            self.committed_pairs: list[tuple[ClimateMode, str]] = []
            self.wd = wd
            self.cli_dir = str(cli_dir)
            self.climatestation_mode = climate_module.ClimateStationMode.Closest
            self.climatestation = "STA-1"
            self.has_observed = True
            self.readonly = False
            self.closest_calls = 0
            self.closest_stations = [
                {
                    "id": "STA-1",
                    "desc": "Station One",
                    "distance_to_query_location": 12.345,
                    "years": 8,
                }
            ]
            self.heuristic_stations: list[dict[str, Any]] | None = None
            self.latest_cli_filename: str | None = None
            self.set_cli_calls = 0
            self.use_gridmet_wind_when_applicable = False
            self.adjust_mx_pt5 = False
            self.silent_pass_observed_quality_guard = False
            self.climatestation_par_contents = "PAR DATA"
            self.climate_mode = ClimateMode.Vanilla
            self.catalog_id = "dataset_a"
            self.climate_spatialmode = 0
            self._datasets = {
                "dataset_a": SimpleNamespace(
                    catalog_id="dataset_a", climate_mode=int(ClimateMode.Vanilla)
                ),
                "dataset_b": SimpleNamespace(
                    catalog_id="dataset_b", climate_mode=int(ClimateMode.Future)
                ),
            }

        def __setattr__(self, name: str, value: Any) -> None:
            if (
                name == "_catalog_id"
                and (
                    getattr(self, "fail_next_catalog_assignment", False)
                    or threading.current_thread().name
                    == getattr(self, "fail_catalog_thread", None)
                )
            ):
                object.__setattr__(self, "fail_next_catalog_assignment", False)
                object.__setattr__(self, "fail_catalog_thread", None)
                raise RuntimeError("injected catalog assignment failure")
            object.__setattr__(self, name, value)
            if (
                name == "_climate_mode"
                and threading.current_thread().name == getattr(self, "_block_pair_thread", None)
            ):
                self.first_mode_written.set()
                assert self.second_lock_attempt.wait(timeout=2)

        @property
        def climate_mode(self) -> ClimateMode:
            return self._climate_mode

        @climate_mode.setter
        def climate_mode(self, value: ClimateMode | int) -> None:
            self._climate_mode = ClimateMode(value)

        @property
        def catalog_id(self) -> str:
            return self._catalog_id

        @catalog_id.setter
        def catalog_id(self, value: str) -> None:
            self._catalog_id = value

        @contextmanager
        def locked(self):
            if (
                threading.current_thread().name == "pair-b"
                and self.first_mode_written.is_set()
            ):
                self.second_lock_attempt.set()
            with self._mutation_lock:
                yield
                self.committed_pairs.append((self._climate_mode, self._catalog_id))

        def _validate_station_catalog_constraints(self, **_kwargs: Any) -> None:
            return None

        @classmethod
        def getInstance(cls, wd: str, ignore_lock: bool = False) -> "DummyClimate":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def set_user_defined_cli(self, filename: str) -> dict[str, str]:
            self.set_cli_calls += 1
            self.latest_cli_filename = filename
            return {"filename": filename}

        def find_closest_stations(self) -> list[dict[str, Any]]:
            self.closest_calls += 1
            return list(self.closest_stations)

        def find_heuristic_stations(self) -> list[dict[str, Any]]:
            return list(self.closest_stations)

        def _resolve_catalog_dataset(self, catalog_id: str, include_hidden: bool = False):
            return self._datasets.get(catalog_id)

    monkeypatch.setattr(climate_module, "Climate", DummyClimate)
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=None),
    )
    monkeypatch.setattr(climate_module, "capability_default", lambda climate, option: None)
    monkeypatch.setattr(
        climate_module, "climate_station_capability_modes", lambda climate, dataset: None
    )
    monkeypatch.setattr(
        climate_module, "climate_spatial_capability_modes", lambda climate, dataset: None
    )

    DummyClimate._instances.clear()

    with app.test_client() as client:
        yield client, DummyClimate, run_dir

    DummyClimate._instances.clear()


def test_set_climatestation_mode_updates_controller(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation_mode/",
        data={"mode": str(int(climate_module.ClimateStationMode.Heuristic))},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climatestation_mode == climate_module.ClimateStationMode.Heuristic


def test_set_climatestation_mode_accepts_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation_mode/",
        json={"mode": int(climate_module.ClimateStationMode.EUHeuristic)},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climatestation_mode == climate_module.ClimateStationMode.EUHeuristic


def test_set_climatestation_accepts_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation/",
        json={"station": "STA-42"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climatestation == "STA-42"


def test_set_climate_mode_updates_catalog_from_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={"mode": int(ClimateMode.Future), "catalog_id": "dataset_b"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climate_mode == ClimateMode.Future
    assert controller.catalog_id == "dataset_b"


def test_stored_authority_accepts_complete_climate_dataset_mode_pair(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    graph = SimpleNamespace(climate_datasets=("dataset_a", "dataset_b"))
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=graph),
    )

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={
            "mode": int(ClimateMode.Future),
            "climate_catalog_id": "dataset_b",
        },
    )

    controller = climate_cls.getInstance(str(run_dir))
    assert response.status_code == 200
    assert controller.climate_mode == ClimateMode.Future
    assert controller.catalog_id == "dataset_b"


def test_schema_v1_europe_preset_drives_flask_discovery_and_setter(
    climate_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.nodb.locales import get_climate_dataset

    client, climate_cls, run_dir = climate_client
    authority = _eu_preset_authority(run_dir)
    assert authority.graph is not None
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda _climate: authority,
    )
    controller = climate_cls.getInstance(str(run_dir))
    controller._datasets.update({
        catalog_id: get_climate_dataset(catalog_id)
        for catalog_id in authority.graph.climate_datasets
    })
    controller.catalog_id = "vanilla_cligen"
    controller.climate_mode = ClimateMode.Vanilla
    controller.catalog_datasets_payload = lambda: [
        get_climate_dataset(catalog_id).to_mapping()
        for catalog_id in authority.graph.climate_datasets
    ]

    discovery = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/climate_catalog")
    user_defined = get_climate_dataset("user_defined_cli")
    accepted = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={
            "mode": int(user_defined.climate_mode),
            "climate_catalog_id": "user_defined_cli",
        },
    )
    prism = get_climate_dataset("prism_stochastic")
    rejected = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={
            "mode": int(prism.climate_mode),
            "climate_catalog_id": "prism_stochastic",
        },
    )

    assert discovery.status_code == 200
    assert [item["catalog_id"] for item in discovery.get_json()] == [
        "vanilla_cligen",
        "eobs_modified",
        "user_defined_cli",
    ]
    assert accepted.status_code == 200
    assert controller.catalog_id == "user_defined_cli"
    assert rejected.status_code == 400
    assert rejected.get_json()["error"]["code"] == "unsupported_capability"
    assert controller.catalog_id == "user_defined_cli"


def test_climate_dataset_mode_pair_rolls_back_on_assignment_fault(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    graph = SimpleNamespace(climate_datasets=("dataset_a", "dataset_b"))
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=graph),
    )
    controller = climate_cls.getInstance(str(run_dir))
    controller.fail_next_catalog_assignment = True

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={"mode": int(ClimateMode.Future), "catalog_id": "dataset_b"},
    )

    assert response.status_code >= 400
    assert controller.climate_mode == ClimateMode.Vanilla
    assert controller.catalog_id == "dataset_a"
    assert controller.committed_pairs == []


def test_climate_dataset_mode_pair_is_serialized_under_one_lock(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    _client, climate_cls, run_dir = climate_client
    graph = SimpleNamespace(climate_datasets=("dataset_a", "dataset_b"))
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=graph),
    )
    controller = climate_cls.getInstance(str(run_dir))
    controller._block_pair_thread = "pair-a"
    failures: list[BaseException] = []

    def apply_pair(catalog_id: str, mode: ClimateMode) -> None:
        try:
            climate_module._apply_climate_selection_pair(
                controller,
                catalog_id=catalog_id,
                mode=int(mode),
            )
        except BaseException as exc:  # Test thread boundary records any failure.
            failures.append(exc)

    first = threading.Thread(
        target=apply_pair,
        args=("dataset_b", ClimateMode.Future),
        name="pair-a",
    )
    second = threading.Thread(
        target=apply_pair,
        args=("dataset_a", ClimateMode.Vanilla),
        name="pair-b",
    )
    first.start()
    assert controller.first_mode_written.wait(timeout=2)
    second.start()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert failures == []
    assert controller.committed_pairs == [
        (ClimateMode.Future, "dataset_b"),
        (ClimateMode.Vanilla, "dataset_a"),
    ]


def test_concurrent_pair_fault_restores_pair_current_at_lock_acquisition(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    _client, climate_cls, run_dir = climate_client
    graph = SimpleNamespace(climate_datasets=("dataset_a", "dataset_b"))
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=graph),
    )
    controller = climate_cls.getInstance(str(run_dir))
    controller._block_pair_thread = "pair-a"
    controller.fail_catalog_thread = "pair-b"
    failures: list[tuple[str, BaseException]] = []

    def apply_pair(catalog_id: str, mode: ClimateMode) -> None:
        try:
            climate_module._apply_climate_selection_pair(
                controller,
                catalog_id=catalog_id,
                mode=int(mode),
            )
        except BaseException as exc:  # Test thread boundary records any failure.
            failures.append((threading.current_thread().name, exc))

    first = threading.Thread(
        target=apply_pair,
        args=("dataset_b", ClimateMode.Future),
        name="pair-a",
    )
    second = threading.Thread(
        target=apply_pair,
        args=("dataset_a", ClimateMode.Vanilla),
        name="pair-b",
    )
    first.start()
    assert controller.first_mode_written.wait(timeout=2)
    second.start()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert [name for name, _exc in failures] == ["pair-b"]
    assert isinstance(failures[0][1], RuntimeError)
    assert controller.committed_pairs == [(ClimateMode.Future, "dataset_b")]
    assert controller.climate_mode == ClimateMode.Future
    assert controller.catalog_id == "dataset_b"


def test_stored_authority_rejects_climate_dataset_without_mode_before_mutation(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    graph = SimpleNamespace(climate_datasets=("dataset_a", "dataset_b"))
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=graph),
    )
    controller = climate_cls.getInstance(str(run_dir))

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={"climate_catalog_id": "dataset_b"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "missing_capability_id"
    assert controller.climate_mode == ClimateMode.Vanilla
    assert controller.catalog_id == "dataset_a"


def test_climate_dataset_alias_disagreement_is_rejected_before_mutation(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    graph = SimpleNamespace(climate_datasets=("dataset_a", "dataset_b"))
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=graph),
    )
    controller = climate_cls.getInstance(str(run_dir))

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={
            "mode": int(ClimateMode.Future),
            "catalog_id": "dataset_a",
            "climate_catalog_id": "dataset_b",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "capability_mismatch"
    assert controller.climate_mode == ClimateMode.Vanilla
    assert controller.catalog_id == "dataset_a"


def test_set_climate_spatialmode_accepts_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_spatialmode/",
        json={"spatialmode": 1},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climate_spatialmode == 1


@pytest.mark.parametrize(
    ("error", "status", "code", "retry_after"),
    (
        (
            climate_module.LocaleAuthorityInvalidError("unknown locale token"),
            409,
            "locale_authority_invalid",
            None,
        ),
        (
            climate_module.CapabilityAuthorityInvalidError("partial schema-v3 graph"),
            409,
            "capability_authority_invalid",
            None,
        ),
        (
            climate_module.BuilderRegistryUnavailableError("registry read failed"),
            503,
            "builder_registry_error",
            "5",
        ),
    ),
)
def test_climate_authority_failures_have_diagnostic_transport(
    climate_client,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
    retry_after: str | None,
) -> None:
    client, _climate_cls, _run_dir = climate_client

    def reject(_climate):
        raise error

    monkeypatch.setattr(climate_module, "resolve_run_capability_authority", reject)
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={"mode": int(ClimateMode.Future), "catalog_id": "dataset_b"},
    )

    assert response.status_code == status
    payload = response.get_json()
    assert payload["error"]["code"] == code
    assert payload["error"]["details"] == str(error)
    assert payload["error_id"]
    assert response.headers.get("Retry-After") == retry_after


@pytest.mark.parametrize(
    ("error", "status", "code", "retry_after"),
    (
        (
            climate_module.LocaleAuthorityInvalidError("unknown locale token"),
            409,
            "locale_authority_invalid",
            None,
        ),
        (
            climate_module.CapabilityAuthorityInvalidError("partial schema-v3 graph"),
            409,
            "capability_authority_invalid",
            None,
        ),
        (
            climate_module.BuilderRegistryUnavailableError("registry read failed"),
            503,
            "builder_registry_error",
            "5",
        ),
    ),
)
def test_climate_catalog_discovery_authority_failures_are_diagnostic(
    climate_client,
    error: Exception,
    status: int,
    code: str,
    retry_after: str | None,
) -> None:
    client, climate_cls, run_dir = climate_client
    climate = climate_cls.getInstance(str(run_dir))

    def reject():
        raise error

    climate.catalog_datasets_payload = reject
    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/query/climate_catalog"
    )

    assert response.status_code == status
    payload = response.get_json()
    assert payload["error"]["code"] == code
    assert payload["error"]["details"] == str(error)
    assert payload["error_id"]
    assert response.headers.get("Retry-After") == retry_after


def test_climate_catalog_denies_before_controller_or_registry_access(
    climate_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from flask import abort
    from werkzeug.exceptions import Forbidden
    import wepppy.weppcloud.utils.helpers as helper_module

    client, climate_cls, _run_dir = climate_client
    touched: list[str] = []
    monkeypatch.setattr(
        helper_module,
        "authorize",
        lambda *_args, **_kwargs: abort(403),
    )
    monkeypatch.setattr(
        climate_cls,
        "getInstance",
        staticmethod(lambda *_args, **_kwargs: touched.append("controller")),
    )
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda *_args, **_kwargs: touched.append("registry"),
    )
    with pytest.raises(Forbidden):
        client.get(f"/runs/{RUN_ID}/{CONFIG}/query/climate_catalog")

    assert touched == []


def test_climate_catalog_classifies_live_graph_failure_as_registry_503(
    climate_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wepppy.nodb.config_builder.resolver as builder_resolver_module
    import wepppy.nodb.project_config_capabilities as capability_module
    from wepppy.nodb.locales.capability_graph import CapabilityGraphError

    client, climate_cls, run_dir = climate_client

    class LegacyConfig:
        def config_get_bool(self, _section, _option, default=False):
            return default

        def config_get_raw(self, section, option, default=None):
            if (section, option) == ("general", "locales"):
                return '["us"]'
            return default

        def config_get_list(self, section, option, default=None):
            if (section, option) == ("general", "locales"):
                return ["us"]
            return default

    monkeypatch.setattr(
        builder_resolver_module,
        "build_locale_capability_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CapabilityGraphError("live provider graph failed validation")
        ),
    )
    climate = climate_cls.getInstance(str(run_dir))
    climate.catalog_datasets_payload = lambda: (
        capability_module.resolve_run_capability_authority(LegacyConfig())
    )

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/query/climate_catalog"
    )

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "builder_registry_error"
    assert "live provider graph failed validation" in response.get_json()["error"]["details"]
    assert response.get_json()["error_id"]
    assert response.headers["Retry-After"] == "5"


def test_climate_catalog_includes_exact_outside_axis_current_as_disabled(
    climate_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, climate_cls, run_dir = climate_client
    climate = climate_cls.getInstance(str(run_dir))
    climate.catalog_id = "observed_daymet"
    climate.climatestation_mode = climate_module.ClimateStationMode.Closest
    climate.climate_spatialmode = 2
    climate.catalog_datasets_payload = lambda: [{"catalog_id": "vanilla_cligen"}]
    monkeypatch.setattr(
        climate_module,
        "get_climate_dataset",
        lambda catalog_id: SimpleNamespace(
            to_mapping=lambda: {"catalog_id": catalog_id, "label": "DAYMET"}
        ),
    )

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/climate_catalog")

    assert response.status_code == 200
    current = response.get_json()[-1]
    assert current["catalog_id"] == "observed_daymet"
    assert current["current_selection_disabled"] is True
    assert current["station_modes"] == [
        int(climate_module.ClimateStationMode.Closest)
    ]
    assert current["spatial_modes"] == [2]
    assert current["current_station_mode_authorized"] is False
    assert current["disabled_station_modes"] == [
        int(climate_module.ClimateStationMode.Closest)
    ]


def test_climate_catalog_marks_relationship_invalid_current_methods_disabled(
    climate_client,
) -> None:
    client, climate_cls, run_dir = climate_client
    climate = climate_cls.getInstance(str(run_dir))
    climate.catalog_id = "vanilla_cligen"
    climate.climatestation_mode = climate_module.ClimateStationMode.MesonetIA
    climate.climate_spatialmode = 2
    climate.catalog_datasets_payload = lambda: [{
        "catalog_id": "vanilla_cligen",
        "station_modes": [-1, 0],
        "spatial_modes": [0, 1],
    }]

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/climate_catalog")

    assert response.status_code == 200
    current = response.get_json()[0]
    assert current["station_modes"] == [-1, 0, 5]
    assert current["current_station_mode"] == int(
        climate_module.ClimateStationMode.MesonetIA
    )
    assert current["current_station_mode_authorized"] is False
    assert current["disabled_station_modes"] == [
        int(climate_module.ClimateStationMode.MesonetIA)
    ]
    assert current["current_spatial_mode_authorized"] is False
    assert current["disabled_spatial_modes"] == [2]
    assert current["spatial_modes"] == [0, 1, 2]


@pytest.mark.parametrize(
    ("path", "field", "unsupported", "allowed", "attribute", "capability_name"),
    (
        (
            "set_climatestation_mode",
            "mode",
            int(climate_module.ClimateStationMode.EUHeuristic),
            int(climate_module.ClimateStationMode.Closest),
            "climatestation_mode",
            "climate_station_capability_modes",
        ),
        (
            "set_climate_spatialmode",
            "spatialmode",
            2,
            0,
            "climate_spatialmode",
            "climate_spatial_capability_modes",
        ),
    ),
)
def test_legacy_live_graph_default_dataset_constrains_climate_methods(
    climate_client,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    field: str,
    unsupported: int,
    allowed: int,
    attribute: str,
    capability_name: str,
) -> None:
    client, climate_cls, run_dir = climate_client
    graph = SimpleNamespace(defaults={"climate_dataset": "vanilla_cligen"})
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=graph),
    )
    seen: list[str] = []
    monkeypatch.setattr(
        climate_module,
        capability_name,
        lambda climate, dataset: seen.append(dataset) or frozenset({allowed}),
    )
    climate = climate_cls.getInstance(str(run_dir))
    climate.catalog_id = None
    before = getattr(climate, attribute)

    rejected = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/{path}/", json={field: unsupported}
    )

    assert rejected.status_code == 400
    assert getattr(climate, attribute) == before
    assert seen == ["vanilla_cligen"]

    accepted = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/{path}/", json={field: allowed}
    )

    assert accepted.status_code == 200
    assert int(getattr(climate, attribute)) == allowed
    assert seen == ["vanilla_cligen", "vanilla_cligen"]


def test_station_method_outside_stored_graph_is_rejected_before_mutation(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    monkeypatch.setattr(
        climate_module,
        "climate_station_capability_modes",
        lambda climate, dataset: frozenset({int(climate_module.ClimateStationMode.Closest)}),
    )
    controller = climate_cls.getInstance(str(run_dir))
    before = controller.climatestation_mode

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation_mode/",
        json={"mode": int(climate_module.ClimateStationMode.EUHeuristic)},
    )

    assert response.status_code >= 400
    assert controller.climatestation_mode == before


def test_exact_current_station_method_outside_stored_graph_remains_usable(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    monkeypatch.setattr(
        climate_module,
        "climate_station_capability_modes",
        lambda climate, dataset: frozenset(
            {int(climate_module.ClimateStationMode.Closest)}
        ),
    )
    controller = climate_cls.getInstance(str(run_dir))
    controller.climatestation_mode = climate_module.ClimateStationMode.EUHeuristic

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation_mode/",
        json={"mode": int(climate_module.ClimateStationMode.EUHeuristic)},
    )

    assert response.status_code == 200
    assert controller.climatestation_mode == climate_module.ClimateStationMode.EUHeuristic


def test_spatial_method_outside_stored_graph_is_rejected_before_mutation(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    monkeypatch.setattr(
        climate_module,
        "climate_spatial_capability_modes",
        lambda climate, dataset: frozenset({0}),
    )
    controller = climate_cls.getInstance(str(run_dir))
    controller.climate_spatialmode = 0

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_spatialmode/",
        json={"spatialmode": 1},
    )

    assert response.status_code >= 400
    assert controller.climate_spatialmode == 0


def test_exact_current_spatial_method_outside_stored_graph_remains_usable(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    monkeypatch.setattr(
        climate_module,
        "climate_spatial_capability_modes",
        lambda climate, dataset: frozenset({0}),
    )
    controller = climate_cls.getInstance(str(run_dir))
    controller.climate_spatialmode = 2

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_spatialmode/",
        json={"spatialmode": 2},
    )

    assert response.status_code == 200
    assert controller.climate_spatialmode == 2


def test_schema_v2_climate_selection_requires_stable_catalog_id_before_mutation(
    climate_client, monkeypatch: pytest.MonkeyPatch,
):
    client, climate_cls, run_dir = climate_client
    monkeypatch.setattr(
        climate_module,
        "resolve_run_capability_authority",
        lambda climate: SimpleNamespace(graph=SimpleNamespace(schema_version=2)),
    )
    controller = climate_cls.getInstance(str(run_dir))
    before = controller.climate_mode

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={"mode": int(ClimateMode.Future)},
    )

    assert response.status_code >= 400
    assert controller.climate_mode == before


def test_view_closest_stations_generates_options(climate_client):
    client, climate_cls, run_dir = climate_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/view/closest_stations/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'value="STA-1"' in html
    assert "Station One" in html

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.closest_calls == 1


def test_task_set_use_gridmet_wind_when_applicable_updates_flag(climate_client):
    client, climate_cls, run_dir = climate_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_use_gridmet_wind_when_applicable/",
        json={"state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.use_gridmet_wind_when_applicable is True


def test_task_set_adjust_mx_pt5_updates_flag(climate_client):
    client, climate_cls, run_dir = climate_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_adjust_mx_pt5/",
        json={"state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.adjust_mx_pt5 is True


def test_task_set_silent_pass_observed_quality_guard_updates_flag(climate_client):
    client, climate_cls, run_dir = climate_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_silent_pass_observed_quality_guard/",
        json={"state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.silent_pass_observed_quality_guard is True
