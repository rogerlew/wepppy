from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from tests.eu.soils.test_esdac_disturbed_downstream import (
    _load_fixture,
    _lookup_row,
    _patch_source_provider,
)
from wepppy.eu.soils.esdac import (
    ESDAC,
    ESDACDisturbedSoilBuildError,
    ESDACSoilQualityReportError,
    load_soil_quality_report,
)
from wepppy.eu.soils.esdac.quality import (
    SoilQualityContext,
    SoilQualityDiagnostic,
)
from wepppy.nodb.mods.disturbed.disturbed import Disturbed
from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _Logger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def debug(self, *_args: object, **_kwargs: object) -> None:
        return

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return


class _Soil:
    def __init__(self, *, key: str, clay: float, sand: float, soils_dir: Path) -> None:
        self.clay = clay
        self.sand = sand
        self.fname = f"{key}.sol"
        self.desc = "EU base soil"
        self.meta_fn = None
        self.soils_dir = str(soils_dir)
        self.area = 0.0
        self.pct_coverage = 0.0


class _Soils:
    def __init__(self, *, key: str, soils_dir: Path) -> None:
        base = WeppSoilUtil(str(soils_dir / f"{key}.sol"))
        self.domsoil_d = {"101": key}
        self.soils = {
            key: _Soil(
                key=key,
                clay=base.clay,
                sand=base.sand,
                soils_dir=soils_dir,
            )
        }
        self.soils_dir = str(soils_dir)
        self.logger = _Logger()
        self.soil_source = "esdac"
        self.rosetta_wc_fc_from_disturbed_bd_override = False

    @contextmanager
    def locked(self):
        yield


class _Management:
    def __init__(self, disturbed_class: str) -> None:
        self.disturbed_class = disturbed_class
        self.sol_path = None
        self.sol_fn = ""


class _Landuse:
    def __init__(self, *, management: _Management) -> None:
        self.domlc_d = {"101": "dom-1"}
        self.domlc_mofe_d = {"101": {"1": "dom-1"}}
        self.managements = {"dom-1": management}


class _Watershed:
    def hillslope_area(self, _topaz_id: str) -> float:
        return 1.0


def _prepare_eu_run(
    monkeypatch: pytest.MonkeyPatch,
    run_dir: Path,
    *,
    case_index: int = 0,
) -> tuple[_Soils, object, dict[str, str]]:
    case = _load_fixture()["cases"][case_index]
    soils_dir = run_dir / "soils"
    _patch_source_provider(monkeypatch, case)
    key, horizon, _description = ESDAC().build_wepp_soil(
        case["provenance"]["lng"],
        case["provenance"]["lat"],
        str(soils_dir),
    )
    quality = replace(
        horizon.quality_result,
        context=SoilQualityContext(
            case["provenance"]["lng"],
            case["provenance"]["lat"],
            "101",
        ),
    )
    profile = quality.as_dict()
    profile["soil_key"] = key
    report = {
        "schema_version": 1,
        "batch_outcome": "accepted",
        "accepted_count": 1,
        "rejected_count": 0,
        "profiles": [profile],
    }
    (soils_dir / "soil_quality.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    soils = _Soils(key=key, soils_dir=soils_dir)
    texture = simple_texture(
        clay=soils.soils[key].clay,
        sand=soils.soils[key].sand,
    )
    assert texture is not None
    replacements = _lookup_row(texture, "forest low sev fire")
    return soils, quality, replacements


@pytest.mark.parametrize("case_index", (0, 2), ids=("valid-base", "degraded-base"))
def test_eu_single_ofe_gate_publishes_only_validated_artifact(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
    case_index: int,
) -> None:
    disturbed, run_dir = disturbed_factory("eu-runtime-single")
    soils, base_quality, replacements = _prepare_eu_run(
        monkeypatch,
        run_dir,
        case_index=case_index,
    )
    landuse = _Landuse(management=_Management("forest low sev fire"))

    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {(replacements["stext"], replacements["luse"]): replacements}),
    )

    report = disturbed_module._load_eu_quality_report(soils)
    disturbed_key = disturbed.modify_soil(
        "101",
        landuse,
        soils,
        disturbed.land_soil_replacements_d,
    )

    output = run_dir / "soils" / f"{disturbed_key}.sol"
    assert output.exists()
    assert not list((run_dir / "soils").glob(".*.sol"))
    parsed = WeppSoilUtil(str(output))
    assert parsed.datver == 9005.0
    assert parsed.obj["ofes"][0]["luse"] == replacements["luse"]
    assert parsed.obj["ofes"][0]["stext"] == replacements["stext"]
    assert base_quality.accepted

    assert (
        disturbed.modify_soil(
            "101",
            landuse,
            soils,
            disturbed.land_soil_replacements_d,
        )
        == disturbed_key
    )


def test_eu_mofe_gate_validates_segment_and_synthesized_artifacts(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("eu-runtime-mofe")
    disturbed._sol_ver = 9002.0
    soils, _base_quality, replacements = _prepare_eu_run(monkeypatch, run_dir)
    landuse = _Landuse(management=_Management("forest low sev fire"))

    monkeypatch.setattr(disturbed_module, "Ron", type("_Ron", (), {"getInstance": staticmethod(lambda _wd: object())}))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(lambda self: _Watershed()))
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {(replacements["stext"], replacements["luse"]): replacements}),
    )

    disturbed.modify_mofe_soils()

    output = run_dir / "soils" / "hill_101.mofe.sol"
    assert output.exists()
    assert not list((run_dir / "soils").glob(".*.sol"))
    parsed = WeppSoilUtil(str(output))
    assert parsed.datver == 9002.0
    assert parsed.obj["ofes"]


def test_rejected_eu_base_cannot_publish_single_ofe_replacement(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("eu-runtime-rejected")
    soils, quality, replacements = _prepare_eu_run(monkeypatch, run_dir)
    rejected = replace(
        quality,
        outcome="rejected",
        diagnostics=(
            SoilQualityDiagnostic(
                "source.stu.mandatory_profile_empty",
                "stu",
                "error",
            ),
        ),
    )
    report_path = run_dir / "soils" / "soil_quality.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["profiles"][0] = {
        **rejected.as_dict(),
        "soil_key": report["profiles"][0]["soil_key"],
    }
    report["accepted_count"] = 0
    report["rejected_count"] = 1
    report_path.write_text(json.dumps(report), encoding="utf-8")
    landuse = _Landuse(management=_Management("forest low sev fire"))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {(replacements["stext"], replacements["luse"]): replacements}),
    )

    with pytest.raises(ESDACDisturbedSoilBuildError) as error:
        disturbed.modify_soil(
            "101",
            landuse,
            soils,
            disturbed.land_soil_replacements_d,
            eu_quality_report=disturbed_module._load_eu_quality_report(soils),
        )

    assert "source.stu.mandatory_profile_empty" in error.value.result.reason_codes
    assert "disturbed.base.rejected" in error.value.result.reason_codes
    assert not list((run_dir / "soils").glob("*-forest low sev fire.sol"))
    assert not list((run_dir / "soils").glob(".*.sol"))


def test_marked_eu_run_requires_quality_report(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("eu-runtime-missing-report")
    soils, _quality, replacements = _prepare_eu_run(monkeypatch, run_dir)
    (run_dir / "soils" / "soil_quality.json").unlink()

    with pytest.raises(ESDACSoilQualityReportError) as error:
        disturbed_module._load_eu_quality_report(soils)

    assert error.value.code == "source.quality_report.missing"


def test_marked_eu_run_rejects_malformed_quality_report(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disturbed, run_dir = disturbed_factory("eu-runtime-malformed-report")
    soils, _quality, _replacements = _prepare_eu_run(monkeypatch, run_dir)
    report_path = run_dir / "soils" / "soil_quality.json"
    report_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ESDACSoilQualityReportError) as error:
        disturbed_module._load_eu_quality_report(soils)

    assert error.value.code == "source.quality_report.unreadable"


def test_marked_eu_run_rejects_incomplete_quality_report_before_generation(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "soil_quality.json"
    report = (report_path, {})

    with pytest.raises(ESDACSoilQualityReportError) as error:
        disturbed_module._validate_eu_quality_coverage(report, ["101", "102"])

    assert error.value.code == "source.quality_report.coverage_incomplete"


def test_marked_eu_run_rejects_quality_for_stale_base_soil_key(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("eu-runtime-stale-key")
    soils, _quality, replacements = _prepare_eu_run(monkeypatch, run_dir)
    report_path = run_dir / "soils" / "soil_quality.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["profiles"][0]["soil_key"] = "stale-base"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    landuse = _Landuse(management=_Management("forest low sev fire"))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        Disturbed,
        "land_soil_replacements_d",
        property(lambda self: {(replacements["stext"], replacements["luse"]): replacements}),
    )

    with pytest.raises(ESDACSoilQualityReportError) as error:
        disturbed.modify_soil(
            "101",
            landuse,
            soils,
            disturbed.land_soil_replacements_d,
        )

    assert error.value.code == "source.quality_report.soil_key_mismatch"


def test_mofe_runtime_wrapper_rolls_back_new_artifacts_on_failure(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("eu-runtime-mofe-rollback")
    soils_dir = run_dir / "soils"
    existing = soils_dir / "hill_101.mofe.sol"
    existing_segment = soils_dir / "segment.sol"
    existing.write_text("before", encoding="utf-8")
    existing_segment.write_text("segment-before", encoding="utf-8")
    soils = SimpleNamespace(
        soils_dir=str(soils_dir),
        domsoil_d={"101": "base"},
        soils={"base": SimpleNamespace(area=1.0, pct_coverage=100.0)},
    )
    monkeypatch.setattr(
        Disturbed,
        "soils_instance",
        property(lambda self: soils),
    )

    def _fail_after_publish(self) -> None:
        (soils_dir / "new-segment.sol").write_text("new", encoding="utf-8")
        existing.write_text("changed", encoding="utf-8")
        existing_segment.write_text("segment-changed", encoding="utf-8")
        soils.domsoil_d["101"] = "new-base"
        soils.soils["new-base"] = SimpleNamespace(area=0.0, pct_coverage=0.0)
        raise RuntimeError("synthetic MOFE failure")

    monkeypatch.setattr(Disturbed, "_modify_mofe_soils_impl", _fail_after_publish)

    with pytest.raises(RuntimeError, match="synthetic MOFE failure"):
        disturbed.modify_mofe_soils()

    assert existing.read_text(encoding="utf-8") == "before"
    assert existing_segment.read_text(encoding="utf-8") == "segment-before"
    assert not (soils_dir / "new-segment.sol").exists()
    assert soils.domsoil_d == {"101": "base"}
    assert set(soils.soils) == {"base"}
    assert soils.soils["base"].area == 1.0
    assert not list(soils_dir.glob(".disturbed-mofe-backup-*"))


def test_single_ofe_runtime_wrapper_rolls_back_batch_on_failure(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, run_dir = disturbed_factory("eu-runtime-single-rollback")
    soils_dir = run_dir / "soils"
    existing = soils_dir / "base.sol"
    existing.write_text("before", encoding="utf-8")
    soils = SimpleNamespace(
        soils_dir=str(soils_dir),
        domsoil_d={"101": "base"},
        soils={"base": SimpleNamespace(area=1.0, pct_coverage=100.0)},
    )
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))

    def _fail_after_publish(self) -> None:
        (soils_dir / "derived.sol").write_text("new", encoding="utf-8")
        existing.write_text("changed", encoding="utf-8")
        soils.domsoil_d["101"] = "derived"
        soils.soils["derived"] = SimpleNamespace(area=0.0, pct_coverage=0.0)
        raise RuntimeError("synthetic single-OFE failure")

    monkeypatch.setattr(Disturbed, "_modify_soils_impl", _fail_after_publish)

    with pytest.raises(RuntimeError, match="synthetic single-OFE failure"):
        disturbed.modify_soils()

    assert existing.read_text(encoding="utf-8") == "before"
    assert not (soils_dir / "derived.sol").exists()
    assert soils.domsoil_d == {"101": "base"}
    assert set(soils.soils) == {"base"}
    assert soils.soils["base"].area == 1.0
    assert not list(soils_dir.glob(".disturbed-single-backup-*"))


def test_quality_report_round_trip_accepts_empty_profiles(tmp_path: Path) -> None:
    report_path = tmp_path / "soil_quality.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "batch_outcome": "accepted",
                "accepted_count": 0,
                "rejected_count": 0,
                "profiles": [],
            }
        ),
        encoding="utf-8",
    )

    assert load_soil_quality_report(report_path) == {}


def test_quality_report_rejects_degraded_profile_without_diagnostics(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "soil_quality.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "batch_outcome": "accepted",
                "accepted_count": 1,
                "rejected_count": 0,
                "profiles": [
                    {
                        "topaz_id": "101",
                        "soil_key": "base",
                        "outcome": "degraded",
                        "longitude": -6.3,
                        "latitude": 43.1,
                        "diagnostics": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ESDACSoilQualityReportError) as error:
        load_soil_quality_report(report_path)

    assert error.value.code == "source.quality_report.outcome_mismatch"


def test_quality_report_rejects_inconsistent_profile_counts(tmp_path: Path) -> None:
    report_path = tmp_path / "soil_quality.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "batch_outcome": "accepted",
                "accepted_count": 2,
                "rejected_count": 0,
                "profiles": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ESDACSoilQualityReportError) as error:
        load_soil_quality_report(report_path)

    assert error.value.code == "source.quality_report.counts_mismatch"


def test_quality_report_rejects_missing_diagnostics_field(tmp_path: Path) -> None:
    report_path = tmp_path / "soil_quality.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "batch_outcome": "accepted",
                "accepted_count": 1,
                "rejected_count": 0,
                "profiles": [
                    {
                        "topaz_id": "101",
                        "soil_key": "base",
                        "outcome": "valid",
                        "longitude": -6.3,
                        "latitude": 43.1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ESDACSoilQualityReportError) as error:
        load_soil_quality_report(report_path)

    assert error.value.code == "source.quality_report.diagnostics_malformed"


def test_quality_report_rejects_boolean_schema_version(tmp_path: Path) -> None:
    report_path = tmp_path / "soil_quality.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": True,
                "batch_outcome": "accepted",
                "accepted_count": 0,
                "rejected_count": 0,
                "profiles": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ESDACSoilQualityReportError) as error:
        load_soil_quality_report(report_path)

    assert error.value.code == "source.quality_report.schema_invalid"
