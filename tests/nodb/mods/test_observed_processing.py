from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

from wepppy.nodb.mods.observed import Observed

pytestmark = [pytest.mark.nodb, pytest.mark.slow]

RUN_DIR = Path("/wc1/runs/un/unpresidential-shabbiness")
OBSERVED_CSV = Path(__file__).resolve().parents[2] / "data" / "observed" / "CedarRv_WA.csv"

EXPECTED_STATS = {
    "Hillslopes": {
        "Daily": {
            "agreementindex": 0.8072641166513037,
            "correlationcoefficient": 0.6868911493790438,
            "kge": 0.6260322267160667,
            "nashsutcliffe": 0.4576934876983516,
            "pbias": -4.29690979337252,
            "rmse": 5.159677709496741,
        },
        "Yearly": {
            "agreementindex": 0.9637933520433822,
            "correlationcoefficient": 0.9490788722274823,
            "kge": 0.9275266836269156,
            "nashsutcliffe": 0.8528990649619959,
            "pbias": -4.201445844566267,
            "rmse": 170.1292948267239,
        },
    },
    "Channels": {
        "Daily": {
            "agreementindex": 0.8111689173743838,
            "correlationcoefficient": 0.6937129475441894,
            "kge": 0.6295187809079817,
            "nashsutcliffe": 0.46968133399904255,
            "pbias": -4.070394970441826,
            "rmse": 5.102330918470064,
        },
        "Yearly": {
            "agreementindex": 0.9647918909840794,
            "correlationcoefficient": 0.9490651666130974,
            "kge": 0.9277908682371475,
            "nashsutcliffe": 0.8568118906994145,
            "pbias": -3.975530794869666,
            "rmse": 167.85135926357924,
        },
    },
}


def _skip_if_missing_inputs() -> None:
    if not RUN_DIR.exists():
        pytest.skip(f"Observed regression run dir not available: {RUN_DIR}")
    if not OBSERVED_CSV.exists():
        pytest.skip(f"Observed CSV not available: {OBSERVED_CSV}")

    required = [
        RUN_DIR / "observed.nodb",
        RUN_DIR / "wepp" / "output" / "ebe_pw0.txt",
        RUN_DIR / "wepp" / "output" / "chanwb.out",
    ]
    if any(not path.exists() for path in required):
        pytest.skip("Observed regression inputs are incomplete.")

    output_dir = RUN_DIR / "wepp" / "output"
    if not any(output_dir.glob("H*.pass.dat")):
        pytest.skip("Observed regression inputs missing H*.pass.dat outputs.")
    if not any(output_dir.glob("H*.wat.dat")):
        pytest.skip("Observed regression inputs missing H*.wat.dat outputs.")


@pytest.fixture()
def observed_run() -> None:
    _skip_if_missing_inputs()
    Observed.cleanup_all_instances()
    yield
    Observed.cleanup_all_instances()


def test_observed_model_fit_regression(observed_run: None) -> None:
    observed = Observed.getInstance(str(RUN_DIR))
    textdata = OBSERVED_CSV.read_text()

    observed.parse_textdata(textdata)
    observed.calc_model_fit()

    results = observed.results
    assert results is not None

    for group_name, expected_group in EXPECTED_STATS.items():
        group_results = results[group_name]["Streamflow (mm)"]
        for period, expected_metrics in expected_group.items():
            period_results = group_results[period]
            for metric, expected in expected_metrics.items():
                assert period_results[metric] == pytest.approx(expected, rel=1e-6, abs=1e-6)
