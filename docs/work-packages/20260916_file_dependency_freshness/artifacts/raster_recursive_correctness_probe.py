"""Disposable GDAL/native discovery characterization, not a production helper.

Archive backing associations below are fixture-owned facts, not a proposed VSI
parser. No named run or production/test file is changed.
"""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZIP_STORED, ZipFile
from unittest.mock import patch

from osgeo import gdal, osr
import rasterio
from wepppy.all_your_base.file_digest import sha256_file
from wepppy.all_your_base import file_digest
from wepppyo3.raster_characteristics import identify_median_single_raster_key


def create(path, value=25, driver="GTiff"):
    dataset = gdal.GetDriverByName(driver).Create(str(path), 4, 4, 1, gdal.GDT_Byte)
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    dataset.SetProjection(spatial.ExportToWkt())
    dataset.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    dataset.GetRasterBand(1).Fill(value)
    dataset = None


def mutate(path, value):
    info = path.stat()
    dataset = gdal.Open(str(path), gdal.GA_Update)
    dataset.GetRasterBand(1).Fill(value)
    dataset = None
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))


def summary(keys, source):
    return identify_median_single_raster_key(key_fn=str(keys), parameter_fn=str(source), band_indx=1)


def graph(source, *, known_archives=(), follow_directory_links=False):
    """Record recursive GDAL edges and complete actual directory membership."""
    pending = [str(source)]
    seen, files, nodes = set(), set(), []
    started = perf_counter()
    while pending:
        selected = pending.pop()
        if selected in seen:
            continue
        seen.add(selected)
        physical = Path(selected)
        if selected.startswith("/vsi"):
            for prefix, backing in known_archives:
                if selected.startswith(prefix):
                    files.add(str(backing))
                    break
            else:
                raise ValueError(f"No fixture-owned backing for {selected}")
        elif physical.is_dir():
            # Deliberate full store enumeration. No metadata-only shortcut.
            if follow_directory_links:
                # Probe fixture has exactly one acyclic link. Production needs
                # visited physical identity and explicit link-edge recording.
                for folder, _, names in os.walk(physical, followlinks=True):
                    files.update(str(Path(folder) / name) for name in names)
            else:
                files.update(str(member) for member in physical.rglob("*") if member.is_file())
        elif physical.is_file():
            files.add(selected)
        driver = gdal.IdentifyDriver(selected)
        if driver is None:
            nodes.append({"selected": selected, "driver": None, "members": []})
            continue
        dataset = gdal.OpenEx(selected, gdal.OF_RASTER | gdal.OF_READONLY)
        members = sorted(dataset.GetFileList() or [])
        nodes.append({"selected": selected, "driver": dataset.GetDriver().ShortName,
                      "members": members, "subdatasets": dataset.GetSubDatasets()})
        dataset = None
        pending.extend(members)
    discovery_seconds = perf_counter() - started
    digests = {name: sha256_file(name) for name in sorted(files)}
    return {"nodes": nodes, "digests": digests, "bytes": sum(Path(n).stat().st_size for n in files),
            "discovery_seconds": discovery_seconds, "seconds": perf_counter() - started}


def signature(observation):
    return observation["digests"]


def main():
    gdal.UseExceptions()
    results = {"gdal_version": gdal.VersionInfo(), "rasterio_gdal_version": rasterio.__gdal_version__,
               "scope": "tiny disposable native fixtures"}
    with TemporaryDirectory(prefix="recursive-raster-review-") as temporary:
        root = Path(temporary)
        keys, source, inner, outer = (root / name for name in ("keys.tif", "source.tif", "inner.vrt", "outer.vrt"))
        create(keys, 1)
        create(source)
        dataset = gdal.Translate(str(inner), str(source), format="VRT")
        dataset = None
        outer.write_text(inner.read_text().replace("source.tif", "inner.vrt"))
        before = graph(outer)
        native_before = summary(keys, outer)
        mutate(source, 75)
        after = graph(outer)
        results["nested_vrt"] = {"before": before, "after": after,
                                 "native_before": native_before, "native_after": summary(keys, outer),
                                 "closure_changed": signature(before) != signature(after)}

        # External mask creation/removal and PAM georeferencing must be rediscovered.
        before_mask = graph(outer)
        gdal.SetConfigOption("GDAL_TIFF_INTERNAL_MASK", "NO")
        dataset = gdal.Open(str(source), gdal.GA_Update)
        dataset.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        dataset.GetRasterBand(1).GetMaskBand().Fill(255)
        dataset = None
        gdal.SetConfigOption("GDAL_TIFF_INTERNAL_MASK", None)
        with_mask = graph(outer)
        mask = Path(str(source) + ".msk")
        mutate(mask, 0)
        changed_mask = graph(outer)
        mask.unlink()
        removed_mask = graph(outer)
        dataset = gdal.Open(str(source))
        dataset.SetMetadataItem("review_note", "external-PAM")
        dataset = None
        with_pam = graph(outer)
        results["sidecars"] = {"before": before_mask, "with_mask": with_mask,
                               "changed_mask": changed_mask, "removed_mask": removed_mask,
                               "with_pam": with_pam,
                               "mask_added_detected": signature(before_mask) != signature(with_mask),
                               "mask_rewrite_detected": signature(with_mask) != signature(changed_mask),
                               "mask_removal_detected": signature(changed_mask) != signature(removed_mask)}

        # A TIFF with no internal georeferencing can select a world-file sibling.
        world_source = root / "world-source.tif"
        dataset = gdal.GetDriverByName("GTiff").Create(str(world_source), 4, 4, 1, gdal.GDT_Byte)
        dataset.GetRasterBand(1).Fill(25)
        dataset = None
        world_file = world_source.with_suffix(".tfw")
        world_file.write_text("30\n0\n0\n-30\n500015\n4999985\n")
        before = graph(world_source)
        dataset = gdal.Open(str(world_source))
        before_transform = dataset.GetGeoTransform()
        dataset = None
        world_file.write_text("30\n0\n0\n-30\n600015\n4999985\n")
        after = graph(world_source)
        dataset = gdal.Open(str(world_source))
        after_transform = dataset.GetGeoTransform()
        dataset = None
        results["world_file"] = {"before": before, "after": after,
            "before_transform": before_transform, "after_transform": after_transform,
            "closure_changed": signature(before) != signature(after)}

        store = root / "source.zarr"
        create(store, driver="Zarr")
        before = graph(store)
        native_before = summary(keys, store)
        mutate(store, 75)
        after = graph(store)
        results["zarr"] = {"before": before, "after": after, "native_before": native_before,
                           "native_after": summary(keys, store),
                           "closure_changed": signature(before) != signature(after)}

        # Native directory stores can use symlinked arrays. Path.rglob does not
        # descend directory symlinks, so characterize rather than assume closure.
        array = store / "source"
        detached = root / "detached-array"
        array.rename(detached)
        array.symlink_to(detached, target_is_directory=True)
        before = graph(store)
        followed_before = graph(store, follow_directory_links=True)
        native_before = summary(keys, store)
        mutate(store, 33)
        after = graph(store)
        followed_after = graph(store, follow_directory_links=True)
        results["zarr_symlinked_array"] = {"before": before, "after": after,
            "native_before": native_before, "native_after": summary(keys, store),
            "closure_changed": signature(before) != signature(after),
            "actual_chunk": str(detached / "0.0"),
            "chunk_observed": str(array / "0.0") in before["digests"],
            "link_following_control_detects_change": signature(followed_before) != signature(followed_after)}

        # A ZIP can contain recursive VRTs; another VRT may point outside the ZIP.
        archive = root / "rasters.zip"
        with ZipFile(archive, "w", compression=ZIP_STORED) as outgoing:
            outgoing.write(source, "source.tif")
            outgoing.writestr("inner.vrt", inner.read_text())
            outgoing.writestr("outer.vrt", outer.read_text())
            outgoing.writestr("external.vrt", inner.read_text().replace(
                'relativeToVRT="1">source.tif', f'relativeToVRT="0">{source}'))
        results["local_zip"] = {}
        for spelling in (f"/vsizip/{archive}/", f"/vsizip/{{{archive}}}/"):
            target = spelling + "outer.vrt"
            observation = graph(target, known_archives=[(spelling, archive)])
            results["local_zip"][spelling] = {"graph": observation, "native": summary(keys, target)}
        spelling = f"/vsizip/{archive}/"
        target = spelling + "external.vrt"
        before = graph(target, known_archives=[(spelling, archive)])
        native_before = summary(keys, target)
        mutate(source, 99)
        after = graph(target, known_archives=[(spelling, archive)])
        results["zip_external_reference"] = {"before": before, "after": after,
            "native_before": native_before, "native_after": summary(keys, target),
            "archive_hash_unchanged": before["digests"][str(archive)] == after["digests"][str(archive)],
            "closure_changed": signature(before) != signature(after)}

        results["rasterio_reader_inventory"] = {}
        for selected in (str(outer), str(world_source), str(store), spelling + "outer.vrt"):
            try:
                with rasterio.open(selected) as dataset:
                    results["rasterio_reader_inventory"][selected] = {
                        "driver": dataset.driver, "files": dataset.files,
                        "first_pixel": int(dataset.read(1)[0, 0])}
            except rasterio.errors.RasterioIOError as error:
                results["rasterio_reader_inventory"][selected] = {"reader_error": str(error)}

        invalid = root / "invalid.tif"
        invalid.write_bytes(b"not a raster")
        driver = gdal.IdentifyDriver(str(invalid))
        try:
            summary(keys, invalid)
        except BaseException as error:
            # Isolated probe boundary: the installed native reader unwraps this
            # failure into a PyO3 PanicException, outside Exception inheritance.
            if type(error).__name__ not in ("RuntimeError", "ValueError", "PanicException"):
                raise
            results["unsupported"] = {"identified": None if driver is None else driver.ShortName,
                                      "native_error_type": type(error).__name__, "native_error": str(error)}
        # Warm tiny graph cost is evidence about discovery shape, not a budget.
        results["tiny_repeat_seconds"] = [graph(outer)["seconds"] for _ in range(10)]

        # More actual Zarr chunk files than the shared LRU capacity. Advance only
        # the admission clock, with immutable fixture bytes, to measure eviction
        # separately from the one-second guard and without a sleeping test.
        many_chunks = root / "many.zarr"
        dataset = gdal.GetDriverByName("Zarr").Create(str(many_chunks), 24, 24, 1, gdal.GDT_Byte,
                                                        options=["BLOCKSIZE=1,1", "COMPRESS=NONE"])
        dataset.GetRasterBand(1).Fill(7)
        dataset = None
        file_digest._observed_at.cache_clear()
        file_digest._digest.cache_clear()
        real_factory = file_digest.hashlib.sha256
        results["zarr_over_lru_capacity"] = []
        for index in range(3):
            calls = []
            def count_factory(*args, **kwargs):
                calls.append(1)
                return real_factory(*args, **kwargs)
            with patch.object(file_digest, "monotonic_ns", return_value=(index + 1) * 2_000_000_000), \
                    patch.object(file_digest.hashlib, "sha256", side_effect=count_factory):
                observation = graph(many_chunks)
            results["zarr_over_lru_capacity"].append({"pass": index + 1,
                "member_count": len(observation["digests"]), "bytes": observation["bytes"],
                "actual_digest_computations": len(calls), "seconds": observation["seconds"],
                "observation_cache": file_digest._observed_at.cache_info()._asdict(),
                "digest_cache": file_digest._digest.cache_info()._asdict()})
        encoded = json.dumps(results, indent=2).replace(str(root), "<temporary>")
    print(encoded)
    output = Path(__file__).with_name(sys.argv[1] + ".json") if len(sys.argv) > 1 else Path(__file__).with_suffix(".json")
    output.write_text(encoded + "\n")


if __name__ == "__main__":
    main()
