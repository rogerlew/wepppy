"""Helpers that dispatch EU ESDAC-based soil builds via multiprocessing."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
import json
from multiprocessing import Pool
from pathlib import Path
import tempfile
from typing import Any

from wepppy.eu.soils.esdac import ESDAC
from wepppy.eu.soils.esdac.esdac import Horizon
from wepppy.eu.soils.esdac.quality import (
    ESDACSoilBuildError,
    SoilQualityContext,
    SoilQualityDiagnostic,
    SoilQualityResult,
)
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.soils.ssurgo import SoilSummary

# ESDAC builds are embarrassingly parallel, so the worker pool defaults to an
# aggressive size to keep runtimes down for large watersheds.
NCPU = 32


@dataclass(frozen=True, slots=True)
class SoilBuildWorkerResult:
    """Structured result from one ESDAC worker invocation."""

    topaz_id: str | int
    key: str | None
    horizon: Horizon | None
    description: str | None
    quality: SoilQualityResult


class ESDACSoilBatchError(RuntimeError):
    """Raised when one or more locations are rejected before commit."""

    def __init__(
        self,
        rejected: Sequence[SoilBuildWorkerResult],
        report_path: Path,
    ) -> None:
        self.rejected = tuple(rejected)
        self.report_path = report_path
        locations = ", ".join(str(result.topaz_id) for result in self.rejected)
        super().__init__(
            f"ESDAC soil batch rejected {len(self.rejected)} location(s): {locations}"
        )


def _build_esdac_soil(kwargs: dict[str, Any]) -> SoilBuildWorkerResult:
    """Invoke :meth:`ESDAC.build_wepp_soil` for a single hillslope.

    Args:
        kwargs: Dictionary produced by :func:`build_esdac_soils` that carries
            the TopoAZ identifier, centroid, and build settings.

    Returns:
        A typed result carrying the legacy builder tuple fields plus quality
        diagnostics for the parent batch coordinator.
    """
    topaz_id = kwargs["topaz_id"]
    lng = kwargs["lng"]
    lat = kwargs["lat"]
    soils_dir = kwargs["soils_dir"]
    res_lyr_ksat_threshold = kwargs["res_lyr_ksat_threshold"]
    status_channel = kwargs["status_channel"]

    esd = ESDAC()
    context = SoilQualityContext(longitude=lng, latitude=lat, topaz_id=topaz_id)
    try:
        key, horizon, desc = esd.build_wepp_soil(
            lng, lat, soils_dir, res_lyr_ksat_threshold
        )
    except ESDACSoilBuildError as exc:
        quality = replace(exc.result, context=context)
        result = SoilBuildWorkerResult(topaz_id, None, None, None, quality)
        if status_channel is not None:
            StatusMessenger.publish(
                status_channel,
                f"_build_esdac_soil({topaz_id}) -> rejected: {quality.reason_codes}",
            )
        return result

    quality = getattr(horizon, "quality_result", None)
    if not isinstance(quality, SoilQualityResult):
        raise RuntimeError(
            "ESDAC.build_wepp_soil returned no SoilQualityResult on its horizon"
        )
    quality = replace(quality, context=context)
    result = SoilBuildWorkerResult(topaz_id, key, horizon, desc, quality)
    if status_channel is not None:
        StatusMessenger.publish(
            status_channel,
            f"_build_esdac_soil({topaz_id}) -> {key}, {desc}; "
            f"quality={quality.outcome}, reasons={quality.reason_codes}",
        )

    return result


def _write_quality_report(
    report_path: Path,
    results: Sequence[SoilBuildWorkerResult],
    *,
    batch_outcome: str,
) -> None:
    """Atomically persist additive per-location quality evidence."""
    entries: list[dict[str, object]] = []
    for result in results:
        entry = result.quality.as_dict()
        entry["soil_key"] = result.key
        entries.append(entry)

    payload = {
        "schema_version": 1,
        "batch_outcome": batch_outcome,
        "accepted_count": sum(result.quality.accepted for result in results),
        "rejected_count": sum(
            result.quality.outcome == "rejected" for result in results
        ),
        "profiles": entries,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = report_path.with_name(f".{report_path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(report_path)


def _mark_batch_conflict(
    result: SoilBuildWorkerResult,
    *,
    code: str,
    field: str,
    raw_value: object,
) -> SoilBuildWorkerResult:
    """Turn a pre-commit collision into a location-scoped rejection."""
    diagnostic = SoilQualityDiagnostic(
        code=code,
        field=field,
        severity="error",
        raw_value=raw_value,
    )
    quality = replace(
        result.quality,
        outcome="rejected",
        diagnostics=result.quality.diagnostics + (diagnostic,),
    )
    return replace(result, key=None, description=None, quality=quality)


def _raise_batch_conflict(
    results: Sequence[SoilBuildWorkerResult],
    indexes: Sequence[int],
    report_path: Path,
    *,
    code: str,
    field: str,
    raw_value: object,
) -> None:
    updated_results = list(results)
    for index in indexes:
        updated_results[index] = _mark_batch_conflict(
            updated_results[index],
            code=code,
            field=field,
            raw_value=raw_value,
        )
    _write_quality_report(
        report_path,
        updated_results,
        batch_outcome="rejected",
    )
    raise ESDACSoilBatchError(
        [updated_results[index] for index in indexes],
        report_path,
    )


def build_esdac_soils(
    orders: Sequence[tuple[int | str, tuple[float, float]]],
    soils_dir: str,
    res_lyr_ksat_threshold: float = 2.0,
    status_channel: str | None = None,
) -> tuple[dict[str, SoilSummary], dict[str, str]]:
    """Build WEPP-ready soils for a collection of hillslopes.

    Args:
        orders: Sequence of ``(topaz_id, (longitude, latitude))`` tuples that
            describe the hillslope centroids to process.
        soils_dir: Output directory where generated ``.sol`` files live.
        res_lyr_ksat_threshold: Hydraulic conductivity threshold that signals a
            restrictive layer.
        status_channel: Optional Redis pub/sub channel for progress updates.

    Returns:
        A tuple containing:
            * Mapping of soil key → :class:`~wepppy.soils.ssurgo.SoilSummary`.
            * Mapping of TopoAZ hillslope id → soil key (dominant soil).

    Raises:
        ESDACSoilBatchError: If any location is rejected or a batch collision
            prevents a safe output commit. The final directory receives a
            ``soil_quality.json`` report with location-scoped diagnostics.
    """
    final_dir = Path(soils_dir)
    final_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        dir=final_dir, prefix=".esdac-build-"
    ) as staging_dir:
        args: list[dict[str, Any]] = []
        for index, (topaz_id, (lng, lat)) in enumerate(orders):
            worker_dir = Path(staging_dir) / str(index)
            worker_dir.mkdir()
            args.append(
                dict(
                    topaz_id=topaz_id,
                    lng=lng,
                    lat=lat,
                    soils_dir=str(worker_dir),
                    res_lyr_ksat_threshold=res_lyr_ksat_threshold,
                    status_channel=status_channel,
                )
            )

        with Pool(processes=NCPU) as pool:
            results = pool.map(_build_esdac_soil, args)

        rejected = [result for result in results if not result.quality.accepted]
        report_path = final_dir / "soil_quality.json"
        if rejected:
            _write_quality_report(
                report_path,
                results,
                batch_outcome="rejected",
            )
            raise ESDACSoilBatchError(rejected, report_path)

        staged_report_path = Path(staging_dir) / "soil_quality.json"
        _write_quality_report(
            staged_report_path,
            results,
            batch_outcome="accepted",
        )

        move_plan: dict[str, Path] = {}
        key_indexes: dict[str, list[int]] = {}
        for index, result in enumerate(results):
            if result.key is None or result.description is None:
                raise RuntimeError(
                    f"accepted ESDAC result for TopoAZ {result.topaz_id!r} "
                    "is missing its soil key or description"
                )
            key_str = str(result.key)
            key_indexes.setdefault(key_str, []).append(index)
            source_path = Path(staging_dir) / str(index) / f"{key_str}.sol"
            if key_str in move_plan:
                if source_path.read_bytes() != move_plan[key_str].read_bytes():
                    _raise_batch_conflict(
                        results,
                        key_indexes[key_str],
                        report_path,
                        code="batch.duplicate_soil_key",
                        field="soil_key",
                        raw_value=key_str,
                    )
            else:
                move_plan[key_str] = source_path

        for key_str, source_path in move_plan.items():
            target_path = final_dir / f"{key_str}.sol"
            if target_path.exists() and target_path.read_bytes() != source_path.read_bytes():
                _raise_batch_conflict(
                    results,
                    key_indexes[key_str],
                    report_path,
                    code="batch.existing_soil_key_conflict",
                    field="soil_key",
                    raw_value=key_str,
                )

        previous_report = report_path.read_bytes() if report_path.exists() else None
        created_targets: list[Path] = []
        report_committed = False
        try:
            for key_str, source_path in move_plan.items():
                target_path = final_dir / f"{key_str}.sol"
                if target_path.exists():
                    continue
                source_path.replace(target_path)
                created_targets.append(target_path)

            staged_report_path.replace(report_path)
            report_committed = True
        except OSError:
            for target_path in created_targets:
                target_path.unlink(missing_ok=True)
            if report_committed:
                if previous_report is None:
                    report_path.unlink(missing_ok=True)
                else:
                    report_path.write_bytes(previous_report)
            raise

    soils: dict[str, SoilSummary] = {}
    domsoil_d: dict[str, str] = {}
    for result in results:
        topaz_id = result.topaz_id
        key = result.key
        desc = result.description
        if key is None or desc is None:
            raise RuntimeError(
                f"accepted ESDAC result for TopoAZ {topaz_id!r} "
                "is missing its soil key or description"
            )
        topaz_str = str(topaz_id)
        key_str = str(key)
        if key_str not in soils:
            fname = f"{key_str}.sol"
            soils[key_str] = SoilSummary(
                mukey=key_str,
                fname=fname,
                soils_dir=soils_dir,
                build_date=str(datetime.now),
                desc=desc,
            )
        domsoil_d[topaz_str] = key_str

    return soils, domsoil_d
