"""Conditional FA-01 dataset checks; ordinary query/cache behavior is unchanged."""
import os
from pathlib import Path

from wepppy.wepp.interchange import _roads_lifecycle as roads_lifecycle

from starlette.exceptions import HTTPException

from wepppy.microservices.browse import auth as browse_auth


def require_root(request, base_dir):
    """Check resolved workflow roots, including absolute paths and aliases."""
    if getattr(request.state, "query_target", None) is not None:
        from .access import require_data_path
        require_data_path(request, base_dir)
        return
    from wepppy.microservices.rq_engine.auth import AuthError
    from wepppy.microservices.rq_engine.feature_access import require_feature_access
    from wepppy.nodb.base import NoDbBase

    resolved = Path(base_dir).resolve()
    try:
        for feature, env, default in (
            ("batch_runner", "BATCH_RUNNER_ROOT", "/wc1/batch"),
            ("culvert_runner", "CULVERTS_ROOT", "/wc1/culverts"),
        ):
            root = Path(os.environ.get(env, default)).resolve()
            if not resolved.is_relative_to(root):
                continue
            relative = resolved.relative_to(root)
            if not relative.parts:
                raise HTTPException(403, "A workflow identifier is required")
            identifier = relative.parts[0]
            batch = feature == "batch_runner"
            public_runid = f"batch;;{identifier};;_base" if batch else None
            principal = getattr(request.state, "mcp_principal", None)
            if principal is None:
                browse_auth.authorize_group_request(
                    request, identifier=identifier, subpath=relative.as_posix(),
                    allowed_token_classes=("user", "service", "session") if batch else ("user", "service"),
                    identifier_claim_aliases=(public_runid,) if batch else None,
                    public_runid=public_runid, allow_public_without_token=batch,
                )
            elif not (batch and NoDbBase.ispublic(str(root / identifier / "_base"))):
                # MCP middleware and route guards verify their own audience,
                # scopes and resource binding before this additional admission.
                require_feature_access(principal.claims, feature, operation="inspect", protected_read=True)
    except (browse_auth.BrowseAuthError, AuthError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _entry_sources(base_dir, entry, request=None):
    from wepppy.query_engine.core import _resolve_dataset_path
    path = entry.get("path", "") if isinstance(entry, dict) else entry.path
    fs_path = entry.get("fs_path") if isinstance(entry, dict) else entry.fs_path
    if request is not None and getattr(request.state, "query_target", None) is not None:
        from .access import require_data_path
        if Path(path).is_absolute() or '..' in Path(path).parts:
            raise HTTPException(403, 'Dataset outside authorized resource')
        require_data_path(request, Path(base_dir) / path)
        require_data_path(request, Path(base_dir) / (fs_path or path))
    return (Path(base_dir) / path, _resolve_dataset_path(Path(base_dir), fs_path or path, path))


def require_datasets(request, base_dir, paths, *, entries=()):
    if getattr(request.state, "query_target", None) is not None:
        from .access import recheck
        recheck(request)
    require_root(request, base_dir)
    by_path = {entry.get("path") if isinstance(entry, dict) else entry.path: entry for entry in entries}
    sources = [source for path in paths for source in _entry_sources(base_dir, by_path.get(path, {"path": path}), request)]
    for source in sources:
        require_root(request, source)


def discovery_headers(base_dir, entries=()):
    """Roads availability in discovery must be refreshed after replacement."""
    if (Path(base_dir) / 'wepp/roads').exists() or any(
        roads_lifecycle.path_owner(source) is not None
        for entry in entries for source in _entry_sources(base_dir, entry)
    ):
        return {'Cache-Control': 'no-store'}
    return {}


def visible_entries(request, base_dir, entries):
    if getattr(request.state, "query_target", None) is not None:
        from .access import recheck
        recheck(request)
    require_root(request, base_dir)
    visible = []
    for entry in entries:
        try:
            sources = _entry_sources(base_dir, entry, request)
            for source in sources:
                require_root(request, source)
        except HTTPException as exc:
            if exc.status_code not in (401, 403):
                raise
            continue
        logical, physical = sources
        owner = roads_lifecycle.path_owner(logical)
        if owner is not None and owner.resolve() / logical.relative_to(owner) != physical:
            continue
        roots = {roads_lifecycle.path_owner(path) for path in sources} - {None}
        if not all(roads_lifecycle.available(root) for root in roots):
            continue
        visible.append(entry)
    return visible
