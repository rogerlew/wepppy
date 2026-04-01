#!/usr/bin/env python3
"""Execute the features-export live-run matrix with gate enforcement and audits."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import re
import tempfile
import traceback
from typing import Any
import zipfile

import geopandas as gpd
import pandas as pd

from wepppy.nodb.mods.features_export.contracts import FeaturesExportValidationError
from wepppy.nodb.mods.features_export.service import FeaturesExportServiceError, execute_features_export
from wepppy.nodb.mods.disturbed.disturbed import Disturbed

SPATIAL_FORMATS = ("geojson", "geoparquet", "kmz", "geopackage", "geodatabase")
TABULAR_FORMATS = ("parquet", "csv")
ALL_FORMATS = (*SPATIAL_FORMATS, *TABULAR_FORMATS)
UNIT_MODES = ("project", "si", "english")
CRS_MODES = ("wgs", "utm")
REQUIRED_BUNDLE_MEMBERS = (
    "manifest.json",
    "README.md",
)
PAYLOAD_EXTENSIONS = (
    ".geojson",
    ".geoparquet",
    ".parquet",
    ".csv",
    ".kmz",
    ".gpkg",
    ".gdb.zip",
)
YEAR_WIDE_RE = re.compile(r"_yr\d{4}$")
DATE_WIDE_RE = re.compile(r"_\d{4}_\d{2}_\d{2}$")
PHASE1_PLAN = "phase1"
PHASE2_OMNI_PLAN = "phase2_omni"
ASH_WATAR_LAYER_ID = "ash.transport.hillslope_annuals"
DISTURBED_LOOKUP_VARIANTS = ("base", "extended")
DISTURBED_BD_MODES = ("blank", "numeric")


@dataclass(frozen=True)
class MatrixCase:
    case_id: str
    gate: str
    group: str
    description: str
    payload: dict[str, Any]
    expect_success: bool = True
    expected_status: int | None = None
    expected_code: str | None = None
    expect_cache_hit: bool | None = None
    reference_case_id: str | None = None
    lookup_variant: str | None = None
    bd_mode: str | None = None


@dataclass(frozen=True)
class DisturbedLookupSnapshot:
    active_lookup_variant: str
    base_exists: bool
    base_bytes: bytes | None
    extended_exists: bool
    extended_bytes: bytes | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_id(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    token = str(value).strip()
    if not token:
        return None
    if token.isdigit():
        return str(int(token))
    try:
        parsed = float(token)
    except ValueError:
        return token
    if parsed.is_integer():
        return str(int(parsed))
    return token


def _load_oracle_domains(wd: Path) -> tuple[set[str], set[str]]:
    topaz_ids: set[str] = set()
    wepp_ids: set[str] = set()
    for relpath in ("watershed/hillslopes.parquet", "watershed/channels.parquet"):
        path = wd / relpath
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        for candidate in ("topaz_id", "TopazID"):
            if candidate in frame.columns:
                for value in frame[candidate].tolist():
                    token = _canonical_id(value)
                    if token is not None:
                        topaz_ids.add(token)
        for candidate in ("wepp_id", "WeppID"):
            if candidate in frame.columns:
                for value in frame[candidate].tolist():
                    token = _canonical_id(value)
                    if token is not None:
                        wepp_ids.add(token)
    return topaz_ids, wepp_ids


def _has_ash_watar_assets(wd: Path) -> bool:
    required_relpaths = (
        "ash/post/hillslope_annuals.parquet",
        "ash/post/ashpost_version.json",
        "ash.nodb",
    )
    return all((wd / relpath).is_file() for relpath in required_relpaths)


def _payload(
    *,
    format_token: str,
    layers: list[str],
    units: str = "si",
    crs: str = "wgs",
    output_scopes: list[str] | None = None,
    temporal: dict[str, Any] | None = None,
    tabular: dict[str, Any] | None = None,
    scenarios: list[str] | None = None,
    contrast_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format": format_token,
        "layers": layers,
        "units": units,
        "crs": crs,
        "output_scopes": output_scopes or ["baseline"],
    }
    if temporal is not None:
        payload["temporal"] = temporal
    if tabular is not None:
        payload["tabular"] = tabular
    if scenarios:
        payload["scenarios"] = scenarios
    if contrast_ids:
        payload["contrast_ids"] = contrast_ids
    return payload


def _read_lookup_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def _write_lookup_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _set_lookup_bd_mode(lookup_csv: Path, bd_mode: str) -> dict[str, str]:
    if bd_mode not in DISTURBED_BD_MODES:
        raise ValueError(f"Unsupported bd_mode {bd_mode!r}; expected one of {DISTURBED_BD_MODES}.")

    fieldnames, rows = _read_lookup_csv(lookup_csv)
    if "bd" not in fieldnames:
        raise ValueError(f"Lookup file {lookup_csv} does not contain required 'bd' column.")
    if not rows:
        raise ValueError(f"Lookup file {lookup_csv} has no rows.")

    target_row: dict[str, str] | None = None
    for row in rows:
        if str(row.get("luse", "")).strip() == "forest moderate sev fire" and str(row.get("stext", "")).strip() == "loam":
            target_row = row
            break
    if target_row is None:
        target_row = rows[0]

    target_row["bd"] = "" if bd_mode == "blank" else "1.6"
    _write_lookup_csv(lookup_csv, fieldnames, rows)
    return {
        "target_luse": str(target_row.get("luse", "")),
        "target_stext": str(target_row.get("stext", "")),
        "bd_value": str(target_row.get("bd", "")),
    }


def _capture_disturbed_lookup_snapshot(wd: Path) -> DisturbedLookupSnapshot:
    disturbed = Disturbed.getInstance(str(wd))
    base_lookup = Path(disturbed.lookup_fn)
    extended_lookup = Path(disturbed.extended_lookup_fn)

    return DisturbedLookupSnapshot(
        active_lookup_variant=disturbed.active_lookup_variant,
        base_exists=base_lookup.exists(),
        base_bytes=base_lookup.read_bytes() if base_lookup.exists() else None,
        extended_exists=extended_lookup.exists(),
        extended_bytes=extended_lookup.read_bytes() if extended_lookup.exists() else None,
    )


def _restore_disturbed_lookup_snapshot(wd: Path, snapshot: DisturbedLookupSnapshot) -> None:
    disturbed = Disturbed.getInstance(str(wd))
    base_lookup = Path(disturbed.lookup_fn)
    extended_lookup = Path(disturbed.extended_lookup_fn)

    if snapshot.base_exists:
        assert snapshot.base_bytes is not None
        base_lookup.write_bytes(snapshot.base_bytes)
    elif base_lookup.exists():
        base_lookup.unlink()

    if snapshot.extended_exists:
        assert snapshot.extended_bytes is not None
        extended_lookup.write_bytes(snapshot.extended_bytes)
    elif extended_lookup.exists():
        extended_lookup.unlink()

    disturbed.active_lookup_variant = snapshot.active_lookup_variant


def _apply_disturbed_bd_precondition(
    *,
    wd: Path,
    lookup_variant: str,
    bd_mode: str,
) -> dict[str, str]:
    if lookup_variant not in DISTURBED_LOOKUP_VARIANTS:
        raise ValueError(
            f"Unsupported lookup_variant {lookup_variant!r}; expected one of {DISTURBED_LOOKUP_VARIANTS}."
        )

    disturbed = Disturbed.getInstance(str(wd))
    disturbed.ensure_land_soil_lookup_schema()

    if lookup_variant == "extended":
        if not Path(disturbed.extended_lookup_fn).exists():
            disturbed.build_extended_land_soil_lookup()
        target_lookup = Path(disturbed.extended_lookup_fn)
    else:
        target_lookup = Path(disturbed.lookup_fn)

    bd_target = _set_lookup_bd_mode(target_lookup, bd_mode)
    disturbed.active_lookup_variant = lookup_variant

    return {
        "lookup_variant": lookup_variant,
        "lookup_path": str(target_lookup),
        "bd_mode": bd_mode,
        **bd_target,
    }


def build_gate1_cases() -> list[MatrixCase]:
    cases: list[MatrixCase] = []
    for format_token in ALL_FORMATS:
        layers = ["watershed.subcatchments"] if format_token in SPATIAL_FORMATS else ["wepp.summary.hillslopes"]
        cases.append(
            MatrixCase(
                case_id=f"gate1_success_{format_token}",
                gate="gate1",
                group="gate1_success",
                description=f"Sentinel success for {format_token}",
                payload=_payload(
                    format_token=format_token,
                    layers=layers,
                    units="si",
                    crs="wgs",
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"}
                    if format_token in TABULAR_FORMATS
                    else None,
                ),
                expect_success=True,
            )
        )

    cases.extend(
        [
            MatrixCase(
                case_id="gate1_neg_mixed_long_event_yearly",
                gate="gate1",
                group="gate1_negative",
                description="Mixed event+yearly long layout rejects.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.interchange.loss_all_years_hill", "wepp.temporal.events"],
                    temporal={
                        "layer_modes": {
                            "wepp.interchange.loss_all_years_hill": "yearly",
                            "wepp.temporal.events": "event",
                        },
                        "event": {"selector": "date", "dates": ["2000-01-03"]},
                    },
                    tabular={"temporal_layout": "long"},
                ),
                expect_success=False,
                expected_status=400,
                expected_code="mixed_temporal_modes",
            ),
            MatrixCase(
                case_id="gate1_neg_missing_event_payload",
                gate="gate1",
                group="gate1_negative",
                description="Event mode without temporal.event rejects.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.temporal.events"],
                    temporal={"mode": "event"},
                ),
                expect_success=False,
                expected_status=400,
                expected_code="missing_field",
            ),
            MatrixCase(
                case_id="gate1_neg_invalid_tabular_object",
                gate="gate1",
                group="gate1_negative",
                description="tabular must be an object.",
                payload={
                    "format": "parquet",
                    "layers": ["wepp.summary.hillslopes"],
                    "units": "si",
                    "crs": "wgs",
                    "output_scopes": ["baseline"],
                    "tabular": "invalid-shape",
                },
                expect_success=False,
                expected_status=400,
                expected_code="invalid_type",
            ),
        ]
    )
    return cases


def build_gate2_cases(*, include_ash_watar: bool = False) -> list[MatrixCase]:
    cases: list[MatrixCase] = []

    for format_token in SPATIAL_FORMATS:
        for crs in CRS_MODES:
            for units in UNIT_MODES:
                cases.append(
                    MatrixCase(
                        case_id=f"a1_{format_token}_{crs}_{units}",
                        gate="gate2",
                        group="A1",
                        description="Spatial format contract.",
                        payload=_payload(
                            format_token=format_token,
                            layers=["watershed.subcatchments"],
                            units=units,
                            crs=crs,
                        ),
                    )
                )

    for format_token in TABULAR_FORMATS:
        for crs in CRS_MODES:
            for units in UNIT_MODES:
                cases.append(
                    MatrixCase(
                        case_id=f"a2_{format_token}_{crs}_{units}",
                        gate="gate2",
                        group="A2",
                        description="Tabular format contract.",
                        payload=_payload(
                            format_token=format_token,
                            layers=["wepp.summary.hillslopes"],
                            units=units,
                            crs=crs,
                            tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                        ),
                    )
                )

    if include_ash_watar:
        for format_token in ALL_FORMATS:
            cases.append(
                MatrixCase(
                    case_id=f"a3_ash_watar_{format_token}",
                    gate="gate2",
                    group="A3",
                    description="Ash/WATAR format contract.",
                    payload=_payload(
                        format_token=format_token,
                        layers=[ASH_WATAR_LAYER_ID],
                        units="si",
                        crs="wgs",
                        tabular={"concatenate_tables": False, "temporal_layout": "wide"}
                        if format_token in TABULAR_FORMATS
                        else None,
                    ),
                )
            )

    year_variants: dict[str, dict[str, Any]] = {
        "all": {"mode": "yearly", "year_selection": "all"},
        "exclude_first": {"mode": "yearly", "year_selection": "exclude_first"},
        "exclude_first_two": {"mode": "yearly", "year_selection": "exclude_first_two"},
        "exclude_first_five": {"mode": "yearly", "year_selection": "exclude_first_five"},
        "custom": {"mode": "yearly", "year_selection": "custom", "exclude_yr_indxs": [0, 2]},
    }
    for variant_id, temporal in year_variants.items():
        cases.append(
            MatrixCase(
                case_id=f"b1_year_selection_{variant_id}",
                gate="gate2",
                group="B1",
                description=f"Year selection variant: {variant_id}",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.interchange.loss_all_years_hill"],
                    temporal=temporal,
                    tabular={"temporal_layout": "wide"},
                ),
            )
        )

    cases.append(
        MatrixCase(
            case_id="b2_yearly_multi_layer",
            gate="gate2",
            group="B2",
            description="Yearly multi-layer export.",
            payload=_payload(
                format_token="parquet",
                layers=["wepp.interchange.loss_all_years_hill", "wepp.interchange.loss_all_years_channel"],
                temporal={"mode": "yearly", "year_selection": "all"},
                tabular={"temporal_layout": "wide"},
            ),
        )
    )

    cases.append(
        MatrixCase(
            case_id="b3_event_selector_date",
            gate="gate2",
            group="B3",
            description="Event selector date.",
            payload=_payload(
                format_token="parquet",
                layers=["wepp.temporal.events"],
                temporal={"mode": "event", "event": {"selector": "date", "dates": ["2000-01-03"]}},
                tabular={"temporal_layout": "wide"},
            ),
        )
    )
    cases.append(
        MatrixCase(
            case_id="b3_event_selector_return_period",
            gate="gate2",
            group="B3",
            description="Event selector return_period.",
            payload=_payload(
                format_token="parquet",
                layers=["wepp.temporal.events"],
                temporal={"mode": "event", "event": {"selector": "return_period", "return_periods": [2]}},
                tabular={"temporal_layout": "wide"},
            ),
        )
    )

    cases.append(
        MatrixCase(
            case_id="b4_mixed_temporal_wide",
            gate="gate2",
            group="B4",
            description="Mixed event+yearly wide success.",
            payload=_payload(
                format_token="parquet",
                layers=["wepp.interchange.loss_all_years_hill", "wepp.temporal.events"],
                temporal={
                    "layer_modes": {
                        "wepp.interchange.loss_all_years_hill": "yearly",
                        "wepp.temporal.events": "event",
                    },
                    "event": {"selector": "date", "dates": ["2000-01-03"]},
                },
                tabular={"temporal_layout": "wide"},
            ),
        )
    )

    cases.append(
        MatrixCase(
            case_id="b5_mixed_temporal_long_negative",
            gate="gate2",
            group="B5",
            description="Mixed event+yearly long rejects.",
            payload=_payload(
                format_token="parquet",
                layers=["wepp.interchange.loss_all_years_hill", "wepp.temporal.events"],
                temporal={
                    "layer_modes": {
                        "wepp.interchange.loss_all_years_hill": "yearly",
                        "wepp.temporal.events": "event",
                    },
                    "event": {"selector": "date", "dates": ["2000-01-03"]},
                },
                tabular={"temporal_layout": "long"},
            ),
            expect_success=False,
            expected_status=400,
            expected_code="mixed_temporal_modes",
        )
    )

    cases.append(
        MatrixCase(
            case_id="b6_atemporal_plus_yearly",
            gate="gate2",
            group="B6",
            description="Atemporal + yearly",
            payload=_payload(
                format_token="parquet",
                layers=["watershed.subcatchments", "wepp.interchange.loss_all_years_hill"],
                temporal={"mode": "yearly", "year_selection": "all"},
                tabular={"temporal_layout": "wide"},
            ),
        )
    )
    cases.append(
        MatrixCase(
            case_id="b6_atemporal_plus_event",
            gate="gate2",
            group="B6",
            description="Atemporal + event",
            payload=_payload(
                format_token="parquet",
                layers=["watershed.subcatchments", "wepp.temporal.events"],
                temporal={"mode": "event", "event": {"selector": "date", "dates": ["2000-01-03"]}},
                tabular={"temporal_layout": "wide"},
            ),
        )
    )

    for format_token in SPATIAL_FORMATS:
        cases.append(
            MatrixCase(
                case_id=f"c1_spatial_yearly_{format_token}",
                gate="gate2",
                group="C1",
                description="Spatial yearly coverage.",
                payload=_payload(
                    format_token=format_token,
                    layers=["wepp.interchange.loss_all_years_hill"],
                    temporal={"mode": "yearly", "year_selection": "all"},
                ),
            )
        )
        cases.append(
            MatrixCase(
                case_id=f"c2_spatial_event_{format_token}",
                gate="gate2",
                group="C2",
                description="Spatial event coverage.",
                payload=_payload(
                    format_token=format_token,
                    layers=["wepp.temporal.events"],
                    temporal={"mode": "event", "event": {"selector": "date", "dates": ["2000-01-03"]}},
                ),
            )
        )
        cases.append(
            MatrixCase(
                case_id=f"c3_spatial_mixed_{format_token}",
                gate="gate2",
                group="C3",
                description="Spatial atemporal+yearly mixed coverage.",
                payload=_payload(
                    format_token=format_token,
                    layers=["watershed.subcatchments", "wepp.interchange.loss_all_years_hill"],
                    temporal={"mode": "yearly", "year_selection": "all"},
                ),
            )
        )

    for format_token in ALL_FORMATS:
        cases.append(
            MatrixCase(
                case_id=f"d1_scope_roads_{format_token}",
                gate="gate2",
                group="D1",
                description="Baseline + roads scope coverage.",
                payload=_payload(
                    format_token=format_token,
                    layers=["wepp.summary.hillslopes", "wepp.summary.channels"],
                    output_scopes=["baseline", "roads"],
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"}
                    if format_token in TABULAR_FORMATS
                    else None,
                ),
            )
        )

    for format_token in TABULAR_FORMATS:
        cases.append(
            MatrixCase(
                case_id=f"d2_concatenate_scope_{format_token}",
                gate="gate2",
                group="D2",
                description="Tabular concatenation with scope provenance.",
                payload=_payload(
                    format_token=format_token,
                    layers=["wepp.summary.hillslopes", "wepp.summary.channels"],
                    output_scopes=["baseline", "roads"],
                    tabular={"concatenate_tables": True, "temporal_layout": "wide"},
                ),
            )
        )

    return cases


def build_expansion_cases(*, include_ash_watar: bool = False) -> list[MatrixCase]:
    cases: list[MatrixCase] = []
    for format_token in ALL_FORMATS:
        layers = ["watershed.subcatchments"] if format_token in SPATIAL_FORMATS else ["wepp.summary.hillslopes"]
        cases.append(
            MatrixCase(
                case_id=f"f1_cache_replay_{format_token}",
                gate="expansion",
                group="F1",
                description="Cache replay contract check.",
                payload=_payload(
                    format_token=format_token,
                    layers=layers,
                    units="si",
                    crs="wgs",
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"}
                    if format_token in TABULAR_FORMATS
                    else None,
                ),
                expect_success=True,
                expect_cache_hit=True,
                reference_case_id=f"gate1_success_{format_token}",
            )
        )

    cases.extend(
        [
            MatrixCase(
                case_id="f2_invalid_layer_id",
                gate="expansion",
                group="F2",
                description="Invalid layer id rejects.",
                payload=_payload(
                    format_token="parquet",
                    layers=["not.a.real.layer"],
                ),
                expect_success=False,
                expected_status=400,
                expected_code="unknown_layer_id",
            ),
            MatrixCase(
                case_id="f2_invalid_tabular_shape",
                gate="expansion",
                group="F2",
                description="Invalid tabular shape rejects.",
                payload={
                    "format": "parquet",
                    "layers": ["wepp.summary.hillslopes"],
                    "units": "si",
                    "crs": "wgs",
                    "output_scopes": ["baseline"],
                    "tabular": "invalid",
                },
                expect_success=False,
                expected_status=400,
                expected_code="invalid_type",
            ),
            MatrixCase(
                case_id="f2_mixed_long_negative",
                gate="expansion",
                group="F2",
                description="Mixed long rejects.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.interchange.loss_all_years_hill", "wepp.temporal.events"],
                    temporal={
                        "layer_modes": {
                            "wepp.interchange.loss_all_years_hill": "yearly",
                            "wepp.temporal.events": "event",
                        },
                        "event": {"selector": "date", "dates": ["2000-01-03"]},
                    },
                    tabular={"temporal_layout": "long"},
                ),
                expect_success=False,
                expected_status=400,
                expected_code="mixed_temporal_modes",
            ),
            MatrixCase(
                case_id="f2_missing_event_selector",
                gate="expansion",
                group="F2",
                description="Missing event selector rejects.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.temporal.events"],
                    temporal={"mode": "event"},
                ),
                expect_success=False,
                expected_status=400,
                expected_code="missing_field",
            ),
            MatrixCase(
                case_id="f2_invalid_crs",
                gate="expansion",
                group="F2",
                description="Invalid CRS token rejects.",
                payload={
                    "format": "geojson",
                    "layers": ["watershed.subcatchments"],
                    "units": "si",
                    "crs": "epsg3857",
                    "output_scopes": ["baseline"],
                },
                expect_success=False,
                expected_status=400,
                expected_code="invalid_enum",
            ),
            MatrixCase(
                case_id="f2_invalid_temporal_mode",
                gate="expansion",
                group="F2",
                description="Invalid temporal mode rejects.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.summary.hillslopes"],
                    temporal={"mode": "daily"},
                ),
                expect_success=False,
                expected_status=400,
                expected_code="unsupported_temporal_mode",
            ),
            MatrixCase(
                case_id="f2_invalid_custom_year_selection_payload",
                gate="expansion",
                group="F2",
                description="Custom year selection requires indices.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.interchange.loss_all_years_hill"],
                    temporal={"mode": "yearly", "year_selection": "custom"},
                ),
                expect_success=False,
                expected_status=400,
                expected_code="missing_field",
            ),
            MatrixCase(
                case_id="f2_invalid_scope_token",
                gate="expansion",
                group="F2",
                description="Invalid output scope rejects.",
                payload={
                    "format": "geojson",
                    "layers": ["watershed.subcatchments"],
                    "units": "si",
                    "crs": "wgs",
                    "output_scopes": ["baseline", "mars"],
                },
                expect_success=False,
                expected_status=400,
                expected_code="invalid_enum",
            ),
        ]
    )

    if include_ash_watar:
        cases.extend(
            [
                MatrixCase(
                    case_id="f3_scope_roads_ash_watar_parquet",
                    gate="expansion",
                    group="F3",
                    description="Scope-invariant Ash/WATAR export accepts roads with warnings.",
                    payload=_payload(
                        format_token="parquet",
                        layers=[ASH_WATAR_LAYER_ID],
                        output_scopes=["baseline", "roads"],
                        tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                    ),
                ),
                MatrixCase(
                    case_id="f3_cache_replay_ash_watar_parquet",
                    gate="expansion",
                    group="F3",
                    description="Ash/WATAR cache replay contract check.",
                    payload=_payload(
                        format_token="parquet",
                        layers=[ASH_WATAR_LAYER_ID],
                        units="si",
                        crs="wgs",
                        tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                    ),
                    expect_success=True,
                    expect_cache_hit=True,
                    reference_case_id="a3_ash_watar_parquet",
                ),
            ]
        )

    cases.extend(
        [
            MatrixCase(
                case_id="g1_hill_pass_project",
                gate="expansion",
                group="G1",
                description="Units oracle baseline project.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.interchange.hill_pass"],
                    units="project",
                    temporal={"mode": "annual_average", "year_selection": "all"},
                    tabular={"temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="g1_hill_pass_si",
                gate="expansion",
                group="G1",
                description="Units oracle baseline si.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.interchange.hill_pass"],
                    units="si",
                    temporal={"mode": "annual_average", "year_selection": "all"},
                    tabular={"temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="g1_hill_pass_english",
                gate="expansion",
                group="G1",
                description="Units oracle baseline english.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.interchange.hill_pass"],
                    units="english",
                    temporal={"mode": "annual_average", "year_selection": "all"},
                    tabular={"temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="g1_events_english",
                gate="expansion",
                group="G1",
                description="Units oracle event english.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.temporal.events"],
                    units="english",
                    temporal={"mode": "event", "event": {"selector": "date", "dates": ["2000-01-03"]}},
                    tabular={"temporal_layout": "wide"},
                ),
            ),
        ]
    )

    for lookup_variant in DISTURBED_LOOKUP_VARIANTS:
        for bd_mode in DISTURBED_BD_MODES:
            cases.append(
                MatrixCase(
                    case_id=f"i1_bd_{lookup_variant}_{bd_mode}",
                    gate="expansion",
                    group="I1",
                    description=(
                        "Disturbed lookup bd matrix coverage "
                        f"({lookup_variant}, {bd_mode})."
                    ),
                    payload=_payload(
                        format_token="parquet",
                        layers=["wepp.summary.hillslopes"],
                        units="si",
                        crs="wgs",
                        tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                    ),
                    lookup_variant=lookup_variant,
                    bd_mode=bd_mode,
                )
            )

    return cases


def _natural_sort_key(value: str) -> tuple[int, object]:
    if value.isdigit():
        return (0, int(value))
    return (1, value)


def discover_omni_phase2_selectors(wd: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    scenario_root = wd / "_pups/omni/scenarios"
    contrast_root = wd / "_pups/omni/contrasts"

    scenario_ids: list[str] = []
    if scenario_root.is_dir():
        for path in sorted(scenario_root.iterdir(), key=lambda item: item.name):
            if not path.is_dir():
                continue
            metrics_path = path / "wepp/output/interchange/loss_pw0.hill.parquet"
            interchange_manifest = path / "wepp/output/interchange/interchange_version.json"
            if metrics_path.is_file() and interchange_manifest.is_file():
                scenario_ids.append(path.name)

    contrast_ids: list[str] = []
    if contrast_root.is_dir():
        for path in sorted(contrast_root.iterdir(), key=lambda item: _natural_sort_key(item.name)):
            if not path.is_dir():
                continue
            metrics_path = path / "wepp/output/interchange/loss_pw0.hill.parquet"
            interchange_manifest = path / "wepp/output/interchange/interchange_version.json"
            if metrics_path.is_file() and interchange_manifest.is_file():
                contrast_ids.append(path.name)

    if not scenario_ids:
        raise RuntimeError(
            "Phase-2 Omni case discovery could not find any scenario selectors with required interchange datasets."
        )
    if not contrast_ids:
        raise RuntimeError(
            "Phase-2 Omni case discovery could not find any contrast selectors with required interchange datasets."
        )

    return tuple(scenario_ids), tuple(contrast_ids)


def build_phase2_omni_cases(
    *,
    scenario_ids: tuple[str, ...],
    contrast_ids: tuple[str, ...],
) -> list[MatrixCase]:
    primary_scenario = scenario_ids[0]
    primary_contrast = contrast_ids[0]
    multi_scenarios = list(scenario_ids[:2]) if len(scenario_ids) > 1 else [primary_scenario]
    multi_contrasts = list(contrast_ids[:2]) if len(contrast_ids) > 1 else [primary_contrast]

    cases: list[MatrixCase] = []

    for format_token in ALL_FORMATS:
        tabular = {"concatenate_tables": False, "temporal_layout": "wide"} if format_token in TABULAR_FORMATS else None
        cases.append(
            MatrixCase(
                case_id=f"h1_omni_scenario_{format_token}",
                gate="phase2_gate1",
                group="H1",
                description="Omni scenario sentinel export.",
                payload=_payload(
                    format_token=format_token,
                    layers=["omni.scenarios.hillslopes"],
                    scenarios=[primary_scenario],
                    tabular=tabular,
                ),
            )
        )

    for format_token in ALL_FORMATS:
        tabular = {"concatenate_tables": False, "temporal_layout": "wide"} if format_token in TABULAR_FORMATS else None
        cases.append(
            MatrixCase(
                case_id=f"h2_omni_contrast_{format_token}",
                gate="phase2_gate1",
                group="H2",
                description="Omni contrast sentinel export.",
                payload=_payload(
                    format_token=format_token,
                    layers=["omni.contrasts.hillslopes"],
                    contrast_ids=[primary_contrast],
                    tabular=tabular,
                ),
            )
        )

    cases.extend(
        [
            MatrixCase(
                case_id="h3_neg_mixed_omni_families",
                gate="phase2_gate1",
                group="H3",
                description="Scenario and contrast Omni families cannot be mixed.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.scenarios.hillslopes", "omni.contrasts.hillslopes"],
                    scenarios=[primary_scenario],
                ),
                expect_success=False,
                expected_status=400,
                expected_code="invalid_selector_combo",
            ),
            MatrixCase(
                case_id="h3_neg_missing_scenario_selector",
                gate="phase2_gate1",
                group="H3",
                description="Scenario selector required for Omni scenario layers.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.scenarios.hillslopes"],
                ),
                expect_success=False,
                expected_status=400,
                expected_code="missing_field",
            ),
            MatrixCase(
                case_id="h3_neg_missing_contrast_selector",
                gate="phase2_gate1",
                group="H3",
                description="Contrast selector required for Omni contrast layers.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.contrasts.hillslopes"],
                ),
                expect_success=False,
                expected_status=400,
                expected_code="missing_field",
            ),
            MatrixCase(
                case_id="h3_neg_mutually_exclusive_selectors",
                gate="phase2_gate1",
                group="H3",
                description="scenarios and contrast_ids are mutually exclusive.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.summary.hillslopes"],
                    scenarios=[primary_scenario],
                    contrast_ids=[primary_contrast],
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
                expect_success=False,
                expected_status=400,
                expected_code="mutually_exclusive",
            ),
        ]
    )

    cases.extend(
        [
            MatrixCase(
                case_id="h4_base_layer_scenarios_mapping",
                gate="phase2_expansion",
                group="H4",
                description="Base WEPP hillslope layer expands to scenario context.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.summary.hillslopes"],
                    scenarios=[primary_scenario],
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="h4_base_layer_contrasts_mapping",
                gate="phase2_expansion",
                group="H4",
                description="Base WEPP hillslope layer expands to contrast context.",
                payload=_payload(
                    format_token="parquet",
                    layers=["wepp.summary.hillslopes"],
                    contrast_ids=[primary_contrast],
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="h4_multi_scenario_selectors",
                gate="phase2_expansion",
                group="H4",
                description="Omni scenario multi-select produces selector-specific outputs.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.scenarios.hillslopes"],
                    scenarios=multi_scenarios,
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="h4_multi_contrast_selectors",
                gate="phase2_expansion",
                group="H4",
                description="Omni contrast multi-select produces selector-specific outputs.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.contrasts.hillslopes"],
                    contrast_ids=multi_contrasts,
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="h4_scope_roads_scenario",
                gate="phase2_expansion",
                group="H4",
                description="Scope-invariant Omni scenario export accepts roads with warnings.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.scenarios.hillslopes"],
                    output_scopes=["baseline", "roads"],
                    scenarios=[primary_scenario],
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="h4_scope_roads_contrast",
                gate="phase2_expansion",
                group="H4",
                description="Scope-invariant Omni contrast export accepts roads with warnings.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.contrasts.hillslopes"],
                    output_scopes=["baseline", "roads"],
                    contrast_ids=[primary_contrast],
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
            ),
            MatrixCase(
                case_id="h4_neg_scenario_event_temporal_columns_missing",
                gate="phase2_expansion",
                group="H4",
                description="Event temporal request fails when required selector columns are absent.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.scenarios.hillslopes"],
                    scenarios=[primary_scenario],
                    temporal={"mode": "event", "event": {"selector": "date", "dates": ["2015-01-15"]}},
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
                expect_success=False,
                expected_status=500,
                expected_code="materialization_error",
            ),
            MatrixCase(
                case_id="h4_neg_contrast_yearly_temporal_columns_missing",
                gate="phase2_expansion",
                group="H4",
                description="Yearly temporal request fails when required year columns are absent.",
                payload=_payload(
                    format_token="parquet",
                    layers=["omni.contrasts.hillslopes"],
                    contrast_ids=[primary_contrast],
                    temporal={"mode": "yearly", "year_selection": "all"},
                    tabular={"concatenate_tables": False, "temporal_layout": "wide"},
                ),
                expect_success=False,
                expected_status=500,
                expected_code="materialization_error",
            ),
        ]
    )

    return cases


def _payload_members(zip_names: list[str]) -> list[str]:
    members: list[str] = []
    for name in zip_names:
        if name in REQUIRED_BUNDLE_MEMBERS:
            continue
        if name.startswith("profiles/"):
            continue
        if any(name.endswith(ext) for ext in PAYLOAD_EXTENSIONS):
            members.append(name)
    return sorted(members)


def _read_zip_manifest(zip_handle: zipfile.ZipFile) -> dict[str, Any]:
    return json.loads(zip_handle.read("manifest.json").decode("utf-8"))


def _signature_ok(format_token: str, member: str, data: bytes) -> tuple[bool, str]:
    if format_token in {"parquet", "geoparquet"}:
        return (data.startswith(b"PAR1"), "parquet_magic")
    if format_token == "csv":
        first_line = data.splitlines()[0].decode("utf-8", errors="ignore") if data else ""
        return ("," in first_line, "csv_header")
    if format_token in {"geojson", "kmz"}:
        try:
            parsed = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return (False, "json_parse")
        if isinstance(parsed, dict):
            if parsed.get("type") == "FeatureCollection":
                return (True, "feature_collection")
            feature_collection = parsed.get("feature_collection")
            if isinstance(feature_collection, dict) and feature_collection.get("type") == "FeatureCollection":
                return (True, "feature_collection")
        return (False, "feature_collection_missing")
    if format_token == "geopackage":
        return (data.startswith(b"SQLite format 3"), "sqlite_header")
    if format_token == "geodatabase":
        return (data.startswith(b"PK"), "zip_header")
    return (False, "unknown_format")


def _epsg_from_ogr_dataset(path: Path) -> int | None:
    try:
        from osgeo import ogr
    except Exception:
        return None
    dataset = ogr.Open(str(path))
    if dataset is None:
        return None
    for layer_index in range(dataset.GetLayerCount()):
        layer = dataset.GetLayerByIndex(layer_index)
        if layer is None:
            continue
        srs = layer.GetSpatialRef()
        if srs is None:
            continue
        authority_code = srs.GetAuthorityCode(None)
        if authority_code is not None and str(authority_code).isdigit():
            return int(authority_code)
    return None


def _epsg_for_member(format_token: str, member: str, data: bytes) -> int | None:
    if format_token in {"geojson", "kmz"}:
        try:
            parsed = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        value = parsed.get("crs_epsg")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None
    if format_token == "geoparquet":
        frame = gpd.read_parquet(io.BytesIO(data))
        if frame.crs is None:
            return None
        try:
            return frame.crs.to_epsg()
        except Exception:
            return None
    if format_token == "geopackage":
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg_path = Path(tmpdir) / "payload.gpkg"
            gpkg_path.write_bytes(data)
            return _epsg_from_ogr_dataset(gpkg_path)
    if format_token == "geodatabase":
        with tempfile.TemporaryDirectory() as tmpdir:
            gdb_zip = Path(tmpdir) / "payload.gdb.zip"
            gdb_zip.write_bytes(data)
            gdb_dir = Path(tmpdir) / "payload.gdb"
            gdb_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(gdb_zip, "r") as nested:
                nested.extractall(gdb_dir)
            return _epsg_from_ogr_dataset(gdb_dir)
    return None


def _read_tabular_member(format_token: str, data: bytes) -> pd.DataFrame:
    if format_token == "parquet":
        return pd.read_parquet(io.BytesIO(data))
    if format_token == "csv":
        return pd.read_csv(io.BytesIO(data))
    raise ValueError(f"Unsupported tabular format {format_token}")


def _audit_success_case(
    case: MatrixCase,
    *,
    wd: Path,
    result: dict[str, Any],
    oracle_topaz_ids: set[str],
    oracle_wepp_ids: set[str],
) -> tuple[bool, dict[str, Any], list[str]]:
    reasons: list[str] = []
    checks: dict[str, Any] = {}

    artifact_relpath = str(result.get("artifact_relpath") or "")
    artifact_path = wd / artifact_relpath
    if not artifact_path.is_file():
        return False, {"artifact_path": str(artifact_path)}, ["artifact_missing"]

    with zipfile.ZipFile(artifact_path, "r") as zip_handle:
        zip_names = sorted(zip_handle.namelist())
        checks["zip_members"] = zip_names
        missing_bundle = [name for name in REQUIRED_BUNDLE_MEMBERS if name not in zip_names]
        checks["bundle_missing"] = missing_bundle
        if missing_bundle:
            reasons.append("bundle_members_missing")

        manifest = _read_zip_manifest(zip_handle)
        checks["manifest_layer_count"] = len(manifest.get("layers", []))
        payload_members = _payload_members(zip_names)
        checks["payload_members"] = payload_members
        if not payload_members:
            reasons.append("payload_members_missing")

        expected_ext = {
            "geojson": ".geojson",
            "geoparquet": ".geoparquet",
            "parquet": ".parquet",
            "csv": ".csv",
            "kmz": ".kmz",
            "geopackage": ".gpkg",
            "geodatabase": ".gdb.zip",
        }[case.payload["format"]]
        if any(not member.endswith(expected_ext) for member in payload_members):
            reasons.append("payload_extension_mismatch")

        signature_failures: list[str] = []
        epsg_values: list[int | None] = []
        tabular_rows_by_member: dict[str, int] = {}
        tabular_null_identity_issues: list[str] = []
        tabular_domain_issues: list[str] = []

        manifest_rows_by_member: dict[str, int] = {}
        for layer_entry in manifest.get("layers", []):
            relpath = str(layer_entry.get("artifact_relpath") or "")
            row_count = layer_entry.get("row_count")
            if isinstance(row_count, int):
                manifest_rows_by_member[relpath] = manifest_rows_by_member.get(relpath, 0) + row_count
        checks["manifest_rows_by_member"] = manifest_rows_by_member

        for member in payload_members:
            data = zip_handle.read(member)
            sig_ok, sig_probe = _signature_ok(case.payload["format"], member, data)
            if not sig_ok:
                signature_failures.append(f"{member}:{sig_probe}")

            if case.payload["format"] in SPATIAL_FORMATS:
                epsg_values.append(_epsg_for_member(case.payload["format"], member, data))
            if case.payload["format"] in TABULAR_FORMATS:
                frame = _read_tabular_member(case.payload["format"], data)
                tabular_rows_by_member[member] = int(len(frame.index))
                if "topaz_id" not in frame.columns or "wepp_id" not in frame.columns:
                    tabular_null_identity_issues.append(f"{member}:missing_identity_columns")
                else:
                    missing_identity_mask = frame["topaz_id"].isna() | frame["wepp_id"].isna()
                    missing_count = int(missing_identity_mask.sum())
                    if missing_count:
                        tabular_null_identity_issues.append(f"{member}:null_identity_rows={missing_count}")
                    for column_name, oracle in (("topaz_id", oracle_topaz_ids), ("wepp_id", oracle_wepp_ids)):
                        if not oracle:
                            continue
                        unknown_count = 0
                        for value in frame[column_name].tolist():
                            token = _canonical_id(value)
                            if token is None:
                                continue
                            if token not in oracle:
                                unknown_count += 1
                        if unknown_count:
                            tabular_domain_issues.append(
                                f"{member}:{column_name}:unknown_domain={unknown_count}"
                            )

        checks["signature_failures"] = signature_failures
        if signature_failures:
            reasons.append("signature_failures")

        if case.payload["format"] in SPATIAL_FORMATS:
            checks["spatial_epsg_values"] = epsg_values
            expected_crs = str(case.payload.get("crs") or "wgs").lower()
            if expected_crs == "wgs":
                if any(epsg != 4326 for epsg in epsg_values):
                    reasons.append("spatial_crs_wgs_mismatch")
            elif expected_crs == "utm":
                if not epsg_values or any(
                    epsg is None or epsg == 4326 for epsg in epsg_values
                ):
                    reasons.append("spatial_crs_utm_mismatch")
        else:
            checks["tabular_rows_by_member"] = tabular_rows_by_member
            checks["tabular_identity_issues"] = tabular_null_identity_issues
            checks["tabular_domain_issues"] = tabular_domain_issues
            for member, observed_rows in tabular_rows_by_member.items():
                expected_rows = manifest_rows_by_member.get(member)
                if expected_rows is not None and observed_rows != expected_rows:
                    reasons.append(f"manifest_row_count_mismatch:{member}")
            if tabular_null_identity_issues:
                reasons.append("tabular_identity_incomplete")
            if tabular_domain_issues:
                reasons.append("tabular_domain_mismatch")

            if "geometry" in ",".join(str(col) for col in tabular_rows_by_member.keys()):
                reasons.append("tabular_geometry_column_present")
            manifest_crs = manifest.get("crs", {})
            if manifest_crs.get("resolved_epsg") is not None:
                reasons.append("tabular_crs_not_noop")

        temporal = case.payload.get("temporal")
        if isinstance(temporal, dict) and case.payload["format"] in TABULAR_FORMATS and payload_members:
            first_member = payload_members[0]
            table = _read_tabular_member(case.payload["format"], zip_handle.read(first_member))
            columns = [str(column) for column in table.columns]
            mode = temporal.get("mode")
            layer_modes = temporal.get("layer_modes")
            uses_event = False
            uses_yearly = False
            if isinstance(layer_modes, dict):
                uses_event = any(value == "event" for value in layer_modes.values())
                uses_yearly = any(value == "yearly" for value in layer_modes.values())
            if mode == "event":
                uses_event = True
            if mode == "yearly":
                uses_yearly = True

            if uses_yearly:
                year_columns = [column for column in columns if YEAR_WIDE_RE.search(column)]
                checks["temporal_year_columns"] = year_columns
                if not year_columns:
                    reasons.append("yearly_columns_missing")
            if uses_event:
                event_selector = temporal.get("event", {})
                selector = event_selector.get("selector") if isinstance(event_selector, dict) else "date"
                if selector == "date":
                    date_columns = [column for column in columns if DATE_WIDE_RE.search(column)]
                    checks["temporal_date_columns"] = date_columns
                    if not date_columns:
                        reasons.append("event_date_columns_missing")
                if selector == "return_period":
                    rp_columns = [column for column in columns if "_rp" in column]
                    checks["temporal_return_period_columns"] = rp_columns
                    if not rp_columns:
                        reasons.append("event_return_period_columns_missing")

        selector_layers = manifest.get("layers", [])
        scenario_ids_in_manifest = sorted(
            {
                str(entry.get("selector_id"))
                for entry in selector_layers
                if entry.get("context") == "scenario" and entry.get("selector_id") is not None
            }
        )
        contrast_ids_in_manifest = sorted(
            {
                str(entry.get("selector_id"))
                for entry in selector_layers
                if entry.get("context") == "contrast" and entry.get("selector_id") is not None
            }
        )
        checks["manifest_scenario_ids"] = scenario_ids_in_manifest
        checks["manifest_contrast_ids"] = contrast_ids_in_manifest

        requested_scenarios = case.payload.get("scenarios")
        if isinstance(requested_scenarios, list):
            missing_scenarios = sorted(
                {
                    str(selector)
                    for selector in requested_scenarios
                    if str(selector) not in scenario_ids_in_manifest
                }
            )
            checks["requested_scenarios"] = [str(item) for item in requested_scenarios]
            if missing_scenarios:
                checks["missing_manifest_scenarios"] = missing_scenarios
                reasons.append("scenario_selector_manifest_mismatch")

        requested_contrasts = case.payload.get("contrast_ids")
        if isinstance(requested_contrasts, list):
            missing_contrasts = sorted(
                {
                    str(selector)
                    for selector in requested_contrasts
                    if str(selector) not in contrast_ids_in_manifest
                }
            )
            checks["requested_contrasts"] = [str(item) for item in requested_contrasts]
            if missing_contrasts:
                checks["missing_manifest_contrasts"] = missing_contrasts
                reasons.append("contrast_selector_manifest_mismatch")

        output_scopes = case.payload.get("output_scopes")
        roads_requested = isinstance(output_scopes, list) and any(
            str(scope_token) == "roads" for scope_token in output_scopes
        )
        if roads_requested:
            warning_codes = sorted(
                {
                    str(warning.get("code"))
                    for warning in result.get("warnings", [])
                    if isinstance(warning, dict) and warning.get("code") is not None
                }
            )
            checks["result_warning_codes"] = warning_codes
            manifest_scope_values = sorted(
                {
                    str(entry.get("scope"))
                    for entry in manifest.get("layers", [])
                    if isinstance(entry, dict) and entry.get("scope") is not None
                }
            )
            checks["manifest_scope_values"] = manifest_scope_values
            roads_emitted = "roads" in manifest_scope_values or any("-roads-" in member for member in payload_members)
            if not roads_emitted and "scope_not_applicable" not in warning_codes:
                reasons.append("scope_not_applicable_warning_missing")

    passed = len(reasons) == 0
    return passed, checks, reasons


def _as_error_payload(exc: FeaturesExportValidationError) -> tuple[int, str, str]:
    issues = [issue.to_mapping() for issue in exc.issues]
    if not issues:
        return 400, "validation_error", "Validation failed"
    first = issues[0]
    return 400, str(first.get("code") or "validation_error"), json.dumps(issues, sort_keys=True)


def _extract_primary_tabular_frame(
    wd: Path,
    result_row: dict[str, Any],
) -> pd.DataFrame:
    artifact_path = wd / str(result_row["result"]["artifact_relpath"])
    with zipfile.ZipFile(artifact_path, "r") as zip_handle:
        payload_members = _payload_members(sorted(zip_handle.namelist()))
        first_member = payload_members[0]
        data = zip_handle.read(first_member)
        if first_member.endswith(".csv"):
            return pd.read_csv(io.BytesIO(data))
        return pd.read_parquet(io.BytesIO(data))


def _first_column_matching(columns: list[str], prefixes: tuple[str, ...]) -> str | None:
    for prefix in prefixes:
        for column in columns:
            if column.startswith(prefix):
                return column
    return None


def _run_numeric_oracles(
    *,
    wd: Path,
    result_by_case_id: dict[str, dict[str, Any]],
) -> tuple[bool, dict[str, Any], list[str]]:
    reasons: list[str] = []
    checks: dict[str, Any] = {}

    required_cases = (
        "g1_hill_pass_project",
        "g1_hill_pass_si",
        "g1_hill_pass_english",
        "g1_events_english",
        "b3_event_selector_date",
    )
    missing = [case_id for case_id in required_cases if case_id not in result_by_case_id]
    if missing:
        return False, {"missing_cases": missing}, ["numeric_oracle_missing_cases"]

    hill_project = _extract_primary_tabular_frame(wd, result_by_case_id["g1_hill_pass_project"])
    hill_si = _extract_primary_tabular_frame(wd, result_by_case_id["g1_hill_pass_si"])
    hill_english = _extract_primary_tabular_frame(wd, result_by_case_id["g1_hill_pass_english"])
    event_si = _extract_primary_tabular_frame(wd, result_by_case_id["b3_event_selector_date"])
    event_english = _extract_primary_tabular_frame(wd, result_by_case_id["g1_events_english"])

    hill_project_col = _first_column_matching(hill_project.columns.tolist(), ("runvol_m3",))
    hill_si_col = _first_column_matching(hill_si.columns.tolist(), ("runvol_m3",))
    hill_english_col = _first_column_matching(hill_english.columns.tolist(), ("runvol_ft_3",))
    if not hill_project_col or not hill_si_col or not hill_english_col:
        reasons.append("hill_pass_oracle_columns_missing")
    else:
        project_value = float(hill_project[hill_project_col].dropna().iloc[0])
        si_value = float(hill_si[hill_si_col].dropna().iloc[0])
        english_value = float(hill_english[hill_english_col].dropna().iloc[0])
        checks["hill_pass_values"] = {
            "project": project_value,
            "si": si_value,
            "english": english_value,
        }
        if not math.isclose(project_value, si_value, rel_tol=1e-9, abs_tol=1e-9):
            reasons.append("project_vs_si_mismatch")
        if not math.isclose(english_value, si_value * 35.3146667, rel_tol=1e-5, abs_tol=1e-5):
            reasons.append("si_to_english_conversion_mismatch")

    event_si_col = next(
        (
            column
            for column in event_si.columns.tolist()
            if "runoff_depth_mm_" in column and column.endswith("_mm")
        ),
        None,
    )
    event_english_col = next(
        (
            column
            for column in event_english.columns.tolist()
            if "runoff_depth_mm_" in column and column.endswith("_in")
        ),
        None,
    )
    if not event_si_col or not event_english_col:
        reasons.append("event_oracle_columns_missing")
    else:
        event_si_value = float(event_si[event_si_col].dropna().iloc[0])
        event_english_value = float(event_english[event_english_col].dropna().iloc[0])
        checks["event_values"] = {
            "si": event_si_value,
            "english": event_english_value,
        }
        if not math.isclose(event_english_value, event_si_value * 0.03937007874, rel_tol=1e-5, abs_tol=1e-5):
            reasons.append("event_si_to_english_conversion_mismatch")

    return len(reasons) == 0, checks, reasons


def execute_cases(
    *,
    cases: list[MatrixCase],
    wd: Path,
    runid: str,
    config: str,
    results_path: Path,
    result_by_case_id: dict[str, dict[str, Any]],
    oracle_topaz_ids: set[str],
    oracle_wepp_ids: set[str],
) -> bool:
    gate_pass = True
    for case in cases:
        row: dict[str, Any] = {
            "timestamp_utc": _utc_now_iso(),
            "case_id": case.case_id,
            "gate": case.gate,
            "group": case.group,
            "description": case.description,
            "payload": case.payload,
            "expect_success": case.expect_success,
        }
        job_id = f"matrix-{case.case_id}"
        row["job_id"] = job_id

        try:
            if case.lookup_variant is not None or case.bd_mode is not None:
                if case.lookup_variant is None or case.bd_mode is None:
                    raise ValueError(
                        f"Case {case.case_id} must define both lookup_variant and bd_mode when using bd preconditions."
                    )
                row["lookup_precondition"] = _apply_disturbed_bd_precondition(
                    wd=wd,
                    lookup_variant=case.lookup_variant,
                    bd_mode=case.bd_mode,
                )

            result = execute_features_export(
                wd,
                runid=runid,
                config=config,
                payload=case.payload,
                job_id=job_id,
            )
            row["outcome"] = "success"
            row["result"] = result
            passed, checks, reasons = _audit_success_case(
                case,
                wd=wd,
                result=result,
                oracle_topaz_ids=oracle_topaz_ids,
                oracle_wepp_ids=oracle_wepp_ids,
            )
            row["checks"] = checks
            row["check_failures"] = reasons

            if case.expect_cache_hit is not None:
                observed_cache_hit = bool(result.get("cache_hit"))
                if observed_cache_hit != case.expect_cache_hit:
                    passed = False
                    row.setdefault("check_failures", []).append("cache_hit_contract_mismatch")
                if case.expect_cache_hit and not result.get("source_job_id"):
                    passed = False
                    row.setdefault("check_failures", []).append("cache_source_job_missing")
                if case.reference_case_id:
                    reference = result_by_case_id.get(case.reference_case_id)
                    reference_artifact = None
                    if reference and reference.get("result"):
                        reference_artifact = reference["result"].get("artifact_relpath")
                    if reference_artifact and reference_artifact != result.get("artifact_relpath"):
                        passed = False
                        row.setdefault("check_failures", []).append("cache_artifact_mapping_changed")

            row["passed"] = bool(case.expect_success and passed)
        except FeaturesExportValidationError as exc:
            status, code, details = _as_error_payload(exc)
            row["outcome"] = "error"
            row["error"] = {
                "status_code": status,
                "code": code,
                "details": details,
            }
            row["passed"] = (
                (not case.expect_success)
                and (case.expected_status is None or status == case.expected_status)
                and (case.expected_code is None or code == case.expected_code)
            )
        except FeaturesExportServiceError as exc:
            row["outcome"] = "error"
            row["error"] = {
                "status_code": exc.status_code,
                "code": exc.code,
                "details": exc.details,
            }
            row["passed"] = (
                (not case.expect_success)
                and (case.expected_status is None or exc.status_code == case.expected_status)
                and (case.expected_code is None or exc.code == case.expected_code)
            )
        except Exception as exc:  # boundary: matrix harness should always record failures
            row["outcome"] = "error"
            row["error"] = {
                "status_code": 500,
                "code": "unexpected_exception",
                "details": str(exc),
                "traceback": traceback.format_exc(),
            }
            row["passed"] = False

        result_by_case_id[case.case_id] = row
        with results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

        print(f"{case.case_id}: {'PASS' if row['passed'] else 'FAIL'}")
        if not row["passed"]:
            gate_pass = False

    return gate_pass


def _write_manual_sanity_notes(
    *,
    notes_path: Path,
    result_by_case_id: dict[str, dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Manual Sanity Notes",
        "",
        f"- Generated: {_utc_now_iso()}",
        "",
    ]

    def append_case_details(case_ids: list[str], section: str) -> None:
        if not any(case_id in result_by_case_id for case_id in case_ids):
            return
        lines.extend([f"## {section}", ""])
        for case_id in case_ids:
            row = result_by_case_id.get(case_id)
            if row is None:
                continue
            lines.append(f"### {case_id}")
            lines.append(f"- Passed: `{row.get('passed')}`")
            result = row.get("result", {})
            if isinstance(result, dict):
                lines.append(f"- cache_hit: `{result.get('cache_hit')}`")
                lines.append(f"- artifact_relpath: `{result.get('artifact_relpath')}`")
            checks = row.get("checks", {})
            if isinstance(checks, dict):
                members = checks.get("payload_members", [])
                lines.append(f"- payload_members: `{members}`")
                epsg_values = checks.get("spatial_epsg_values")
                if epsg_values is not None:
                    lines.append(f"- spatial_epsg_values: `{epsg_values}`")
                identity_issues = checks.get("tabular_identity_issues")
                if identity_issues is not None:
                    lines.append(f"- tabular_identity_issues: `{identity_issues}`")
                scenario_ids = checks.get("manifest_scenario_ids")
                if scenario_ids:
                    lines.append(f"- manifest_scenario_ids: `{scenario_ids}`")
                contrast_ids = checks.get("manifest_contrast_ids")
                if contrast_ids:
                    lines.append(f"- manifest_contrast_ids: `{contrast_ids}`")
                warning_codes = checks.get("result_warning_codes")
                if warning_codes is not None:
                    lines.append(f"- warning_codes: `{warning_codes}`")
            failures = row.get("check_failures", [])
            if failures:
                lines.append(f"- check_failures: `{failures}`")
            lines.append("")

    append_case_details(
        [f"gate1_success_{format_token}" for format_token in ALL_FORMATS],
        "Gate-1 Format Sentinel",
    )
    append_case_details(
        [f"h1_omni_scenario_{format_token}" for format_token in ALL_FORMATS],
        "Phase-2 Omni Scenario Sentinel (H1)",
    )
    append_case_details(
        [f"h2_omni_contrast_{format_token}" for format_token in ALL_FORMATS],
        "Phase-2 Omni Contrast Sentinel (H2)",
    )
    append_case_details(
        [
            "h4_base_layer_scenarios_mapping",
            "h4_base_layer_contrasts_mapping",
            "h4_multi_scenario_selectors",
            "h4_multi_contrast_selectors",
            "h4_scope_roads_scenario",
            "h4_scope_roads_contrast",
        ],
        "Phase-2 Omni Compatibility (H4)",
    )
    append_case_details(
        [
            *[f"a3_ash_watar_{format_token}" for format_token in ALL_FORMATS],
            "f3_scope_roads_ash_watar_parquet",
            "f3_cache_replay_ash_watar_parquet",
        ],
        "Ash/WATAR Coverage",
    )
    append_case_details(
        [
            "i1_bd_base_blank",
            "i1_bd_base_numeric",
            "i1_bd_extended_blank",
            "i1_bd_extended_numeric",
        ],
        "Disturbed BD Variant Coverage (I1)",
    )

    notes_path.write_text("\n".join(lines), encoding="utf-8")


def _write_defect_log(
    *,
    defect_path: Path,
    result_by_case_id: dict[str, dict[str, Any]],
    numeric_oracle_row: dict[str, Any] | None = None,
) -> None:
    group_totals: dict[str, int] = {}
    group_passed: dict[str, int] = {}
    for row in result_by_case_id.values():
        group = str(row.get("group") or "unknown")
        group_totals[group] = group_totals.get(group, 0) + 1
        if row.get("passed"):
            group_passed[group] = group_passed.get(group, 0) + 1

    lines: list[str] = [
        "# Defect Log",
        "",
        f"- Generated: {_utc_now_iso()}",
        "",
        "## Group Summary",
        "",
    ]
    for group in sorted(group_totals):
        lines.append(
            f"- `{group}`: `{group_passed.get(group, 0)}/{group_totals[group]}` passed"
        )

    lines.extend(
        [
            "",
            "## Outstanding Failures",
            "",
        ]
    )

    outstanding = [row for row in result_by_case_id.values() if not row.get("passed")]
    if not outstanding:
        lines.append("- None. All executed cases passed.")
    else:
        for row in sorted(outstanding, key=lambda item: item.get("case_id", "")):
            lines.append(
                f"- `{row.get('case_id')}`: outcome={row.get('outcome')} error={row.get('error')} failures={row.get('check_failures')}"
            )

    if numeric_oracle_row is not None:
        lines.extend(
            [
                "",
                "## Numeric Oracle Summary",
                "",
                f"- Passed: `{numeric_oracle_row.get('passed')}`",
                f"- Details: `{numeric_oracle_row.get('checks')}`",
                f"- Failures: `{numeric_oracle_row.get('check_failures')}`",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Numeric Oracle Summary",
                "",
                "- Not executed in this phase.",
                "",
            ]
        )

    defect_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runid", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--wd", required=True, help="Absolute run working directory.")
    parser.add_argument("--results", required=True, help="Output matrix_results.jsonl path.")
    parser.add_argument("--manual-notes", required=True, help="Output manual_sanity_notes.md path.")
    parser.add_argument("--defect-log", required=True, help="Output defect_log.md path.")
    parser.add_argument(
        "--phase",
        choices=(PHASE1_PLAN, PHASE2_OMNI_PLAN),
        default=PHASE1_PLAN,
        help="Matrix case plan to execute.",
    )
    parser.add_argument(
        "--append-results",
        action="store_true",
        help="Append to results file instead of replacing it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wd = Path(args.wd).resolve()
    results_path = Path(args.results).resolve()
    manual_notes_path = Path(args.manual_notes).resolve()
    defect_log_path = Path(args.defect_log).resolve()
    for output_path in (results_path, manual_notes_path, defect_log_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    if results_path.exists() and not args.append_results:
        results_path.unlink()

    oracle_topaz_ids, oracle_wepp_ids = _load_oracle_domains(wd)
    include_ash_watar = _has_ash_watar_assets(wd)
    if include_ash_watar:
        print("Detected ash assets in run path; enabling optional Ash/WATAR matrix cases (A3/F3).")
    else:
        print("No ash assets detected in run path; skipping optional Ash/WATAR matrix cases (A3/F3).")
    result_by_case_id: dict[str, dict[str, Any]] = {}
    disturbed_lookup_snapshot = _capture_disturbed_lookup_snapshot(wd)

    try:
        if args.phase == PHASE2_OMNI_PLAN:
            scenario_ids, contrast_ids = discover_omni_phase2_selectors(wd)
            phase2_cases = build_phase2_omni_cases(
                scenario_ids=scenario_ids,
                contrast_ids=contrast_ids,
            )
            sentinel_cases = [case for case in phase2_cases if case.gate == "phase2_gate1"]
            expansion_cases = [case for case in phase2_cases if case.gate == "phase2_expansion"]

            sentinel_ok = execute_cases(
                cases=sentinel_cases,
                wd=wd,
                runid=args.runid,
                config=args.config,
                results_path=results_path,
                result_by_case_id=result_by_case_id,
                oracle_topaz_ids=oracle_topaz_ids,
                oracle_wepp_ids=oracle_wepp_ids,
            )
            if not sentinel_ok:
                _write_manual_sanity_notes(notes_path=manual_notes_path, result_by_case_id=result_by_case_id)
                _write_defect_log(
                    defect_path=defect_log_path,
                    result_by_case_id=result_by_case_id,
                    numeric_oracle_row=None,
                )
                return 1

            expansion_ok = execute_cases(
                cases=expansion_cases,
                wd=wd,
                runid=args.runid,
                config=args.config,
                results_path=results_path,
                result_by_case_id=result_by_case_id,
                oracle_topaz_ids=oracle_topaz_ids,
                oracle_wepp_ids=oracle_wepp_ids,
            )

            _write_manual_sanity_notes(notes_path=manual_notes_path, result_by_case_id=result_by_case_id)
            _write_defect_log(
                defect_path=defect_log_path,
                result_by_case_id=result_by_case_id,
                numeric_oracle_row=None,
            )
            return 0 if expansion_ok else 1

        gate1_ok = execute_cases(
            cases=build_gate1_cases(),
            wd=wd,
            runid=args.runid,
            config=args.config,
            results_path=results_path,
            result_by_case_id=result_by_case_id,
            oracle_topaz_ids=oracle_topaz_ids,
            oracle_wepp_ids=oracle_wepp_ids,
        )
        if not gate1_ok:
            _write_manual_sanity_notes(notes_path=manual_notes_path, result_by_case_id=result_by_case_id)
            _write_defect_log(
                defect_path=defect_log_path,
                result_by_case_id=result_by_case_id,
                numeric_oracle_row={"passed": False, "checks": {}, "check_failures": ["gate1_failed"]},
            )
            return 1

        gate2_ok = execute_cases(
            cases=build_gate2_cases(include_ash_watar=include_ash_watar),
            wd=wd,
            runid=args.runid,
            config=args.config,
            results_path=results_path,
            result_by_case_id=result_by_case_id,
            oracle_topaz_ids=oracle_topaz_ids,
            oracle_wepp_ids=oracle_wepp_ids,
        )
        if not gate2_ok:
            _write_manual_sanity_notes(notes_path=manual_notes_path, result_by_case_id=result_by_case_id)
            _write_defect_log(
                defect_path=defect_log_path,
                result_by_case_id=result_by_case_id,
                numeric_oracle_row={"passed": False, "checks": {}, "check_failures": ["gate2_failed"]},
            )
            return 1

        expansion_ok = execute_cases(
            cases=build_expansion_cases(include_ash_watar=include_ash_watar),
            wd=wd,
            runid=args.runid,
            config=args.config,
            results_path=results_path,
            result_by_case_id=result_by_case_id,
            oracle_topaz_ids=oracle_topaz_ids,
            oracle_wepp_ids=oracle_wepp_ids,
        )

        numeric_passed, numeric_checks, numeric_failures = _run_numeric_oracles(
            wd=wd,
            result_by_case_id=result_by_case_id,
        )
        numeric_row = {
            "timestamp_utc": _utc_now_iso(),
            "case_id": "g1_numeric_oracles",
            "gate": "expansion",
            "group": "G1",
            "description": "Cross-case numeric conversion oracle checks.",
            "expect_success": True,
            "outcome": "success",
            "checks": numeric_checks,
            "check_failures": numeric_failures,
            "passed": numeric_passed,
        }
        with results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(numeric_row, sort_keys=True) + "\n")
        result_by_case_id["g1_numeric_oracles"] = numeric_row

        # Group E synthesized audits from all successful core cases.
        core_rows = [
            row
            for row in result_by_case_id.values()
            if row.get("gate") == "gate2" and row.get("expect_success") and row.get("outcome") == "success"
        ]
        e1_failures: list[str] = []
        e2_failures: list[str] = []
        for row in core_rows:
            failures = row.get("check_failures") or []
            for failure in failures:
                if "identity" in failure or "domain" in failure:
                    e1_failures.append(f"{row.get('case_id')}:{failure}")
                if "manifest" in failure or "bundle" in failure:
                    e2_failures.append(f"{row.get('case_id')}:{failure}")
        e1_row = {
            "timestamp_utc": _utc_now_iso(),
            "case_id": "e1_integrity_audit",
            "gate": "gate2",
            "group": "E1",
            "description": "Cross-run identity/data-integrity audit.",
            "expect_success": True,
            "outcome": "success",
            "checks": {"core_success_case_count": len(core_rows)},
            "check_failures": e1_failures,
            "passed": len(e1_failures) == 0,
        }
        e2_row = {
            "timestamp_utc": _utc_now_iso(),
            "case_id": "e2_manifest_audit",
            "gate": "gate2",
            "group": "E2",
            "description": "Cross-run manifest integrity audit.",
            "expect_success": True,
            "outcome": "success",
            "checks": {"core_success_case_count": len(core_rows)},
            "check_failures": e2_failures,
            "passed": len(e2_failures) == 0,
        }
        with results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(e1_row, sort_keys=True) + "\n")
            handle.write(json.dumps(e2_row, sort_keys=True) + "\n")
        result_by_case_id[e1_row["case_id"]] = e1_row
        result_by_case_id[e2_row["case_id"]] = e2_row

        _write_manual_sanity_notes(notes_path=manual_notes_path, result_by_case_id=result_by_case_id)
        _write_defect_log(
            defect_path=defect_log_path,
            result_by_case_id=result_by_case_id,
            numeric_oracle_row=numeric_row,
        )

        all_passed = (
            gate1_ok
            and gate2_ok
            and expansion_ok
            and numeric_row["passed"]
            and e1_row["passed"]
            and e2_row["passed"]
        )
        return 0 if all_passed else 1
    finally:
        _restore_disturbed_lookup_snapshot(wd, disturbed_lookup_snapshot)


if __name__ == "__main__":
    raise SystemExit(main())
