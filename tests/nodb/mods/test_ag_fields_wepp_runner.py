from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from wepppy.nodb.mods.ag_fields import ag_fields as ag_fields_module


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_run_wepp_ag_fields_passes_configured_binary_to_subfield_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subfields = pd.DataFrame(
        [
            {
                "field_id": 10,
                "topaz_id": 20,
                "wepp_id": 30,
                "sub_field_id": 40,
            }
        ]
    )
    schedule = pd.DataFrame([{"field_id": 10, "Crop2001": "wheat"}])
    monkeypatch.setattr(pd, "read_parquet", lambda _path: schedule)

    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        ag_fields_module,
        "run_wepp_subfield",
        lambda *args: calls.append(args),
    )

    controller = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
        climate_instance=SimpleNamespace(observed_start_year=2001, observed_end_year=2001),
        watershed_instance=SimpleNamespace(clip_hillslopes=False, clip_hillslope_length=None),
        wepp_instance=SimpleNamespace(wepp_bin="/opt/wepp/bin/wepp"),
        subfields_parquet=subfields,
        rotation_schedule_parquet="rotation_schedule.parquet",
        field_id_key="field_id",
        wd="/tmp/ag-fields-run",
        get_rotation_key=lambda year: f"Crop{year}",
        _observed_year_bounds=lambda: (2001, 2001),
        locked=lambda: nullcontext(),
        _workflow_signature=lambda: "workflow-signature",
    )

    ag_fields_module.AgFields.run_wepp_ag_fields(controller, max_workers=1)

    assert len(calls) == 1
    assert calls[0][8] == "/opt/wepp/bin/wepp"


def test_run_wepp_subfield_reaches_runner_with_explicit_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs_dir = tmp_path / "wepp" / "ag_fields" / "runs"
    slope_dir = tmp_path / "ag_fields" / "sub_fields" / "slope_files"
    runs_dir.mkdir(parents=True)
    slope_dir.mkdir(parents=True)
    (slope_dir / "field_1_2.slp").write_text("slope", encoding="utf-8")

    monkeypatch.setattr(
        ag_fields_module.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(input_years=1),
    )
    monkeypatch.setattr(
        ag_fields_module.Landuse,
        "getInstance",
        lambda _wd: SimpleNamespace(mapping="default"),
    )

    class DummyRotationManager:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def build_rotation_stack(self, schedule: list[str], path: str) -> None:
            assert schedule == ["wheat"]
            Path(path).write_text("management", encoding="utf-8")

    monkeypatch.setattr(ag_fields_module, "CropRotationManager", DummyRotationManager)
    monkeypatch.setattr(
        ag_fields_module,
        "_template_loader",
        lambda _name: "{sub_field_id} {man_relpath} {slp_relpath} {cli_relpath} {sol_relpath} {sim_years}",
    )

    runner_calls: list[tuple[int, str, str, bool]] = []

    def _run_hillslope(sub_field_id: int, wd: str, *, wepp_bin: str, no_file_checks: bool) -> None:
        runner_calls.append((sub_field_id, wd, wepp_bin, no_file_checks))

    monkeypatch.setattr(ag_fields_module, "run_hillslope", _run_hillslope)

    ag_fields_module.run_wepp_subfield(
        str(tmp_path),
        field_id=1,
        topaz_id="2",
        wepp_id=3,
        sub_field_id=4,
        crop_rotation_schedule=["wheat"],
        clip_hillslopes=False,
        clip_hillslope_length=None,
        wepp_bin="/opt/wepp/bin/wepp",
    )

    assert runner_calls == [(4, str(runs_dir), "/opt/wepp/bin/wepp", True)]
    assert (runs_dir / "p4.run").is_file()
    assert (runs_dir / "p4.man").is_file()
    assert (runs_dir / "p4.slp").read_text(encoding="utf-8") == "slope"
