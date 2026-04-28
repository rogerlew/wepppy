from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.errors import GenevaKernelError, GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import normalize_frequency_panel_payload

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva

_DEFAULT_DURATIONS = (5, 10, 15, 30, 60, 120, 180, 360, 720, 1440)
_DEFAULT_ARI = (1, 2, 5, 10, 25, 50, 100)
_DEFAULT_CLIGEN_PATH = "climate/wepp_cli_pds_mean_metric.csv"
_DEFAULT_NOAA_PATH = "climate/atlas14_intensity_pds_mean_metric.csv"
_NORMALIZED_CLIGEN_RELPATH = "normalized_sources/wepp_cli_pds_mean_metric_kernel.csv"


class GenevaFrequencyPanelService:
    """Build and persist Geneva frequency panel artifacts."""

    def normalize_request(self, payload: Mapping[str, Any] | None) -> dict[str, Any]:
        data = dict(payload or {})

        try:
            schema_version = int(data.get("schema_version", 1))
        except (TypeError, ValueError) as exc:
            raise GenevaValidationError(
                "schema_version must equal 1",
                code="invalid_input",
                details="schema_version must equal 1",
                status_code=400,
            ) from exc
        if schema_version != 1:
            raise GenevaValidationError(
                "schema_version must equal 1",
                code="invalid_input",
                details="schema_version must equal 1",
                status_code=400,
            )

        distribution_type = data.get("distribution_type", "neh4_type_b")
        if distribution_type not in {"neh4_type_b"}:
            raise GenevaValidationError(
                "hyetograph.distribution_type is unsupported in v1; expected neh4_type_b",
                code="invalid_input",
                details={
                    "distribution_type": distribution_type,
                    "supported_distribution_types": ["neh4_type_b"],
                    "reserved_distribution_types": ["uniform", "custom_breakpoint"],
                },
                status_code=400,
            )

        durations_raw = data.get("durations_minutes")
        ari_raw = data.get("ari_years")
        sources_raw = data.get("sources")
        rebuild_raw = data.get("rebuild", False)

        if durations_raw not in (None, "") and not isinstance(durations_raw, (list, tuple)):
            raise GenevaValidationError(
                "durations_minutes must be a list of positive integers",
                code="invalid_input",
                details="durations_minutes must be a list of positive integers",
                status_code=400,
            )
        if ari_raw not in (None, "") and not isinstance(ari_raw, (list, tuple)):
            raise GenevaValidationError(
                "ari_years must be a list of positive integers",
                code="invalid_input",
                details="ari_years must be a list of positive integers",
                status_code=400,
            )
        if not isinstance(rebuild_raw, bool):
            raise GenevaValidationError(
                "rebuild must be boolean",
                code="invalid_input",
                details="rebuild must be boolean",
                status_code=400,
            )
        if sources_raw not in (None, "") and not isinstance(sources_raw, Mapping):
            raise GenevaValidationError(
                "sources must be an object when provided",
                code="invalid_input",
                details="sources must be an object when provided",
                status_code=400,
            )

        try:
            durations_minutes = [int(value) for value in (durations_raw or _DEFAULT_DURATIONS)]
        except (TypeError, ValueError) as exc:
            raise GenevaValidationError(
                "durations_minutes must be a list of positive integers",
                code="invalid_input",
                details="durations_minutes must be a list of positive integers",
                status_code=400,
            ) from exc
        try:
            ari_years = [int(value) for value in (ari_raw or _DEFAULT_ARI)]
        except (TypeError, ValueError) as exc:
            raise GenevaValidationError(
                "ari_years must be a list of positive integers",
                code="invalid_input",
                details="ari_years must be a list of positive integers",
                status_code=400,
            ) from exc
        if any(value <= 0 for value in durations_minutes):
            raise GenevaValidationError(
                "durations_minutes values must be positive integers",
                code="invalid_input",
                details={"durations_minutes": durations_minutes},
                status_code=400,
            )
        if any(value <= 0 for value in ari_years):
            raise GenevaValidationError(
                "ari_years values must be positive integers",
                code="invalid_input",
                details={"ari_years": ari_years},
                status_code=400,
            )

        normalized_sources: dict[str, str | None] = {}
        for key, value in dict(sources_raw or {}).items():
            key_text = str(key).strip()
            if key_text not in {"cligen_freq", "noaa14_pds"}:
                raise GenevaValidationError(
                    "sources keys must be cligen_freq and/or noaa14_pds",
                    code="invalid_input",
                    details={"invalid_source_key": key_text},
                    status_code=400,
                )
            normalized_sources[key_text] = None if value in (None, "") else str(value)

        return {
            "schema_version": 1,
            "durations_minutes": durations_minutes,
            "ari_years": ari_years,
            "rebuild": rebuild_raw,
            "sources": normalized_sources,
        }

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
            payload = artifact_io.read_json(geneva.wd, "frequency_panel.json")
            return normalize_frequency_panel_payload(payload)

        payload_sources = {
            "cligen_freq": _DEFAULT_CLIGEN_PATH,
            "noaa14_pds": _DEFAULT_NOAA_PATH,
        }
        for key, value in (sources or {}).items():
            if key in payload_sources:
                payload_sources[key] = None if value in (None, "") else str(value)

        payload_sources["cligen_freq"] = self._normalize_cligen_source_for_kernel(
            geneva,
            payload_sources["cligen_freq"],
        )

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

        normalized = normalize_frequency_panel_payload(response)
        artifact_io.write_json(geneva.wd, "frequency_panel.json", normalized)
        return normalized

    def get_frequency_panel(self, geneva: "Geneva") -> dict[str, Any]:
        artifact_io = geneva.artifact_io
        if not artifact_io.exists(geneva.wd, "frequency_panel.json"):
            raise GenevaValidationError(
                "Frequency panel has not been built yet.",
                code="not_found",
                details="Run build_frequency_panel before requesting frequency panel payload.",
                status_code=404,
            )
        payload = artifact_io.read_json(geneva.wd, "frequency_panel.json")
        return normalize_frequency_panel_payload(payload)

    def _normalize_cligen_source_for_kernel(
        self,
        geneva: "Geneva",
        source_path: str | None,
    ) -> str | None:
        if source_path in (None, ""):
            return None

        raw_source = str(source_path)
        resolved = Path(raw_source)
        if not resolved.is_absolute():
            resolved = Path(geneva.wd) / resolved
        if not resolved.exists():
            return raw_source

        normalized_text = _normalize_cligen_text_for_kernel(resolved.read_text(encoding="utf-8"))
        if normalized_text is None:
            return raw_source

        artifact_io = geneva.artifact_io
        artifact_path = artifact_io.resolve_path(geneva.wd, _NORMALIZED_CLIGEN_RELPATH)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        if not artifact_path.exists() or artifact_path.read_text(encoding="utf-8") != normalized_text:
            artifact_io.write_text(geneva.wd, _NORMALIZED_CLIGEN_RELPATH, normalized_text)
        return str(artifact_path)


def _normalize_cligen_text_for_kernel(text: str) -> str | None:
    normalized_lines: list[str] = []
    has_ari_row = False
    has_storm_depth_row = False
    has_precipitation_depth_row = False
    has_duration_row = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if lower.startswith("by metric for ari (years):"):
            has_ari_row = True
        elif lower.startswith("storm depth (mm):"):
            has_storm_depth_row = True
        elif lower.startswith("precipitation depth (mm):"):
            has_precipitation_depth_row = True
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]
            _, separator, rest = raw_line.partition(":")
            raw_line = f"{indent}Storm depth (mm){separator}{rest}"
        elif lower.startswith("storm duration (hours):"):
            has_duration_row = True
        normalized_lines.append(raw_line)

    if has_storm_depth_row:
        return None
    if not has_precipitation_depth_row or not has_ari_row or not has_duration_row:
        return None

    return "\n".join(normalized_lines) + "\n"


__all__ = ["GenevaFrequencyPanelService"]
