# test_climate_scaling.py
import os
import tempfile
import numpy as np
import pytest

from wepppyo3.climate import rust_cli_p_scale as pyo3_cli_p_scale
from wepppy.climates.cligen import ClimateFile

TEST_CLI = "test.cli"


def _prcp_series(cli_path: str) -> np.ndarray:
    """Load a .cli file via ClimateFile and return the precipitation series as float64."""
    cf = ClimateFile(cli_path)
    df = cf.as_dataframe()
    try:
        prcp = df.prcp.to_numpy(dtype=float)
    except Exception:
        prcp = df["prcp"].to_numpy(dtype=float)
    return prcp


@pytest.mark.parametrize("p_mult", [0.0, 0.5, 1.0, 1.23, 2.5])
def test_prcp_scaling_matches_rust_round1(p_mult):
    """
    Sanity check: Python transform_precip(offset=0, scale=p_mult) should match
    Rust rust_cli_p_scale(*, p_mult) after rounding to 1 decimal (Rust formats '{:.1}').
    """
    if not os.path.exists(TEST_CLI):
        pytest.skip(f"Missing test input: {TEST_CLI}")

    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "src.cli")
        dst_rust = os.path.join(td, "dst_rust.cli")

        # Copy test input into temp dir
        with open(TEST_CLI, "rb") as r, open(src, "wb") as w:
            w.write(r.read())

        # Run Rust scaler (writes with one-decimal formatting)
        pyo3_cli_p_scale(src, dst_rust, p_mult)

        # Load original & Rust-scaled precip
        prcp_src = _prcp_series(src)
        prcp_rust = _prcp_series(dst_rust)

        # Python-side transform w/ offset=0 to mirror Rust
        cf_py = ClimateFile(src)
        cf_py.transform_precip(offset=0.0, scale=p_mult)
        prcp_py = cf_py.as_dataframe().prcp.to_numpy(dtype=float)

        # Match Rust's one-decimal rounding for comparison
        prcp_py_round1 = np.round(prcp_py, 1)

        # Allow exact equality on rounded arrays; if desired, loosen to allclose with atol=0.05
        np.testing.assert_array_equal(prcp_py_round1, prcp_rust)


@pytest.mark.parametrize("p_mult,offset", [(1.23, 0.1), (0.8, -0.2)])
def test_nonzero_offset_diverges_from_rust(p_mult, offset):
    """
    Nonzero offset in Python should *not* match the Rust output.
    """
    if not os.path.exists(TEST_CLI):
        pytest.skip(f"Missing test input: {TEST_CLI}")

    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "src.cli")
        dst_rust = os.path.join(td, "dst_rust.cli")

        with open(TEST_CLI, "rb") as r, open(src, "wb") as w:
            w.write(r.read())

        pyo3_cli_p_scale(src, dst_rust, p_mult)
        prcp_rust = _prcp_series(dst_rust)

        cf_py = ClimateFile(src)
        cf_py.transform_precip(offset=offset, scale=p_mult)
        prcp_py = cf_py.as_dataframe().prcp.to_numpy(dtype=float)

        # Even after rounding to 1 decimal, they should differ when offset != 0
        prcp_py_round1 = np.round(prcp_py, 1)

        with pytest.raises(AssertionError):
            np.testing.assert_array_equal(prcp_py_round1, prcp_rust)

