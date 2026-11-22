"""Inspect a declared asset in one published query catalog without triggering refresh."""

from __future__ import annotations

from wepppy.project_assets import WEPP_LOSS_HILL, get_asset
from wepppy.query_engine.catalog import CatalogEntry, DatasetCatalog


def declared_catalog_entry(
    catalog: DatasetCatalog,
    asset_id: str,
    *,
    output_scope: str = "baseline",
    scenario: str | None = None,
    contrast_id: str | None = None,
) -> CatalogEntry | None:
    """Return the published entry for one selected asset, without opening its source.

    Named projections apply only to baseline child hill loss. Presence in the child's
    own catalog does not establish visibility in the parent. Physical authorization
    and Roads currentness are enforced by the caller's normal scoped query planner.
    """
    asset = get_asset(asset_id)
    key = asset.relative_path(output_scope)
    if scenario is not None or contrast_id is not None:
        if scenario is not None and contrast_id is not None:
            raise ValueError("Choose one Omni scenario or contrast")
        if asset != WEPP_LOSS_HILL or output_scope != "baseline":
            raise ValueError("Named Omni projections support baseline hill loss only")
        kind, name = ("scenarios", scenario) if scenario is not None else ("contrasts", contrast_id)
        if not name or name in (".", "..") or any(char in name for char in ("/", "\\", "\0")):
            raise ValueError("Expected one Omni child name")
        key = f"_pups/omni/{kind}/{name}/{key}"

    # Retained listings can contain duplicates even though dictionary lookup is unique.
    matches = [entry for entry in catalog.entries() if entry.path == key]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous published catalog key: {key}")
    return catalog.get(key)
