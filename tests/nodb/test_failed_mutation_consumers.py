"""Real controller and executable-input checks for failed NoDb mutations."""
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.base as base
import wepppy.nodb.core.wepp as wepp_module
from tests.nodb.test_base_boundary_characterization import _RedisStub
from wepppy.nodb.core import Ron, Soils, Watershed, Wepp
from wepppy.nodb.core.wepp import BaseflowOpts, PhosphorusOpts, prep_soil
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.integration


@pytest.fixture
def controllers(tmp_path, monkeypatch):
    # Only distributed coordination is doubled; all NoDb encoding, reads, writes,
    # signature validation and controller recovery execute their real paths.
    monkeypatch.setattr(base, "redis_lock_client", _RedisStub())
    monkeypatch.setattr(base, "redis_nodb_cache_client", None)
    monkeypatch.setattr(Wepp, "clean", lambda self: None)
    wd = str(tmp_path)
    config = "canada-wbt-mofe.cfg"
    Ron(wd, config, initialize_components=False)
    Watershed(wd, config)
    Soils(wd, config)
    Wepp(wd, config)
    wepp, soils = Wepp.getInstance(wd), Soils.getInstance(wd)
    with wepp.locked():
        wepp._kslast = 0.02
    with soils.locked():
        soils._initial_sat = 0.2
    try:
        yield wepp, soils
    finally:
        for cls in (Wepp, Soils, Watershed, Ron):
            cls.cleanup_run_instances(wd)


def _prepared_soil(wepp, soils):
    source = Path(__file__).resolve().parents[1] / "omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs/p118.sol"
    destination = Path(wepp.wd) / "wepp/runs/p101.sol"
    destination.parent.mkdir(parents=True, exist_ok=True)
    prep_soil(("101", str(source), str(destination), wepp.kslast, None,
               soils.initial_sat, soils.clip_soils, soils.clip_soils_depth,
               soils.clip_soils_minimum, soils.clip_soils_minimum_depth, False))
    return WeppSoilUtil(str(destination), preserve_input_format=True)


@pytest.mark.parametrize("boundary", ["parser", "decorator"])
def test_valid_wepp_replace_failure_cannot_reach_prepared_soil(controllers, monkeypatch, boundary):
    wepp, soils = controllers
    held = Wepp.getInstance(wepp.wd)
    accepted_gwstorage = wepp.baseflow_opts.gwstorage
    original = Path(wepp.wd, Wepp.filename).read_bytes()
    real_replace = base.os.replace

    def fail_wepp_replace(source, target):
        if str(target) == str(Path(wepp.wd, Wepp.filename)):
            raise OSError("injected precommit replace failure")
        return real_replace(source, target)

    with monkeypatch.context() as fault:
        fault.setattr(base.os, "replace", fail_wepp_replace)
        with pytest.raises(OSError, match="precommit replace"):
            if boundary == "parser":
                wepp.parse_inputs({"kslast": 0.9, "baseflow_opts_gwstorage": 15.0})
            else:
                wepp.kslast = 0.9
    assert held is wepp
    assert Path(wepp.wd, Wepp.filename).read_bytes() == original
    assert wepp.kslast == 0.02
    assert wepp.baseflow_opts.gwstorage == accepted_gwstorage
    assert Wepp.getInstance(wepp.wd) is wepp
    wepp.parse_inputs({"delete_after_interchange": True})
    assert Wepp.load_detached(wepp.wd).kslast == 0.02
    prepared = _prepared_soil(wepp, soils)
    assert prepared.obj["res_lyr"]["kslast"] == pytest.approx(0.02)
    assert prepared.obj["ofes"][0]["res_lyr"]["kslast"] == pytest.approx(0.02)


def test_soils_domain_failure_cannot_reach_prepared_saturation(controllers):
    wepp, soils = controllers
    original = Path(soils.wd, Soils.filename).read_bytes()
    with pytest.raises(FileNotFoundError, match="not found"):
        soils._build_gridded(initial_sat=0.9, retrieve_gridded_ssurgo=False)
    assert Path(soils.wd, Soils.filename).read_bytes() == original
    assert soils.initial_sat == 0.2
    assert Soils.getInstance(soils.wd) is soils
    with soils.locked():
        soils._clear_ssurgo_cache_on_rebuild = True
    assert Soils.load_detached(soils.wd).initial_sat == 0.2
    prepared = _prepared_soil(wepp, soils)
    assert all(ofe["sat"] == pytest.approx(0.2) for ofe in prepared.obj["ofes"])


@pytest.mark.parametrize("kind", ["phosphorus", "baseflow"])
def test_option_map_failure_preserves_live_alias_and_executable_input(controllers, monkeypatch, kind):
    wepp, _soils = controllers
    with wepp.locked():
        wepp.phosphorus_opts = PhosphorusOpts(1.0, 2.0, 3.0, 4.0)
        wepp.baseflow_opts = BaseflowOpts(200.0, 0.04, 0.0, 1.0)
        wepp.p_surf_runoff_map = "first.tif"
        wepp.p_lateral_flow_map = "broken.tif"
        wepp.baseflow_gwstorage_map = "first.tif"
        wepp.baseflow_bfcoeff_map = "broken.tif"
    alias = getattr(wepp, f"{kind}_opts")
    baseline = alias.contents
    original = Path(wepp.wd, Wepp.filename).read_bytes()
    monkeypatch.setattr(Wepp, "watershed_instance", property(lambda self:
        SimpleNamespace(outlet=SimpleNamespace(actual_loc=(-116.0, 46.0)))))
    monkeypatch.setattr(Wepp, "climate_instance", property(lambda self:
        SimpleNamespace(is_single_storm=False)))

    class Raster:
        def __init__(self, path):
            self.path = path

        def get_location_info(self, *_args, **_kwargs):
            if self.path == "broken.tif":
                raise OSError("later raster read failed")
            return 9.0

    monkeypatch.setattr(wepp_module, "RasterDatasetInterpolator", Raster)
    with pytest.raises(OSError, match="later raster"):
        getattr(wepp, f"_check_and_set_{kind}_map")()
    assert alias.contents == baseline
    assert getattr(wepp, f"{kind}_opts").contents == baseline
    assert Path(wepp.wd, Wepp.filename).read_bytes() == original
    wepp.parse_inputs({"delete_after_interchange": True})
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)
    getattr(wepp, f"_prep_{kind}")()
    path = Path(wepp.runs_dir) / ("phosphorus.txt" if kind == "phosphorus" else "gwcoeff.txt")
    lines = path.read_text().splitlines()
    parsed = [float(line.split()[0]) for line in lines[(1 if kind == "phosphorus" else 0):] if line.strip()]
    assert parsed == ([1.0, 2.0, 3.0, 4.0] if kind == "phosphorus" else [200.0, 0.04, 0.0, 1.0])

    # Correct the unavailable map and retry the real producer. Only the accepted
    # first map changes its field; no abandoned alias is reattached.
    with wepp.locked():
        if kind == "phosphorus":
            wepp.p_lateral_flow_map = None
            wepp.p_baseflow_map = None
            wepp.p_sediment_map = None
        else:
            wepp.baseflow_bfcoeff_map = None
            wepp.baseflow_dscoeff_map = None
            wepp.baseflow_bfthreshold_map = None
    getattr(wepp, f"_check_and_set_{kind}_map")()
    getattr(wepp, f"_prep_{kind}")()
    accepted_lines = path.read_text().splitlines()
    accepted = [float(line.split()[0]) for line in
                accepted_lines[(1 if kind == "phosphorus" else 0):] if line.strip()]
    assert accepted == [9.0, *parsed[1:]]
    assert alias.contents == baseline
    assert getattr(Wepp.load_detached(wepp.wd), f"{kind}_opts").contents == path.read_text()


def test_repeated_real_controller_recovery_preserves_logging_resources(controllers):
    wepp, _soils = controllers
    resources = {name: getattr(wepp, name, None) for name in
                 ("logger", "runid_logger", "_queue_listener", "_queue_handler",
                  "_run_file_handler", "_redis_handler", "_log_queue")}
    listener = resources["_queue_listener"]
    assert listener is not None and listener._thread.is_alive()
    fd_root = Path("/proc/self/fd")
    descriptors_before = len(list(fd_root.iterdir()))
    handlers_before = tuple(wepp.logger.handlers)
    for _ in range(12):
        with pytest.raises(ValueError, match="repeated domain failure"):
            with wepp.locked():
                wepp._kslast = 0.9
                wepp.baseflow_opts.gwstorage = 17.0
                raise ValueError("repeated domain failure")
        assert wepp.kslast == 0.02
        assert Wepp.getInstance(wepp.wd) is wepp
        for name, resource in resources.items():
            assert getattr(wepp, name, None) is resource
    assert tuple(wepp.logger.handlers) == handlers_before
    assert listener._thread.is_alive()
    # Permit one transient descriptor for concurrent log delivery, not one per failure.
    assert len(list(fd_root.iterdir())) <= descriptors_before + 1
