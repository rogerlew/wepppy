"""HttpOnly query credentials issued after Flask resource admission."""
from __future__ import annotations

import uuid

from flask import request
from flask_login import current_user
from starlette.exceptions import HTTPException

from wepppy.query_engine.app.access import authorize_resource
from wepppy.query_engine.app.helpers import resolve_target
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.browse_cookie import query_cookie_name, query_cookie_path
from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal
from wepppy.weppcloud.utils.feature_access_identity import principal_claim


def set_query_cookie(response, runid, config, *, omit_public=False):
    """Issue only for the current authenticated human's admitted resource."""
    if not current_user.is_authenticated or not current_user.is_active:
        return response
    from wepppy.weppcloud.routes.run_0.run_0_bp import (
        SESSION_TOKEN_TTL_SECONDS, _resolve_session_id_from_request,
        _store_session_marker, _session_cookie_secure,
    )
    target = resolve_target(runid, config)
    principal = VerifiedPrincipal('human', int(current_user.id))
    identity_claims = {'token_class': 'session', 'feature_access_principal': principal_claim(principal)}
    try:
        authorize_resource(target, identity_claims)
    except HTTPException as exc:
        if exc.status_code in {401, 403}:
            return response  # The page's grant does not necessarily include query access.
        raise
    if omit_public:
        from wepppy.nodb.base import NoDbBase
        from wepppy.weppcloud.utils.helpers import get_run_owners_lazy
        if (NoDbBase.ispublic(str(target.group_base or target.parent_path))
                or (';;' not in target.parent_id and not get_run_owners_lazy(target.parent_id))):
            return response
    sid = _resolve_session_id_from_request()
    if not sid:
        raise RuntimeError("Authenticated query session has no session identifier")
    claims = {**identity_claims, 'session_id': sid, 'runid': runid,
              'config': config, 'user_id': int(current_user.id), 'jti': uuid.uuid4().hex}
    payload = auth_tokens.issue_token(sid, audience='query-engine',
                                     scopes=['runs:read', 'queries:execute'],
                                     expires_in=SESSION_TOKEN_TTL_SECONDS, extra_claims=claims)
    _store_session_marker(runid, sid)
    response.set_cookie(query_cookie_name(runid, config), payload['token'],
                        max_age=SESSION_TOKEN_TTL_SECONDS, httponly=True,
                        secure=_session_cookie_secure(), samesite='Lax', path=query_cookie_path())
    return response


def set_page_query_cookie(response):
    """Cover direct run/report/dashboard entry, not just no-config redirects."""
    values = request.view_args or {}
    if (request.method == 'GET' and response.status_code == 200
            and response.mimetype == 'text/html' and values.get('runid') and values.get('config')):
        return set_query_cookie(response, values['runid'], values['config'])
    return response
