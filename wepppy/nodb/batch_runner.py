"""NoDb scaffolding for the Batch Runner feature (Phase 0).

Provides a minimal manifest container so subsequent phases can persist
batch metadata using the existing NoDb infrastructure without yet
implementing orchestration logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .base import NoDbBase


@dataclass
class BatchRunnerManifest:
    """Lightweight manifest for batch runner state."""

    version: int = 2
    batch_name: Optional[str] = None
    config: Optional[str] = None
    batch_config: Optional[str] = None
    base_config: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    runid_template: Optional[str] = None
    selected_tasks: List[str] = field(default_factory=list)
    force_rebuild: bool = False
    runs: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    control_hashes: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return asdict(self)


class BatchRunner(NoDbBase):
    """NoDb stub for the batch runner controller."""

    __name__ = "BatchRunner"
    filename = "batch_runner.nodb"
    RESOURCE_WATERSHED = "watershed_geojson"

    def __init__(self, wd: str,
                 batch_config: str,
                 base_config: str):
        super().__init__(wd, batch_config)
        with self.locked():
            if not hasattr(self, "_manifest") or self._manifest is None:
                self._manifest = BatchRunnerManifest()
            self._base_config = base_config
            self._manifest = self._apply_defaults(self._manifest)

        self._init_base_project()

        os.makedirs(self.batch_runs_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)

    #
    # resource + template handling
    #

    def register_resource(
        self,
        resource_id: str,
        payload: Dict[str, Any],
        *,
        user: Optional[str] = None,
        replaced: bool = False,
    ) -> Dict[str, Any]:
        """Persist resource metadata and append a history entry."""
        if not resource_id:
            raise ValueError("resource_id is required")
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        timestamp = datetime.now(timezone.utc).isoformat()

        with self.locked():
            manifest = self._manifest
            manifest = self._apply_defaults(manifest)

            existing = manifest.resources.get(resource_id)
            payload_copy = dict(payload)
            payload_copy.setdefault("resource_id", resource_id)
            payload_copy.setdefault("uploaded_at", timestamp)
            if user:
                payload_copy.setdefault("uploaded_by", user)
            payload_copy["replaced"] = bool(replaced or existing is not None)

            manifest.resources[resource_id] = payload_copy

            history_event = {
                "event": "resource_uploaded",
                "timestamp": timestamp,
                "resource_id": resource_id,
                "replaced": payload_copy["replaced"],
            }
            if user:
                history_event["user"] = user
            if "filename" in payload_copy:
                history_event["filename"] = payload_copy["filename"]
            manifest.history.append(history_event)

            validation_state = manifest.metadata.get("template_validation")
            if validation_state:
                if validation_state.get("resource_id") == resource_id and (
                    payload_copy.get("checksum")
                    and validation_state.get("resource_checksum")
                    and validation_state["resource_checksum"] != payload_copy.get("checksum")
                ):
                    validation_state["status"] = "stale"
                    validation_state["stale_since"] = timestamp
                elif validation_state.get("resource_id") == resource_id:
                    validation_state["status"] = "stale"
                    validation_state["stale_since"] = timestamp

            self.logger.info(
                "Registered resource '%s' (replaced=%s)",
                resource_id,
                payload_copy["replaced"],
            )
            return payload_copy

    def record_template_validation(
        self,
        payload: Dict[str, Any],
        *,
        user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist template validation metadata."""
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        timestamp = datetime.now(timezone.utc).isoformat()

        with self.locked():
            manifest = self._manifest
            manifest = self._apply_defaults(manifest)

            payload_copy = dict(payload)
            payload_copy.setdefault("validated_at", timestamp)
            if user:
                payload_copy.setdefault("validated_by", user)
            payload_copy.setdefault("status", "ok")
            payload_copy.setdefault("stale", False)
            payload_copy.pop("stale", None)  # prefer status flag only

            manifest.metadata["template_validation"] = payload_copy

            history_event = {
                "event": "template_validated",
                "timestamp": timestamp,
                "template_hash": payload_copy.get("template_hash"),
                "resource_checksum": payload_copy.get("resource_checksum"),
            }
            if user:
                history_event["user"] = user
            manifest.history.append(history_event)

            self.logger.info(
                "Recorded template validation (status=%s)",
                payload_copy.get("status", "unknown"),
            )
            return payload_copy

    #
    # manifest properties and methods, managed primarily by codex
    #

    def _init_base_project(self) -> None:
        from wepppy.nodb.ron import Ron
        if os.path.exists(self._base_wd):
            shutil.rmtree(self._base_wd)
        os.makedirs(self._base_wd)
        Ron(self._base_wd, self.base_config)

    @property
    def _base_wd(self) -> str:
        """Return the base working directory."""
        return os.path.join(self.wd, "_base")

    @property
    def base_config(self) -> str:
        """Return the base config for create _base"""
        return self._base_config

    @property
    def batch_runs_dir(self) -> str:
        """Return the directory where batch runs are stored."""
        return os.path.join(self.wd, "runs")
    
    @property
    def resources_dir(self) -> str:
        """Return the directory where resources are stored."""
        return os.path.join(self.wd, "resources")

    #
    # manifest properties and methods, managed primarily by codex
    #
    @property
    def manifest(self) -> BatchRunnerManifest:
        """Return the in-memory manifest object."""
        return self._manifest

    def manifest_dict(self) -> Dict[str, Any]:
        """Return the manifest as a primitive dictionary."""
        return self._manifest.to_dict()

    def reset_manifest(self) -> BatchRunnerManifest:
        """Reset the manifest back to default values."""
        with self.locked():
            self._manifest = self._apply_defaults(BatchRunnerManifest())
            return self._manifest

    def update_manifest(self, **updates: Any) -> BatchRunnerManifest:
        """Apply shallow updates to the manifest (Phase 0 placeholder)."""
        if not updates:
            return self._manifest

        with self.locked():
            for key, value in updates.items():
                if hasattr(self._manifest, key):
                    setattr(self._manifest, key, value)
                else:
                    self._manifest.metadata[key] = value
            return self._manifest

    @classmethod
    def default_manifest(cls) -> BatchRunnerManifest:
        """Convenience helper for creating a detached default manifest."""
        return BatchRunnerManifest()

    @classmethod
    def _post_instance_loaded(cls, instance: "BatchRunner") -> "BatchRunner":
        """Backfill config identifiers when decoding persisted manifests."""
        instance._manifest = instance._apply_defaults(instance._manifest)
        return instance

    @staticmethod
    def _normalize_config_name(config: str) -> Optional[str]:
        """Return a stemmed config name, keeping None intact."""
        if not config:
            return None
        stem = Path(config).stem
        return stem

    def _apply_defaults(self, manifest: BatchRunnerManifest) -> BatchRunnerManifest:
        """Ensure manifest carries canonical configuration identifiers and versioning."""
        base_config_name = self._normalize_config_name(self._base_config)
        batch_config_name = self._normalize_config_name(getattr(self, "_config", None))

        if manifest.base_config is None:
            manifest.base_config = base_config_name

        if manifest.config is None:
            manifest.config = base_config_name

        if manifest.batch_config is None:
            manifest.batch_config = batch_config_name

        if not manifest.version or manifest.version < 2:
            manifest.version = 2

        return manifest

    #
    # static helpers for resource analysis & templating
    #

    @staticmethod
    def compute_file_checksum(path: Path, chunk_size: int = 1024 * 1024) -> Tuple[int, str]:
        """Return file size and sha256 checksum."""
        hasher = hashlib.sha256()
        size = 0
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                hasher.update(chunk)
        return size, hasher.hexdigest()

    @classmethod
    def analyse_geojson(cls, path: Path) -> Dict[str, Any]:
        """Compute metadata for a GeoJSON FeatureCollection."""
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError("GeoJSON payload must be an object")

        if data.get("type") != "FeatureCollection":
            raise ValueError("GeoJSON must be a FeatureCollection")

        features = data.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("GeoJSON FeatureCollection requires a non-empty 'features' array")

        bbox = cls._calculate_bbox(features)
        epsg_code, epsg_source = cls._extract_epsg(data)
        schema = cls._build_property_schema(features)

        return {
            "feature_count": len(features),
            "bbox": bbox,
            "epsg": epsg_code,
            "epsg_source": epsg_source,
            "properties": sorted(schema.keys()),
            "attribute_schema": schema,
            "sample_properties": cls._sample_properties(features, limit=5),
        }

    @staticmethod
    def _calculate_bbox(features: Iterable[Dict[str, Any]]) -> List[float]:
        min_x: Optional[float] = None
        min_y: Optional[float] = None
        max_x: Optional[float] = None
        max_y: Optional[float] = None

        for feature in features:
            geometry = feature.get("geometry") or {}
            if not geometry:
                continue
            coords = geometry.get("coordinates")
            for x, y in BatchRunner._iter_coordinates(coords):
                if min_x is None or x < min_x:
                    min_x = x
                if min_y is None or y < min_y:
                    min_y = y
                if max_x is None or x > max_x:
                    max_x = x
                if max_y is None or y > max_y:
                    max_y = y

        if None in (min_x, min_y, max_x, max_y):
            raise ValueError("Unable to determine bounding box from GeoJSON geometry")
        return [float(min_x), float(min_y), float(max_x), float(max_y)]

    @staticmethod
    def _iter_coordinates(node: Any) -> Iterable[Tuple[float, float]]:
        if node is None:
            return
        if isinstance(node, (list, tuple)):
            if node and isinstance(node[0], (list, tuple)):
                for child in node:
                    yield from BatchRunner._iter_coordinates(child)
            elif len(node) >= 2 and all(isinstance(val, (int, float)) for val in node[:2]):
                yield float(node[0]), float(node[1])
        # other types ignored

    @staticmethod
    def _extract_epsg(payload: Dict[str, Any]) -> Tuple[Optional[str], str]:
        crs = payload.get("crs")
        if isinstance(crs, dict):
            name = crs.get("name")
            if not name and isinstance(crs.get("properties"), dict):
                name = crs["properties"].get("name")
            if isinstance(name, str):
                match = re.search(r"EPSG[:/](\d+)", name, flags=re.IGNORECASE)
                if match:
                    return f"EPSG:{match.group(1)}", "declared"

        return "EPSG:4326", "default"

    @staticmethod
    def _build_property_schema(features: Iterable[Dict[str, Any]]) -> Dict[str, str]:
        schema: Dict[str, str] = {}
        for feature in features:
            props = feature.get("properties") or {}
            if not isinstance(props, dict):
                continue
            for key, value in props.items():
                dtype = BatchRunner._infer_type(value)
                existing = schema.get(key)
                if existing is None:
                    schema[key] = dtype
                elif existing != dtype:
                    schema[key] = "mixed"
        return schema

    @staticmethod
    def _sample_properties(features: Iterable[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        samples: List[Dict[str, Any]] = []
        for idx, feature in enumerate(features):
            props = feature.get("properties") or {}
            if not isinstance(props, dict):
                props = {}
            samples.append({"index": idx, "properties": props})
            if len(samples) >= limit:
                break
        return samples

    @staticmethod
    def _infer_type(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "unknown"

    @staticmethod
    def evaluate_template(
        template: str,
        context: Dict[str, Any],
        *,
        allowed_functions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render a template by evaluating expressions between braces."""
        if allowed_functions is None:
            allowed_functions = {}

        if template is None:
            raise ValueError("template is required")

        chunks: List[str] = []
        i = 0
        length = len(template)
        while i < length:
            char = template[i]
            if char == '{':
                if i + 1 < length and template[i + 1] == '{':
                    chunks.append('{')
                    i += 2
                    continue
                expr, new_index = BatchRunner._extract_expression(template, i + 1)
                value = BatchRunner._render_expression(expr, context, allowed_functions)
                chunks.append(value)
                i = new_index
            elif char == '}':
                if i + 1 < length and template[i + 1] == '}':
                    chunks.append('}')
                    i += 2
                    continue
                raise ValueError("Single '}' encountered in format string")
            else:
                start = i
                while i < length and template[i] not in ('{', '}'):
                    i += 1
                chunks.append(template[start:i])
                continue
        return ''.join(chunks)

    @staticmethod
    def _extract_expression(template: str, start: int) -> Tuple[str, int]:
        depth = 1
        i = start
        while i < len(template) and depth:
            if template[i] == '{':
                depth += 1
            elif template[i] == '}':
                depth -= 1
                if depth == 0:
                    expr = template[start:i]
                    return expr, i + 1
            i += 1
        raise ValueError("Unmatched '{' in template")

    @staticmethod
    def _render_expression(expr: str, context: Dict[str, Any], allowed_functions: Dict[str, Any]) -> str:
        expression, format_spec = BatchRunner._split_format(expr)
        value = BatchRunner._safe_eval(expression, context, allowed_functions)
        if format_spec is not None and format_spec != "":
            return format(value, format_spec)
        return str(value)

    @staticmethod
    def _split_format(expr: str) -> Tuple[str, Optional[str]]:
        depth = 0
        in_single = False
        in_double = False
        for idx, char in enumerate(expr):
            if char == "'" and not in_double:
                in_single = not in_single
            elif char == '"' and not in_single:
                in_double = not in_double
            elif char in ('[', '(', '{') and not (in_single or in_double):
                depth += 1
            elif char in (']', ')', '}') and not (in_single or in_double):
                depth = max(depth - 1, 0)
            elif char == ':' and depth == 0 and not in_single and not in_double:
                return expr[:idx].strip(), expr[idx + 1 :].strip()
        return expr.strip(), None

    @staticmethod
    def _safe_eval(expr: str, context: Dict[str, Any], allowed_functions: Dict[str, Any]) -> Any:
        import ast

        allowed_names = set(context.keys()) | set(allowed_functions.keys())

        node = ast.parse(expr, mode="eval")

        class Validator(ast.NodeVisitor):
            allowed_nodes = (
                ast.Expression,
                ast.BinOp,
                ast.UnaryOp,
                ast.BoolOp,
                ast.Compare,
                ast.IfExp,
                ast.Name,
                ast.Load,
                ast.Constant,
                ast.Subscript,
                ast.Index,
                ast.Slice,
                ast.List,
                ast.Tuple,
                ast.Dict,
                ast.Set,
                ast.JoinedStr,
                ast.FormattedValue,
            )

            allowed_binops = (
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.Mod,
                ast.Pow,
                ast.FloorDiv,
            )

            allowed_unary = (ast.UAdd, ast.USub, ast.Not)

            allowed_bool = (ast.And, ast.Or)

            allowed_cmp = (
                ast.Eq,
                ast.NotEq,
                ast.Lt,
                ast.LtE,
                ast.Gt,
                ast.GtE,
                ast.In,
                ast.NotIn,
            )

            def visit(self, node):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name):
                        if func.id not in allowed_functions:
                            raise ValueError(f"Function '{func.id}' is not permitted in templates")
                    else:
                        raise ValueError("Only named function calls are permitted in templates")
                    for keyword in node.keywords:
                        if keyword.arg not in (None, "sep", "join", "fillchar"):
                            continue
                    for arg in node.args:
                        self.visit(arg)
                    return

                if not isinstance(node, self.allowed_nodes):
                    raise ValueError(f"Unsupported expression component: {type(node).__name__}")

                if isinstance(node, ast.BinOp) and not isinstance(node.op, self.allowed_binops):
                    raise ValueError("Binary operator not permitted in template expression")

                if isinstance(node, ast.UnaryOp) and not isinstance(node.op, self.allowed_unary):
                    raise ValueError("Unary operator not permitted in template expression")

                if isinstance(node, ast.BoolOp) and not isinstance(node.op, self.allowed_bool):
                    raise ValueError("Boolean operator not permitted in template expression")

                if isinstance(node, ast.Compare):
                    for op in node.ops:
                        if not isinstance(op, self.allowed_cmp):
                            raise ValueError("Comparison operator not permitted in template expression")

                if isinstance(node, ast.Name):
                    if node.id not in allowed_names:
                        raise ValueError(f"Unknown name '{node.id}' in template expression")

                for child in ast.iter_child_nodes(node):
                    self.visit(child)

        Validator().visit(node)

        safe_globals = {name: fn for name, fn in allowed_functions.items()}
        safe_globals["__builtins__"] = {}
        return eval(compile(node, "<template>", "eval"), safe_globals, context)

    @staticmethod
    def default_template_functions() -> Dict[str, Any]:
        """Helper functions available to template expressions."""

        def slug(value: Any, *, separator: str = "-") -> str:
            text = str(value or "")
            text = text.strip()
            text = re.sub(r"[^A-Za-z0-9]+", separator, text)
            text = re.sub(rf"{re.escape(separator)}+", separator, text)
            return text.strip(separator)

        def lower(value: Any) -> str:
            return str(value or "").lower()

        def upper(value: Any) -> str:
            return str(value or "").upper()

        def title(value: Any) -> str:
            return str(value or "").title()

        def zfill(value: Any, width: int) -> str:
            return str(value or "").zfill(int(width))

        def replace(value: Any, old: str, new: str) -> str:
            return str(value or "").replace(old, new)

        return {
            "slug": slug,
            "lower": lower,
            "upper": upper,
            "title": title,
            "zfill": zfill,
            "replace": replace,
        }

    @classmethod
    def template_context(cls, feature: Dict[str, Any], index: int) -> Dict[str, Any]:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        return {
            "feature": feature,
            "properties": properties,
            "index": index,
            "one_based_index": index + 1,
        }

    @classmethod
    def validate_template(
        cls,
        template: str,
        features: List[Dict[str, Any]],
        *,
        resource_checksum: Optional[str] = None,
        preview_limit: int = 20,
    ) -> Dict[str, Any]:
        if not template or not template.strip():
            raise ValueError("template is required")
        if not isinstance(features, list) or not features:
            raise ValueError("features must be a non-empty list")

        allowed_functions = cls.default_template_functions()
        rows: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        duplicates: Dict[str, List[int]] = {}

        for index, feature in enumerate(features):
            context = cls.template_context(feature, index)
            try:
                rendered = cls.evaluate_template(template, context, allowed_functions=allowed_functions)
                rendered = str(rendered).strip()
                if not rendered:
                    raise ValueError("Template produced an empty run id")
            except Exception as exc:  # noqa: BLE001 - surface template errors
                message = str(exc)
                errors.append({
                    "index": index,
                    "feature_id": feature.get("id"),
                    "error": message,
                })
                rows.append({
                    "index": index,
                    "feature_id": feature.get("id"),
                    "run_id": None,
                    "error": message,
                })
                continue

            duplicates.setdefault(rendered, []).append(index)
            rows.append({
                "index": index,
                "feature_id": feature.get("id"),
                "run_id": rendered,
                "error": None,
            })

        duplicate_entries = [
            {
                "run_id": run_id,
                "count": len(indexes),
                "indexes": indexes,
            }
            for run_id, indexes in duplicates.items()
            if len(indexes) > 1
        ]

        summary = {
            "total_features": len(features),
            "errors": len(errors),
            "duplicate_run_ids": len(duplicate_entries),
            "unique_run_ids": len(duplicates),
            "valid_run_ids": len(features) - len(errors),
            "is_valid": not errors and not duplicate_entries,
        }

        preview = rows[: preview_limit]
        template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
        validation_key_material = template
        if resource_checksum:
            validation_key_material += f"|{resource_checksum}"
        validation_hash = hashlib.sha256(validation_key_material.encode("utf-8")).hexdigest()

        return {
            "template": template,
            "template_hash": template_hash,
            "resource_checksum": resource_checksum,
            "summary": summary,
            "errors": errors,
            "duplicates": duplicate_entries,
            "rows": rows,
            "preview": preview,
            "validation_hash": validation_hash,
        }


__all__ = ["BatchRunner", "BatchRunnerManifest"]
