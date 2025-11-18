import copy
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

pyarrow = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from wepppy.wepp.interchange import watershed_totalwatsed_export as mod


pytestmark = pytest.mark.unit


def _build_dataframe():
    dates = pd.date_range("2011-01-01", periods=60, freq="D")
    return pd.DataFrame(
        {
            "year": dates.year,
            "month": dates.month,
            "day_of_month": dates.day,
            "julian": dates.dayofyear,
            "sim_day_index": range(len(dates)),
            "water_year": dates.year,
            "Area": 1200.0,
            "Streamflow": 1.0,
            "runvol": 2.0,
        }
    )


def _run_export(monkeypatch, tmp_path, frames, **kwargs):
    wd = tmp_path / "run"
    (wd / "wepp" / "output" / "interchange").mkdir(parents=True)
    (wd / "export" / "dss").mkdir(parents=True)

    translator_ids = [f"chn_{channel_id}" for channel_id in frames]

    class DummyTranslator:
        def iter_chn_ids(self):
            return translator_ids

    translator = DummyTranslator()

    class DummyWatershed:
        def __init__(self):
            self.network = object()

        def translator_factory(self):
            return translator

        @classmethod
        def getInstance(cls, _wd):
            return cls()

    class DummyWepp:
        def __init__(self):
            self.baseflow_opts = None

        @classmethod
        def getInstance(cls, _wd):
            return cls()

    class DummyBaseflowOpts:
        pass

    monkeypatch.setattr("wepppy.nodb.core.Watershed", DummyWatershed)
    monkeypatch.setattr("wepppy.nodb.core.Wepp", DummyWepp)
    monkeypatch.setattr("wepppy.nodb.core.wepp.BaseflowOpts", DummyBaseflowOpts)

    def fake_run_totalwatsed3(interchange_dir, baseflow_opts, wepp_ids=None):
        channel_id = wepp_ids[0]
        path = Path(interchange_dir) / f"{channel_id}.parquet"
        table = pyarrow.Table.from_pandas(frames[channel_id])
        pq.write_table(table, path)
        return path

    monkeypatch.setattr(mod, "run_totalwatsed3", fake_run_totalwatsed3)
    monkeypatch.setattr(mod, "_channel_wepp_ids", lambda translator, network, channel_top_id: [channel_top_id])

    class RecordingTSC:
        def __init__(self):
            self.pathname = ""
            self.startDateTime = ""
            self.interval = None
            self.numberValues = 0
            self.units = ""
            self.type = ""
            self.values = []

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
                "start": tsc.startDateTime,
                "count": tsc.numberValues,
            }
            self.writes[self.path.name].append(copy.deepcopy(payload))

    class RecordingHecDss:
        @staticmethod
        def Open(path):
            return RecordingHecDssFile(path)

    monkeypatch.setattr(mod, "_require_pydsstools", lambda: (RecordingTSC, RecordingHecDss))

    mod.totalwatsed_partitioned_dss_export(str(wd), **kwargs)
    return RecordingHecDssFile.writes


def test_partitioned_dss_respects_date_range_per_channel(monkeypatch, tmp_path):
    frames = {channel_id: _build_dataframe() for channel_id in (101, 104)}

    writes = _run_export(
        monkeypatch,
        tmp_path,
        frames,
        start_date=date(2011, 2, 1),
        end_date=date(2011, 2, 3),
    )

    for chan_id in (101, 104):
        fname = f"totalwatsed3_chan_{chan_id}.dss"
        records = writes[fname]
        assert records, f"Missing DSS writes for channel {chan_id}"
        runvol_record = next((rec for rec in records if "RUNVOL" in rec["pathname"]), None)
        assert runvol_record is not None
        assert runvol_record["start"] == "01FEB2011 00:00:00"
        assert runvol_record["count"] == 3
        assert "01FEB2011" in runvol_record["pathname"]


def test_partitioned_dss_accepts_year_one_dates(monkeypatch, tmp_path):
    frame = pd.DataFrame(
        {
            "year": [1, 1, 1],
            "month": [1, 1, 1],
            "day_of_month": [11, 12, 13],
            "julian": [11, 12, 13],
            "sim_day_index": [10, 11, 12],
            "water_year": [1, 1, 1],
            "Area": 1200.0,
            "Streamflow": 1.0,
            "runvol": 2.0,
        }
    )

    writes = _run_export(monkeypatch, tmp_path, {101: frame})

    records = writes["totalwatsed3_chan_101.dss"]
    assert records, "DSS writes missing for year-one start date"
    runvol_record = next((rec for rec in records if "RUNVOL" in rec["pathname"]), None)
    assert runvol_record is not None
    assert runvol_record["start"] == "11JAN0001 00:00:00"
    assert "11JAN0001" in runvol_record["pathname"]
