"""Low-level SSURGO fallback support with explicit raster provenance."""

from __future__ import annotations

import hashlib
import json
import math
import os
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FULL_SSURGO_DATASET = Path("ssurgo/gNATSGSO/2025")
CANDIDATE_ARTIFACT_DIRNAME = "ssurgo_candidate_mukey"
CANDIDATE_ACTIVE_MANIFEST = "active.json"
POLICY_VERSION = "ssurgo_local_vector_profile_v1"
DIRECT_VECTOR_FIELDS: dict[str, tuple[float, float]] = {
    "dbthirdbar_r": (0.5, 3.0),
    "ksat_r": (0.0, 100_000.0),
    "cec7_r": (0.0, 200.0),
    "hzdepb_r": (0.0, 1_000.0),
    "fraggt10_r": (0.0, 100.0),
    "frag3to10_r": (0.0, 100.0),
    "sandtotal_r": (0.0, 100.0),
    "claytotal_r": (0.0, 100.0),
}


class CandidateRasterUnavailable(RuntimeError):
    """The local-candidate stage cannot safely use a raster artifact."""


@dataclass(frozen=True)
class CandidateRasterArtifact:
    """Validated active candidate raster evidence; paths are run-relative."""

    raster_path: Path
    metadata_path: Path
    manifest_path: Path
    metadata: dict[str, Any]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _resolved_directory(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_dir():
        raise CandidateRasterUnavailable(f"candidate artifact root is not a directory: {resolved}")
    return resolved


def _resolved_child(root: Path, relative_name: str, *, must_exist: bool = False) -> Path:
    candidate = root / relative_name
    if candidate.parent.resolve(strict=True) != root:
        raise CandidateRasterUnavailable(f"candidate artifact path escapes root: {relative_name!r}")
    if candidate.is_symlink():
        raise CandidateRasterUnavailable(f"candidate artifact path may not be a symlink: {relative_name!r}")
    if must_exist:
        resolved = candidate.resolve(strict=True)
        if not _is_relative_to(resolved, root) or not resolved.is_file():
            raise CandidateRasterUnavailable(f"candidate artifact is not a regular root-contained file: {relative_name!r}")
        return resolved
    return candidate


def canonical_full_ssurgo_mukey_raster() -> Path:
    """Resolve the configured, root-contained 2025 gNATSGO MUKEY VRT."""
    geodata_root = Path(os.environ.get("GEODATA_DIR", "/geodata")).resolve(strict=True)
    approved_root = (geodata_root / FULL_SSURGO_DATASET).resolve(strict=True)
    if not _is_relative_to(approved_root, geodata_root) or not approved_root.is_dir():
        raise FileNotFoundError(f"Canonical 2025 gNATSGO root is unavailable: {approved_root}")
    source = (approved_root / ".vrt").resolve(strict=True)
    if not _is_relative_to(source, approved_root) or not source.is_file() or not os.access(source, os.R_OK):
        raise FileNotFoundError(f"Full 2025 gNATSGO MUKEY VRT is unavailable: {source}")
    return source


def full_ssurgo_mukey_raster_path() -> str:
    """Return the configured canonical full 2025 gNATSGO MUKEY VRT path."""
    return str(canonical_full_ssurgo_mukey_raster())


def prepare_padded_candidate_raster(
    *,
    soils_dir: str | Path,
    primary_raster_path: str | Path,
    padding_m: float = 2_000.0,
) -> CandidateRasterArtifact:
    """Publish one validated immutable candidate crop and switch its manifest.

    The source is intentionally not an argument: only the canonical configured
    gNATSGO source may feed this operation. The native crop primitive owns CRS
    geometry; this boundary owns run-path containment and publication.
    """
    if padding_m != 2_000.0:
        raise ValueError("SSURGO fallback candidate padding must be exactly 2000 m")
    source = canonical_full_ssurgo_mukey_raster()
    soils_root = _resolved_directory(soils_dir)
    primary_input = Path(primary_raster_path)
    primary = primary_input.resolve(strict=True)
    if (
        primary_input.name != "ssurgo.tif"
        or primary_input.is_symlink()
        or not primary.is_file()
        or primary.parent != soils_root
    ):
        raise CandidateRasterUnavailable(
            f"primary SSURGO raster must be the regular run-contained soils/ssurgo.tif: {primary}"
        )
    artifact_dir = soils_root / CANDIDATE_ARTIFACT_DIRNAME
    if artifact_dir.is_symlink():
        raise CandidateRasterUnavailable("candidate artifact directory may not be a symlink")
    artifact_dir.mkdir(mode=0o750, exist_ok=True)
    artifact_root = _resolved_directory(artifact_dir)
    if not _is_relative_to(artifact_root, soils_root):
        raise CandidateRasterUnavailable("candidate artifact root escapes the run soils directory")

    try:
        from wepppyo3.raster_characteristics import (
            categorical_raster_metadata,
            crop_categorical_raster_to_padded_reference,
        )
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 categorical raster crop support is required for SSURGO fallback"
        ) from exc

    generation = uuid.uuid4().hex
    raster_name = f"candidate-{generation}.tif"
    metadata_name = f"candidate-{generation}.json"
    raster_path = _resolved_child(artifact_root, raster_name)
    metadata_path = _resolved_child(artifact_root, metadata_name)
    temporary_raster = raster_path.with_name(f".{raster_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        crop_categorical_raster_to_padded_reference(
            str(source), str(primary), str(temporary_raster), padding_m, 1
        )
        _fsync_file(temporary_raster)
        os.replace(temporary_raster, raster_path)
        _fsync_directory(artifact_root)
        bounds, crs_wkt, width, height = categorical_raster_metadata(str(raster_path))
        metadata: dict[str, Any] = {
            "policy_version": POLICY_VERSION,
            "source": {
                "identity": "gNATSGO-2025-mukey-vrt",
                "sha256": _sha256(source),
            },
            "primary_raster_sha256": _sha256(primary),
            "primary_raster": "ssurgo.tif",
            "padding_m": padding_m,
            "bounds": [float(value) for value in bounds],
            "crs_wkt": crs_wkt,
            "width": int(width),
            "height": int(height),
            "raster_sha256": _sha256(raster_path),
        }
        _atomic_json(metadata_path, metadata)
        manifest_path = _resolved_child(artifact_root, CANDIDATE_ACTIVE_MANIFEST)
        _atomic_json(
            manifest_path,
            {
                "policy_version": POLICY_VERSION,
                "raster": raster_name,
                "metadata": metadata_name,
                "raster_sha256": metadata["raster_sha256"],
                "metadata_sha256": _sha256(metadata_path),
                "primary_raster_sha256": metadata["primary_raster_sha256"],
            },
        )
    except (OSError, RuntimeError, ValueError):
        if temporary_raster.exists():
            temporary_raster.unlink()
        raise
    return load_active_candidate_raster(soils_root, primary_raster_path=primary)


def load_active_candidate_raster(
    soils_dir: str | Path,
    *,
    primary_raster_path: str | Path,
) -> CandidateRasterArtifact:
    """Load only a complete active manifest whose map and metadata still match."""
    soils_root = _resolved_directory(soils_dir)
    artifact_dir = soils_root / CANDIDATE_ARTIFACT_DIRNAME
    if artifact_dir.is_symlink():
        raise CandidateRasterUnavailable("candidate artifact directory may not be a symlink")
    artifact_root = _resolved_directory(artifact_dir)
    if not _is_relative_to(artifact_root, soils_root):
        raise CandidateRasterUnavailable("candidate artifact root escapes the run soils directory")
    manifest_path = _resolved_child(artifact_root, CANDIDATE_ACTIVE_MANIFEST, must_exist=True)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raster_name = manifest["raster"]
        metadata_name = manifest["metadata"]
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise CandidateRasterUnavailable("candidate active manifest is unreadable") from exc
    if not isinstance(raster_name, str) or not isinstance(metadata_name, str):
        raise CandidateRasterUnavailable("candidate active manifest paths are invalid")
    raster_path = _resolved_child(artifact_root, raster_name, must_exist=True)
    metadata_path = _resolved_child(artifact_root, metadata_name, must_exist=True)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CandidateRasterUnavailable("candidate metadata is unreadable") from exc
    primary_input = Path(primary_raster_path)
    primary = primary_input.resolve(strict=True)
    if (
        primary_input.name != "ssurgo.tif"
        or primary_input.is_symlink()
        or not primary.is_file()
        or primary.parent != soils_root
    ):
        raise CandidateRasterUnavailable("candidate primary raster identity is not run-contained ssurgo.tif")
    try:
        from wepppyo3.raster_characteristics import categorical_raster_metadata
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 categorical raster metadata support is required for SSURGO fallback"
        ) from exc
    try:
        actual_bounds, actual_crs_wkt, actual_width, actual_height = categorical_raster_metadata(str(raster_path))
    except (OSError, ValueError, RuntimeError) as exc:
        raise CandidateRasterUnavailable("candidate raster metadata is unreadable") from exc
    metadata_bounds = metadata.get("bounds")
    metadata_source = metadata.get("source")
    try:
        normalized_metadata_bounds = [float(value) for value in metadata_bounds]
    except (TypeError, ValueError):
        normalized_metadata_bounds = []
    required_matches = (
        metadata.get("policy_version") == POLICY_VERSION,
        manifest.get("policy_version") == POLICY_VERSION,
        metadata.get("primary_raster") == "ssurgo.tif",
        metadata.get("padding_m") == 2_000.0,
        isinstance(metadata_source, dict) and metadata_source.get("identity") == "gNATSGO-2025-mukey-vrt",
        isinstance(metadata_bounds, list) and len(metadata_bounds) == 4,
        normalized_metadata_bounds == [float(value) for value in actual_bounds],
        metadata.get("crs_wkt") == actual_crs_wkt,
        metadata.get("width") == actual_width,
        metadata.get("height") == actual_height,
        metadata.get("raster_sha256") == manifest.get("raster_sha256") == _sha256(raster_path),
        manifest.get("metadata_sha256") == _sha256(metadata_path),
        metadata.get("primary_raster_sha256") == manifest.get("primary_raster_sha256") == _sha256(primary),
        isinstance(metadata_source, dict)
        and metadata_source.get("sha256") == _sha256(canonical_full_ssurgo_mukey_raster()),
    )
    if not all(required_matches):
        raise CandidateRasterUnavailable("candidate artifact provenance does not match its active manifest")
    return CandidateRasterArtifact(raster_path, metadata_path, manifest_path, metadata)


def candidate_raster_mukeys(artifact: CandidateRasterArtifact) -> set[int]:
    """Enumerate positive MUKEYs from the bounded persisted map in native code."""
    try:
        from wepppyo3.raster_characteristics import categorical_support_within_bounds
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 categorical support is required for SSURGO fallback candidate enumeration"
        ) from exc
    bounds = artifact.metadata.get("bounds")
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise CandidateRasterUnavailable("candidate metadata lacks raster bounds")
    support = categorical_support_within_bounds(str(artifact.raster_path), tuple(float(v) for v in bounds), 0.0)
    return {int(mukey) for mukey, _pixels in support if int(mukey) > 0}


def _mukey_number(mukey: int | str) -> int:
    try:
        return int(str(mukey).split("-", 1)[0])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"MUKEY must begin with an integer: {mukey!r}") from exc


def categorical_candidate_support(
    raster_path: str | Path,
    bounds_in_raster_crs: tuple[float, float, float, float],
    radius_m: float,
    invalid_mukeys: Iterable[int | str],
    valid_mukeys: Iterable[int | str],
) -> list[tuple[str, int]]:
    """Return deterministic valid donor support from one persisted categorical map."""
    try:
        from wepppyo3.raster_characteristics import categorical_support_within_bounds
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 categorical support is required for SSURGO fallback candidate support"
        ) from exc
    valid_by_number: dict[int, str] = {}
    for mukey in valid_mukeys:
        numeric_mukey = _mukey_number(mukey)
        canonical_mukey = str(mukey)
        previous = valid_by_number.setdefault(numeric_mukey, canonical_mukey)
        if previous != canonical_mukey:
            raise ValueError(
                f"Ambiguous buildable MUKEY values for {numeric_mukey}: {previous!r}, {canonical_mukey!r}"
            )
    support = categorical_support_within_bounds(
        str(raster_path),
        bounds_in_raster_crs,
        radius_m,
        excluded_values={_mukey_number(mukey) for mukey in invalid_mukeys},
    )
    return sorted(
        ((valid_by_number[mukey], pixel_support) for mukey, pixel_support in support if mukey in valid_by_number),
        key=lambda item: (-item[1], _mukey_number(item[0]), item[0]),
    )


def categorical_candidate_support_wgs84(
    raster_path: str | Path,
    longitude_wgs84: float,
    latitude_wgs84: float,
    radius_m: float,
    invalid_mukeys: Iterable[int | str],
    valid_mukeys: Iterable[int | str],
) -> list[tuple[str, int]]:
    """Return deterministic support around a WGS84 source location in native code."""
    try:
        from wepppyo3.raster_characteristics import categorical_support_within_wgs84_radius
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 WGS84 categorical support is required for SSURGO fallback"
        ) from exc
    valid_by_number = {_mukey_number(mukey): str(mukey) for mukey in valid_mukeys}
    support = categorical_support_within_wgs84_radius(
        str(raster_path),
        longitude_wgs84,
        latitude_wgs84,
        radius_m,
        excluded_values={_mukey_number(mukey) for mukey in invalid_mukeys},
    )
    return sorted(
        ((valid_by_number[mukey], pixels) for mukey, pixels in support if mukey in valid_by_number),
        key=lambda item: (-item[1], _mukey_number(item[0]), item[0]),
    )


def categorical_value_centroid_wgs84(raster_path: str | Path, value: int | str) -> tuple[float, float]:
    """Return a categorical source location without Python raster-cell iteration."""
    try:
        from wepppyo3.raster_characteristics import categorical_value_centroid_wgs84 as native_centroid
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 categorical centroid support is required for SSURGO fallback"
        ) from exc
    longitude, latitude = native_centroid(str(raster_path), _mukey_number(value))
    return float(longitude), float(latitude)


def raw_mukey_source_locations_wgs84(
    hillslope_raster_path: str | Path,
    ssurgo_raster_path: str | Path,
    raw_pairs: Iterable[tuple[int | str, int | str]],
) -> dict[str, tuple[float, float]]:
    """Locate raw dominant MUKEY occurrences inside their hillslopes in one scan."""
    try:
        from wepppyo3.raster_characteristics import intersecting_categorical_value_centroids_wgs84
    except ImportError as exc:
        raise RuntimeError(
            "wepppyo3 intersecting categorical centroid support is required for SSURGO fallback"
        ) from exc
    pairs = [(_mukey_number(topaz_id), _mukey_number(mukey)) for topaz_id, mukey in raw_pairs]
    native_locations = intersecting_categorical_value_centroids_wgs84(
        str(hillslope_raster_path), str(ssurgo_raster_path), pairs
    )
    return {str(topaz_id): (float(longitude), float(latitude)) for topaz_id, (longitude, latitude) in native_locations.items()}


def full_ssurgo_candidate_support(
    bounds_epsg5070: tuple[float, float, float, float],
    radius_m: float,
    invalid_mukeys: Iterable[int | str],
    valid_mukeys: Iterable[int | str],
) -> list[tuple[str, int]]:
    """Research-only full-map support; production must use the persisted map."""
    return categorical_candidate_support(
        full_ssurgo_mukey_raster_path(), bounds_epsg5070, radius_m, invalid_mukeys, valid_mukeys
    )


def direct_shallow_profile(layers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Extract the first stored raw horizon usable by the v1 vector policy."""
    for index, layer in enumerate(layers):
        try:
            organic_matter = float(layer.get("om_r"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(organic_matter) or not 0.0 <= organic_matter <= 20.0:
            continue
        values: dict[str, float] = {}
        for field, (minimum, maximum) in DIRECT_VECTOR_FIELDS.items():
            try:
                value = float(layer.get(field))
            except (TypeError, ValueError):
                continue
            is_valid = math.isfinite(value) and minimum <= value <= maximum
            if field == "hzdepb_r":
                is_valid = is_valid and value > 0.0
            if is_valid:
                values[field] = value
        if (
            "sandtotal_r" in values
            and "claytotal_r" in values
            and values["sandtotal_r"] + values["claytotal_r"] > 100.0
        ):
            values.pop("sandtotal_r")
            values.pop("claytotal_r")
        if len(values) >= 3:
            return {
                "horizon_index": index,
                "chkey": layer.get("chkey"),
                "organic_matter_pct": organic_matter,
                "direct_values": values,
            }
    return {"horizon_index": None, "chkey": None, "direct_values": {}}


def select_vector_donor(
    source_profile: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Return the v1 vector winner within one already-successful radius."""
    source_values = source_profile.get("direct_values", {})
    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_values = candidate.get("profile", {}).get("direct_values", {})
        fields = sorted(set(source_values) & set(candidate_values))
        if len(fields) < 3:
            continue
        scales = {
            field: max(0.05 * abs(float(source_values[field])), 0.05 * abs(float(candidate_values[field])), 1.0e-6)
            for field in fields
        }
        distance = sum(
            abs(float(source_values[field]) - float(candidate_values[field])) / scales[field]
            for field in fields
        ) / len(fields)
        scored.append(
            {
                **dict(candidate),
                "shared_fields": fields,
                "scales": scales,
                "distance": distance,
            }
        )
    if not scored:
        return None
    return min(
        scored,
        key=lambda item: (item["distance"], -int(item["pixel_support"]), _mukey_number(item["mukey"])),
    )


__all__ = [
    "CANDIDATE_ACTIVE_MANIFEST",
    "CANDIDATE_ARTIFACT_DIRNAME",
    "CandidateRasterArtifact",
    "CandidateRasterUnavailable",
    "DIRECT_VECTOR_FIELDS",
    "POLICY_VERSION",
    "canonical_full_ssurgo_mukey_raster",
    "candidate_raster_mukeys",
    "categorical_candidate_support",
    "categorical_candidate_support_wgs84",
    "categorical_value_centroid_wgs84",
    "direct_shallow_profile",
    "full_ssurgo_candidate_support",
    "full_ssurgo_mukey_raster_path",
    "load_active_candidate_raster",
    "prepare_padded_candidate_raster",
    "raw_mukey_source_locations_wgs84",
    "select_vector_donor",
]
