from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import pandas as pd

if TYPE_CHECKING:
    from wepppy.nodb.mods.omni.omni import Omni


class OmniArtifactExportService:
    """Route Omni artifact/report exports through dedicated collaborator seams."""

    def build_contrast_ids_geojson(self, omni: "Omni") -> Optional[str]:
        return omni._build_contrast_ids_geojson_impl()

    def scenarios_report(self, omni: "Omni") -> pd.DataFrame:
        return omni._scenarios_report_impl()

    def contrasts_report(self, omni: "Omni") -> pd.DataFrame:
        return omni._contrasts_report_impl()

    def compile_hillslope_summaries(self, omni: "Omni") -> pd.DataFrame:
        return omni._compile_hillslope_summaries_impl()

    def compile_channel_summaries(self, omni: "Omni") -> pd.DataFrame:
        return omni._compile_channel_summaries_impl()
