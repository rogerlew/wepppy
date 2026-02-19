#!/usr/bin/env python3
"""Extract static RQ enqueue dependency edges from repository source."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_GRAPH_PATH = Path("wepppy/rq/job-dependency-graph.static.json")
SOURCE_GLOBS: tuple[str, ...] = (
    "wepppy/rq/*.py",
    "wepppy/microservices/rq_engine/*.py",
    "wepppy/weppcloud/routes/**/*.py",
    "wepppy/weppcloud/bootstrap/*.py",
)
ENQUEUE_METHODS = {"enqueue", "enqueue_call"}
_JOBS_STAGE_RE = re.compile(r"jobs:([^,]+)")


@dataclass
class _Event:
    kind: str
    lineno: int
    order: int
    function: str
    data: dict[str, Any]


@dataclass
class _EdgeRecord:
    source_module: str
    source_function: str
    source_lineno: int
    enqueue_target: str
    depends_on: list[str]
    job_meta_stage: str | None
    queue_name: str
    notes: list[str]
    job_var: str | None


def _expr_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node).strip()
    except Exception:
        return ast.dump(node, include_attributes=False)


def _string_template(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append("{}")
            else:
                return None
        return "".join(parts)
    return None


def _extract_stage_from_meta_key(node: ast.AST) -> str | None:
    template = _string_template(node)
    if template is None:
        return None
    match = _JOBS_STAGE_RE.search(template)
    if match is None:
        return None
    token = match.group(1).split("{", 1)[0].rstrip(":")
    if not token:
        return None
    if not token[:1].isdigit() and ":" in token:
        token = token.split(":", 1)[0]
    if not token:
        return None
    return f"jobs:{token}"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _is_dependency_list_var(name: str) -> bool:
    lowered = name.lower()
    return "depend" in lowered or "deps" in lowered or lowered.startswith("jobs") or lowered.endswith("_jobs")


def _collect_dep_refs(
    node: ast.AST | None,
    *,
    job_bindings: dict[str, str],
    list_bindings: dict[str, list[str]],
) -> list[str]:
    if node is None:
        return []

    if isinstance(node, ast.Constant):
        if node.value is None:
            return []
        return [str(node.value)]

    if isinstance(node, ast.Name):
        if node.id in list_bindings:
            return list_bindings[node.id][:]
        if node.id in job_bindings:
            return [job_bindings[node.id]]
        return [node.id]

    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        refs: list[str] = []
        for elt in node.elts:
            refs.extend(_collect_dep_refs(elt, job_bindings=job_bindings, list_bindings=list_bindings))
        return _dedupe(refs)

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        refs = _collect_dep_refs(node.left, job_bindings=job_bindings, list_bindings=list_bindings)
        refs.extend(_collect_dep_refs(node.right, job_bindings=job_bindings, list_bindings=list_bindings))
        return _dedupe(refs)

    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        refs: list[str] = []
        for value in node.values:
            refs.extend(_collect_dep_refs(value, job_bindings=job_bindings, list_bindings=list_bindings))
        return _dedupe(refs)

    if isinstance(node, ast.IfExp):
        refs = _collect_dep_refs(node.body, job_bindings=job_bindings, list_bindings=list_bindings)
        refs.extend(_collect_dep_refs(node.orelse, job_bindings=job_bindings, list_bindings=list_bindings))
        return _dedupe(refs)

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "list" and node.args:
            return _collect_dep_refs(node.args[0], job_bindings=job_bindings, list_bindings=list_bindings)
        return [_expr_text(node)]

    return [_expr_text(node)]


def _queue_name_from_constructor(call: ast.Call) -> str:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    for keyword in call.keywords:
        if keyword.arg == "name":
            if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                return keyword.value.value
            return _expr_text(keyword.value)
    return "default"


def _queue_ref_from_enqueue_call(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        return call.func.value.id
    return None


def _keyword_value(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _enqueue_target_expr(call: ast.Call) -> ast.AST | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    method = call.func.attr
    if method not in ENQUEUE_METHODS:
        return None
    if method == "enqueue_call":
        explicit = _keyword_value(call, "func")
        if explicit is not None:
            return explicit
        if call.args:
            return call.args[0]
        return None
    if call.args:
        return call.args[0]
    explicit = _keyword_value(call, "func")
    if explicit is not None:
        return explicit
    return _keyword_value(call, "f")


def _target_label(target_expr: ast.AST | None, aliases: dict[str, set[str]]) -> tuple[str, list[str]]:
    if target_expr is None:
        return "<unknown>", ["missing enqueue target"]
    if isinstance(target_expr, ast.Name):
        alias_values = aliases.get(target_expr.id)
        if alias_values:
            if len(alias_values) == 1:
                return next(iter(alias_values)), []
            return "/".join(sorted(alias_values)), [f"ambiguous target alias: {target_expr.id}"]
        return target_expr.id, []
    if isinstance(target_expr, ast.Attribute):
        return _expr_text(target_expr), []
    if isinstance(target_expr, ast.Constant) and isinstance(target_expr.value, str):
        return target_expr.value, []
    return _expr_text(target_expr), []


def _extract_enqueue_event_data(call: ast.Call) -> dict[str, Any] | None:
    if not isinstance(call.func, ast.Attribute) or call.func.attr not in ENQUEUE_METHODS:
        return None

    target_expr = _enqueue_target_expr(call)
    return {
        "queue_ref": _queue_ref_from_enqueue_call(call),
        "target_expr": target_expr,
        "depends_on_expr": _keyword_value(call, "depends_on"),
        "method": call.func.attr,
    }


def _extract_stage_assignment(
    target: ast.expr,
    value: ast.expr,
) -> tuple[str, str] | None:
    if not isinstance(target, ast.Subscript):
        return None
    if not isinstance(target.value, ast.Attribute):
        return None
    if target.value.attr != "meta":
        return None

    if not isinstance(value, ast.Attribute):
        return None
    if value.attr != "id":
        return None
    if not isinstance(value.value, ast.Name):
        return None

    stage = _extract_stage_from_meta_key(target.slice)
    if stage is None:
        return None
    return value.value.id, stage


def _assign_name_target(node: ast.Assign | ast.AnnAssign) -> str | None:
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            return None
        target = node.targets[0]
    else:
        target = node.target

    if isinstance(target, ast.Name):
        return target.id
    return None


class _Collector(ast.NodeVisitor):
    def __init__(self) -> None:
        self._function_stack: list[str] = ["<module>"]
        self._counter = 0
        self.events: list[_Event] = []

    def _emit(self, *, kind: str, lineno: int, data: dict[str, Any]) -> None:
        self._counter += 1
        self.events.append(
            _Event(
                kind=kind,
                lineno=lineno,
                order=self._counter,
                function=self._function_stack[-1],
                data=data,
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()
        return None

    def visit_Assign(self, node: ast.Assign) -> Any:
        self._collect_assignment(node)
        self.generic_visit(node)
        return None

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        self._collect_assignment(node)
        self.generic_visit(node)
        return None

    def visit_Expr(self, node: ast.Expr) -> Any:
        value = node.value
        if isinstance(value, ast.Call):
            enqueue_data = _extract_enqueue_event_data(value)
            if enqueue_data is not None:
                self._emit(kind="enqueue", lineno=node.lineno, data={**enqueue_data, "job_var": None})
            append_data = _extract_append_event_data(value)
            if append_data is not None:
                self._emit(kind="list_append", lineno=node.lineno, data=append_data)
        self.generic_visit(node)
        return None

    def _collect_assignment(self, node: ast.Assign | ast.AnnAssign) -> None:
        name_target = _assign_name_target(node)
        value = node.value

        if isinstance(value, ast.Call):
            enqueue_data = _extract_enqueue_event_data(value)
            if enqueue_data is not None:
                self._emit(
                    kind="enqueue",
                    lineno=node.lineno,
                    data={**enqueue_data, "job_var": name_target},
                )
                return

            if name_target and _is_queue_constructor(value):
                self._emit(
                    kind="queue_bind",
                    lineno=node.lineno,
                    data={
                        "queue_var": name_target,
                        "queue_name": _queue_name_from_constructor(value),
                    },
                )
                return

        if isinstance(node, ast.Assign):
            for target in node.targets:
                stage_assignment = _extract_stage_assignment(target, value)
                if stage_assignment is not None:
                    job_var, stage = stage_assignment
                    self._emit(
                        kind="meta_stage",
                        lineno=node.lineno,
                        data={"job_var": job_var, "stage": stage},
                    )
                    return

        if name_target is None:
            return

        if _is_dependency_list_var(name_target):
            self._emit(
                kind="list_assign",
                lineno=node.lineno,
                data={"var_name": name_target, "value": value},
            )

        alias_value = _callable_alias(value)
        if alias_value is not None:
            self._emit(
                kind="alias_assign",
                lineno=node.lineno,
                data={"var_name": name_target, "alias": alias_value},
            )


def _is_queue_constructor(call: ast.Call) -> bool:
    if isinstance(call.func, ast.Name):
        return call.func.id == "Queue"
    if isinstance(call.func, ast.Attribute):
        return call.func.attr == "Queue"
    return False


def _callable_alias(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _expr_text(node)
    return None


def _extract_append_event_data(call: ast.Call) -> dict[str, Any] | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    if call.func.attr not in {"append", "extend"}:
        return None
    if not isinstance(call.func.value, ast.Name):
        return None
    if not _is_dependency_list_var(call.func.value.id):
        return None
    if not call.args:
        return None
    return {
        "var_name": call.func.value.id,
        "op": call.func.attr,
        "value": call.args[0],
    }


def _group_events(events: list[_Event]) -> dict[str, list[_Event]]:
    grouped: dict[str, list[_Event]] = {}
    for event in events:
        grouped.setdefault(event.function, []).append(event)
    for function_events in grouped.values():
        function_events.sort(key=lambda item: (item.lineno, item.order))
    return grouped


def _extract_module_edges(*, module_path: Path, repo_root: Path) -> list[_EdgeRecord]:
    source_text = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(module_path))
    collector = _Collector()
    collector.visit(tree)
    grouped = _group_events(collector.events)

    module_rel = module_path.relative_to(repo_root).as_posix()
    all_edges: list[_EdgeRecord] = []

    for function_name, events in grouped.items():
        queue_bindings: dict[str, str] = {}
        list_bindings: dict[str, list[str]] = {}
        aliases: dict[str, set[str]] = {}
        job_bindings: dict[str, str] = {}
        function_edges: list[_EdgeRecord] = []
        edge_indices_by_var: dict[str, list[int]] = {}

        for event in events:
            if event.kind == "queue_bind":
                queue_bindings[event.data["queue_var"]] = event.data["queue_name"]
                continue

            if event.kind == "alias_assign":
                aliases.setdefault(event.data["var_name"], set()).add(event.data["alias"])
                continue

            if event.kind == "list_assign":
                refs = _collect_dep_refs(
                    event.data["value"],
                    job_bindings=job_bindings,
                    list_bindings=list_bindings,
                )
                list_bindings[event.data["var_name"]] = refs
                continue

            if event.kind == "list_append":
                refs = _collect_dep_refs(
                    event.data["value"],
                    job_bindings=job_bindings,
                    list_bindings=list_bindings,
                )
                existing = list_bindings.setdefault(event.data["var_name"], [])
                if event.data["op"] == "append":
                    existing.extend(refs[:1] if len(refs) > 1 else refs)
                else:
                    existing.extend(refs)
                list_bindings[event.data["var_name"]] = _dedupe(existing)
                continue

            if event.kind == "enqueue":
                queue_name = "unknown"
                queue_ref = event.data.get("queue_ref")
                if queue_ref is not None:
                    queue_name = queue_bindings.get(queue_ref, "default")

                target, target_notes = _target_label(event.data.get("target_expr"), aliases)
                depends_on = _collect_dep_refs(
                    event.data.get("depends_on_expr"),
                    job_bindings=job_bindings,
                    list_bindings=list_bindings,
                )

                edge = _EdgeRecord(
                    source_module=module_rel,
                    source_function=function_name,
                    source_lineno=event.lineno,
                    enqueue_target=target,
                    depends_on=_dedupe(depends_on),
                    job_meta_stage=None,
                    queue_name=queue_name,
                    notes=target_notes,
                    job_var=event.data.get("job_var"),
                )
                function_edges.append(edge)
                edge_index = len(function_edges) - 1

                job_var = edge.job_var
                if job_var:
                    job_bindings[job_var] = edge.enqueue_target
                    edge_indices_by_var.setdefault(job_var, []).append(edge_index)
                continue

            if event.kind == "meta_stage":
                job_var = event.data["job_var"]
                indices = edge_indices_by_var.get(job_var, [])
                for index in reversed(indices):
                    edge = function_edges[index]
                    if edge.job_meta_stage is None and edge.source_lineno <= event.lineno:
                        edge.job_meta_stage = event.data["stage"]
                        break
                continue

        all_edges.extend(function_edges)

    return all_edges


def _edge_sort_key(edge: _EdgeRecord) -> tuple[Any, ...]:
    return (
        edge.source_module,
        edge.source_function,
        edge.source_lineno,
        edge.enqueue_target,
        edge.queue_name,
        edge.job_meta_stage or "",
        tuple(edge.depends_on),
        tuple(edge.notes),
    )


def _iter_source_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for glob_pattern in SOURCE_GLOBS:
        files.extend((repo_root / ".").glob(glob_pattern))
    unique = sorted({path.resolve() for path in files if path.suffix == ".py"})
    return unique


def extract_dependency_edges(
    *,
    repo_root: Path | None = None,
    source_files: list[Path] | None = None,
) -> list[dict[str, Any]]:
    """Return normalized dependency graph edges from RQ enqueue source."""
    root = (repo_root or REPO_ROOT).resolve()
    files = [path.resolve() for path in source_files] if source_files else _iter_source_files(root)
    edges: list[_EdgeRecord] = []

    for source_path in files:
        try:
            edges.extend(_extract_module_edges(module_path=source_path, repo_root=root))
        except SyntaxError as exc:  # pragma: no cover - parser failure path
            raise RuntimeError(f"Unable to parse {source_path}: {exc}") from exc

    edges.sort(key=_edge_sort_key)
    return [
        {
            "source_module": edge.source_module,
            "source_function": edge.source_function,
            "source_lineno": edge.source_lineno,
            "enqueue_target": edge.enqueue_target,
            "depends_on": edge.depends_on,
            "job_meta_stage": edge.job_meta_stage,
            "queue_name": edge.queue_name,
            "notes": edge.notes,
        }
        for edge in edges
    ]


def serialize_edges(edges: list[dict[str, Any]]) -> str:
    return json.dumps(edges, indent=2, sort_keys=True) + "\n"


def static_graph_path(repo_root: Path | None = None) -> Path:
    root = (repo_root or REPO_ROOT).resolve()
    return root / STATIC_GRAPH_PATH


def _check_static_graph(*, repo_root: Path | None = None) -> int:
    root = (repo_root or REPO_ROOT).resolve()
    output_path = static_graph_path(root)
    edges = extract_dependency_edges(repo_root=root)
    expected = serialize_edges(edges)
    current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
    if current != expected:
        rel = output_path.relative_to(root).as_posix()
        print("RQ dependency graph drift detected:")
        print(f"- {rel}")
        return 1
    rel = output_path.relative_to(root).as_posix()
    print(f"RQ dependency graph static artifact is up to date ({rel})")
    return 0


def _write_static_graph(*, repo_root: Path | None = None) -> int:
    root = (repo_root or REPO_ROOT).resolve()
    output_path = static_graph_path(root)
    edges = extract_dependency_edges(repo_root=root)
    payload = serialize_edges(edges)
    output_path.write_text(payload, encoding="utf-8")
    rel = output_path.relative_to(root).as_posix()
    print(f"wrote {len(edges)} edges to {rel}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the static graph artifact.")
    parser.add_argument("--check", action="store_true", help="Fail if the static graph artifact is stale.")
    args = parser.parse_args(argv)

    if not args.write and not args.check:
        edges = extract_dependency_edges(repo_root=REPO_ROOT)
        print(serialize_edges(edges), end="")
        return 0

    if args.write:
        _write_static_graph(repo_root=REPO_ROOT)
    if args.check:
        return _check_static_graph(repo_root=REPO_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
