"""Producer-owned logical names for shared project assets.

Names are relative to one already selected project view. Consumers own child
selection, inheritance, access checks and decisions about visibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re

_SCOPE_ROOTS = {"baseline": "output", "roads": "roads/output"}
_PATH_COMPONENT = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*")


def wepp_output_scope_root(output_scope: str) -> str:
    """Return the directory below wepp/ for a normalized output scope."""
    try:
        return _SCOPE_ROOTS[output_scope]
    except KeyError:
        raise ValueError(f"Unsupported output scope: {output_scope!r}") from None


@dataclass(frozen=True, slots=True)
class ProjectAsset:
    """An exact logical key or a bounded WEPP output-scope template."""

    asset_id: str
    path_template: str

    def __post_init__(self) -> None:
        components = self.path_template.split("/")
        if not self.asset_id or not all(
            part == "{scope_root}" or _PATH_COMPONENT.fullmatch(part)
            for part in components
        ):
            raise ValueError(f"Invalid asset declaration: {self!r}")
        if components.count("{scope_root}") > 1 or components[-1] == "{scope_root}":
            raise ValueError(f"Invalid scope template: {self.path_template!r}")

    @property
    def filename(self) -> str:
        return PurePosixPath(self.path_template).name

    def relative_path(self, output_scope: str = "baseline") -> str:
        return self.path_template.replace("{scope_root}", wepp_output_scope_root(output_scope))


WATERSHED_HILLSLOPES = ProjectAsset("watershed.hillslopes", "watershed/hillslopes.parquet")
WEPP_LOSS_HILL = ProjectAsset("wepp.loss_hill", "wepp/{scope_root}/interchange/loss_pw0.hill.parquet")


def _index_assets(*assets: ProjectAsset) -> dict[str, ProjectAsset]:
    by_id: dict[str, ProjectAsset] = {}
    by_key: dict[str, ProjectAsset] = {}
    for asset in assets:
        if asset.asset_id in by_id:
            raise ValueError(f"Duplicate asset ID: {asset.asset_id}")
        by_id[asset.asset_id] = asset
        for scope in _SCOPE_ROOTS:
            key = asset.relative_path(scope)
            if by_key.setdefault(key, asset) is not asset:
                raise ValueError(f"Conflicting asset declarations for {key}")
    return by_id


_BY_ID = _index_assets(WATERSHED_HILLSLOPES, WEPP_LOSS_HILL)


def get_asset(asset_id: str) -> ProjectAsset:
    """Look up an exact declaration ID; unknown IDs raise KeyError."""
    return _BY_ID[asset_id]
