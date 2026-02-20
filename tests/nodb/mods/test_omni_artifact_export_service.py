from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.nodb.mods.omni.omni_artifact_export_service import OmniArtifactExportService

pytestmark = pytest.mark.unit


class _DummyOmni:
    def _build_contrast_ids_geojson_impl(self):
        return "geojson-path"

    def _scenarios_report_impl(self):
        return pd.DataFrame([{"scenario": "undisturbed", "key": "runoff", "v": 1.0}])

    def _contrasts_report_impl(self):
        return pd.DataFrame([{"contrast": "c1", "key": "runoff", "v": 2.0}])

    def _compile_hillslope_summaries_impl(self):
        return pd.DataFrame([{"scenario": "undisturbed", "Topaz ID": 10}])

    def _compile_channel_summaries_impl(self):
        return pd.DataFrame([{"scenario": "undisturbed", "Channel ID": 1}])


def test_compile_artifact_export_service_routes_to_impl_methods() -> None:
    service = OmniArtifactExportService()
    omni = _DummyOmni()

    assert service.build_contrast_ids_geojson(omni) == "geojson-path"
    assert list(service.scenarios_report(omni)["scenario"]) == ["undisturbed"]
    assert list(service.contrasts_report(omni)["contrast"]) == ["c1"]
    assert list(service.compile_hillslope_summaries(omni)["Topaz ID"]) == [10]
    assert list(service.compile_channel_summaries(omni)["Channel ID"]) == [1]


def _new_detached_omni(tmp_path: Path) -> omni_module.Omni:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    return omni


def test_compile_facade_artifact_methods_delegate_to_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    omni = _new_detached_omni(tmp_path)

    monkeypatch.setattr(
        omni_module._OMNI_ARTIFACT_EXPORT_SERVICE,
        "build_contrast_ids_geojson",
        lambda instance: "delegated-geojson",
    )
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

    assert omni._build_contrast_ids_geojson() == "delegated-geojson"
    assert list(omni.scenarios_report()["scenario"]) == ["s1"]
    assert list(omni.contrasts_report()["contrast"]) == ["c1"]
    assert list(omni.compile_hillslope_summaries()["Topaz ID"]) == [20]
    assert list(omni.compile_channel_summaries()["Channel ID"]) == [2]
