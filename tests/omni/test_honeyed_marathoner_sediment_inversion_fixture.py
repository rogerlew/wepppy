"""Regression coverage for the honeyed-marathoner OMNI sediment inversion fixture."""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

FIXTURE_ROOT = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "honeyed_marathoner_sediment_inversion"
    / "run_root"
)

HILLSLOPES = (118, 122, 264)

EXPECTED = {
    118: {
        "j167_soil_water": {"burned": 342.86, "unburned": 342.73},
        "j168_runoff": {"burned": 0.0, "unburned": 4.9954},
        "loss_kg": {"burned": 0.0, "unburned": 0.765},
        "unburned_sedleave": 0.032,
        "base_event_row": False,
    },
    122: {
        "j167_soil_water": {"burned": 343.21, "unburned": 343.16},
        "j168_runoff": {"burned": 0.0, "unburned": 4.7153},
        "loss_kg": {"burned": 0.0, "unburned": 0.159},
        "unburned_sedleave": 0.004,
        "base_event_row": False,
    },
    264: {
        "j167_soil_water": {"burned": 347.10, "unburned": 348.00},
        "j168_runoff": {"burned": 0.0559, "unburned": 7.4450},
        "loss_kg": {"burned": 0.0, "unburned": 61.179},
        "unburned_sedleave": 0.202,
        "base_event_row": True,
    },
}


def _output_dir(scenario: str) -> Path:
    if scenario == "burned":
        return FIXTURE_ROOT / "wepp" / "output"
    if scenario == "unburned":
        return FIXTURE_ROOT / "_pups" / "omni" / "scenarios" / "undisturbed" / "wepp" / "output"
    raise ValueError(f"unknown scenario: {scenario}")


def _runs_dir(scenario: str) -> Path:
    if scenario == "burned":
        return FIXTURE_ROOT / "wepp" / "runs"
    if scenario == "unburned":
        return FIXTURE_ROOT / "_pups" / "omni" / "scenarios" / "undisturbed" / "wepp" / "runs"
    raise ValueError(f"unknown scenario: {scenario}")


def _daily_water(path: Path) -> dict[tuple[int, int, int], dict[str, float]]:
    rows: dict[tuple[int, int, int], dict[str, float]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) != 20 or not parts[0].isdigit():
            continue
        ofe, julian, year = int(parts[0]), int(parts[1]), int(parts[2])
        if ofe != 1:
            continue
        rows[(year, julian, ofe)] = {
            "precip": float(parts[3]),
            "runoff": float(parts[5]),
            "soil_water": float(parts[13]),
            "deep_percolation": float(parts[9]),
            "lateral_flow": float(parts[12]),
        }
    return rows


def _loss_summary(path: Path) -> dict[str, float]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if "AVERAGE ANNUAL SEDIMENT LEAVING PROFILE" not in line:
            continue
        kg_per_m = re.search(r"([-0-9.]+)\s+kg/m", lines[index + 1])
        kg = re.search(r"([-0-9.]+)\s+kg", lines[index + 2])
        tonnes_per_ha = re.search(r"([-0-9.]+)\s+t/ha", lines[index + 3])
        assert kg_per_m and kg and tonnes_per_ha
        return {
            "kg_per_m": float(kg_per_m.group(1)),
            "kg": float(kg.group(1)),
            "tonnes_per_ha": float(tonnes_per_ha.group(1)),
        }
    raise AssertionError(f"missing sediment summary in {path}")


def _element_events(path: Path) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) != 24 or not parts[0].isdigit():
            continue
        rows.append(
            {
                "ofe": int(parts[0]),
                "day": int(parts[1]),
                "month": int(parts[2]),
                "year": int(parts[3]),
                "precip": float(parts[4]),
                "runoff": float(parts[5]),
                "peak_runoff": float(parts[7]),
                "keff": float(parts[10]),
                "soil_water": float(parts[11]),
                "leaf_area": float(parts[12]),
                "canopy_cover": float(parts[14]),
                "interrill_cover": float(parts[15]),
                "rill_cover": float(parts[16]),
                "ki": float(parts[19]),
                "kr": float(parts[20]),
                "sedleave": float(parts[23]),
            }
        )
    return rows


def _event_on_1992_06_16(path: Path) -> dict[str, float | int] | None:
    matches = [
        row
        for row in _element_events(path)
        if row["day"] == 16 and row["month"] == 6 and row["year"] == 1992
    ]
    if not matches:
        return None
    assert len(matches) == 1
    return matches[0]


def test_fixture_contains_expected_inputs_and_outputs() -> None:
    for hillslope in HILLSLOPES:
        for suffix in ("run", "man", "sol", "err"):
            assert (_runs_dir("burned") / f"p{hillslope}.{suffix}").exists()
            assert (_runs_dir("unburned") / f"p{hillslope}.{suffix}").exists()

        # The unburned runs reference the burned root slope/climate files by
        # relative path, so those shared files are intentionally present once.
        for suffix in ("slp", "cli"):
            assert (_runs_dir("burned") / f"p{hillslope}.{suffix}").exists()

        for suffix in ("ebe.dat", "element.dat", "loss.dat", "pass.dat", "plot.dat", "soil.dat", "wat.dat"):
            assert (_output_dir("burned") / f"H{hillslope}.{suffix}").exists()
            assert (_output_dir("unburned") / f"H{hillslope}.{suffix}").exists()


@pytest.mark.parametrize("hillslope", HILLSLOPES)
def test_june_1992_event_threshold_behavior_is_preserved(hillslope: int) -> None:
    expected = EXPECTED[hillslope]

    burned_water = _daily_water(_output_dir("burned") / f"H{hillslope}.wat.dat")
    unburned_water = _daily_water(_output_dir("unburned") / f"H{hillslope}.wat.dat")

    burned_j167 = burned_water[(1992, 167, 1)]
    unburned_j167 = unburned_water[(1992, 167, 1)]
    burned_j168 = burned_water[(1992, 168, 1)]
    unburned_j168 = unburned_water[(1992, 168, 1)]

    assert math.isclose(
        burned_j167["soil_water"],
        expected["j167_soil_water"]["burned"],
        abs_tol=0.01,
    )
    assert math.isclose(
        unburned_j167["soil_water"],
        expected["j167_soil_water"]["unburned"],
        abs_tol=0.01,
    )
    assert abs(unburned_j167["soil_water"] - burned_j167["soil_water"]) <= 1.0

    assert math.isclose(burned_j168["runoff"], expected["j168_runoff"]["burned"], abs_tol=0.0001)
    assert math.isclose(unburned_j168["runoff"], expected["j168_runoff"]["unburned"], abs_tol=0.0001)
    assert unburned_j168["runoff"] > burned_j168["runoff"] + 4.0
    assert unburned_j168["soil_water"] < burned_j168["soil_water"] - 6.0

    burned_loss = _loss_summary(_output_dir("burned") / f"H{hillslope}.loss.dat")
    unburned_loss = _loss_summary(_output_dir("unburned") / f"H{hillslope}.loss.dat")
    assert burned_loss["kg"] == expected["loss_kg"]["burned"]
    assert math.isclose(unburned_loss["kg"], expected["loss_kg"]["unburned"], abs_tol=0.001)

    burned_event = _event_on_1992_06_16(_output_dir("burned") / f"H{hillslope}.element.dat")
    unburned_event = _event_on_1992_06_16(_output_dir("unburned") / f"H{hillslope}.element.dat")

    assert (burned_event is not None) is expected["base_event_row"]
    assert unburned_event is not None
    assert math.isclose(
        float(unburned_event["sedleave"]),
        expected["unburned_sedleave"],
        abs_tol=0.001,
    )
    assert float(unburned_event["keff"]) == 50.0
    assert float(unburned_event["leaf_area"]) == 11.875
    assert float(unburned_event["canopy_cover"]) == 90.0
    assert float(unburned_event["interrill_cover"]) == 99.9
    assert float(unburned_event["rill_cover"]) == 99.9

    if burned_event is not None:
        assert float(burned_event["sedleave"]) == 0.0
        assert float(burned_event["keff"]) == 20.0
        assert float(burned_event["leaf_area"]) == 2.32
