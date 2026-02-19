from __future__ import annotations

from http.cookies import SimpleCookie
from urllib.parse import quote

import pytest

from wepppy.weppcloud.utils import auth_tokens


pytestmark = pytest.mark.integration


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_lifecycle__mx_l1_browser_renewal_fallback_sequence(
    integration_run,
    issue_session_token,
    rq_engine_client,
    weppcloud_client,
    set_weppcloud_user,
) -> None:
    stale_session_token = issue_session_token(
        runid=integration_run.runid,
        config=integration_run.config,
        session_id="stale-session",
    )

    initial = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(stale_session_token),
    )
    assert initial.status_code == 401

    set_weppcloud_user(authenticated=True, user_id=42, email="user@example.com", roles=("User",))
    fallback = weppcloud_client.post(
        "/weppcloud/api/auth/rq-engine-token",
        headers={"Origin": "http://localhost"},
    )
    assert fallback.status_code == 200
    fallback_token = fallback.get_json()["token"]

    retry = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(fallback_token),
    )
    assert retry.status_code == 200
    retry_payload = retry.json()
    assert retry_payload["token_class"] == "session"

    set_weppcloud_user(authenticated=False)
    anonymous_fallback = weppcloud_client.post(
        "/weppcloud/api/auth/rq-engine-token",
        headers={"Origin": "http://localhost"},
    )
    assert anonymous_fallback.status_code == 401

    set_weppcloud_user(authenticated=True, user_id=42)
    cross_origin_fallback = weppcloud_client.post(
        "/weppcloud/api/auth/rq-engine-token",
        headers={"Origin": "https://evil.example"},
    )
    assert cross_origin_fallback.status_code == 403


def test_lifecycle__mx_l2_revocation_denylist_propagates_across_surfaces(
    integration_run,
    integration_redis,
    issue_user_token,
    issue_mcp_token,
    rq_engine_client,
    browse_client,
    make_mcp_client,
) -> None:
    shared_jti = "shared-revocation-jti"
    rq_and_browse_token = issue_user_token(
        runs=(integration_run.runid,),
        scopes=("rq:status",),
        jti=shared_jti,
    )
    mcp_token = issue_mcp_token(
        runs=(integration_run.runid,),
        scopes=("runs:read",),
        jti=shared_jti,
    )

    rq_before = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(rq_and_browse_token),
    )
    assert rq_before.status_code == 200

    browse_before = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(rq_and_browse_token),
    )
    assert browse_before.status_code == 200

    with make_mcp_client() as mcp_client:
        mcp_before = mcp_client.get("/mcp/ping", headers=_auth_header(mcp_token))
    assert mcp_before.status_code == 200

    integration_redis.setex(f"auth:jwt:revoked:{shared_jti}", 600, "1")

    rq_after = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(rq_and_browse_token),
    )
    assert rq_after.status_code == 403
    assert rq_after.json()["error"]["code"] == "forbidden"

    browse_after = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(rq_and_browse_token),
        follow_redirects=False,
    )
    assert browse_after.status_code == 403
    assert "revoked" in browse_after.text.lower()

    with make_mcp_client() as mcp_client:
        mcp_after = mcp_client.get("/mcp/ping", headers=_auth_header(mcp_token))
    assert mcp_after.status_code == 403
    assert mcp_after.json()["errors"][0]["code"] == "forbidden"


def test_lifecycle__mx_l3_wepp_secret_rotation_overlap_and_retirement(
    integration_run,
    monkeypatch: pytest.MonkeyPatch,
    issue_user_token,
    rq_engine_client,
    browse_client,
) -> None:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRETS", "new-secret,old-secret")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRET", raising=False)
    auth_tokens.get_jwt_config.cache_clear()

    new_token = issue_user_token(
        runs=(integration_run.runid,),
        scopes=("rq:status",),
    )
    new_claims = auth_tokens.decode_token(new_token, audience="rq-engine")

    overlap_config = auth_tokens.get_jwt_config()
    old_token = auth_tokens.encode_jwt(
        new_claims,
        "old-secret",
        algorithm=overlap_config.algorithms[0],
    )

    rq_old_overlap = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(old_token),
    )
    assert rq_old_overlap.status_code == 200

    browse_old_overlap = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(old_token),
    )
    assert browse_old_overlap.status_code == 200

    decoded_with_new = auth_tokens.decode_jwt(
        new_token,
        secret="new-secret",
        algorithms=("HS256",),
        audience=["rq-engine"],
        issuer="weppcloud",
        leeway=0,
    )
    assert decoded_with_new["sub"] == "42"

    with pytest.raises(auth_tokens.JWTDecodeError):
        auth_tokens.decode_jwt(
            new_token,
            secret="old-secret",
            algorithms=("HS256",),
            audience=["rq-engine"],
            issuer="weppcloud",
            leeway=0,
        )

    monkeypatch.setenv("WEPP_AUTH_JWT_SECRETS", "new-secret")
    auth_tokens.get_jwt_config.cache_clear()

    rq_old_retired = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(old_token),
    )
    assert rq_old_retired.status_code == 401

    browse_old_retired = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(old_token),
        follow_redirects=False,
    )
    assert browse_old_retired.status_code in {302, 401, 403}
    assert browse_old_retired.status_code != 200


def test_lifecycle__mx_l4_grouped_cookie_round_trip_from_issue_to_browse(
    grouped_integration_run,
    issue_user_token,
    rq_engine_client,
    browse_client,
) -> None:
    bearer_token = issue_user_token(
        runs=(grouped_integration_run.runid,),
        scopes=("rq:status",),
    )
    grouped_runid_url = quote(grouped_integration_run.runid, safe="")

    issue_response = rq_engine_client.post(
        f"/api/runs/{grouped_runid_url}/{grouped_integration_run.config}/session-token",
        headers=_auth_header(bearer_token),
    )
    assert issue_response.status_code == 200
    cookie_header = issue_response.headers["set-cookie"]
    assert "%3B" not in cookie_header
    assert "Path=/weppcloud/runs/" in cookie_header

    parsed_cookie = SimpleCookie()
    parsed_cookie.load(cookie_header)
    assert parsed_cookie
    cookie_key = next(iter(parsed_cookie.keys()))
    cookie_value = parsed_cookie[cookie_key].value

    browse_client.cookies.set(cookie_key, cookie_value)
    browse_response = browse_client.get(
        f"/weppcloud/runs/{grouped_integration_run.runid}/{grouped_integration_run.config}/browse/secret.txt",
        follow_redirects=False,
    )

    assert browse_response.status_code == 200
    assert "grouped-secret" in browse_response.text
