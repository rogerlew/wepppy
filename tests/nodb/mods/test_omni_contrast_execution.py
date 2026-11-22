"""Omni contrast preparation, freshness and execution tests."""

import json
import logging
import types
from pathlib import Path

import pytest

from tests.nodb.mods._omni_test_support import _noop_lock, omni_module as omni_module


pytestmark = pytest.mark.unit


def test_apply_contrast_output_triggers_creates_missing_diagnostics(tmp_path, omni_module):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    created = {"chan": 0}

    class DummyWepp:
        def __init__(self, runs_dir):
            self.runs_dir = str(runs_dir)
            self.logger = logging.getLogger("tests.omni.output_triggers")

        def _prep_channel_input(self):
            created["chan"] += 1
            (Path(self.runs_dir) / "chan.inp").write_text("chan", encoding="ascii")

    wepp = DummyWepp(runs_dir)

    omni_module._apply_contrast_output_triggers(
        wepp,
        {"chan_out": True, "tcr_out": True},
    )

    assert (runs_dir / "chan.inp").exists()
    assert (runs_dir / "tc.txt").exists()
    assert created["chan"] == 1


def test_apply_contrast_output_triggers_prepares_chan_input_for_ebe_only(tmp_path, omni_module):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    class DummyWepp:
        def __init__(self, runs_dir):
            self.runs_dir = str(runs_dir)

        def _prep_channel_input(self):
            (Path(self.runs_dir) / "chan.inp").write_text("outlet-channel", encoding="ascii")

    omni_module._apply_contrast_output_triggers(
        DummyWepp(runs_dir),
        {"chan_out": False, "ebe_pw0": True, "tcr_out": False},
    )

    assert (runs_dir / "chan.inp").read_text(encoding="ascii") == "outlet-channel"


def test_apply_contrast_output_triggers_propagates_required_sidecar_failure(
    tmp_path,
    omni_module,
):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    class DummyWepp:
        def __init__(self, runs_dir):
            self.runs_dir = str(runs_dir)

        def _prep_channel_input(self):
            raise OSError("cannot prepare channel selection")

    with pytest.raises(OSError, match="cannot prepare channel selection"):
        omni_module._apply_contrast_output_triggers(
            DummyWepp(runs_dir),
            {"chan_out": False, "ebe_pw0": True, "tcr_out": False},
        )


def test_apply_contrast_output_triggers_preserves_inherited_sidecars(tmp_path, omni_module):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "chan.inp").write_text("base-channel-sidecar", encoding="ascii")
    (runs_dir / "tc.txt").write_text("base-tc-sidecar", encoding="ascii")

    class DummyWepp:
        def __init__(self, runs_dir):
            self.runs_dir = str(runs_dir)

        def _prep_channel_input(self):
            raise AssertionError("existing base chan.inp should not be regenerated")

    wepp = DummyWepp(runs_dir)

    omni_module._apply_contrast_output_triggers(
        wepp,
        {"chan_out": False, "tcr_out": False},
    )

    assert (runs_dir / "chan.inp").read_text(encoding="ascii") == "base-channel-sidecar"
    assert (runs_dir / "tc.txt").read_text(encoding="ascii") == "base-tc-sidecar"


@pytest.mark.parametrize(
    ("delete_after_interchange", "expected_cleanup_calls"),
    [(True, 1), (False, 0)],
)
def test_post_watershed_run_cleanup_defers_hillslope_cleanup_until_after_success(
    tmp_path,
    monkeypatch,
    omni_module,
    delete_after_interchange,
    expected_cleanup_calls,
):
    runs_dir = tmp_path / "runs"
    output_dir = tmp_path / "output"
    runs_dir.mkdir()
    output_dir.mkdir()
    (runs_dir / "pw0.out").write_text("watershed", encoding="ascii")
    (runs_dir / "tc_out.txt").write_text("tc", encoding="ascii")

    cleanup_calls = []
    tc_calls = []

    monkeypatch.setattr(
        omni_module.Climate,
        "getInstance",
        lambda _wd: types.SimpleNamespace(climate_mode=omni_module.ClimateMode.Observed),
    )
    monkeypatch.setattr(
        omni_module,
        "cleanup_hillslope_sources_for_completed_interchange",
        lambda output_dir: cleanup_calls.append(Path(output_dir)),
    )
    monkeypatch.setattr(
        omni_module,
        "run_wepp_watershed_tc_out_interchange",
        lambda output_dir, *, delete_after_interchange: tc_calls.append(
            (Path(output_dir), delete_after_interchange)
        ),
    )

    wepp = types.SimpleNamespace(
        wd=str(tmp_path),
        runs_dir=str(runs_dir),
        output_dir=str(output_dir),
        delete_after_interchange=delete_after_interchange,
        logger=logging.getLogger("tests.omni.post_watershed_cleanup"),
    )

    omni_module._post_watershed_run_cleanup(wepp)

    assert not (runs_dir / "pw0.out").exists()
    assert not (runs_dir / "tc_out.txt").exists()
    assert (output_dir / "pw0.out").exists()
    assert (output_dir / "tc_out.txt").exists()
    assert tc_calls == [(output_dir, delete_after_interchange)]
    assert cleanup_calls == [output_dir] * expected_cleanup_calls


def test_run_omni_contrasts_delegates_to_run_orchestration_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_run(instance):
        captured["instance"] = instance

    monkeypatch.setattr(omni_module._OMNI_RUN_ORCHESTRATION_SERVICE, "run_omni_contrasts", _fake_run)

    omni.run_omni_contrasts()

    assert captured["instance"] is omni


def test_run_omni_contrast_delegates_to_run_orchestration_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_run(instance, contrast_id, *, rq_job_id=None):
        captured["instance"] = instance
        captured["contrast_id"] = contrast_id
        captured["rq_job_id"] = rq_job_id
        return str(tmp_path / "_pups" / "omni" / "contrasts" / str(contrast_id))

    monkeypatch.setattr(omni_module._OMNI_RUN_ORCHESTRATION_SERVICE, "run_omni_contrast", _fake_run)

    result = omni.run_omni_contrast(3, rq_job_id="job-123")

    assert captured == {"instance": omni, "contrast_id": 3, "rq_job_id": "job-123"}
    assert result.endswith("/_pups/omni/contrasts/3")


def test_run_omni_contrasts_skips_up_to_date(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts")
    omni.locked = _noop_lock
    omni._contrast_names = ["None,10__to__undisturbed"]
    omni._contrast_dependency_tree = {}

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H10\n", encoding="ascii")

    readme_path = tmp_path / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "output" / "interchange" / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("ok", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    snapshot = {"timestamps:run_wepp_watershed": 123}
    redisprep_path.write_text(json.dumps(snapshot), encoding="ascii")

    omni._contrast_dependency_tree = {
        "None,10__to__undisturbed": {
            "dependencies": {},
            "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar_path)),
            "control_redisprep": snapshot,
            "contrast_redisprep": snapshot,
            "last_run": 1.0,
        }
    }

    calls = []

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key, **_kwargs):
        calls.append((contrast_id, contrast_name))
        return f"{wd}/_pups/omni/contrasts/{contrast_id}"

    monkeypatch.setattr(omni_module, "_run_contrast", fake_run)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert calls == []


def test_run_omni_contrasts_runs_when_readme_missing(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts_missing_readme")
    omni.locked = _noop_lock
    contrast_name = "uniform_low,10__to__mulch"
    omni._contrast_names = [contrast_name]
    omni._contrast_dependency_tree = {}

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H10\n", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    snapshot = {"timestamps:run_wepp_watershed": 456}
    redisprep_path.write_text(json.dumps(snapshot), encoding="ascii")

    calls = []

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key, **_kwargs):
        calls.append((contrast_id, contrast_name))
        contrast_dir = Path(wd) / "_pups" / "omni" / "contrasts" / contrast_id
        (contrast_dir / "wepp" / "output" / "interchange").mkdir(parents=True, exist_ok=True)
        return str(contrast_dir)

    monkeypatch.setattr(omni_module, "_run_contrast", fake_run)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert calls
    assert calls[0][0] == "1"
    assert contrast_name in omni.contrast_dependency_tree


def test_run_omni_contrasts_runs_when_sidecar_changes(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts_sidecar")
    omni.locked = _noop_lock
    omni._contrast_names = ["uniform_low,10__to__mulch"]

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H10\n", encoding="ascii")

    readme_path = tmp_path / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "output" / "interchange" / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("ok", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    snapshot = {"timestamps:run_wepp_watershed": 789}
    redisprep_path.write_text(json.dumps(snapshot), encoding="ascii")

    omni._contrast_dependency_tree = {
        "None,10__to__undisturbed": {
            "dependencies": {},
            "sidecar_sha1": "stale",
            "control_redisprep": snapshot,
            "contrast_redisprep": snapshot,
            "last_run": 1.0,
        }
    }

    calls = []

    def fake_run(contrast_id, contrast_name, contrasts, wd, runid, control_key, contrast_key, **_kwargs):
        calls.append((contrast_id, contrast_name))
        contrast_dir = Path(wd) / "_pups" / "omni" / "contrasts" / contrast_id
        (contrast_dir / "wepp" / "output" / "interchange").mkdir(parents=True, exist_ok=True)
        return str(contrast_dir)

    monkeypatch.setattr(omni_module, "_run_contrast", fake_run)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert calls
    assert calls[0][0] == "1"


def test_contrast_run_status_needs_run_when_redisprep_missing_watershed_timestamp(
    tmp_path, monkeypatch, omni_module
):
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False))
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.redisprep_missing")

    contrast_name = "None,10__to__undisturbed"
    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H1\n", encoding="ascii")
    readme_path = Path(omni._contrast_run_readme_path(1))
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("done", encoding="ascii")

    redisprep_path = tmp_path / "redisprep.dump"
    redisprep_path.write_text(
        json.dumps({"timestamps:run_wepp_hillslopes": 123}),
        encoding="utf-8",
    )

    omni._contrast_dependency_tree = {
        contrast_name: {
            "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar_path)),
            "control_redisprep": {"timestamps:run_wepp_watershed": 123},
            "contrast_redisprep": {"timestamps:run_wepp_watershed": 123},
        }
    }

    assert omni._contrast_run_status(1, contrast_name) == "needs_run"


def test_contrast_run_status_needs_run_when_order_reduction_passes_change(
    tmp_path,
    monkeypatch,
    omni_module,
):
    monkeypatch.setattr(omni_module.NoDbBase, "has_sbs", property(lambda self: False))
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.order_reduction_status")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_order_reduction_passes = 2

    contrast_name = "None,10__to__undisturbed"
    sidecar_path = Path(omni._contrast_sidecar_path(1))
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text("10\t/tmp/H1\n", encoding="ascii")
    readme_path = Path(omni._contrast_run_readme_path(1))
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("done", encoding="ascii")

    snapshot = {"timestamps:run_wepp_watershed": 123}
    (tmp_path / "redisprep.dump").write_text(json.dumps(snapshot), encoding="utf-8")

    omni._contrast_dependency_tree = {
        contrast_name: {
            "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar_path)),
            "control_redisprep": snapshot,
            "contrast_redisprep": snapshot,
            "order_reduction_passes": 1,
        }
    }

    assert omni._contrast_run_status(1, contrast_name) == "needs_run"


def test_run_omni_contrasts_cleans_stale_runs(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.run_contrasts_stale")
    omni.locked = _noop_lock
    omni._contrast_names = ["None,10__to__undisturbed"]
    omni._contrast_dependency_tree = {}

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    contrasts_root = tmp_path / "_pups" / "omni" / "contrasts"
    (contrasts_root / "1").mkdir(parents=True, exist_ok=True)
    (contrasts_root / "2").mkdir(parents=True, exist_ok=True)
    (contrasts_root / "_uploads").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(omni, "_contrast_run_status", lambda contrast_id, name: "up_to_date")
    monkeypatch.setattr(omni_module, "_run_contrast", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni, "_post_omni_run", lambda wd, name: None)

    omni.run_omni_contrasts()

    assert (contrasts_root / "1").exists()
    assert not (contrasts_root / "2").exists()
    assert (contrasts_root / "_uploads").exists()


def test_run_contrast_skips_archives_and_inherits_parent_wepp_bin(
    tmp_path: Path,
    omni_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)
    (wd / "wepp" / "runs" / "H1.run").write_text("run", encoding="ascii")
    for sidecar in ("chan.inp", "tc.txt", "snow.txt", "wepp_ui.txt"):
        (wd / "wepp" / "runs" / sidecar).write_text(sidecar, encoding="ascii")
    (wd / "wepp" / "runs" / "pw0.run").write_text("parent run", encoding="ascii")
    (wd / "wepp" / "runs" / "pw0.err").write_text("parent log", encoding="ascii")

    (wd / "landuse.nodir").write_text("landuse", encoding="ascii")
    (wd / "soils.nodir").write_text("soils", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", lambda *_args, **_kwargs: "/tmp/mock.parquet")
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)

    def _resolve(wd_path: str, rel: str, view: str = "effective"):
        if wd_path == str(wd) and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(form="archive")
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.baseflow_opts = object()
            self.wepp_interchange_dir = str(Path(run_wd) / "wepp" / "output" / "interchange")
            self.wepp_bin = None
            self.pass_family = "legacy_ascii"

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, **kwargs):
            return None

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    wepp_instances: dict[str, DummyWepp] = {}

    def _get_wepp_instance(run_wd: str) -> DummyWepp:
        instance = wepp_instances.setdefault(run_wd, DummyWepp(run_wd))
        if Path(run_wd) == wd:
            instance.wepp_bin = "wepp_260803"
        return instance

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", _get_wepp_instance)

    new_wd = Path(
        omni_module._run_contrast(
            contrast_id="1",
            contrast_name="demo",
            contrasts={10: str(wd / "wepp" / "output" / "H1")},
            wd=str(wd),
            runid="run-123",
            control_scenario_key="undisturbed",
            contrast_scenario_key="undisturbed",
        )
    )

    assert (new_wd / "landuse").is_dir()
    assert list((new_wd / "landuse").iterdir()) == []
    assert (new_wd / "soils").is_dir()
    assert list((new_wd / "soils").iterdir()) == []
    assert wepp_instances[str(new_wd)].wepp_bin == "wepp_260803"
    for sidecar in ("chan.inp", "tc.txt", "snow.txt", "wepp_ui.txt"):
        inherited = new_wd / "wepp" / "runs" / sidecar
        assert inherited.is_symlink()
        assert inherited.read_text(encoding="ascii") == sidecar
    assert not (new_wd / "wepp" / "runs" / "pw0.run").exists()
    assert not (new_wd / "wepp" / "runs" / "pw0.err").exists()


def test_run_contrast_copies_directory_landuse_and_soils(tmp_path: Path, omni_module, monkeypatch):
    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)
    (wd / "wepp" / "runs" / "H1.run").write_text("run", encoding="ascii")
    disturbed_src = wd / "disturbed"
    disturbed_src.mkdir()
    disturbed_source = disturbed_src / "source.tif"
    disturbed_source.write_text("source", encoding="ascii")
    (wd / "disturbed.nodb").write_text(
        json.dumps(
            {
                "py/state": {
                    "wd": str(wd),
                    "_disturbed_fn": str(disturbed_source),
                }
            }
        ),
        encoding="ascii",
    )

    landuse_src = wd / "landuse"
    soils_src = wd / "soils"
    landuse_src.mkdir()
    soils_src.mkdir()
    (landuse_src / "landuse.txt").write_text("landuse", encoding="ascii")
    (soils_src / "soils.txt").write_text("soils", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", lambda *_args, **_kwargs: "/tmp/mock.parquet")
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)

    def _resolve(wd_path: str, rel: str, view: str = "effective"):
        if wd_path == str(wd) and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(
                form="dir",
                dir_path=str(wd),
                inner_path=rel,
            )
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.baseflow_opts = object()
            self.wepp_interchange_dir = str(Path(run_wd) / "wepp" / "output" / "interchange")
            self.wepp_bin = None
            self.pass_family = "legacy_ascii"

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, **kwargs):
            return None

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda run_wd: DummyWepp(run_wd))

    new_wd = Path(
        omni_module._run_contrast(
            contrast_id="1",
            contrast_name="demo",
            contrasts={10: str(wd / "wepp" / "output" / "H1")},
            wd=str(wd),
            runid="run-123",
            control_scenario_key="undisturbed",
            contrast_scenario_key="undisturbed",
        )
    )

    assert (new_wd / "landuse" / "landuse.txt").read_text(encoding="ascii") == "landuse"
    assert (new_wd / "soils" / "soils.txt").read_text(encoding="ascii") == "soils"
    assert not (new_wd / "disturbed").exists()
    state = json.loads((new_wd / "disturbed.nodb").read_text(encoding="ascii"))
    assert state["py/state"]["wd"] == str(new_wd)
    assert state["py/state"]["_parent_wd"] == str(wd)
    assert state["py/state"]["_disturbed_fn"] == str(disturbed_source)


def test_run_contrast_rewrites_legacy_omni_prefix_when_pass_dat_exists(
    tmp_path: Path,
    omni_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "nodir_resolve", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "_resolve_contrast_scenario_wd", lambda wd, *_args, **_kwargs: wd)
    monkeypatch.setattr(omni_module, "_contrast_topaz_ids_from_mapping", lambda mapping, _wd: list(mapping.keys()))

    landuse_parquet = tmp_path / "landuse.parquet"
    soils_parquet = tmp_path / "soils.parquet"
    landuse_parquet.write_text("landuse", encoding="ascii")
    soils_parquet.write_text("soils", encoding="ascii")

    def _pick_parquet(_wd: str, rel: str):
        if rel.startswith("landuse/"):
            return landuse_parquet
        if rel.startswith("soils/"):
            return soils_parquet
        raise AssertionError(rel)

    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", _pick_parquet)
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **_kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *_args, **_kwargs: None)

    old_path = str(wd / "omni" / "scenarios" / "uniform_low" / "wepp" / "output" / "H1")
    candidate = str(wd / "_pups" / "omni" / "scenarios" / "uniform_low" / "wepp" / "output" / "H1")
    Path(candidate).parent.mkdir(parents=True, exist_ok=True)
    Path(f"{candidate}.pass.dat").write_text("pass", encoding="ascii")

    captured: dict[str, object] = {}

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.wepp_bin = None
            self.pass_family = "legacy_ascii"

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, *, wepp_id_paths, output_options):
            captured["wepp_id_paths"] = list(wepp_id_paths)
            captured["output_options"] = dict(output_options)

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda run_wd: DummyWepp(run_wd))

    omni_module._run_contrast(
        contrast_id="1",
        contrast_name="demo",
        contrasts={10: old_path},
        wd=str(wd),
        runid="run-123",
        control_scenario_key="uniform_low",
        contrast_scenario_key="uniform_low",
        output_options={},
    )

    assert captured["wepp_id_paths"] == [candidate]


def test_run_contrast_skips_projection_lock_retry_in_directory_only_mode(
    tmp_path: Path,
    omni_module,
    monkeypatch,
):
    wd = tmp_path / "run"
    (wd / "climate").mkdir(parents=True)
    (wd / "watershed").mkdir(parents=True)
    (wd / "wepp" / "runs").mkdir(parents=True)
    (wd / "wepp" / "output").mkdir(parents=True)
    (wd / "wepp" / "runs" / "H1.run").write_text("run", encoding="ascii")

    (wd / "landuse.nodir").write_text("landuse", encoding="ascii")
    (wd / "soils.nodir").write_text("soils", encoding="ascii")

    monkeypatch.setattr(omni_module, "copy_version_for_clone", lambda src, dst: None)
    monkeypatch.setattr(omni_module, "_clear_nodb_cache_and_locks", lambda runid, pup_relpath=None: None)
    monkeypatch.setattr(omni_module, "_resolve_base_scenario_key", lambda wd: "undisturbed")
    monkeypatch.setattr(omni_module, "pick_existing_parquet_path", lambda *_args, **_kwargs: "/tmp/mock.parquet")
    monkeypatch.setattr(omni_module, "_merge_contrast_parquet", lambda **kwargs: None)
    monkeypatch.setattr(omni_module, "_apply_contrast_output_triggers", lambda *args, **kwargs: None)
    monkeypatch.setattr(omni_module, "_post_watershed_run_cleanup", lambda *args, **kwargs: None)

    def _resolve(wd_path: str, rel: str, view: str = "effective"):
        if wd_path == str(wd) and rel in {"landuse", "soils"}:
            return types.SimpleNamespace(form="archive")
        return None

    monkeypatch.setattr(omni_module, "nodir_resolve", _resolve)

    class DummyWepp:
        def __init__(self, run_wd: str):
            self.runs_dir = str(Path(run_wd) / "wepp" / "runs")
            self.output_dir = str(Path(run_wd) / "wepp" / "output")
            self.baseflow_opts = object()
            self.wepp_interchange_dir = str(Path(run_wd) / "wepp" / "output" / "interchange")
            self.wepp_bin = None
            self.pass_family = "legacy_ascii"

        def clean(self):
            Path(self.runs_dir).mkdir(parents=True, exist_ok=True)
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        def make_watershed_run(self, **kwargs):
            return None

        def run_watershed(self):
            return None

        def report_loss(self):
            return None

    import wepppy.nodb.core as nodb_core

    monkeypatch.setattr(nodb_core.Wepp, "getInstance", lambda run_wd: DummyWepp(run_wd))

    new_wd = Path(
        omni_module._run_contrast(
            contrast_id="1",
            contrast_name="demo",
            contrasts={10: str(wd / "wepp" / "output" / "H1")},
            wd=str(wd),
            runid="run-123",
            control_scenario_key="undisturbed",
            contrast_scenario_key="undisturbed",
        )
    )

    assert (new_wd / "landuse").is_dir()
    assert list((new_wd / "landuse").iterdir()) == []
    assert (new_wd / "soils").is_dir()
    assert list((new_wd / "soils").iterdir()) == []
