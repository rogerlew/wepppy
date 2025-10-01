import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional, Sequence, Dict, Tuple, List, Iterable


class WatershedCollection(object):
    """
    Represents a collection of watersheds defined in a GeoJSON file.
    """
    def __init__(self, geojson_filepath: str):
        self._geojson_filepath = geojson_filepath
        self._analysis_results = None
        self._load_geojson()

    def _load_geojson(self) -> None:
        with open(self._geojson_filepath, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise ValueError("GeoJSON resource must be a FeatureCollection")
        features = payload.get("features", [])
        if not isinstance(features, list) or not features:
            raise ValueError("GeoJSON resource contains no features")
        self.geojson_features = features
        self.data = payload

    @property
    def geojson_filepath(self) -> str:
        return self._geojson_filepath

    def _analyze_geojson(self) -> Dict[str, Any]:
        data = self.data
        checksum = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
        data_size_bytes = len(json.dumps(data).encode("utf-8"))

        features = self.geojson_features

        if not isinstance(data, dict):
            raise ValueError("GeoJSON payload must be an object")
        if data.get("type") != "FeatureCollection":
            raise ValueError("GeoJSON must be a FeatureCollection")

        features = data.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("GeoJSON FeatureCollection requires a non-empty 'features' array")

        bbox = self._calculate_bbox()
        epsg_code, epsg_source = self._extract_epsg()
        schema = self._build_property_schema()

        self._analysis_results = {
            "_geojson_filepath": self._geojson_filepath,
            "feature_count": len(features),
            "bbox": bbox,
            "epsg": epsg_code,
            "epsg_source": epsg_source,
            "properties": sorted(schema.keys()),
            "attribute_schema": schema,
            "sample_properties": self._sample_properties(limit=5),
            "checksum": checksum,
            "size_bytes": data_size_bytes,
        }

        return self._analysis_results

    def update_analysis_results(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update the analysis results with new metadata."""
        if not hasattr(self, "_analysis"):
            self._analyze_geojson()
        self._analysis_results.update(metadata)
        return self._analysis_results

    @classmethod
    def load_from_analysis_results(cls, analysis: Dict[str, Any]) -> None:
        """Load analysis results from a previously saved dictionary."""
        geojson_filepath = analysis.get("_geojson_filepath")
        if not geojson_filepath or not isinstance(geojson_filepath, str):
            raise ValueError("Invalid analysis results: missing or invalid '_geojson_filepath'")

        instance = WatershedCollection(geojson_filepath)
        instance._analysis_results = analysis
        return instance

    @property
    def analysis_results(self) -> Dict[str, Any]:
        """Get the analysis results, computing them if necessary."""
        if not hasattr(self, "_analysis"):
            self._analyze_geojson()
        return self._analysis_results

    def _calculate_bbox(self) -> List[float]:
        features = self.geojson_features

        min_x: Optional[float] = None
        min_y: Optional[float] = None
        max_x: Optional[float] = None
        max_y: Optional[float] = None

        for feature in features:
            geometry = feature.get("geometry") or {}
            if not geometry:
                continue
            coords = geometry.get("coordinates")
            for x, y in WatershedCollection._iter_coordinates(coords):
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
                    yield from WatershedCollection._iter_coordinates(child)
            elif len(node) >= 2 and all(isinstance(val, (int, float)) for val in node[:2]):
                yield float(node[0]), float(node[1])

    def _extract_epsg(self) -> Tuple[Optional[str], str]:
        crs = self.data.get("crs")
        if isinstance(crs, dict):
            name = crs.get("name")
            if not name and isinstance(crs.get("properties"), dict):
                name = crs["properties"].get("name")
            if isinstance(name, str):
                match = re.search(r"EPSG[:/](\d+)", name, flags=re.IGNORECASE)
                if match:
                    return f"EPSG:{match.group(1)}", "declared"
        return "EPSG:4326", "default"

    def _build_property_schema(self) -> Dict[str, str]:
        schema: Dict[str, str] = {}
        for feature in self.geojson_features:
            props = feature.get("properties") or {}
            if not isinstance(props, dict):
                continue
            for key, value in props.items():
                dtype = WatershedCollection._infer_type(value)
                existing = schema.get(key)
                if existing is None:
                    schema[key] = dtype
                elif existing != dtype:
                    schema[key] = "mixed"
        return schema
    
    def _sample_properties(self, limit: int = 5) -> List[Dict[str, Any]]:
        samples: List[Dict[str, Any]] = []
        for idx, feature in enumerate(self.geojson_features):
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
        feature_context: Dict[str, Any],
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
                expr, new_index = WatershedCollection._extract_expression(template, i + 1)
                value = WatershedCollection._render_expression(expr, feature_context, allowed_functions)
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
        expression, format_spec = WatershedCollection._split_format(expr)
        value = WatershedCollection._safe_eval(expression, context, allowed_functions)
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

    def template_feature_context(self, index: int) -> Dict[str, Any]:
        feature = self.geojson_features[index]
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        return {
            "feature": feature,
            "properties": properties,
            "index": index,
            "one_based_index": index + 1,
        }

    @property
    def checksum(self): 
        return self.analysis_results.get("checksum")

    def validate_template(
        self,
        template: str,
        preview_limit: int = 20,
    ) -> Dict[str, Any]:
        resource_checksum = self.checksum

        features = self.geojson_features
        if not template or not template.strip():
            raise ValueError("template is required")
        if not isinstance(features, list) or not features:
            raise ValueError("features must be a non-empty list")

        allowed_functions = self.default_template_functions()
        rows: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        duplicates: Dict[str, List[int]] = {}

        for index, feature in enumerate(features):
            feature_context = self.template_feature_context(index)
            try:
                rendered = self.evaluate_template(template, feature_context, allowed_functions=allowed_functions)
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
