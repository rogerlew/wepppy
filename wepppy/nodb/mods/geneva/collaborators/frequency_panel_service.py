from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.errors import GenevaKernelError

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva

_DEFAULT_DURATIONS = (5, 10, 30, 60, 120, 180, 360, 720, 1440)
_DEFAULT_ARI = (1, 2, 5, 10, 25, 50, 100)
_DEFAULT_CLIGEN_PATH = "climate/wepp_cli_pds_mean_metric.csv"
_DEFAULT_NOAA_PATH = "climate/atlas14_intensity_pds_mean_metric.csv"


class GenevaFrequencyPanelService:
    """Build and persist Geneva frequency panel artifacts."""

    def build_frequency_panel(
        self,
        geneva: "Geneva",
        *,
        durations_minutes: list[int] | tuple[int, ...] | None = None,
        ari_years: list[int] | tuple[int, ...] | None = None,
        rebuild: bool = False,
        sources: Mapping[str, str | None] | None = None,
    ) -> dict[str, Any]:
        artifact_io = geneva.artifact_io
        if not rebuild and artifact_io.exists(geneva.wd, "frequency_panel.json"):
            return artifact_io.read_json(geneva.wd, "frequency_panel.json")

        payload_sources = {
            "cligen_freq": _DEFAULT_CLIGEN_PATH,
            "noaa14_pds": _DEFAULT_NOAA_PATH,
        }
        for key, value in (sources or {}).items():
            if key in payload_sources:
                payload_sources[key] = None if value in (None, "") else str(value)

        payload: dict[str, Any] = {
            "kernel_schema_version": 1,
            "durations_minutes": [int(value) for value in (durations_minutes or _DEFAULT_DURATIONS)],
            "ari_years": [int(value) for value in (ari_years or _DEFAULT_ARI)],
            "distribution_type": "neh4_type_b",
            "allow_duration_interpolation": False,
            "source_root": geneva.wd,
            "sources": {
                "cligen_freq": payload_sources["cligen_freq"],
                "noaa14_pds": payload_sources["noaa14_pds"],
            },
        }

        response = geneva.kernel_gateway.call_json_api("geneva_build_frequency_panel", payload)
        cells = response.get("cells")
        if not isinstance(cells, list):
            raise GenevaKernelError(
                "geneva_build_frequency_panel returned invalid cells payload.",
                code="contract_violation",
            )

        artifact_io.write_json(geneva.wd, "frequency_panel.json", response)
        return response


__all__ = ["GenevaFrequencyPanelService"]
