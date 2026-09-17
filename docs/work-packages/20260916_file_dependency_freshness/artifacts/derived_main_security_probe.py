"""Disposable native compatibility and uncached main-file error probes."""
import errno
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from osgeo import gdal
from wepppy.nodb._derived_build import file_signature
from wepppyo3.raster_characteristics import identify_median_single_raster_key


def main():
    gdal.UseExceptions()
    results = {}
    with TemporaryDirectory(prefix="derived-main-security-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.write_bytes(b"AAAA")
        alias = root / "alias"
        alias.symlink_to(source)
        assert file_signature(alias) == file_signature(source)
        results["unchanged_symlink"] = True
        denied = PermissionError(errno.EACCES, "review injected read denial", str(source))
        with patch.object(Path, "open", side_effect=denied):
            try:
                file_signature(source)
            except PermissionError as error:
                assert error is denied
                results["read_error_object_preserved"] = True
        real_open = Path.open
        class TruncatingReader:
            def __init__(self, stream):
                self.stream = stream
                self.once = False
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def fileno(self):
                return self.stream.fileno()
            def read(self, count):
                result = self.stream.read(count)
                if not self.once:
                    self.once = True
                    with real_open(source, "wb") as writer:
                        writer.write(b"A")
                return result
        with patch.object(Path, "open", lambda path, *args, **kwargs: TruncatingReader(real_open(path, *args, **kwargs))):
            try:
                file_signature(source)
            except OSError as error:
                assert error.errno == errno.ESTALE
                results["truncate_after_read_rejected"] = True
        source.write_bytes(b"AAAA")
        replacement = root / "replacement"
        replacement.write_bytes(b"BBBB")
        def replace_before_open(path, *args, **kwargs):
            os.replace(replacement, source)
            return real_open(path, *args, **kwargs)
        with patch.object(Path, "open", replace_before_open):
            try:
                file_signature(source)
            except OSError as error:
                assert error.errno == errno.ESTALE
                results["replace_before_open_rejected"] = True
        driver = gdal.GetDriverByName("Zarr")
        results["zarr_driver_available"] = driver is not None
        if driver is not None:
            keys = root / "keys.tif"
            dataset = gdal.GetDriverByName("GTiff").Create(str(keys), 2, 2, 1, gdal.GDT_Byte)
            dataset.SetGeoTransform((0, 1, 0, 2, 0, -1))
            dataset.GetRasterBand(1).Fill(1)
            dataset = None
            raster = root / "source.zarr"
            dataset = driver.Create(str(raster), 2, 2, 1, gdal.GDT_Byte)
            dataset.SetGeoTransform((0, 1, 0, 2, 0, -1))
            dataset.GetRasterBand(1).Fill(25)
            dataset = None
            results["zarr_is_directory"] = raster.is_dir()
            info = raster.stat()
            results["previous_signature_accepts"] = (str(raster.resolve()), info.st_mtime_ns, info.st_size)
            try:
                results["zarr_native_summary"] = identify_median_single_raster_key(
                    key_fn=str(keys), parameter_fn=str(raster), band_indx=1
                )
            except (RuntimeError, ValueError) as error:
                results["zarr_native_error"] = str(error)
            try:
                signature = file_signature(raster)
            except OSError as error:
                results["new_signature_error_errno"] = error.errno
            else:
                assert signature == (str(raster.resolve()), info.st_mtime_ns, info.st_size, None)
                results["directory_metadata_compatibility_preserved"] = True
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
