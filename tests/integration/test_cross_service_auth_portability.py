from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_portability__mx_a1_session_token_requires_active_marker(
    integration_run,
    integration_redis,
    issue_session_token,
    rq_engine_client,
) -> None:
    token = issue_session_token(
        runid=integration_run.runid,
        config=integration_run.config,
        session_id="session-accept",
    )

    integration_redis.setex(
        f"auth:session:run:{integration_run.runid}:session-accept",
        60,
        "1",
    )

    accepted = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(token),
    )

    assert accepted.status_code == 200
    accepted_payload = accepted.json()
    assert accepted_payload["token_class"] == "session"

    rejected_token = issue_session_token(
        runid=integration_run.runid,
        config=integration_run.config,
        session_id="session-missing-marker",
    )
    rejected = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(rejected_token),
    )

    assert rejected.status_code == 401
    rejected_payload = rejected.json()
    assert rejected_payload["error"]["code"] == "unauthorized"
    assert "session token invalid or expired" in rejected_payload["error"]["message"].lower()


def test_portability__mx_a2_user_token_portable_to_rq_engine_and_browse(
    integration_run,
    issue_user_token,
    rq_engine_client,
    browse_client,
) -> None:
    token = issue_user_token(
        runs=(integration_run.runid,),
        scopes=("rq:status",),
    )

    rq_response = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(token),
    )
    assert rq_response.status_code == 200

    browse_response = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(token),
    )
    assert browse_response.status_code == 200
    assert "demo.txt" in browse_response.text


def test_portability__mx_a3_service_token_portable_to_rq_engine_and_browse(
    integration_run,
    issue_service_token,
    rq_engine_client,
    browse_client,
) -> None:
    token = issue_service_token(
        runs=(integration_run.runid,),
        scopes=("rq:status",),
    )

    rq_response = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(token),
    )
    assert rq_response.status_code == 200

    browse_response = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(token),
    )
    assert browse_response.status_code == 200
    assert "demo.txt" in browse_response.text


def test_portability__mx_a4_wepp_signed_mcp_class_token_rejected_by_browse_policy(
    integration_run,
    issue_user_token,
    browse_client,
) -> None:
    token = issue_user_token(
        runs=(integration_run.runid,),
        scopes=("rq:status",),
        extra_claims={"token_class": "mcp", "roles": []},
    )

    response = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(token),
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert "token class is not allowed" in response.text.lower()


def test_portability__mx_a5_wepp_signed_mcp_class_token_conditionally_allows_rq_engine(
    integration_run,
    issue_user_token,
    rq_engine_client,
) -> None:
    token = issue_user_token(
        runs=(integration_run.runid,),
        scopes=("rq:status",),
        extra_claims={"token_class": "mcp", "roles": []},
    )

    response = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(token),
    )

    assert response.status_code == 200


def test_portability__mx_a6_mcp_token_is_accepted_on_mcp_and_denied_elsewhere(
    integration_run,
    issue_mcp_token,
    make_mcp_client,
    rq_engine_client,
    browse_client,
) -> None:
    token = issue_mcp_token(
        runs=(integration_run.runid,),
        scopes=("runs:read",),
    )

    with make_mcp_client() as mcp_client:
        mcp_response = mcp_client.get("/mcp/ping", headers=_auth_header(token))
    assert mcp_response.status_code == 200

    rq_response = rq_engine_client.post(
        f"/api/runs/{integration_run.runid}/{integration_run.config}/session-token",
        headers=_auth_header(token),
    )
    assert rq_response.status_code == 401

    browse_response = browse_client.get(
        f"/weppcloud/runs/{integration_run.runid}/{integration_run.config}/browse/",
        headers=_auth_header(token),
        follow_redirects=False,
    )
    assert browse_response.status_code in {302, 401, 403}
    assert browse_response.status_code != 200
