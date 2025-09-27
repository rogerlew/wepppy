"""Helpers for resolving run working directories, including pup projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from flask import abort, g, request

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


def load_run_context(runid: str, config: str) -> RunContext:
    """Resolve the working directories for the given run route.

    Stores the ``RunContext`` on ``flask.g`` so downstream helpers can reuse it.
    """

    run_root = Path(get_wd(runid, prefer_active=False)).resolve()
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

    @bp.url_value_preprocessor
    def _load_context(endpoint, values):  # pragma: no cover - flask hook
        if not values:
            return

        runid = values.get('runid')
        config = values.get('config')

        if runid is None or config is None:
            return

        load_run_context(runid, config)

    return bp
