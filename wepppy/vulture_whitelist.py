"""Shared Vulture whitelist for WEPPpy-level dead-code scans."""

from __future__ import annotations

import zipfile

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.contracts import FeaturesExportValidationError

_zip_info = zipfile.ZipInfo(filename="placeholder")

_VULTURE_WHITELIST = (
    FeaturesExportValidationError.to_error_payload,
    service._layer_outputs_from_cache_entry,
    _zip_info.compress_type,
    _zip_info.date_time,
    _zip_info.external_attr,
)
