"""Typed writer contracts and shared helpers for features export WP-3."""

from __future__ import annotations

import abc
import collections.abc as cabc
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING

from ..contracts import ExportWarning, ResolvedExportPlan, ResolvedLayerPlan

if TYPE_CHECKING:
    import pandas as pd

_OUTPUT_LAYER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class FeaturesExportWriterError(RuntimeError):
    """Base error for writer and packaging failures."""


class ExportPayloadValidationError(FeaturesExportWriterError):
    """Raised when prepared payloads do not match the resolved export plan."""


class ExportBackendCapabilityError(FeaturesExportWriterError):
    """Raised when a required backend capability is unavailable."""


@dataclass(frozen=True)
class PreparedLayerPayload:
    """Prepared per-layer bytes and metadata consumed by writers."""

    output_layer_id: str
    payload: bytes | str
    tabular_frame: pd.DataFrame | None = None
    row_count: int | None = None
    feature_count: int | None = None
    warnings: tuple[ExportWarning, ...] = ()

    def payload_bytes(self) -> bytes:
        """Return payload bytes with deterministic UTF-8 encoding for text."""

        if isinstance(self.payload, bytes):
            return self.payload
        return self.payload.encode("utf-8")

    def payload_sha256(self) -> str:
        """Return deterministic payload digest for container synthesis."""

        return sha256(self.payload_bytes()).hexdigest()


@dataclass(frozen=True)
class ExportWriterRequest:
    """Input contract for WP-3 writer execution."""

    plan: ResolvedExportPlan
    layer_payloads: cabc.Mapping[str, PreparedLayerPayload]
    artifact_dir: str | Path
    artifact_basename: str = "features_export"

    def artifact_dir_path(self) -> Path:
        return Path(self.artifact_dir).resolve()


@dataclass(frozen=True)
class ExportedLayerArtifact:
    """Structured metadata for one layer output within an artifact."""

    layer_id: str
    output_layer_id: str
    scope: str
    scope_class: str
    format: str
    relpath: str
    row_count: int | None
    feature_count: int | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "layer_id": self.layer_id,
            "output_layer_id": self.output_layer_id,
            "scope": self.scope,
            "scope_class": self.scope_class,
            "format": self.format,
            "relpath": self.relpath,
            "row_count": self.row_count,
            "feature_count": self.feature_count,
        }


@dataclass(frozen=True)
class ExportArtifactMetadata:
    """Structured result metadata returned by each format writer."""

    format: str
    artifact_relpath: str
    artifact_path: str
    layer_outputs: tuple[ExportedLayerArtifact, ...]
    warnings: tuple[ExportWarning, ...] = ()
    packaged_member_relpaths: tuple[str, ...] = ()

    def to_mapping(self) -> dict[str, object]:
        return {
            "format": self.format,
            "artifact_relpath": self.artifact_relpath,
            "artifact_path": self.artifact_path,
            "layer_outputs": [layer.to_mapping() for layer in self.layer_outputs],
            "warnings": [warning.to_mapping() for warning in self.warnings],
            "packaged_member_relpaths": list(self.packaged_member_relpaths),
        }


class ExportWriter(abc.ABC):
    """Writer interface for WP-3 export format implementations."""

    format_token: str

    @abc.abstractmethod
    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        """Write export artifact(s) for the provided resolved plan and payloads."""


def deterministic_layer_filename(output_layer_id: str, extension: str) -> str:
    """Return deterministic per-layer filename derived from `output_layer_id`."""

    if not output_layer_id:
        raise ExportPayloadValidationError("output_layer_id must be a non-empty string.")
    if not _OUTPUT_LAYER_ID_PATTERN.fullmatch(output_layer_id):
        raise ExportPayloadValidationError(
            "output_layer_id must match [A-Za-z0-9._-]+ for deterministic naming, "
            f"received {output_layer_id!r}."
        )

    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"{output_layer_id}{suffix}"


def resolve_layer_payload_pairs(
    request: ExportWriterRequest,
) -> tuple[tuple[ResolvedLayerPlan, PreparedLayerPayload], ...]:
    """Return layer/payload pairs aligned to the resolved plan order."""

    if not isinstance(request.layer_payloads, cabc.Mapping):
        raise ExportPayloadValidationError("layer_payloads must be a mapping keyed by output_layer_id.")

    plan_layers = tuple(sorted(request.plan.layers, key=lambda item: item.output_layer_id))
    if not plan_layers:
        raise ExportPayloadValidationError("Resolved plan does not contain exportable layers.")

    payload_keys: set[str] = set()
    for key in request.layer_payloads.keys():
        if not isinstance(key, str) or not key:
            raise ExportPayloadValidationError(
                "layer_payloads keys must be non-empty output_layer_id strings."
            )
        payload_keys.add(key)
    expected_keys = {layer.output_layer_id for layer in plan_layers}

    missing = sorted(expected_keys - payload_keys)
    if missing:
        raise ExportPayloadValidationError(
            f"Missing prepared payload(s) for output_layer_id(s): {missing}."
        )

    extra = sorted(payload_keys - expected_keys)
    if extra:
        raise ExportPayloadValidationError(
            f"Received payload(s) for unknown output_layer_id(s): {extra}."
        )

    pairs: list[tuple[ResolvedLayerPlan, PreparedLayerPayload]] = []
    for layer in plan_layers:
        payload = request.layer_payloads[layer.output_layer_id]
        if not isinstance(payload, PreparedLayerPayload):
            raise ExportPayloadValidationError(
                f"Payload for {layer.output_layer_id!r} must be PreparedLayerPayload, "
                f"received {type(payload).__name__}."
            )
        if payload.output_layer_id != layer.output_layer_id:
            raise ExportPayloadValidationError(
                "Prepared payload output_layer_id mismatch for "
                f"{layer.output_layer_id!r}: payload has {payload.output_layer_id!r}."
            )
        pairs.append((layer, payload))

    return tuple(pairs)


def build_container_payload_bytes(
    format_token: str,
    layer_payload_pairs: cabc.Sequence[tuple[ResolvedLayerPlan, PreparedLayerPayload]],
) -> bytes:
    """Build deterministic synthesized container bytes from prepared layer payloads."""

    payload = {
        "format": format_token,
        "layers": [
            {
                "layer_id": layer.layer_id,
                "output_layer_id": layer.output_layer_id,
                "scope": layer.scope,
                "scope_class": layer.scope_class,
                "row_count": prepared.row_count,
                "feature_count": prepared.feature_count,
                "payload_sha256": prepared.payload_sha256(),
            }
            for layer, prepared in layer_payload_pairs
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def merge_warnings(
    *warning_groups: cabc.Sequence[ExportWarning],
) -> tuple[ExportWarning, ...]:
    """Merge warning sequences while preserving deterministic order."""

    merged: list[ExportWarning] = []
    for group in warning_groups:
        for warning in group:
            if not isinstance(warning, ExportWarning):
                raise TypeError(
                    "warning groups must contain ExportWarning entries, "
                    f"received {type(warning).__name__}."
                )
            merged.append(warning)
    return tuple(merged)


def payload_warnings(
    layer_payload_pairs: cabc.Sequence[tuple[ResolvedLayerPlan, PreparedLayerPayload]],
) -> tuple[ExportWarning, ...]:
    """Return payload warnings in resolved layer order."""

    warnings: list[ExportWarning] = []
    for _, payload in layer_payload_pairs:
        warnings.extend(payload.warnings)
    return tuple(warnings)


def container_layer_outputs(
    *,
    format_token: str,
    relpath: str,
    layer_payload_pairs: cabc.Sequence[tuple[ResolvedLayerPlan, PreparedLayerPayload]],
) -> tuple[ExportedLayerArtifact, ...]:
    """Return per-layer metadata for multi-layer container outputs."""

    return tuple(
        ExportedLayerArtifact(
            layer_id=layer.layer_id,
            output_layer_id=layer.output_layer_id,
            scope=layer.scope,
            scope_class=layer.scope_class,
            format=format_token,
            relpath=relpath,
            row_count=payload.row_count,
            feature_count=payload.feature_count,
        )
        for layer, payload in layer_payload_pairs
    )


class SingleLayerZipWriter(ExportWriter):
    """Common behavior for single-layer-per-file formats that return one zip bundle."""

    layer_extension: str

    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        if not isinstance(self.layer_extension, str) or not self.layer_extension:
            raise FeaturesExportWriterError(
                f"{self.__class__.__name__} must define non-empty layer_extension."
            )

        artifact_dir = request.artifact_dir_path()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        layer_pairs = resolve_layer_payload_pairs(request)
        per_layer_files: dict[str, Path] = {}
        layer_outputs: list[ExportedLayerArtifact] = []

        for layer, payload in layer_pairs:
            layer_filename = deterministic_layer_filename(layer.output_layer_id, self.layer_extension)
            layer_path = artifact_dir / layer_filename
            layer_path.write_bytes(payload.payload_bytes())
            per_layer_files[layer_filename] = layer_path

            layer_outputs.append(
                ExportedLayerArtifact(
                    layer_id=layer.layer_id,
                    output_layer_id=layer.output_layer_id,
                    scope=layer.scope,
                    scope_class=layer.scope_class,
                    format=self.format_token,
                    relpath=layer_filename,
                    row_count=payload.row_count,
                    feature_count=payload.feature_count,
                )
            )

        bundle_filename = f"{request.artifact_basename}.{self.format_token}.zip"
        bundle_path = artifact_dir / bundle_filename

        from .packaging import package_files_as_zip

        packaged_member_relpaths = package_files_as_zip(bundle_path, per_layer_files)

        warnings = merge_warnings(
            request.plan.warnings,
            payload_warnings(layer_pairs),
        )
        return ExportArtifactMetadata(
            format=self.format_token,
            artifact_relpath=bundle_filename,
            artifact_path=str(bundle_path),
            layer_outputs=tuple(layer_outputs),
            warnings=warnings,
            packaged_member_relpaths=packaged_member_relpaths,
        )


class MultiLayerContainerWriter(ExportWriter):
    """Common behavior for writers that emit a single multi-layer container file."""

    container_extension: str

    def build_container_bytes(
        self,
        request: ExportWriterRequest,
        layer_payload_pairs: cabc.Sequence[tuple[ResolvedLayerPlan, PreparedLayerPayload]],
    ) -> bytes:
        return build_container_payload_bytes(self.format_token, layer_payload_pairs)

    def container_filename(self, request: ExportWriterRequest) -> str:
        suffix = (
            self.container_extension
            if self.container_extension.startswith(".")
            else f".{self.container_extension}"
        )
        return f"{request.artifact_basename}{suffix}"

    def write(self, request: ExportWriterRequest) -> ExportArtifactMetadata:
        if not isinstance(self.container_extension, str) or not self.container_extension:
            raise FeaturesExportWriterError(
                f"{self.__class__.__name__} must define non-empty container_extension."
            )

        artifact_dir = request.artifact_dir_path()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        layer_pairs = resolve_layer_payload_pairs(request)
        container_filename = self.container_filename(request)
        container_path = artifact_dir / container_filename
        container_path.write_bytes(self.build_container_bytes(request, layer_pairs))

        warnings = merge_warnings(
            request.plan.warnings,
            payload_warnings(layer_pairs),
        )
        return ExportArtifactMetadata(
            format=self.format_token,
            artifact_relpath=container_filename,
            artifact_path=str(container_path),
            layer_outputs=container_layer_outputs(
                format_token=self.format_token,
                relpath=container_filename,
                layer_payload_pairs=layer_pairs,
            ),
            warnings=warnings,
            packaged_member_relpaths=(container_filename,),
        )


__all__ = [
    "ExportArtifactMetadata",
    "ExportBackendCapabilityError",
    "ExportPayloadValidationError",
    "ExportWriter",
    "ExportWriterRequest",
    "ExportedLayerArtifact",
    "FeaturesExportWriterError",
    "MultiLayerContainerWriter",
    "PreparedLayerPayload",
    "SingleLayerZipWriter",
    "build_container_payload_bytes",
    "container_layer_outputs",
    "deterministic_layer_filename",
    "merge_warnings",
    "payload_warnings",
    "resolve_layer_payload_pairs",
]
