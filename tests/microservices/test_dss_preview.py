from datetime import datetime, timedelta

import pytest

pytestmark = pytest.mark.microservice

pydsstools = pytest.importorskip("pydsstools")
from pydsstools.heclib.dss import HecDss  # type: ignore  # noqa: E402
from pydsstools.core import TimeSeriesContainer, setMessageLevel  # type: ignore  # noqa: E402

from wepppy.microservices.dss_preview import build_preview


@pytest.fixture
def sample_dss(tmp_path):
    path = tmp_path / "sample.dss"
    for method in range(19):
        setMessageLevel(method, 0)

    with HecDss.Open(str(path)) as fid:
        tsc = TimeSeriesContainer()
        tsc.pathname = "/EX/CHANNEL/FLOW//IR-YEAR/001/"
        values = [1.0, 2.0, 3.0]
        base = datetime(2000, 1, 1)
        tsc.times = [base + timedelta(days=idx) for idx in range(len(values))]
        tsc.interval = -1
        tsc.numberValues = len(values)
        tsc.units = "CFS"
        tsc.type = "INST"
        tsc.values = values
        fid.deletePathname(tsc.pathname)
        fid.put_ts(tsc)

    return path


def test_build_preview_reports_basic_fields(sample_dss):
    preview = build_preview(str(sample_dss))
    assert preview.record_count >= 1
    assert "FLOW" in preview.unique_parts["C"]

    row = next(row for row in preview.rows if row.c_part == "FLOW" and "IR" in (row.e_part or ""))
    assert row.record_type == "TS"
    assert (row.value_count or 0) > 0
