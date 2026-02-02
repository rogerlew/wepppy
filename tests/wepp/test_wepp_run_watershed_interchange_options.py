import logging
from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.core.wepp as wepp_module
from wepppy.nodb.core.climate import Climate, ClimateMode
from wepppy.nodb.core.wepp import Wepp


pytestmark = pytest.mark.unit


@contextmanager
def _noop_timed(*args, **kwargs):
    yield


def test_run_watershed_respects_contrast_output_options(tmp_path, monkeypatch):
    wepp = Wepp.__new__(Wepp)
    wepp.wd = str(tmp_path / "omni" / "contrasts" / "1")

    runs_dir = Path(wepp.runs_dir)
    output_dir = Path(wepp.output_dir)
    interchange_dir = Path(wepp.wepp_interchange_dir)
    runs_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    interchange_dir.mkdir(parents=True)
    wepp.logger = logging.getLogger("tests.wepp.run_watershed_outputs")
    wepp.config_get_bool = lambda *args, **kwargs: False
    wepp._run_wepp_watershed = True
    wepp._wepp_bin = "wepp"
    wepp.timed = _noop_timed
    wepp._contrast_output_options = {
        "ebe_pw0": False,
        "chan_out": False,
        "chnwb": False,
        "soil_pw0": False,
    }

    class DummyClimate:
        climate_mode = ClimateMode.Observed
        is_single_storm = False
        calendar_start_year = 2000

        def getInstance(self, wd):
            return self

    dummy_climate = DummyClimate()
    monkeypatch.setattr(Climate, "getInstance", lambda wd: dummy_climate)

    monkeypatch.setattr(wepp_module, "run_watershed", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        wepp_module.RedisPrep,
        "getInstance",
        lambda wd: (_ for _ in ()).throw(FileNotFoundError()),
    )
    monkeypatch.setattr(
        "wepppy.wepp.interchange.interchange_documentation.generate_interchange_documentation",
        lambda *args, **kwargs: None,
    )

    captured = {}

    def fake_interchange(
        output_dir,
        *,
        start_year,
        run_ebe_interchange,
        run_chan_out_interchange,
        run_soil_interchange,
        run_chnwb_interchange,
        delete_after_interchange,
    ):
        captured["flags"] = {
            "start_year": start_year,
            "run_ebe_interchange": run_ebe_interchange,
            "run_chan_out_interchange": run_chan_out_interchange,
            "run_soil_interchange": run_soil_interchange,
            "run_chnwb_interchange": run_chnwb_interchange,
            "delete_after_interchange": delete_after_interchange,
        }

    monkeypatch.setattr(
        "wepppy.wepp.interchange.watershed_interchange.run_wepp_watershed_interchange",
        fake_interchange,
    )

    wepp.run_watershed()

    assert captured["flags"]["start_year"] == 2000
    assert captured["flags"]["run_ebe_interchange"] is False
    assert captured["flags"]["run_chan_out_interchange"] is False
    assert captured["flags"]["run_soil_interchange"] is False
    assert captured["flags"]["run_chnwb_interchange"] is False
    assert captured["flags"]["delete_after_interchange"] is False
