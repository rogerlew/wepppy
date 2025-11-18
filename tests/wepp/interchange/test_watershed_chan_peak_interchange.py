import copy
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import types

import pandas as pd
import pytest

pyarrow = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from wepppy.wepp.interchange import watershed_chan_peak_interchange as mod


pytestmark = pytest.mark.unit


def _run_export(monkeypatch, tmp_path, frame):
    wd = tmp_path / "run"
    (wd / "wepp" / "output").mkdir(parents=True)
    (wd / "export" / "dss").mkdir(parents=True)

    class DummyWatershed:
        def __init__(self):
            self._translator = None

        def translator_factory(self):
            return self._translator

        @classmethod
        def getInstance(cls, _wd):
            return cls()

    monkeypatch.setattr("wepppy.nodb.core.Watershed", DummyWatershed)

    def fake_run_wepp_watershed_chan_peak_interchange(wepp_output_dir, *, start_year=None):
        target = Path(wepp_output_dir) / "interchange" / "chan.out.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        table = pyarrow.Table.from_pandas(frame)
        pq.write_table(table, target)
        return target

    monkeypatch.setattr(mod, "run_wepp_watershed_chan_peak_interchange", fake_run_wepp_watershed_chan_peak_interchange)

    class RecordingTSC:
        def __init__(self):
            self.pathname = ""
            self.times = []
            self.values = []
            self.numberValues = 0
            self.units = ""
            self.type = ""
            self.interval = None

    class RecordingHecDssFile:
        writes = defaultdict(list)

        def __init__(self, path):
            self.path = Path(path)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.path.touch()
            return False

        def deletePathname(self, pathname):
            pass

        def put_ts(self, tsc):
            payload = {
                "pathname": tsc.pathname,
                "times": copy.deepcopy(tsc.times),
                "values": copy.deepcopy(tsc.values),
            }
            self.writes[self.path.name].append(payload)

    class RecordingHecDss:
        @staticmethod
        def Open(path):
            return RecordingHecDssFile(path)

    core_mod = types.SimpleNamespace(TimeSeriesContainer=RecordingTSC)
    dss_mod = types.SimpleNamespace(HecDss=RecordingHecDss)
    monkeypatch.setitem(sys.modules, "pydsstools.core", core_mod)
    monkeypatch.setitem(sys.modules, "pydsstools.heclib.dss", dss_mod)
    monkeypatch.setitem(sys.modules, "pydsstools.heclib", types.SimpleNamespace(dss=dss_mod))

    class DummyStatusMessenger:
        @staticmethod
        def publish(_channel, _msg):
            return None

    monkeypatch.setattr("wepppy.nodb.status_messenger.StatusMessenger", DummyStatusMessenger)

    mod.chanout_dss_export(str(wd))
    return RecordingHecDssFile.writes


def test_chanout_dss_export_handles_small_year(monkeypatch, tmp_path):
    frame = pd.DataFrame(
        {
            "year": [2],
            "simulation_year": [2],
            "julian": [15],
            "month": [1],
            "day_of_month": [15],
            "water_year": [2],
            "Elmt_ID": [1],
            "Chan_ID": [1],
            "Time (s)": [60.0],
            "Peak_Discharge (m^3/s)": [3.5],
        }
    )

    writes = _run_export(monkeypatch, tmp_path, frame)

    records = writes["peak_chan_1.dss"]
    assert records, "DSS writes missing for channel export"
    payload = records[0]
    assert payload["values"] == [3.5]
    assert len(payload["times"]) == 1
    assert isinstance(payload["times"][0], datetime)
    assert payload["times"][0].year == 2
    assert payload["times"][0].month == 1
    assert payload["times"][0].day == 15
    assert payload["times"][0].second == 0
    assert payload["times"][0].minute == 1
