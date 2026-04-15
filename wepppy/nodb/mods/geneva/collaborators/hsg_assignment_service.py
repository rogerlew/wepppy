from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.errors import GenevaGuardrailError, GenevaValidationError

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


class GenevaHsgAssignmentService:
    """Domain and input-reference checks for Geneva HRU preparation."""

    def enforce_wbt_backend(self, geneva: "Geneva") -> None:
        watershed = geneva.watershed_instance
        if not bool(getattr(watershed, "delineation_backend_is_wbt", False)):
            raise GenevaGuardrailError(
                "Geneva requires the WBT delineation backend.",
                code="unsupported_backend",
                details="Enable Geneva only for runs with delineation_backend_is_wbt=true.",
            )

    def enforce_supported_domain(self, geneva: "Geneva") -> None:
        landuse = geneva.landuse_instance
        soils = geneva.soils_instance
        watershed = geneva.watershed_instance

        lnglat = self._extract_lnglat(watershed)
        outside_us = lnglat is not None and not _is_us_lnglat(lnglat[0], lnglat[1])
        nlcd_compatible = _is_nlcd_compatible(landuse)
        hsg_compatible = _is_hsg_compatible(soils)

        if outside_us or not nlcd_compatible or not hsg_compatible:
            details = {
                "outside_us": outside_us,
                "nlcd_compatible": nlcd_compatible,
                "hsg_compatible": hsg_compatible,
                "lnglat": lnglat,
                "required_datasets": ["NLCD", "US NRCS-compatible HSG source"],
            }
            raise GenevaGuardrailError(
                "Geneva v1 is US-only and requires NLCD + US NRCS-compatible HSG inputs.",
                code="unsupported_domain",
                details=details,
            )

    def resolve_prepare_input_refs(
        self,
        geneva: "Geneva",
        *,
        overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, str]:
        values = dict(overrides or {})
        watershed = geneva.watershed_instance
        landuse = geneva.landuse_instance
        soils = geneva.soils_instance

        resolved = {
            "bound_tif": str(values.get("bound_tif") or getattr(watershed, "bound", "") or ""),
            "landuse_tif": str(values.get("landuse_tif") or getattr(landuse, "lc_fn", "") or ""),
            "hydgrpdcd_tif": str(values.get("hydgrpdcd_tif") or getattr(soils, "ssurgo_fn", "") or ""),
        }

        burn_override = values.get("burn_severity_tif")
        if burn_override not in (None, ""):
            resolved["burn_severity_tif"] = str(burn_override)
        else:
            discovered_burn = self._discover_burn_severity_path(geneva)
            if discovered_burn is not None:
                resolved["burn_severity_tif"] = discovered_burn

        missing = [
            name
            for name, path in resolved.items()
            if name != "burn_severity_tif" and not path.strip()
        ]
        if missing:
            raise GenevaValidationError(
                "Missing required Geneva input references.",
                code="invalid_input",
                details={"missing": missing},
            )

        for key in ("bound_tif", "landuse_tif", "hydgrpdcd_tif"):
            if not Path(resolved[key]).exists():
                raise GenevaValidationError(
                    f"Required input raster does not exist: {resolved[key]}",
                    code="invalid_input",
                    details={"missing_path_key": key, "path": resolved[key]},
                )

        if "burn_severity_tif" in resolved and not Path(resolved["burn_severity_tif"]).exists():
            # Burn severity is optional; drop unavailable path without masking required inputs.
            resolved.pop("burn_severity_tif")

        return resolved

    def resolve_default_hsg(self, config: Mapping[str, Any]) -> tuple[int | None, str | None]:
        configured = config.get("default_hsg_code")
        if configured in (None, ""):
            return None, None
        return int(configured), "user_override"

    def _discover_burn_severity_path(self, geneva: "Geneva") -> str | None:
        try:
            from wepppy.nodb.mods.disturbed import Disturbed
        except ImportError:
            return None

        disturbed = Disturbed.tryGetInstance(geneva.wd)
        if disturbed is None:
            return None

        candidates = [
            getattr(disturbed, "sbs_4class_path", None),
            getattr(disturbed, "disturbed_cropped", None),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            candidate_text = str(candidate)
            if Path(candidate_text).exists():
                return candidate_text
        return None

    def _extract_lnglat(self, watershed: Any) -> tuple[float, float] | None:
        outlet = getattr(watershed, "outlet", None)
        if outlet is not None:
            actual_loc = getattr(outlet, "actual_loc", None)
            if isinstance(actual_loc, (list, tuple)) and len(actual_loc) == 2:
                return float(actual_loc[0]), float(actual_loc[1])

        centroid = getattr(watershed, "_centroid", None)
        if isinstance(centroid, (list, tuple)) and len(centroid) == 2:
            return float(centroid[0]), float(centroid[1])
        return None


def _is_us_lnglat(lng: float, lat: float) -> bool:
    # Broad US envelope including AK/HI/PR for v1 domain guard checks.
    return -179.5 <= lng <= -64.0 and 17.0 <= lat <= 72.5


def _is_nlcd_compatible(landuse: Any) -> bool:
    dataset = str(getattr(landuse, "nlcd_db", "") or "").lower()
    raster_path = str(getattr(landuse, "lc_fn", "") or "").lower()
    return "nlcd" in dataset or "nlcd" in raster_path


def _is_hsg_compatible(soils: Any) -> bool:
    source = str(getattr(soils, "ssurgo_db", "") or "").lower()
    raster_path = str(getattr(soils, "ssurgo_fn", "") or "").lower()
    return (
        "ssurgo" in source
        or "hydgrpdcd" in source
        or "ssurgo" in raster_path
        or "hydgrpdcd" in raster_path
    )


__all__ = ["GenevaHsgAssignmentService"]
