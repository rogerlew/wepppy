"""Conditional FA-01 dataset checks; ordinary query/cache behavior is unchanged."""
import os
from pathlib import Path

from starlette.exceptions import HTTPException

from wepppy.microservices.browse import auth as browse_auth
from wepppy.weppcloud.utils.feature_access_data import protected_source


def require_root(request, base_dir):
    """Check resolved workflow roots, including absolute paths and aliases."""
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
        if protected_source(resolved):
            browse_auth.require_data_access(_context(request), resolved)
    except (browse_auth.BrowseAuthError, AuthError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _context(request):
    principal = getattr(request.state, "mcp_principal", None)
    if principal is not None:
        return browse_auth.AuthContext(principal.claims, principal.claims.get("token_class"), frozenset())
    try:
        return browse_auth.resolve_auth_context(request, runid=request.path_params.get("runid", ""), config="")
    except browse_auth.BrowseAuthError:
        # Optional identity cannot alter ordinary public queries. A protected
        # request without verified identity still fails its entitlement check.
        return browse_auth.AuthContext(None, None, frozenset())


def _entry_sources(base_dir, entry):
    from wepppy.query_engine.core import _resolve_dataset_path
    path = entry.get("path", "") if isinstance(entry, dict) else entry.path
    fs_path = entry.get("fs_path") if isinstance(entry, dict) else entry.fs_path
    return (Path(base_dir) / path, _resolve_dataset_path(Path(base_dir), fs_path or path, path))


def require_datasets(request, base_dir, paths, *, entries=()):
    require_root(request, base_dir)
    by_path = {entry.get("path") if isinstance(entry, dict) else entry.path: entry for entry in entries}
    sources = [source for path in paths for source in _entry_sources(base_dir, by_path.get(path, {"path": path}))]
    for source in sources:
        require_root(request, source)
    protected = [path for path in sources if protected_source(path)]
    if not protected:
        return
    context = _context(request)
    try:
        for path in protected:
            browse_auth.require_data_access(context, path)
    except browse_auth.BrowseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def visible_entries(request, base_dir, entries):
    require_root(request, base_dir)
    context = None
    visible = []
    for entry in entries:
        sources = _entry_sources(base_dir, entry)
        try:
            for source in sources:
                require_root(request, source)
        except HTTPException as exc:
            if exc.status_code not in (401, 403):
                raise
            continue
        protected = [source for source in sources if protected_source(source)]
        if protected:
            if context is None:
                context = _context(request)
            try:
                for source in protected:
                    browse_auth.require_data_access(context, source)
            except browse_auth.BrowseAuthError:
                continue
        visible.append(entry)
    return visible
