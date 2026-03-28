"""Shared helpers for geometryless tabular features-export writers."""

from __future__ import annotations

import collections.abc as cabc

import pandas as pd

from ..contracts import ResolvedLayerPlan
from .base import ExportPayloadValidationError, PreparedLayerPayload


def table_frame_from_payload(
    *,
    layer: ResolvedLayerPlan,
    payload: PreparedLayerPayload,
) -> pd.DataFrame:
    """Return one geometryless frame from one prepared layer payload."""

    if payload.tabular_frame is None:
        raise ExportPayloadValidationError(
            "Tabular writer received payload without tabular_frame."
        )
    if not isinstance(payload.tabular_frame, pd.DataFrame):
        raise ExportPayloadValidationError(
            "Prepared tabular_frame must be a pandas DataFrame."
        )
    return payload.tabular_frame.copy()


def build_tabular_frames(
    *,
    layer_payload_pairs: cabc.Sequence[tuple[ResolvedLayerPlan, PreparedLayerPayload]],
    file_extension: str,
    concatenate_tables: bool,
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Group per-layer frames into output files based on tabular settings."""

    grouped_frames: dict[str, list[pd.DataFrame]] = {}
    filename_by_output_layer_id: dict[str, str] = {}
    filename_by_group: dict[str, str] = {}

    suffix = file_extension.lstrip(".")
    for layer, payload in layer_payload_pairs:
        frame = table_frame_from_payload(layer=layer, payload=payload)
        frame = _apply_provenance_columns(frame=frame, layer=layer)

        if concatenate_tables:
            concat_group = _concat_group_for_layer(layer)
        else:
            concat_group = None

        if concat_group is None:
            group_key = f"layer::{layer.output_layer_id}"
            filename = f"{layer.output_layer_id}.{suffix}"
        else:
            group_key = f"concat::{concat_group}"
            filename = f"{concat_group}.{suffix}"

        grouped_frames.setdefault(group_key, []).append(frame)
        filename_by_group[group_key] = filename
        filename_by_output_layer_id[layer.output_layer_id] = filename

    frame_by_filename: dict[str, pd.DataFrame] = {}
    for group_key, frames in grouped_frames.items():
        if not frames:
            continue
        filename = filename_by_group[group_key]
        if len(frames) == 1:
            merged = frames[0]
        else:
            merged = pd.concat(frames, ignore_index=True, sort=False)
        frame_by_filename[filename] = merged

    return frame_by_filename, filename_by_output_layer_id


def _apply_provenance_columns(*, frame: pd.DataFrame, layer: ResolvedLayerPlan) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["output_scope"] = layer.scope
    enriched["omni_scenario"] = layer.selector_id if layer.context == "scenario" else None
    enriched["omni_contrast_id"] = layer.selector_id if layer.context == "contrast" else None
    return enriched


def _concat_group_for_layer(layer: ResolvedLayerPlan) -> str | None:
    token = str(layer.carrier_layer or "").strip().lower()
    if token == "sbs_map-subcatchments":
        return "hillslopes"
    if token == "chan_map-channels":
        return "channels"
    return None


__all__ = [
    "build_tabular_frames",
    "table_frame_from_payload",
]
