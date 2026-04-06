from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.weppcloud.usersum_docs.docs_contracts import load_and_validate_contracts
from wepppy.weppcloud.usersum_docs.docs_index import build_generated_index


pytestmark = pytest.mark.routes


def test_generated_usersum_index_contains_manifest_documents() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    usersum_dir = repo_root / "wepppy" / "weppcloud" / "routes" / "usersum"

    contracts = load_and_validate_contracts(
        base_dir=usersum_dir,
        repo_root=repo_root,
        require_local_files=True,
        require_vendor_files=True,
    )
    index = build_generated_index(contracts, repo_root=repo_root)

    assert len(index.documents) == len(contracts.docs)
    assert index.nav_tree


def test_generated_usersum_index_includes_vendor_routes_and_breadcrumbs() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    usersum_dir = repo_root / "wepppy" / "weppcloud" / "routes" / "usersum"

    contracts = load_and_validate_contracts(
        base_dir=usersum_dir,
        repo_root=repo_root,
        require_local_files=True,
        require_vendor_files=True,
    )
    index = build_generated_index(contracts, repo_root=repo_root)
    by_doc_id = {doc["doc_id"]: doc for doc in index.documents}

    vendor_doc = by_doc_id["vendor.weppcloud_wbt.culvert_web_app_hydroenforcement"]
    assert vendor_doc["vendor_route_path"] == (
        "/usersum/vendor/weppcloud-wbt/docs/hydroenforcement/culvert-web-app-hydroenforcement.md"
    )
    assert vendor_doc["breadcrumbs"]
    assert vendor_doc["breadcrumbs"][-1]["title"] == "Culvert Web App Hydroenforcement"

    wepp_forest_doc = by_doc_id["usersum.weppcloud.wepp_forest_change_log"]
    assert wepp_forest_doc["source"] == "vendor"
    assert wepp_forest_doc["vendor_route_path"] == "/usersum/vendor/wepp-forest/change-log.md"
    assert wepp_forest_doc["legacy_route_path"] == "/usersum/view/weppcloud/wepp-forest-change-log.md"

    local_doc = by_doc_id["usersum.weppcloud.mods_overview"]
    assert local_doc["legacy_route_path"] == "/usersum/view/weppcloud/mods-overview.md"
    assert local_doc["route_path"] == "/usersum/doc/usersum.weppcloud.mods_overview"
