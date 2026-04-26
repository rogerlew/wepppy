from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.microservice

REPO_ROOT = Path(__file__).resolve().parents[2]


def _parse_module(relpath: str) -> ast.Module:
    path = REPO_ROOT / relpath
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path))


def _get_function_node(module: ast.Module, function_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    raise AssertionError(f"Function '{function_name}' not found")


def _as_dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _as_dotted_name(node.value)
        if prefix is None:
            return None
        return f"{prefix}.{node.attr}"
    return None


def _collect_call_targets(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    call_targets: set[str] = set()
    for node in ast.walk(fn_node):
        if not isinstance(node, ast.Call):
            continue
        target = _as_dotted_name(node.func)
        if target is not None:
            call_targets.add(target)
    return call_targets


def _iter_assignment_targets(target: ast.AST):
    if isinstance(target, ast.Attribute):
        yield target
        return
    if isinstance(target, (ast.List, ast.Tuple)):
        for element in target.elts:
            yield from _iter_assignment_targets(element)


def _collect_assigned_attributes(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    assigned: set[str] = set()
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for attr in _iter_assignment_targets(target):
                    dotted = _as_dotted_name(attr)
                    if dotted is not None:
                        assigned.add(dotted)
        elif isinstance(node, ast.AnnAssign):
            for attr in _iter_assignment_targets(node.target):
                dotted = _as_dotted_name(attr)
                if dotted is not None:
                    assigned.add(dotted)
        elif isinstance(node, ast.AugAssign):
            for attr in _iter_assignment_targets(node.target):
                dotted = _as_dotted_name(attr)
                if dotted is not None:
                    assigned.add(dotted)
    return assigned


def _collect_setattr_assigned_attributes(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    assigned: set[str] = set()
    for node in ast.walk(fn_node):
        if not isinstance(node, ast.Call):
            continue
        target = _as_dotted_name(node.func)
        if target not in {"setattr", "builtins.setattr"}:
            continue
        if len(node.args) < 2:
            continue
        obj_name = _as_dotted_name(node.args[0])
        attr_name = node.args[1]
        if obj_name is None:
            continue
        if not isinstance(attr_name, ast.Constant) or not isinstance(attr_name.value, str):
            continue
        assigned.add(f"{obj_name}.{attr_name.value}")
    return assigned


def _has_call_target(call_targets: set[str], target: str) -> bool:
    return target in call_targets or any(entry.endswith(f".{target}") for entry in call_targets)


def test_apply_wepp_run_payload_uses_grouped_update_helpers() -> None:
    module = _parse_module("wepppy/microservices/rq_engine/wepp_run_payload.py")
    fn_node = _get_function_node(module, "apply_wepp_run_payload")

    call_targets = _collect_call_targets(fn_node)

    assert "_acquire_grouped_update_locks" in call_targets
    assert "_apply_grouped_soils_watershed_updates" in call_targets
    assert not _has_call_target(call_targets, "apply_wepp_run_payload_updates")


def test_watershed_route_uses_batch_update_helper_without_setter_churn() -> None:
    module = _parse_module("wepppy/microservices/rq_engine/watershed_routes.py")
    fn_node = _get_function_node(module, "build_subcatchments_and_abstract_watershed")

    call_targets = _collect_call_targets(fn_node)
    assigned_attrs = _collect_assigned_attributes(fn_node)
    setattr_assigned_attrs = _collect_setattr_assigned_attributes(fn_node)

    assert "watershed.apply_build_subcatchment_updates" in call_targets

    forbidden_attrs = {
        "watershed.clip_hillslopes",
        "watershed.walk_flowpaths",
        "watershed.clip_hillslope_length",
        "watershed.mofe_target_length",
        "watershed.mofe_buffer",
        "watershed.mofe_buffer_length",
        "watershed.mofe_max_ofes",
        "watershed.bieger2015_widths",
    }
    assert assigned_attrs.isdisjoint(forbidden_attrs)
    assert setattr_assigned_attrs.isdisjoint(forbidden_attrs)


def test_landuse_routes_use_grouped_update_helpers_without_direct_setters() -> None:
    module = _parse_module("wepppy/microservices/rq_engine/landuse_routes.py")

    build_landuse_node = _get_function_node(module, "build_landuse")
    build_landuse_calls = _collect_call_targets(build_landuse_node)
    build_landuse_assigned = _collect_assigned_attributes(build_landuse_node)
    build_landuse_setattr_assigned = _collect_setattr_assigned_attributes(build_landuse_node)

    assert "disturbed.apply_build_landuse_updates" in build_landuse_calls
    assert "disturbed.burn_shrubs" not in build_landuse_assigned
    assert "disturbed.burn_shrubs" not in build_landuse_setattr_assigned
    assert "disturbed.burn_grass" not in build_landuse_assigned
    assert "disturbed.burn_grass" not in build_landuse_setattr_assigned

    set_landuse_mode_node = _get_function_node(module, "set_landuse_mode")
    set_landuse_mode_calls = _collect_call_targets(set_landuse_mode_node)
    set_landuse_mode_assigned = _collect_assigned_attributes(set_landuse_mode_node)
    set_landuse_mode_setattr_assigned = _collect_setattr_assigned_attributes(set_landuse_mode_node)

    assert "landuse.apply_set_landuse_mode_updates" in set_landuse_mode_calls
    assert "landuse.mode" not in set_landuse_mode_assigned
    assert "landuse.mode" not in set_landuse_mode_setattr_assigned
    assert "landuse.single_selection" not in set_landuse_mode_assigned
    assert "landuse.single_selection" not in set_landuse_mode_setattr_assigned


def test_upload_sbs_map_uses_batch_runner_resource_update_helper() -> None:
    module = _parse_module("wepppy/microservices/rq_engine/upload_batch_runner_routes.py")
    fn_node = _get_function_node(module, "upload_sbs_map")

    call_targets = _collect_call_targets(fn_node)
    assigned_attrs = _collect_assigned_attributes(fn_node)
    setattr_assigned_attrs = _collect_setattr_assigned_attributes(fn_node)

    assert "batch_runner.apply_sbs_resource_update" in call_targets
    assert "batch_runner.sbs_map" not in assigned_attrs
    assert "batch_runner.sbs_map" not in setattr_assigned_attrs
    assert "batch_runner.sbs_map_metadata" not in assigned_attrs
    assert "batch_runner.sbs_map_metadata" not in setattr_assigned_attrs
