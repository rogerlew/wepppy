"""Parity tests: vendored solver core vs goldens from Jackson's unmodified code.

These call ``ce_select_sites_flexible`` directly (no wrapper seam) so they
certify faithfulness to upstream 4e3b4a6, including its hectare-area cost
basis. The wepppy seam contracts (acre conversion, label alignment) are
tested separately in test_solver_seam.py.

Golden cases cover both id schemas (wepp_id / contrast_id), one- and
three-treatment configurations, both solver paths (primary optimal /
secondary maximize fallback), and slope/severity-filtered runs. Assertions
compare the full ordered outputs: selections, untreatable id sets,
increase-class ids, the complete final-Sdyd table, per-treatment cost-vector
sums, and the reduction-threshold sum.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pulp")
pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from wepppy.nodb.mods.path_ce.path_ce_solver import ce_select_sites_flexible

GOLDENS = Path(__file__).resolve().parents[3] / "data" / "path_ce" / "goldens"

pytestmark = pytest.mark.unit

UPSTREAM_COMMIT = "4e3b4a6"


def load_golden(name: str) -> dict:
    with open(GOLDENS / name) as f:
        golden = json.load(f)
    assert golden["upstream_commit"] == UPSTREAM_COMMIT
    return golden


def _clean_numeric(frame):
    frame = frame.copy()
    num = frame.select_dtypes(include=[np.number]).columns
    frame[num] = frame[num].replace([np.inf, -np.inf], np.nan)
    for col in [c for c in frame.columns if "Sddc" in c or "Sdyd" in c]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0)
    return frame


def _assert_case(result, case, id_col):
    (status, cost_vectors, syrt, selected, treat_hills, sddc_red, final_sddc,
     _hs, sdyd_df, untreatable, total_cost, total_fixed, untreat_inc) = result

    assert int(status) == case["primary_status"]
    assert sorted(int(x) for x in selected) == case["selected_hillslopes"]
    assert [sorted(int(x) for x in t) for t in treat_hills] == case["treatment_hillslopes"]
    assert float(total_cost) == pytest.approx(case["total_cost"], abs=0.01)
    assert float(total_fixed) == pytest.approx(case["total_fixed_cost"], abs=0.01)
    assert float(sddc_red) == pytest.approx(case["total_sddc_reduction"], abs=1e-4)
    assert float(final_sddc) == pytest.approx(case["final_sddc"], abs=1e-4)

    assert sorted(int(x) for x in untreatable[id_col].tolist()) == case["untreatable_ids"]
    increase_ids = sorted(int(x) for x in untreat_inc[id_col].tolist()) if len(untreat_inc) else []
    assert increase_ids == case["untreatable_increase_ids"]

    got_sdyd = sorted(
        (int(i), float(v))
        for i, v in zip(sdyd_df[id_col].tolist(), pd.to_numeric(sdyd_df["final_Sdyd"]).tolist())
    )
    want_sdyd = [(int(i), float(v)) for i, v in case["sdyd_final"]]
    assert [i for i, _ in got_sdyd] == [i for i, _ in want_sdyd]
    for (_, got), (_, want) in zip(got_sdyd, want_sdyd):
        assert got == pytest.approx(want, abs=1e-4)

    for label, want_sum in case["cost_vector_sums"].items():
        assert float(pd.to_numeric(cost_vectors[label]).sum()) == pytest.approx(want_sum, abs=0.01)
    assert float(pd.to_numeric(syrt).sum()) == pytest.approx(case["syrt_sum"], abs=1e-4)


def _run_cases(golden, frame, id_col):
    for case in golden["cases"]:
        result = ce_select_sites_flexible(
            data=frame,
            treatments=golden["treatments"],
            treatment_cost=golden["treatment_cost"],
            treatment_quantity=golden["treatment_quantity"],
            fixed_cost=golden["fixed_cost"],
            sdyd_threshold=case["sdyd_threshold"],
            sddc_threshold=case["sddc_threshold"],
            slope_range=tuple(case["slope_range"]) if case.get("slope_range") else None,
            bs_threshold=list(case["bs_threshold"]) if case.get("bs_threshold") else None,
        )
        assert result is not None
        _assert_case(result, case, id_col)


def test_solver_parity_contrast_id_single_treatment_incl_filters():
    golden = load_golden("solver_goldens.json")
    frame = pd.read_parquet(GOLDENS / "prepared_frame.parquet")
    assert any(c.get("slope_range") for c in golden["cases"]), "filtered coverage required"
    assert any(c.get("bs_threshold") for c in golden["cases"]), "severity-filtered coverage required"
    _run_cases(golden, frame, "contrast_id")


def test_solver_parity_wepp_id_three_treatments():
    golden = load_golden("solver_goldens_3treat.json")
    frame = pd.read_csv(GOLDENS / "PATH_prepared_hillslope_data.csv")
    frame = frame.replace([np.inf, -np.inf], np.nan)
    for col in [c for c in frame.columns if "Sddc" in c or "Sdyd" in c]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0)
    frame = frame.dropna(subset=["wepp_id", "area"]).fillna(0)
    _run_cases(golden, frame, "wepp_id")


def test_solver_parity_grouped_three_treatments():
    golden = load_golden("solver_goldens_austere.json")
    frame = _clean_numeric(pd.read_parquet(GOLDENS / "prepared_frame_austere.parquet"))
    _run_cases(golden, frame, "contrast_id")


def test_solver_requires_sddc_reduction_columns():
    frame = pd.read_parquet(GOLDENS / "prepared_frame.parquet")
    frame = frame.drop(columns=[c for c in frame.columns if c.startswith("Sddc reduction")])
    with pytest.raises(ValueError, match="Sddc reduction"):
        ce_select_sites_flexible(
            data=frame, treatments=["2 tons/acre"], treatment_cost=[2475.0],
            treatment_quantity=[2.0], fixed_cost=[1500.0],
            sdyd_threshold=15, sddc_threshold=43000,
        )
