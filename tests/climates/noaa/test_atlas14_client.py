from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.climates.noaa import atlas14

pytestmark = pytest.mark.unit


def _payload_text() -> str:
    quantiles = [[str((row + 1) * (col + 2)) for col in range(10)] for row in range(19)]
    upper = [[str((row + 2) * (col + 3)) for col in range(10)] for row in range(19)]
    lower = [[str((row + 3) * (col + 1)) for col in range(10)] for row in range(19)]

    return "\n".join(
        [
            "result = 'values';",
            f"quantiles = {quantiles};",
            f"upper = {upper};",
            f"lower = {lower};",
            "lat = '39.0000';",
            "lon = '-105.0000';",
            "region = 'Midwestern States';",
            "volume = '8';",
            "version = '2';",
            "pyRunTime = 0.12;",
        ]
    )


class _Response:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


def test_download_writes_expected_noaa_report_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        atlas14.requests,
        "get",
        lambda *_args, **_kwargs: _Response(_payload_text()),
    )

    path = atlas14.download(
        lat=39.0,
        lon=-105.0,
        parent=tmp_path,
        name="atlas14_intensity_pds_mean_metric.csv",
        overwrite=True,
        statistic="mean",
        data="intensity",
        series="pds",
        units="metric",
        timeout=30,
    )

    assert path.exists()
    text = path.read_text()
    assert "NOAA Atlas 14 Volume 8 Version 2" in text
    assert "by duration for ARI (years):, 1,2,5,10,25,50,100,200,500,1000" in text
    assert "5-min:, 2,3,4,5,6,7,8,9,10,11" in text
    assert "Date/time (GMT):" in text
    assert "pyRunTime:" in text


def test_download_no_coverage_raises_value_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    no_coverage = "\n".join(
        [
            "result = 'none';",
            "ErrorMsg = 'Error 3.0: Selected location is not within a project area';",
        ]
    )
    monkeypatch.setattr(
        atlas14.requests,
        "get",
        lambda *_args, **_kwargs: _Response(no_coverage),
    )

    with pytest.raises(ValueError, match="not available"):
        atlas14.download(lat=45.5152, lon=-122.6784, parent=tmp_path, overwrite=True)


def test_download_existing_file_requires_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        atlas14.requests,
        "get",
        lambda *_args, **_kwargs: _Response(_payload_text()),
    )

    existing = tmp_path / "atlas.csv"
    existing.write_text("old")

    with pytest.raises(FileExistsError):
        atlas14.download(lat=39.0, lon=-105.0, parent=tmp_path, name=existing.name)


def test_query_url_rejects_invalid_statistic() -> None:
    with pytest.raises(ValueError, match="Invalid statistic"):
        atlas14.query_url("bogus")
