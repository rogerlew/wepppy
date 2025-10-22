"""Helpers for resolving run working directories, including pup projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from flask import abort, g, request
import sys

from wepppy.weppcloud.utils.helpers import get_wd


@dataclass(frozen=True)
class RunContext:
    """Resolved filesystem roots for a run request."""

    runid: str
    config: str
    run_root: Path
    active_root: Path
    pup_root: Optional[Path]
    pup_relpath: Optional[str]


def _validate_pup_root(run_root: Path, pup_relpath: str) -> Path:
    """Return the absolute pup directory if it exists under ``run_root``."""

    pups_root = (run_root / "_pups").resolve()
    if not pups_root.is_dir():
        abort(404, description=f"0 Unknown pup project: run_root:{run_root}\tpup_relpath:{pup_relpath}")

    candidate = (pups_root / pup_relpath).resolve()
    try:
        candidate.relative_to(pups_root)
    except ValueError:
        abort(404, description=f"1 Unknown pup project: run_root:{run_root}\tpup_relpath:{pup_relpath}\tcandidate:{candidate}")

    if not candidate.is_dir():
        abort(404, description=f"2 Unknown pup project: run_root:{run_root}\tpup_relpath:{pup_relpath}\tcandidate:{candidate}")

    return candidate


def _store_run_context(ctx: Any) -> None:
    g.run_context = ctx
    if hasattr(ctx, "run_root"):
        run_root = getattr(ctx, "run_root")
        g.run_root = str(run_root)
    if hasattr(ctx, "active_root"):
        active_root = getattr(ctx, "active_root")
        g.active_run_root = str(active_root)
    if hasattr(ctx, "pup_root"):
        pup_root = getattr(ctx, "pup_root")
        g.pup_root = None if pup_root is None else str(pup_root)
    if hasattr(ctx, "pup_relpath"):
        g.pup_relpath = getattr(ctx, "pup_relpath")


def load_run_context(
    runid: str, config: str, get_wd_fn: Optional[Callable[..., str]] = None
) -> RunContext:
    """
    Resolve the working directories for the given run route.

    Stores the ``RunContext`` on ``flask.g`` so downstream helpers can reuse it.
    """

    resolver: Callable[..., str] = get_wd_fn or get_wd
    try:
        resolved_path = resolver(runid, prefer_active=False)
    except TypeError:
        resolved_path = resolver(runid)

    run_root = Path(resolved_path).resolve()
    if not run_root.is_dir():
        abort(404, description=f"Run '{runid}' not found")

    pup_relpath = request.args.get("pup")
    pup_root: Optional[Path] = None
    active_root = run_root

    if pup_relpath:
        pup_root = _validate_pup_root(run_root, pup_relpath)
        active_root = pup_root

    context = RunContext(
        runid=runid,
        config=config,
        run_root=run_root,
        active_root=active_root,
        pup_root=pup_root,
        pup_relpath=pup_relpath,
    )

    g.run_context = context
    g.run_root = str(run_root)
    g.active_run_root = str(active_root)
    g.pup_root = None if pup_root is None else str(pup_root)
    g.pup_relpath = pup_relpath

    return context


def register_run_context_preprocessor(bp):
    """Attach a url value preprocessor that resolves run context lazily."""

    module_name = bp.import_name

    @bp.url_value_preprocessor
    def _load_context(endpoint, values):  # pragma: no cover - flask hook
        if not values:
            return

        runid = values.get('runid')
        config = values.get('config')

        if runid is None or config is None:
            return

        module = sys.modules.get(module_name)
        override_get_wd = None
        override_load = None
        if module is not None:
            override_get_wd = getattr(module, "get_wd", None)
            override_load = getattr(module, "load_run_context", None)

        if callable(override_load) and override_load is not load_run_context:
            result = override_load(runid, config)
            if result is not None:
                _store_run_context(result)
            return

        load_run_context(runid, config, get_wd_fn=override_get_wd)

    return bp
