#!/usr/bin/env python3
"""Validate route inventory drift against the frozen endpoint inventory artifact."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys

INVENTORY_FILE = Path(
    "docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md"
)

_ALLOWED_CLASSIFICATIONS = {"agent-facing", "internal", "ui-only"}
_ALLOWED_OWNERS = {"rq-engine", "Flask wrapper"}


@dataclass(frozen=True)
class RouteRecord:
    method: str
    path: str
    module: str
    function: str
    lineno: int | None = None


@dataclass(frozen=True)
class InventoryRecord:
    method: str
    path: str
    module: str
    function: str
    classification: str
    owner: str


def _join_prefix(prefix: str, path: str) -> str:
    if not prefix:
        return path
    return f"{prefix.rstrip('/')}{path}"


def _strip_markdown_code(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped


def _split_module_ref(module_ref: str) -> tuple[str, int | None]:
    module_ref = module_ref.strip()
    if ":" not in module_ref:
        return module_ref, None

    module_path, maybe_lineno = module_ref.rsplit(":", 1)
    if maybe_lineno.isdigit():
        return module_path, int(maybe_lineno)
    return module_ref, None


def _extract_rq_router_prefixes(repo_root: Path) -> dict[str, str]:
    init_path = repo_root / "wepppy/microservices/rq_engine/__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))

    alias_to_module: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level < 1:
            continue
        if not node.module:
            continue

        module_name = node.module
        for alias in node.names:
            if alias.name != "router":
                continue
            alias_to_module[alias.asname or alias.name] = module_name

    module_to_prefix: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Attribute) or call.func.attr != "include_router":
            continue
        if not call.args or not isinstance(call.args[0], ast.Name):
            continue

        router_alias = call.args[0].id
        module_name = alias_to_module.get(router_alias)
        if module_name is None:
            continue

        prefix = ""
        for keyword in call.keywords:
            if keyword.arg != "prefix":
                continue
            if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                prefix = keyword.value.value
        module_to_prefix[module_name] = prefix

    return module_to_prefix


def _extract_rq_engine_routes(repo_root: Path) -> list[RouteRecord]:
    module_to_prefix = _extract_rq_router_prefixes(repo_root)
    routes: list[RouteRecord] = []

    for module_name, prefix in sorted(module_to_prefix.items()):
        module_path = repo_root / f"wepppy/microservices/rq_engine/{module_name}.py"
        if not module_path.exists():
            continue

        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not isinstance(decorator.func, ast.Attribute):
                    continue
                if not isinstance(decorator.func.value, ast.Name):
                    continue
                if decorator.func.value.id != "router":
                    continue

                method = decorator.func.attr.upper()
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
                    continue
                if not decorator.args:
                    continue

                first_arg = decorator.args[0]
                if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                    continue

                raw_path = first_arg.value
                full_path = _join_prefix(prefix, raw_path)
                routes.append(
                    RouteRecord(
                        method=method,
                        path=full_path,
                        module=f"wepppy/microservices/rq_engine/{module_name}.py",
                        function=node.name,
                        lineno=node.lineno,
                    )
                )

    init_path = repo_root / "wepppy/microservices/rq_engine/__init__.py"
    init_tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    for node in init_tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name):
                continue
            if decorator.func.value.id != "app":
                continue
            method = decorator.func.attr.upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
                continue
            if not decorator.args:
                continue
            first_arg = decorator.args[0]
            if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                continue
            routes.append(
                RouteRecord(
                    method=method,
                    path=first_arg.value,
                    module="wepppy/microservices/rq_engine/__init__.py",
                    function=node.name,
                    lineno=node.lineno,
                )
            )

    return routes


def _extract_flask_bootstrap_routes(repo_root: Path) -> list[RouteRecord]:
    bootstrap_path = repo_root / "wepppy/weppcloud/routes/bootstrap.py"
    tree = ast.parse(bootstrap_path.read_text(encoding="utf-8"), filename=str(bootstrap_path))

    routes: list[RouteRecord] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name):
                continue
            if decorator.func.value.id != "bootstrap_bp" or decorator.func.attr != "route":
                continue
            if not decorator.args:
                continue

            first_arg = decorator.args[0]
            if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                continue

            path = first_arg.value
            methods = ["GET"]
            for keyword in decorator.keywords:
                if keyword.arg != "methods":
                    continue
                if isinstance(keyword.value, (ast.List, ast.Tuple)):
                    resolved: list[str] = []
                    for item in keyword.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            resolved.append(item.value.upper())
                    if resolved:
                        methods = resolved

            for method in methods:
                routes.append(
                    RouteRecord(
                        method=method,
                        path=path,
                        module="wepppy/weppcloud/routes/bootstrap.py",
                        function=node.name,
                        lineno=node.lineno,
                    )
                )

    return routes


def _parse_inventory(repo_root: Path) -> dict[tuple[str, str], InventoryRecord]:
    inventory_path = repo_root / INVENTORY_FILE
    lines = inventory_path.read_text(encoding="utf-8").splitlines()

    in_table = False
    records: dict[tuple[str, str], InventoryRecord] = {}

    for line in lines:
        if line.strip().startswith("| Method | Path | Module | Function | Classification | Owner |"):
            in_table = True
            continue

        if not in_table:
            continue

        stripped = line.strip()
        if not stripped.startswith("|"):
            if records:
                break
            continue
        if stripped.startswith("|---"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6:
            continue

        method, path, module, function, classification, owner = cells[:6]
        method = _strip_markdown_code(method).upper()
        path = _strip_markdown_code(path)
        module = _strip_markdown_code(module)
        function = _strip_markdown_code(function)
        classification = _strip_markdown_code(classification)
        owner = _strip_markdown_code(owner)
        key = (method.upper(), path)
        records[key] = InventoryRecord(
            method=method.upper(),
            path=path,
            module=module,
            function=function,
            classification=classification,
            owner=owner,
        )

    return records


def collect_inventory_issues(repo_root: Path | None = None) -> list[str]:
    root = repo_root or Path(__file__).resolve().parents[1]

    extracted_routes = _extract_rq_engine_routes(root) + _extract_flask_bootstrap_routes(root)
    extracted_keys = {(route.method, route.path) for route in extracted_routes}
    extracted_by_key = {(route.method, route.path): route for route in extracted_routes}

    inventory_records = _parse_inventory(root)
    inventory_keys = set(inventory_records)

    issues: list[str] = []

    for key in sorted(extracted_keys - inventory_keys):
        issues.append(f"Route missing from inventory: {key[0]} {key[1]}")

    for key in sorted(inventory_keys - extracted_keys):
        issues.append(f"Inventory route not found in source: {key[0]} {key[1]}")

    for key in sorted(inventory_keys):
        record = inventory_records[key]
        route = extracted_by_key.get(key)
        if not record.classification or record.classification not in _ALLOWED_CLASSIFICATIONS:
            issues.append(
                "Inventory classification missing/invalid for "
                f"{record.method} {record.path}: {record.classification!r}"
            )
        if not record.owner or record.owner not in _ALLOWED_OWNERS:
            issues.append(
                "Inventory owner missing/invalid for "
                f"{record.method} {record.path}: {record.owner!r}"
            )
        if route is None:
            continue

        inventory_module_path, inventory_lineno = _split_module_ref(record.module)
        if inventory_module_path != route.module:
            issues.append(
                "Inventory module mismatch for "
                f"{record.method} {record.path}: inventory={inventory_module_path!r} "
                f"source={route.module!r}"
            )
        if inventory_lineno is not None and route.lineno is not None and inventory_lineno != route.lineno:
            issues.append(
                "Inventory module line mismatch for "
                f"{record.method} {record.path}: inventory={inventory_lineno} source={route.lineno}"
            )
        if record.function != route.function:
            issues.append(
                "Inventory function mismatch for "
                f"{record.method} {record.path}: inventory={record.function!r} "
                f"source={route.function!r}"
            )

    return issues


def main() -> int:
    issues = collect_inventory_issues()
    if not issues:
        print("Endpoint inventory check passed")
        return 0

    print("Endpoint inventory drift detected:")
    for issue in issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
