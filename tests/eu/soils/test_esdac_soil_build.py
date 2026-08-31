from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
import redis

from wepppy.eu.soils import soil_build
from wepppy.eu.soils.esdac.quality import (
    ESDACSoilBuildError,
    SoilQualityContext,
    SoilQualityDiagnostic,
    SoilQualityResult,
)


pytestmark = pytest.mark.unit


class _InlinePool:
    def __init__(self, **_kwargs) -> None:
        pass

    def __enter__(self) -> "_InlinePool":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def map(self, function, values):
        return [function(value) for value in values]


def _quality(
    topaz_id: int,
    *,
    outcome: str = "valid",
    diagnostic: SoilQualityDiagnostic | None = None,
) -> SoilQualityResult:
    diagnostics: tuple[SoilQualityDiagnostic, ...] = ()
    if diagnostic is not None:
        diagnostics = (diagnostic,)
    elif outcome == "degraded":
        diagnostics = (
            SoilQualityDiagnostic(
                "source.usedom.no_information",
                "usedom",
                "warning",
                raw_value="0",
            ),
        )
    return SoilQualityResult(
        SoilQualityContext(-6.3, 43.1, topaz_id),
        outcome,
        diagnostics,
    )


def _worker_args(tmp_path: Path, topaz_id: int = 50) -> dict[str, object]:
    return {
        "topaz_id": topaz_id,
        "lng": -6.3,
        "lat": 43.1,
        "soils_dir": str(tmp_path),
        "res_lyr_ksat_threshold": 2.0,
        "status_channel": None,
    }


def test_worker_converts_expected_rejection_to_structured_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    rejected = _quality(50, outcome="rejected")

    class _RejectedESDAC:
        def build_wepp_soil(self, *_args):
            raise ESDACSoilBuildError(rejected)

    monkeypatch.setattr(soil_build, "ESDAC", _RejectedESDAC)

    result = soil_build._build_esdac_soil(_worker_args(tmp_path))

    assert result.topaz_id == 50
    assert result.key is None
    assert result.horizon is None
    assert result.quality.outcome == "rejected"
    assert result.quality.context.topaz_id == 50


def test_batch_commits_staged_outputs_and_quality_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _AcceptedESDAC:
        def build_wepp_soil(self, _lng, _lat, soils_dir, _threshold):
            topaz_id = int(Path(soils_dir).name) + 1
            key = f"soil-{topaz_id}"
            Path(soils_dir, f"{key}.sol").write_text("soil")
            return (
                key,
                SimpleNamespace(
                    quality_result=_quality(
                        topaz_id,
                        outcome="degraded" if topaz_id == 2 else "valid",
                    )
                ),
                f"description-{topaz_id}",
            )

    monkeypatch.setattr(soil_build, "Pool", _InlinePool)
    monkeypatch.setattr(soil_build, "ESDAC", _AcceptedESDAC)

    soils, dominant = soil_build.build_esdac_soils(
        [(1, (-6.3, 43.1)), (2, (-6.4, 43.2))],
        str(tmp_path),
    )

    assert set(soils) == {"soil-1", "soil-2"}
    assert dominant == {"1": "soil-1", "2": "soil-2"}
    assert (tmp_path / "soil-1.sol").exists()
    assert (tmp_path / "soil-2.sol").exists()
    report = json.loads((tmp_path / "soil_quality.json").read_text())
    assert report["batch_outcome"] == "accepted"
    assert report["accepted_count"] == 2
    assert report["rejected_count"] == 0
    assert [entry["outcome"] for entry in report["profiles"]] == [
        "valid",
        "degraded",
    ]
    assert not list(tmp_path.glob(".esdac-build-*"))


def test_batch_rejects_divergent_duplicate_soil_keys_before_commit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_worker(kwargs: dict[str, object]) -> soil_build.SoilBuildWorkerResult:
        topaz_id = int(kwargs["topaz_id"])
        key = "shared-key"
        Path(str(kwargs["soils_dir"]), f"{key}.sol").write_text(
            f"soil-{topaz_id}"
        )
        return soil_build.SoilBuildWorkerResult(
            topaz_id,
            key,
            None,
            f"description-{topaz_id}",
            _quality(topaz_id),
        )

    monkeypatch.setattr(soil_build, "Pool", _InlinePool)
    monkeypatch.setattr(soil_build, "_build_esdac_soil", fake_worker)

    with pytest.raises(soil_build.ESDACSoilBatchError) as error:
        soil_build.build_esdac_soils(
            [(1, (-6.3, 43.1)), (2, (-6.4, 43.2))],
            str(tmp_path),
        )

    assert [result.topaz_id for result in error.value.rejected] == [1, 2]
    assert not (tmp_path / "shared-key.sol").exists()
    report = json.loads((tmp_path / "soil_quality.json").read_text())
    assert report["batch_outcome"] == "rejected"
    assert report["rejected_count"] == 2
    assert all(
        entry["reason_codes"] == ["batch.duplicate_soil_key"]
        for entry in report["profiles"]
    )


def test_rejected_batch_discards_staged_outputs_and_writes_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_worker(kwargs: dict[str, object]) -> soil_build.SoilBuildWorkerResult:
        topaz_id = int(kwargs["topaz_id"])
        key = f"soil-{topaz_id}"
        Path(str(kwargs["soils_dir"]), f"{key}.sol").write_text("staged")
        outcome = "rejected" if topaz_id == 2 else "valid"
        diagnostic = (
            SoilQualityDiagnostic(
                "source.categorical.empty",
                "fao90lev1",
                "error",
                raw_value=["24", "", "No information"],
            )
            if outcome == "rejected"
            else None
        )
        return soil_build.SoilBuildWorkerResult(
            topaz_id,
            None if outcome == "rejected" else key,
            None,
            None if outcome == "rejected" else f"description-{topaz_id}",
            _quality(topaz_id, outcome=outcome, diagnostic=diagnostic),
        )

    monkeypatch.setattr(soil_build, "Pool", _InlinePool)
    monkeypatch.setattr(soil_build, "_build_esdac_soil", fake_worker)

    with pytest.raises(soil_build.ESDACSoilBatchError) as error:
        soil_build.build_esdac_soils(
            [(1, (-6.3, 43.1)), (2, (-6.4, 43.2))],
            str(tmp_path),
        )

    assert [result.topaz_id for result in error.value.rejected] == [2]
    assert error.value.report_path == tmp_path / "soil_quality.json"
    assert str(error.value) == (
        "ESDAC soil batch rejected 1 location(s) (TopoAZ: 2); reasons: "
        "source.categorical.empty[field=fao90lev1, count=1, "
        'raw_value=["24","","No information"]]; report: soil_quality.json'
    )
    assert not list(tmp_path.glob("*.sol"))
    report = json.loads((tmp_path / "soil_quality.json").read_text())
    assert report["batch_outcome"] == "rejected"
    assert report["accepted_count"] == 1
    assert report["rejected_count"] == 1
    assert [entry["topaz_id"] for entry in report["profiles"]] == [1, 2]
    assert not list(tmp_path.glob(".esdac-build-*"))


def test_batch_error_summary_is_grouped_bounded_and_published(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    published: list[tuple[str, str]] = []

    def fake_worker(kwargs: dict[str, object]) -> soil_build.SoilBuildWorkerResult:
        topaz_id = int(kwargs["topaz_id"])
        diagnostic = SoilQualityDiagnostic(
            "source.categorical.empty",
            "fao90lev1",
            "error",
            raw_value=["24", "", "No information"],
        )
        return soil_build.SoilBuildWorkerResult(
            topaz_id,
            None,
            None,
            None,
            _quality(topaz_id, outcome="rejected", diagnostic=diagnostic),
        )

    monkeypatch.setattr(soil_build, "Pool", _InlinePool)
    monkeypatch.setattr(soil_build, "_build_esdac_soil", fake_worker)
    monkeypatch.setattr(
        soil_build.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    orders = [(topaz_id, (-6.3, 43.1)) for topaz_id in range(1, 13)]
    with caplog.at_level(logging.ERROR, logger=soil_build.__name__):
        with pytest.raises(soil_build.ESDACSoilBatchError) as error:
            soil_build.build_esdac_soils(
                orders,
                str(tmp_path),
                status_channel="run:status",
            )

    message = str(error.value)
    assert "TopoAZ: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, +2 more" in message
    assert "source.categorical.empty[field=fao90lev1, count=12" in message
    assert "report: soil_quality.json" in message
    assert published == [("run:status", message)]
    assert message in caplog.messages


def test_batch_error_summary_bounds_raw_value_and_reason_groups(
    tmp_path: Path,
) -> None:
    rejected = []
    for topaz_id in range(1, 8):
        diagnostic = SoilQualityDiagnostic(
            f"source.failure.{topaz_id}",
            "source_field",
            "error",
            raw_value="x" * 500,
        )
        rejected.append(
            soil_build.SoilBuildWorkerResult(
                topaz_id,
                None,
                None,
                None,
                _quality(
                    topaz_id,
                    outcome="rejected",
                    diagnostic=diagnostic,
                ),
            )
        )

    message = str(
        soil_build.ESDACSoilBatchError(
            rejected,
            tmp_path / "soil_quality.json",
        )
    )

    assert "source.failure.1" in message
    assert "source.failure.5" in message
    assert "source.failure.6" not in message
    assert "+2 more reason(s)" in message
    assert 'raw_value="' + "x" * 159 + "..." in message
    assert "..." in message
    assert len(message) < 1_500


def test_batch_error_groups_errors_by_code_and_field_only(tmp_path: Path) -> None:
    warning = SoilQualityDiagnostic(
        "source.optional.warning",
        "usedom",
        "warning",
        raw_value="warning",
    )
    rejected = []
    for topaz_id, raw_value in ((1, "z-value"), (2, "a-value")):
        error = SoilQualityDiagnostic(
            "source.categorical.empty",
            "fao90lev1",
            "error",
            raw_value=raw_value,
        )
        quality = SoilQualityResult(
            SoilQualityContext(-6.3, 43.1, topaz_id),
            "rejected",
            (warning, error),
        )
        rejected.append(
            soil_build.SoilBuildWorkerResult(
                topaz_id,
                None,
                None,
                None,
                quality,
            )
        )

    message = str(
        soil_build.ESDACSoilBatchError(
            rejected,
            tmp_path / "soil_quality.json",
        )
    )

    assert "source.categorical.empty[field=fao90lev1, count=2" in message
    assert 'raw_value="a-value"' in message
    assert "z-value" not in message
    assert "source.optional.warning" not in message


def test_status_publish_failure_does_not_mask_batch_error(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    diagnostic = SoilQualityDiagnostic(
        "source.categorical.empty",
        "fao90lev1",
        "error",
        raw_value=["24", "", "No information"],
    )
    rejected = [
        soil_build.SoilBuildWorkerResult(
            73,
            None,
            None,
            None,
            _quality(73, outcome="rejected", diagnostic=diagnostic),
        )
    ]

    def fail_publish(_channel: str, _message: str) -> None:
        raise redis.RedisError("status unavailable")

    monkeypatch.setattr(soil_build.StatusMessenger, "publish", fail_publish)

    with caplog.at_level(logging.ERROR, logger=soil_build.__name__):
        with pytest.raises(soil_build.ESDACSoilBatchError) as error:
            soil_build._raise_batch_error(
                rejected,
                tmp_path / "soil_quality.json",
                status_channel="run:status",
            )

    assert "source.categorical.empty[field=fao90lev1, count=1" in str(error.value)
    assert any(
        "Failed to publish ESDAC batch diagnostic" in message
        for message in caplog.messages
    )
