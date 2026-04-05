from __future__ import annotations

import pytest

from wepppy.nodb.core.soils import Soils

pytestmark = pytest.mark.unit


class _SoilStub:
    def __init__(self, mukey: str, pct_coverage: float) -> None:
        self.mukey = mukey
        self.pct_coverage = pct_coverage

    def as_dict(self, abbreviated: bool = True) -> dict[str, float | str | bool]:
        return {
            "mukey": self.mukey,
            "pct_coverage": self.pct_coverage,
            "abbreviated": abbreviated,
        }


def test_report_sorts_used_soils_by_descending_pct_coverage() -> None:
    soils = Soils.__new__(Soils)
    soils.domsoil_d = {"101": "200", "102": "300", "103": "100"}
    soils.soils = {
        "100": _SoilStub("100", 15.0),
        "200": _SoilStub("200", 8.0),
        "300": _SoilStub("300", 10.9),
        "999": _SoilStub("999", 99.0),
    }

    report = soils.report

    assert [row["mukey"] for row in report] == ["100", "300", "200"]
    assert [row["pct_coverage"] for row in report] == [15.0, 10.9, 8.0]
