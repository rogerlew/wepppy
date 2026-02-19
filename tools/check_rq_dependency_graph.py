#!/usr/bin/env python3
"""Check drift for generated RQ dependency graph artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.extract_rq_dependency_graph import STATIC_GRAPH_PATH, extract_dependency_edges, serialize_edges
from tools.render_rq_dependency_graph_docs import CATALOG_PATH, render_catalog_text


def _artifact_paths(repo_root: Path) -> tuple[Path, Path]:
    return repo_root / STATIC_GRAPH_PATH, repo_root / CATALOG_PATH


def _generated_outputs(repo_root: Path) -> tuple[str, str, int]:
    edges = extract_dependency_edges(repo_root=repo_root)
    static_payload = serialize_edges(edges)
    rendered_catalog = render_catalog_text(repo_root=repo_root, edges=edges)
    return static_payload, rendered_catalog, len(edges)


def check_rq_dependency_graph(*, repo_root: Path | None = None) -> tuple[int, list[str]]:
    root = (repo_root or REPO_ROOT).resolve()
    static_path, catalog_path = _artifact_paths(root)
    static_expected, catalog_expected, _ = _generated_outputs(root)

    stale: list[str] = []
    static_current = static_path.read_text(encoding="utf-8") if static_path.exists() else ""
    if static_current != static_expected:
        stale.append(static_path.relative_to(root).as_posix())

    catalog_current = catalog_path.read_text(encoding="utf-8") if catalog_path.exists() else ""
    if catalog_current != catalog_expected:
        stale.append(catalog_path.relative_to(root).as_posix())

    if stale:
        print("RQ dependency graph drift detected:")
        for rel_path in stale:
            print(f"- {rel_path}")
        return 1, stale

    print("RQ dependency graph artifacts are up to date")
    return 0, []


def write_rq_dependency_graph(*, repo_root: Path | None = None) -> int:
    root = (repo_root or REPO_ROOT).resolve()
    static_path, catalog_path = _artifact_paths(root)
    static_payload, catalog_payload, edge_count = _generated_outputs(root)

    static_path.write_text(static_payload, encoding="utf-8")
    catalog_path.write_text(catalog_payload, encoding="utf-8")
    static_rel = static_path.relative_to(root).as_posix()
    catalog_rel = catalog_path.relative_to(root).as_posix()
    print(f"wrote {edge_count} edges to {static_rel}")
    print(f"updated managed catalog section in {catalog_rel}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate static graph JSON and the managed catalog section.",
    )
    args = parser.parse_args(argv)

    if args.write:
        return write_rq_dependency_graph(repo_root=REPO_ROOT)

    status, _stale = check_rq_dependency_graph(repo_root=REPO_ROOT)
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
