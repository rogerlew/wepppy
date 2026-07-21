"""Parity tests: vendored data prep vs golden prepared frames.

Runs prepare_ce_and_plot_data on raw run artifacts (parquet/psv, verbatim
copies from the reference runs) and asserts the resulting final_df matches
the golden frames captured from Jackson's unmodified code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from wepppy.nodb.mods.path_ce.data_prep import prepare_ce_and_plot_data

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "path_ce"
GOLDENS = FIXTURES / "goldens"

pytestmark = pytest.mark.unit


def run_inputs(run_name: str) -> dict:
    """Load a run fixture's artifacts keyed like prepare_ce_and_plot_data kwargs."""
    base = FIXTURES / run_name
    return {
        "hillslopes": pd.read_parquet(base / "scenarios.hillslope_summaries.parquet"),
        "contrasts": pd.read_parquet(base / "contrasts.out.parquet"),
        "hillslope_char": pd.read_parquet(base / "hillslopes.parquet"),
        "outlet_totals": pd.read_parquet(base / "scenarios.out.parquet"),
        "contrast_groups": str(base / "contrast_id_definitions.psv"),
    }


def _normalize_lists(df):
    df = df.copy()
    for c in ("topaz_ids", "topaz_ids_all"):
        if c in df.columns:
            df[c] = df[c].apply(lambda v: list(v) if isinstance(v, (list, np.ndarray)) else v)
    return df.reset_index(drop=True)


def _prepare(run_name):
    inputs = run_inputs(run_name)
    _, _, _, final_df = prepare_ce_and_plot_data(write_outputs=False, **inputs)
    return final_df


def test_data_prep_parity_honeyed_marathoner():
    final_df = _prepare("honeyed_marathoner")

    # The golden frame was captured after the upstream report's cleaning pass;
    # apply the same steps before comparing.
    data = final_df.copy().replace([np.inf, -np.inf], np.nan)
    for col in [c for c in data.columns if "Sddc" in c or "Sdyd" in c]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
    data = data.dropna(subset=["contrast_id", "area_sum"]).fillna(0)

    golden = pd.read_parquet(GOLDENS / "prepared_frame.parquet")
    pd.testing.assert_frame_equal(
        _normalize_lists(data), _normalize_lists(golden), check_dtype=False
    )


def test_data_prep_parity_austere_inaction():
    final_df = _prepare("austere_inaction")
    golden = pd.read_parquet(GOLDENS / "prepared_frame_austere.parquet")
    pd.testing.assert_frame_equal(
        _normalize_lists(final_df), _normalize_lists(golden), check_dtype=False
    )


def test_data_prep_grouped_mode_covers_all_treatments():
    final_df = _prepare("austere_inaction")
    for label in ("0.5 tons/acre", "1 tons/acre", "2 tons/acre"):
        for metric in ("Sdyd", "Sddc"):
            assert f"{metric} post-treat {label}" in final_df.columns
            assert f"{metric} reduction {label}" in final_df.columns
    assert final_df["Sddc post-fire"].nunique() == 1
    assert final_df["Sddc post-fire"].iloc[0] == pytest.approx(48.3)


def test_data_prep_parity_austere_slope_filtered():
    """slope_range engages the eligibility masking/substitution paths."""
    inputs = run_inputs("austere_inaction")
    _, _, _, final_df = prepare_ce_and_plot_data(
        write_outputs=False, slope_range=(20, 35), **inputs
    )
    golden = pd.read_parquet(GOLDENS / "prepared_frame_austere_slope20_35.parquet")
    pd.testing.assert_frame_equal(
        _normalize_lists(final_df), _normalize_lists(golden), check_dtype=False
    )
    # the filter must actually change the frame vs the unfiltered golden
    unfiltered = pd.read_parquet(GOLDENS / "prepared_frame_austere.parquet")
    assert not final_df["Sdyd post-treat 2 tons/acre"].equals(
        unfiltered["Sdyd post-treat 2 tons/acre"]
    )


def test_data_prep_writes_parquet_not_csv(tmp_path):
    inputs = run_inputs("austere_inaction")
    prepare_ce_and_plot_data(
        write_outputs=True, output_dir=str(tmp_path), output_prefix="t", **inputs
    )
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == [
        "t_char_agg.parquet",
        "t_final_data.parquet",
        "t_hillslope_agg.parquet",
        "t_outlet_agg.parquet",
    ]
