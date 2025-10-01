"""NoDb scaffolding for the Batch Runner feature."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from copy import deepcopy
from pathlib import Path
import shutil
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .base import NoDbBase


class BatchRunner(NoDbBase):
    """NoDb controller for batch runner state."""

    __name__ = "BatchRunner"
    filename = "batch_runner.nodb"

    RESOURCE_WATERSHED = "watershed_geojson"

    _DEFAULT_STATE = {
        "batch_name": None,
        "batch_config": None,
        "config": None,
        "base_config": None,
        "created_at": None,
        "created_by": None,
        "runid_template": None,
        "selected_tasks": [],
        "force_rebuild": False,
        "runs": {},
        "history": [],
        "resources": {},
        "control_hashes": {},
        "metadata": {},
        "template_validation": None,
        "state_version": 2,
    }

    def __init__(self, wd: str, batch_config: str, base_config: str):
        super().__init__(wd, batch_config)
        with self.locked():
            self._base_config = base_config
            self._ensure_defaults()

        self._init_base_project()

        os.makedirs(self.batch_runs_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # core helpers
    # ------------------------------------------------------------------
    def _ensure_defaults(self) -> None:
        for key, value in self._DEFAULT_STATE.items():
            if not hasattr(self, key):
                setattr(self, key, deepcopy(value))
        # base_config stored separately for runtime use, but expose alias
        if self.base_config is None:
            self.base_config = self._normalize_config_name(self._base_config)
        if self.config is None:
            self.config = self.base_config
        if self.batch_config is None:
            self.batch_config = self._normalize_config_name(getattr(self, "_config", None))

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------
    @property
    def _base_wd(self) -> str:
        return os.path.join(self.wd, "_base")

    @property
    def base_config(self) -> Optional[str]:
        return getattr(self, "_base_config_name", None)

    @base_config.setter
    def base_config(self, value: Optional[str]) -> None:
        self._base_config_name = value

    @property
    def batch_runs_dir(self) -> str:
        return os.path.join(self.wd, "runs")

    @property
    def resources_dir(self) -> str:
        return os.path.join(self.wd, "resources")

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------
    def _init_base_project(self) -> None:
        from wepppy.nodb.ron import Ron

        if os.path.exists(self._base_wd):
            shutil.rmtree(self._base_wd)
        os.makedirs(self._base_wd)
        Ron(self._base_wd, self._base_config)

    def reset_state(self) -> None:
        with self.locked():
            for key in self._DEFAULT_STATE:
                setattr(self, key, deepcopy(self._DEFAULT_STATE[key]))
            self._ensure_defaults()

    def update_state(self, **updates: Any) -> None:
        if not updates:
            return
        with self.locked():
            self._ensure_defaults()
            for key, value in updates.items():
                if key in self._DEFAULT_STATE:
                    setattr(self, key, value)
                else:
                    self.metadata[key] = value

    def add_history(self, entry: Dict[str, Any]) -> None:
        if not isinstance(entry, dict):
            raise TypeError("history entry must be a mapping")
        with self.locked():
            self._ensure_defaults()
            self.history.append(deepcopy(entry))

    # ------------------------------------------------------------------
    # resource registration & template validation
    # ------------------------------------------------------------------
    def register_resource(
        self,
        resource_id: str,
        payload: Dict[str, Any],
        *,
        user: Optional[str] = None,
        replaced: bool = False,
    ) -> Dict[str, Any]:
        if not resource_id:
            raise ValueError("resource_id is required")
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        timestamp = datetime.now(timezone.utc).isoformat()

        with self.locked():
            self._ensure_defaults()

            resources = self.resources
            existing = resources.get(resource_id)

            payload_copy = dict(payload)
            payload_copy.setdefault("resource_id", resource_id)
            payload_copy.setdefault("uploaded_at", timestamp)
            if user:
                payload_copy.setdefault("uploaded_by", user)
            payload_copy["replaced"] = bool(replaced or existing is not None)

            resources[resource_id] = payload_copy

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
            self.history.append(history_event)

            validation_state = self.template_validation
            if validation_state and validation_state.get("resource_id") == resource_id:
                if (
                    payload_copy.get("checksum")
                    and validation_state.get("resource_checksum")
                    and validation_state["resource_checksum"] != payload_copy.get("checksum")
                ):
                    validation_state["status"] = "stale"
                    validation_state["stale_since"] = timestamp
                else:
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
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        timestamp = datetime.now(timezone.utc).isoformat()

        with self.locked():
            self._ensure_defaults()

            payload_copy = dict(payload)
            payload_copy.setdefault("validated_at", timestamp)
            if user:
                payload_copy.setdefault("validated_by", user)
            payload_copy.setdefault("status", "ok")

            self.template_validation = payload_copy

            history_event = {
                "event": "template_validated",
                "timestamp": timestamp,
                "template_hash": payload_copy.get("template_hash"),
                "resource_checksum": payload_copy.get("resource_checksum"),
            }
            if user:
                history_event["user"] = user
            self.history.append(history_event)

            self.logger.info(
                "Recorded template validation (status=%s)",
                payload_copy.get("status", "unknown"),
            )
            return payload_copy

    # ------------------------------------------------------------------
    # serialisation helpers
    # ------------------------------------------------------------------
    def state_dict(self) -> Dict[str, Any]:
        self._ensure_defaults()
        return {
            key: deepcopy(getattr(self, key))
            for key in self._DEFAULT_STATE
        }

    @classmethod
    def default_state(cls) -> Dict[str, Any]:
        return {key: deepcopy(value) for key, value in cls._DEFAULT_STATE.items()}

    # ------------------------------------------------------------------
    # static helpers (geojson analysis & templating)
    # ------------------------------------------------------------------
    @staticmethod
    def compute_file_checksum(path: Path, chunk_size: int = 1024 * 1024) -> Tuple[int, str]:
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
        if format_spec:
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
                    for arg in node.args:
                        self.visit(arg)
                    for keyword in node.keywords:
                        if keyword.arg:
                            self.visit(keyword.value)
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

                if isinstance(node, ast.Name) and node.id not in allowed_names:
                    raise ValueError(f"Unknown name '{node.id}' in template expression")

                for child in ast.iter_child_nodes(node):
                    self.visit(child)

        Validator().visit(node)

        safe_globals = {name: fn for name, fn in allowed_functions.items()}
        safe_globals["__builtins__"] = {}
        return eval(compile(node, "<template>", "eval"), safe_globals, context)

    @staticmethod
    def default_template_functions() -> Dict[str, Any]:
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
            except Exception as exc:  # noqa: BLE001
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

    @staticmethod
    def _normalize_config_name(config: Optional[str]) -> Optional[str]:
        if not config:
            return None
        return Path(config).stem


__all__ = ["BatchRunner"]
