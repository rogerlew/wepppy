"""Pin producer names independently of either consumer's listing policy."""

from __future__ import annotations

import pytest

from wepppy.project_assets import (
    WATERSHED_HILLSLOPES,
    WEPP_LOSS_HILL,
    ProjectAsset,
    _index_assets,
    get_asset,
)


def test_lookup_and_scoped_paths() -> None:
    assert get_asset("watershed.hillslopes") is WATERSHED_HILLSLOPES
    assert get_asset("wepp.loss_hill") is WEPP_LOSS_HILL
    assert WATERSHED_HILLSLOPES.relative_path() == "watershed/hillslopes.parquet"
    assert WEPP_LOSS_HILL.relative_path() == "wepp/output/interchange/loss_pw0.hill.parquet"
    assert WEPP_LOSS_HILL.relative_path("roads") == "wepp/roads/output/interchange/loss_pw0.hill.parquet"
    assert WATERSHED_HILLSLOPES.relative_path("roads") == WATERSHED_HILLSLOPES.relative_path()
    with pytest.raises(KeyError):
        get_asset("missing")
    with pytest.raises(ValueError, match="Unsupported output scope"):
        WEPP_LOSS_HILL.relative_path("scenario")


@pytest.mark.parametrize("template", [
    "/outside", "../outside", "wepp//loss", "wepp/{arbitrary}/loss",
    "{scope_root}/{scope_root}/loss", "wepp/{scope_root}", "wepp/*.parquet", r"wepp\loss",
])
def test_declaration_rejects_unbounded_templates(template: str) -> None:
    with pytest.raises(ValueError):
        ProjectAsset("bad", template)


def test_registry_rejects_collisions_before_lookup() -> None:
    with pytest.raises(ValueError, match="Duplicate asset ID"):
        _index_assets(WEPP_LOSS_HILL, ProjectAsset("wepp.loss_hill", "other"))
    same_roads_key = ProjectAsset("other", WEPP_LOSS_HILL.relative_path("roads"))
    with pytest.raises(ValueError, match="Conflicting asset declarations"):
        _index_assets(WEPP_LOSS_HILL, same_roads_key)
