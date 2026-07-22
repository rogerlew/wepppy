"""Deterministic contracts for low-level SSURGO intelligent fallback support."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sys
import threading
import types
from pathlib import Path

import pytest

from wepppy.soils.ssurgo import fallback


pytestmark = pytest.mark.unit


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _configure_geodata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    source = tmp_path / "geodata" / "ssurgo" / "gNATSGSO" / "2025" / ".vrt"
    source.parent.mkdir(parents=True)
    source.write_text("canonical-vrt", encoding="utf-8")
    monkeypatch.setenv("GEODATA_DIR", str(tmp_path / "geodata"))
    return source


def test_canonical_source_resolves_only_configured_2025_vrt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _configure_geodata(monkeypatch, tmp_path)

    assert fallback.canonical_full_ssurgo_mukey_raster() == source.resolve()
    assert fallback.full_ssurgo_mukey_raster_path() == str(source.resolve())


def test_canonical_source_rejects_symlink_escape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    geodata = tmp_path / "geodata"
    approved = geodata / "ssurgo" / "gNATSGSO" / "2025"
    approved.mkdir(parents=True)
    outside = tmp_path / "outside.vrt"
    outside.write_text("not canonical", encoding="utf-8")
    (approved / ".vrt").symlink_to(outside)
    monkeypatch.setenv("GEODATA_DIR", str(geodata))

    with pytest.raises(FileNotFoundError, match="unavailable"):
        fallback.canonical_full_ssurgo_mukey_raster()


def test_active_candidate_loader_rejects_checksum_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    source = _configure_geodata(monkeypatch, tmp_path)
    soils = tmp_path / "run" / "soils"
    artifact_dir = soils / fallback.CANDIDATE_ARTIFACT_DIRNAME
    artifact_dir.mkdir(parents=True)
    primary = soils / "ssurgo.tif"
    profile = {
        "driver": "GTiff",
        "dtype": "uint32",
        "count": 1,
        "width": 1,
        "height": 1,
        "crs": "EPSG:5070",
        "transform": from_origin(0, 10, 10, 10),
    }
    with rasterio.open(primary, "w", **profile) as dataset:
        dataset.write(np.array([[1]], dtype=np.uint32), 1)
    raster = artifact_dir / "candidate-a.tif"
    with rasterio.open(raster, "w", **profile) as dataset:
        dataset.write(np.array([[2]], dtype=np.uint32), 1)
    with rasterio.open(raster) as dataset:
        bounds = list(dataset.bounds)
        crs_wkt = dataset.crs.to_wkt()
    metadata = {
        "policy_version": fallback.POLICY_VERSION,
        "source": {"identity": "gNATSGO-2025-mukey-vrt", "sha256": _sha256(source)},
        "primary_raster_sha256": _sha256(primary),
        "primary_raster": "ssurgo.tif",
        "padding_m": 2_000.0,
        "bounds": bounds,
        "crs_wkt": crs_wkt,
        "width": 1,
        "height": 1,
        "raster_sha256": "wrong",
    }
    metadata_path = artifact_dir / "candidate-a.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    (artifact_dir / fallback.CANDIDATE_ACTIVE_MANIFEST).write_text(
        json.dumps(
            {
                "policy_version": fallback.POLICY_VERSION,
                "raster": "candidate-a.tif",
                "metadata": "candidate-a.json",
                "raster_sha256": "wrong",
                "metadata_sha256": _sha256(metadata_path),
                "primary_raster_sha256": _sha256(primary),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(fallback.CandidateRasterUnavailable, match="provenance"):
        fallback.load_active_candidate_raster(soils, primary_raster_path=primary)


def test_candidate_preparation_rejects_nested_primary_raster(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_geodata(monkeypatch, tmp_path)
    soils = tmp_path / "run" / "soils"
    nested_primary = soils / "nested" / "ssurgo.tif"
    nested_primary.parent.mkdir(parents=True)
    nested_primary.write_text("not reached", encoding="utf-8")

    with pytest.raises(fallback.CandidateRasterUnavailable, match="run-contained"):
        fallback.prepare_padded_candidate_raster(soils_dir=soils, primary_raster_path=nested_primary)


def test_candidate_preparation_records_persisted_raster_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Publication must use the GeoTIFF's re-read CRS serialization."""
    _configure_geodata(monkeypatch, tmp_path)
    soils = tmp_path / "run" / "soils"
    soils.mkdir(parents=True)
    primary = soils / "ssurgo.tif"
    primary.write_bytes(b"primary")

    characteristics = types.ModuleType("wepppyo3.raster_characteristics")

    def crop(
        _source: str, _reference: str, destination: str, _padding: float, _band: int
    ) -> tuple[object, ...]:
        Path(destination).write_bytes(b"candidate")
        return (0.0, 0.0, 1.0, 1.0, "crop-crs", 1, 1)

    characteristics.crop_categorical_raster_to_padded_reference = crop
    characteristics.categorical_raster_metadata = lambda _path: (
        (0.0, 0.0, 1.0, 1.0), "persisted-crs", 1, 1
    )
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", characteristics)

    artifact = fallback.prepare_padded_candidate_raster(soils_dir=soils, primary_raster_path=primary)

    assert artifact.metadata["crs_wkt"] == "persisted-crs"
    assert artifact.metadata["bounds"] == [0.0, 0.0, 1.0, 1.0]
    loaded = fallback.load_active_candidate_raster(soils, primary_raster_path=primary)
    assert loaded == artifact


def test_candidate_preparation_concurrent_retry_leaves_valid_active_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Concurrent publication and a failed attempt cannot leave partial active state."""
    _configure_geodata(monkeypatch, tmp_path)
    soils = tmp_path / "run" / "soils"
    soils.mkdir(parents=True)
    primary = soils / "ssurgo.tif"
    primary.write_bytes(b"primary")

    characteristics = types.ModuleType("wepppyo3.raster_characteristics")
    barrier = threading.Barrier(3)
    crop_lock = threading.Lock()
    crop_attempts = 0

    def crop(
        _source: str, _reference: str, destination: str, _padding: float, _band: int
    ) -> tuple[object, ...]:
        nonlocal crop_attempts
        with crop_lock:
            crop_attempts += 1
            attempt = crop_attempts
        if attempt <= 3:
            barrier.wait(timeout=5)
        if attempt == 1:
            raise OSError("injected concurrent crop failure")
        Path(destination).write_bytes(f"candidate-{attempt}".encode())
        return (0.0, 0.0, 1.0, 1.0, "crop-crs", 1, 1)

    characteristics.crop_categorical_raster_to_padded_reference = crop
    characteristics.categorical_raster_metadata = lambda _path: (
        (0.0, 0.0, 1.0, 1.0), "persisted-crs", 1, 1
    )
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", characteristics)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(
                fallback.prepare_padded_candidate_raster,
                soils_dir=soils,
                primary_raster_path=primary,
            )
            for _ in range(3)
        ]
    failures = [future.exception() for future in futures if future.exception() is not None]

    assert len(failures) == 1
    assert isinstance(failures[0], OSError)
    retried = fallback.prepare_padded_candidate_raster(soils_dir=soils, primary_raster_path=primary)
    artifact_dir = soils / fallback.CANDIDATE_ARTIFACT_DIRNAME
    assert len(list(artifact_dir.glob("candidate-*.tif"))) == 3
    assert len(list(artifact_dir.glob("candidate-*.json"))) == 3
    assert not list(artifact_dir.glob(".*.tmp"))
    assert fallback.load_active_candidate_raster(soils, primary_raster_path=primary) == retried


def test_candidate_preparation_preserves_prior_active_manifest_on_crop_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed new crop cannot replace the last published candidate identity."""
    _configure_geodata(monkeypatch, tmp_path)
    soils = tmp_path / "run" / "soils"
    soils.mkdir(parents=True)
    primary = soils / "ssurgo.tif"
    primary.write_bytes(b"primary")
    artifact_dir = soils / fallback.CANDIDATE_ARTIFACT_DIRNAME
    artifact_dir.mkdir()
    active_manifest = artifact_dir / fallback.CANDIDATE_ACTIVE_MANIFEST
    active_manifest.write_text('{"raster":"prior.tif"}', encoding="utf-8")

    characteristics = types.ModuleType("wepppyo3.raster_characteristics")

    def crop(*_args: object) -> None:
        raise OSError("injected crop failure")

    characteristics.crop_categorical_raster_to_padded_reference = crop
    characteristics.categorical_raster_metadata = lambda _path: None
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", characteristics)

    with pytest.raises(OSError, match="injected crop failure"):
        fallback.prepare_padded_candidate_raster(soils_dir=soils, primary_raster_path=primary)

    assert active_manifest.read_text(encoding="utf-8") == '{"raster":"prior.tif"}'
    assert not list(artifact_dir.glob(".*.tmp"))


def test_candidate_preparation_requires_canonical_source_before_native_crop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing configured gNATSGO data is explicit and does not enter native work."""
    geodata = tmp_path / "geodata"
    geodata.mkdir()
    monkeypatch.setenv("GEODATA_DIR", str(geodata))
    soils = tmp_path / "run" / "soils"
    soils.mkdir(parents=True)
    primary = soils / "ssurgo.tif"
    primary.write_bytes(b"primary")

    with pytest.raises(FileNotFoundError, match="gNATSGO"):
        fallback.prepare_padded_candidate_raster(soils_dir=soils, primary_raster_path=primary)


def test_candidate_preparation_requires_native_crop_support(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing native crop primitive is an explicit required-dependency error."""
    _configure_geodata(monkeypatch, tmp_path)
    soils = tmp_path / "run" / "soils"
    soils.mkdir(parents=True)
    primary = soils / "ssurgo.tif"
    primary.write_bytes(b"primary")
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", types.ModuleType("native_missing_crop"))

    with pytest.raises(RuntimeError, match="categorical raster crop support"):
        fallback.prepare_padded_candidate_raster(soils_dir=soils, primary_raster_path=primary)


def test_categorical_support_excludes_nonbuildable_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native spatial support is reduced to the current buildable MUKEY set."""
    characteristics = types.ModuleType("wepppyo3.raster_characteristics")
    characteristics.categorical_support_within_wgs84_radius = lambda *_args, **_kwargs: [
        (30, 100),
        (20, 6),
    ]
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", characteristics)

    support = fallback.categorical_candidate_support_wgs84(
        "candidate.tif",
        -116.1,
        47.1,
        250.0,
        invalid_mukeys={"99"},
        valid_mukeys={"10", "20"},
    )

    assert support == [("20", 6)]


def test_direct_shallow_profile_uses_first_valid_raw_horizon_and_texture_balance() -> None:
    layers = [
        {"chkey": "bad-om", "om_r": 30, "dbthirdbar_r": 1.2, "ksat_r": 9, "cec7_r": 12},
        {
            "chkey": "bad-texture",
            "om_r": 4,
            "dbthirdbar_r": 1.2,
            "ksat_r": 9,
            "cec7_r": 12,
            "sandtotal_r": 80,
            "claytotal_r": 30,
        },
        {"chkey": "good", "om_r": 3, "dbthirdbar_r": 1.1, "ksat_r": 8, "cec7_r": 10},
    ]

    profile = fallback.direct_shallow_profile(layers)

    assert profile["horizon_index"] == 1
    assert profile["chkey"] == "bad-texture"
    assert profile["direct_values"] == {"dbthirdbar_r": 1.2, "ksat_r": 9.0, "cec7_r": 12.0}


def test_direct_shallow_profile_rejects_zero_depth_endpoint() -> None:
    profile = fallback.direct_shallow_profile(
        [{"om_r": 2, "dbthirdbar_r": 1.1, "ksat_r": 8, "cec7_r": 10, "hzdepb_r": 0}]
    )

    assert "hzdepb_r" not in profile["direct_values"]


def test_select_vector_donor_uses_distance_then_support_then_numeric_mukey() -> None:
    source = {"direct_values": {"dbthirdbar_r": 1.0, "ksat_r": 10.0, "cec7_r": 20.0}}
    candidates = [
        {
            "mukey": "20",
            "pixel_support": 2,
            "profile": {"direct_values": {"dbthirdbar_r": 1.0, "ksat_r": 10.0, "cec7_r": 20.0}},
        },
        {
            "mukey": "10",
            "pixel_support": 2,
            "profile": {"direct_values": {"dbthirdbar_r": 1.0, "ksat_r": 10.0, "cec7_r": 20.0}},
        },
        {
            "mukey": "30",
            "pixel_support": 3,
            "profile": {"direct_values": {"dbthirdbar_r": 1.0, "ksat_r": 10.0, "cec7_r": 20.0}},
        },
    ]

    winner = fallback.select_vector_donor(source, candidates)

    assert winner is not None
    assert winner["mukey"] == "30"
    assert winner["distance"] == 0.0


def test_native_crop_uses_padded_reference_extent(tmp_path: Path) -> None:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from wepppyo3.raster_characteristics import (
        categorical_support_within_wgs84_radius,
        categorical_value_centroid_wgs84,
        crop_categorical_raster_to_padded_reference,
    )

    source = tmp_path / "source.tif"
    reference = tmp_path / "reference.tif"
    destination = tmp_path / "destination.tif"
    profile = {
        "driver": "GTiff",
        "dtype": "uint32",
        "count": 1,
        "crs": "EPSG:5070",
        "transform": from_origin(0, 80, 10, 10),
    }
    with rasterio.open(source, "w", width=8, height=8, **profile) as dataset:
        dataset.write(np.arange(1, 65, dtype=np.uint32).reshape(8, 8), 1)
    with rasterio.open(
        reference,
        "w",
        width=2,
        height=2,
        **{**profile, "transform": from_origin(20, 60, 10, 10)},
    ) as dataset:
        dataset.write(np.ones((2, 2), dtype=np.uint32), 1)

    result = crop_categorical_raster_to_padded_reference(
        str(source), str(reference), str(destination), 10.0
    )

    assert result[-2:] == (4, 4)
    with rasterio.open(destination) as dataset:
        assert dataset.shape == (4, 4)
        assert dataset.read(1).tolist() == [
            [10, 11, 12, 13],
            [18, 19, 20, 21],
            [26, 27, 28, 29],
            [34, 35, 36, 37],
        ]
    longitude, latitude = categorical_value_centroid_wgs84(str(destination), 19)
    assert np.isfinite(longitude)
    assert np.isfinite(latitude)
    assert (19, 1) in categorical_support_within_wgs84_radius(
        str(destination), longitude, latitude, 1.0
    )


def test_native_raw_mukey_locations_use_intersected_hillslope_cells(tmp_path: Path) -> None:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    hillslopes = tmp_path / "hillslopes.tif"
    mukeys = tmp_path / "mukeys.tif"
    profile = {
        "driver": "GTiff",
        "dtype": "int32",
        "count": 1,
        "width": 2,
        "height": 2,
        "crs": "EPSG:5070",
        "transform": from_origin(0, 20, 10, 10),
    }
    with rasterio.open(hillslopes, "w", **profile) as dataset:
        dataset.write(np.array([[10, 10], [20, 20]], dtype=np.int32), 1)
    with rasterio.open(mukeys, "w", **profile) as dataset:
        dataset.write(np.array([[1, 2], [1, 2]], dtype=np.int32), 1)

    locations = fallback.raw_mukey_source_locations_wgs84(hillslopes, mukeys, [(10, 2), (20, 1)])

    assert set(locations) == {"10", "20"}
    assert locations["10"] != locations["20"]
