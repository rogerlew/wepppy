from __future__ import annotations

import pytest

from wepppy.nodb.mods.features_export.profiles import (
    load_builtin_profiles,
    profile_bundle_member_sources,
)

pytestmark = pytest.mark.unit


def test_load_builtin_profiles_includes_temporal_yearly_profile() -> None:
    profiles = load_builtin_profiles()
    keys = [str(profile.get("key")) for profile in profiles]

    assert keys[:2] == ["prep_details", "post_wepp"]
    assert "temporal_yearly" in keys

    temporal_profile = next(profile for profile in profiles if profile.get("key") == "temporal_yearly")
    request = temporal_profile.get("request")
    assert isinstance(request, dict)
    assert request["layers"] == ["wepp.interchange.loss_all_years_hill"]
    assert request["format"] == "parquet"
    assert request["units"] == "project"
    assert request["crs"] == "wgs"
    assert request["output_scopes"] == ["baseline"]
    assert request["tabular"] == {"concatenate_tables": False, "temporal_layout": "wide"}
    assert request["temporal"] == {"mode": "yearly", "year_selection": "all"}


def test_profile_bundle_member_sources_includes_temporal_yearly_profile() -> None:
    members = profile_bundle_member_sources()

    assert "profiles/temporal-yearly.yml" in members
