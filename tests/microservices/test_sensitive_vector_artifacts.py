from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request

from wepppy.microservices.browse import _download, dtale, listing
from wepppy.microservices.browse import auth as browse_auth
from wepppy.microservices.browse.sensitive_vectors import (
    can_access_run_sensitive_vector,
    is_retained_original,
    is_sensitive_vector_path,
    sensitive_child_names,
)
import wepppy.microservices._gdalinfo as gdalinfo


pytestmark = pytest.mark.unit


def _request(path_params: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "raw_path": b"/test",
            "query_string": b"",
            "headers": [],
            "path_params": path_params,
            "server": ("test", 80),
            "scheme": "http",
        }
    )


@pytest.mark.parametrize(
    "path",
    [
        "roads/vector_upload_attempts/a/original/source.upload",
        "ag_fields\\vector_upload_attempts\\a\\normalization.json",
        "_pups/omni/contrasts/VECTOR_UPLOAD_ATTEMPTS/a/candidate.geojson",
        "resources/vector%5Fupload%5Fattempts/a/original/source.upload",
        "archives/private/evidence.zip",
    ],
)
def test_sensitive_path_classifier_covers_aliases(path: str) -> None:
    assert is_sensitive_vector_path(path)


def test_sensitive_parent_names_are_hidden_only_at_direct_parent() -> None:
    assert sensitive_child_names("") == frozenset()
    assert sensitive_child_names("roads") == frozenset({"vector_upload_attempts"})
    assert sensitive_child_names("_pups/omni/contrasts") == frozenset(
        {"vector_upload_attempts"}
    )
    assert sensitive_child_names("archives") == frozenset({"private"})


def test_run_sensitive_access_requires_matching_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    from wepppy.weppcloud.utils import helpers

    context = SimpleNamespace(is_root=False, claims={"user_id": 41})
    monkeypatch.setattr(helpers, "get_run_owners_lazy", lambda _runid: [SimpleNamespace(id=42)])
    assert not can_access_run_sensitive_vector(context, "run-1")
    monkeypatch.setattr(helpers, "get_run_owners_lazy", lambda _runid: [SimpleNamespace(id=41)])
    assert can_access_run_sensitive_vector(context, "run-1")
    assert can_access_run_sensitive_vector(SimpleNamespace(is_root=True, claims=None), "run-1")


def test_shared_run_auth_rejects_authenticated_public_nonowner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wepppy.weppcloud.utils import helpers

    context = browse_auth.AuthContext(
        claims={"token_class": "user", "user_id": 41},
        token_class="user",
        roles=frozenset(),
    )
    monkeypatch.setattr(browse_auth, "resolve_auth_context", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(browse_auth, "authorize_run_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helpers, "get_run_owners_lazy", lambda _runid: [SimpleNamespace(id=42)])
    with pytest.raises(browse_auth.BrowseAuthError) as captured:
        browse_auth.authorize_run_request(
            _request({}),
            runid="public-run",
            config="cfg",
            subpath="roads/vector_upload_attempts/attempt/normalization.json",
            allow_public_without_token=True,
            require_authenticated=False,
        )
    assert captured.value.status_code == 403


def test_aria2c_inventory_omits_sensitive_tree_for_public_caller(tmp_path: Path) -> None:
    (tmp_path / "public.txt").write_text("ok")
    original = tmp_path / "roads" / "vector_upload_attempts" / "attempt" / "original"
    original.mkdir(parents=True)
    (original / "hostile.upload").write_bytes(b"hostile")
    (tmp_path / "innocent-name").symlink_to(original / "hostile.upload")

    public_specs = _download._collect_file_specs(str(tmp_path), "https://example/download", False)
    owner_specs = _download._collect_file_specs(
        str(tmp_path), "https://example/download", False, True
    )
    assert any("public.txt" in item for item in public_specs)
    assert all("vector_upload_attempts" not in item for item in public_specs)
    assert all("innocent-name" not in item for item in public_specs)
    assert any("hostile.upload" in item for item in owner_specs)


def test_retained_original_download_is_attachment_octet_stream(tmp_path: Path) -> None:
    original = tmp_path / "roads" / "vector_upload_attempts" / "attempt" / "original" / "x.upload"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"payload")
    assert is_retained_original(str(original))

    response = asyncio.run(_download.download_response_file(str(original), {}))
    assert response.media_type == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"

    alias = tmp_path / "alias.bin"
    alias.symlink_to(original)
    alias_response = asyncio.run(_download.download_response_file(str(alias), {}))
    assert alias_response.media_type == "application/octet-stream"
    assert alias_response.headers["x-content-type-options"] == "nosniff"


def test_listing_excludes_sensitive_child_before_stat_metadata(tmp_path: Path) -> None:
    (tmp_path / "ordinary").mkdir()
    (tmp_path / "vector_upload_attempts").mkdir()
    entries, total = listing._scan_directory_snapshot(
        str(tmp_path),
        "",
        "name",
        "asc",
        excluded_names=frozenset({"vector_upload_attempts"}),
    )
    assert total == 1
    assert [entry["name"] for entry in entries] == ["ordinary"]


def test_dtale_and_gdal_reject_sensitive_tool_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    context = SimpleNamespace(is_root=True, is_authenticated=True, claims={"roles": ["root"]})
    monkeypatch.setattr(dtale, "authorize_run_request", lambda *_args, **_kwargs: context)
    monkeypatch.setattr(gdalinfo, "authorize_run_request", lambda *_args, **_kwargs: context)

    dtale_open, _culvert, _batch = dtale.build_handlers(
        get_wd=lambda _runid: "/unused",
        assert_within_root=lambda *_args: None,
        resolve_culvert_batch_root=lambda _uuid: Path("/unused"),
        resolve_batch_root=lambda _name: Path("/unused"),
        logger=SimpleNamespace(),
    )
    path = "roads/vector_upload_attempts/a/original/source.upload"
    with pytest.raises(HTTPException) as dtale_error:
        asyncio.run(
            dtale_open(
                _request({"runid": "run-1", "config": "cfg", "subpath": path})
            )
        )
    assert dtale_error.value.status_code == 415

    with pytest.raises(HTTPException) as gdal_error:
        asyncio.run(
            gdalinfo.gdalinfo_with_subpath(
                _request({"runid": "run-1", "config": "cfg", "subpath": path})
            )
        )
    assert gdal_error.value.status_code == 415
