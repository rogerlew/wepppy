from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import pytest

import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.nodb.mods.omni.omni_artifact_export_service import OmniArtifactExportService

pytestmark = pytest.mark.unit


class _ArtifactOmniStub:
    def __init__(self, wd: Path) -> None:
        self.wd = str(wd)
        self.logger = logging.getLogger("tests.omni.artifacts")
        self.scenarios: list[dict] = []
        self.contrast_names: list[str] = []
        self._contrast_selection_mode = "cumulative"
        self._contrast_labels = {}
        self.refreshed: list[str] = []

    @property
    def base_scenario(self):
        return omni_module.OmniScenario.Undisturbed

    @property
    def omni_dir(self) -> str:
        return str(Path(self.wd) / "omni")

    def _refresh_catalog(self, rel_path: str | None = None) -> None:
        self.refreshed.append(str(rel_path))


def test_scenarios_report_compiles_base_and_scenario_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniArtifactExportService()
    omni = _ArtifactOmniStub(tmp_path)
    omni.scenarios = [{"type": "uniform_low"}]

    base_path = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    scenario_path = (
        tmp_path
        / omni_module.OMNI_REL_DIR
        / "scenarios"
        / "uniform_low"
        / "wepp"
        / "output"
        / "interchange"
        / "loss_pw0.out.parquet"
    )
    base_path.parent.mkdir(parents=True, exist_ok=True)
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text("", encoding="ascii")
    scenario_path.write_text("", encoding="ascii")

    read_calls: list[str] = []

    def _fake_read_parquet(path, *args, **kwargs):
        read_calls.append(str(path))
        if str(path) == str(base_path):
            return pd.DataFrame([{"key": "runoff", "v": 2.0, "units": "m^3/yr"}])
        return pd.DataFrame([{"key": "runoff", "v": 1.0, "units": "m^3/yr"}])

    written: list[str] = []
    monkeypatch.setattr(pd, "read_parquet", _fake_read_parquet)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, path, *args, **kwargs: written.append(str(path)))

    report = service.scenarios_report(omni)

    assert str(base_path) in read_calls
    assert str(scenario_path) in read_calls
    assert sorted(report["scenario"].unique().tolist()) == [
        str(omni_module.OmniScenario.Undisturbed),
        "uniform_low",
    ]
    assert written and written[0].endswith("omni/scenarios.out.parquet")
    assert omni.refreshed == ["omni/scenarios.out.parquet"]


def test_contrasts_report_computes_control_minus_contrast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniArtifactExportService()
    omni = _ArtifactOmniStub(tmp_path)
    omni.contrast_names = ["None,10__to__undisturbed"]
    omni._contrast_selection_mode = "cumulative"

    contrast_path = (
        tmp_path
        / omni_module.OMNI_REL_DIR
        / "contrasts"
        / "1"
        / "wepp"
        / "output"
        / "interchange"
        / "loss_pw0.out.parquet"
    )
    control_path = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    contrast_path.parent.mkdir(parents=True, exist_ok=True)
    control_path.parent.mkdir(parents=True, exist_ok=True)
    contrast_path.write_text("", encoding="ascii")
    control_path.write_text("", encoding="ascii")

    def _fake_read_parquet(path, *args, **kwargs):
        if str(path) == str(contrast_path):
            return pd.DataFrame([{"key": "runoff", "value": 1.0, "units": "m^3/yr"}])
        return pd.DataFrame([{"key": "runoff", "value": 3.0, "units": "m^3/yr"}])

    written: list[str] = []
    monkeypatch.setattr(pd, "read_parquet", _fake_read_parquet)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, path, *args, **kwargs: written.append(str(path)))

    report = service.contrasts_report(omni)

    assert report["contrast_topaz_id"].iloc[0] == "10"
    assert report["control-contrast_v"].iloc[0] == 2.0
    assert written and written[0].endswith("omni/contrasts.out.parquet")
    assert omni.refreshed[-1] == "omni/contrasts.out.parquet"


def test_compile_hillslope_summaries_generates_derived_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniArtifactExportService()
    omni = _ArtifactOmniStub(tmp_path)

    class RonStub:
        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.readonly = True

    ron = RonStub(str(tmp_path))
    monkeypatch.setattr("wepppy.nodb.core.Ron.getInstance", lambda wd: ron)

    class WeppStub:
        def report_loss(self):
            return {"rows": 1}

    monkeypatch.setattr("wepppy.nodb.core.Wepp.getInstance", lambda wd: WeppStub())

    class HillSummaryReportStub:
        def __init__(self, _loss) -> None:
            pass

        def to_dataframe(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {
                        "Runoff Depth (mm/yr)": 5.0,
                        "Lateral Flow Depth (mm/yr)": 1.0,
                        "Baseflow Depth (mm/yr)": 2.0,
                        "Landuse Area (ha)": 10.0,
                        "Soil Loss Density (kg/ha/yr)": 100.0,
                        "Sediment Deposition Density (kg/ha/yr)": 50.0,
                        "Sediment Yield Density (kg/ha/yr)": 40.0,
                    }
                ]
            )

    monkeypatch.setattr("wepppy.wepp.reports.HillSummaryReport", HillSummaryReportStub)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, *args, **kwargs: None)

    report = service.compile_hillslope_summaries(omni)

    assert "Runoff (m^3)" in report.columns
    assert "NTU (g/L)" in report.columns
    assert ron.readonly is True
    assert omni.refreshed[-1] == "omni/scenarios.hillslope_summaries.parquet"


def test_compile_channel_summaries_restores_readonly_and_writes_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OmniArtifactExportService()
    omni = _ArtifactOmniStub(tmp_path)

    class RonStub:
        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.readonly = True

    ron = RonStub(str(tmp_path))
    monkeypatch.setattr("wepppy.nodb.core.Ron.getInstance", lambda wd: ron)

    class WeppStub:
        def report_loss(self):
            return {"rows": 1}

    monkeypatch.setattr("wepppy.nodb.core.Wepp.getInstance", lambda wd: WeppStub())

    class ChannelSummaryReportStub:
        def __init__(self, _loss) -> None:
            pass

        def to_dataframe(self) -> pd.DataFrame:
            return pd.DataFrame([{"key": "runoff", "v": 1.0, "units": "m^3/yr"}])

    monkeypatch.setattr("wepppy.wepp.reports.ChannelSummaryReport", ChannelSummaryReportStub)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda self, *args, **kwargs: None)

    report = service.compile_channel_summaries(omni)

    assert list(report["scenario"].unique()) == [str(omni_module.OmniScenario.Undisturbed)]
    assert ron.readonly is True
    assert omni.refreshed[-1] == "omni/scenarios.channel_summaries.parquet"


def test_build_contrast_ids_geojson_stream_order_empty_fallback_without_gis_deps(
    tmp_path: Path,
) -> None:
    service = OmniArtifactExportService()
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.artifacts.geojson")
    omni._contrast_selection_mode = "stream_order"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "selection_mode": "stream_order",
                "contrast_id": 1,
                "subcatchments_group": 10,
                "n_hillslopes": 0,
                "status": "skipped",
            }
        )
        + "\n",
        encoding="ascii",
    )

    output_path = service.build_contrast_ids_geojson(omni)
    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    assert payload == {"type": "FeatureCollection", "features": []}


def test_build_contrast_ids_geojson_stream_order_rejects_invalid_group_id(
    tmp_path: Path,
) -> None:
    service = OmniArtifactExportService()
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.artifacts.geojson.invalid_group")
    omni._contrast_selection_mode = "stream_order"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "selection_mode": "stream_order",
                "contrast_id": 1,
                "subcatchments_group": "bad-group",
                "n_hillslopes": 2,
            }
        )
        + "\n",
        encoding="ascii",
    )

    with pytest.raises(ValueError, match="Invalid subcatchments_group"):
        service.build_contrast_ids_geojson(omni)


def test_build_contrast_ids_geojson_user_defined_areas_empty_fallback_without_gis_deps(
    tmp_path: Path,
) -> None:
    service = OmniArtifactExportService()
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.artifacts.geojson.user_defined")
    omni._contrast_selection_mode = "user_defined_areas"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "selection_mode": "user_defined_areas",
                "contrast_id": 1,
                "feature_index": 1,
                "status": "skipped",
                "topaz_ids": [],
                "n_hillslopes": 0,
            }
        )
        + "\n",
        encoding="ascii",
    )

    output_path = service.build_contrast_ids_geojson(omni)
    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    assert payload == {"type": "FeatureCollection", "features": []}


def _new_detached_omni(tmp_path: Path) -> omni_module.Omni:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    return omni


def test_facade_artifact_methods_delegate_to_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path)

    monkeypatch.setattr(
        omni_module._OMNI_ARTIFACT_EXPORT_SERVICE,
        "scenarios_report",
        lambda instance: pd.DataFrame([{"scenario": "s1"}]),
    )
    monkeypatch.setattr(
        omni_module._OMNI_ARTIFACT_EXPORT_SERVICE,
        "contrasts_report",
        lambda instance: pd.DataFrame([{"contrast": "c1"}]),
    )
    monkeypatch.setattr(
        omni_module._OMNI_ARTIFACT_EXPORT_SERVICE,
        "compile_hillslope_summaries",
        lambda instance: pd.DataFrame([{"Topaz ID": 20}]),
    )
    monkeypatch.setattr(
        omni_module._OMNI_ARTIFACT_EXPORT_SERVICE,
        "compile_channel_summaries",
        lambda instance: pd.DataFrame([{"Channel ID": 2}]),
    )
    monkeypatch.setattr(
        omni_module._OMNI_ARTIFACT_EXPORT_SERVICE,
        "build_contrast_ids_geojson",
        lambda instance: str(Path(instance.wd) / "omni" / "contrasts.overlay.wgs.geojson"),
    )

    assert list(omni.scenarios_report()["scenario"]) == ["s1"]
    assert list(omni.contrasts_report()["contrast"]) == ["c1"]
    assert list(omni.compile_hillslope_summaries()["Topaz ID"]) == [20]
    assert list(omni.compile_channel_summaries()["Channel ID"]) == [2]
    assert omni._build_contrast_ids_geojson().endswith("contrasts.overlay.wgs.geojson")
    assert omni._build_contrast_ids_geojson_impl().endswith("contrasts.overlay.wgs.geojson")
