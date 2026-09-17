"""Read-only security characterization of local RAP raster dependency closure.

Uses disposable datasets only; no external URLs or network reads.
"""
import json
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_STORED, ZipFile

from osgeo import gdal
from wepppyo3.raster_characteristics import identify_median_single_raster_key


def main():
    gdal.UseExceptions()
    with TemporaryDirectory(prefix="derived-gdal-security-") as temporary:
        root = Path(temporary)
        source = root / "source.tif"
        keys = root / "keys.tif"
        for path, value in ((source, 25), (keys, 1)):
            dataset = gdal.GetDriverByName("GTiff").Create(str(path), 2, 2, 1, gdal.GDT_Byte)
            dataset.SetGeoTransform((0, 1, 0, 2, 0, -1))
            dataset.GetRasterBand(1).Fill(value)
            dataset = None
        inner, outer = root / "inner.vrt", root / "outer.vrt"
        gdal.Translate(str(inner), str(source), format="VRT")
        # Translate(VRT, VRT) may flatten its source list. Explicit nesting is
        # needed to characterize an actual separately mutable VRT dependency.
        outer.write_text('''<VRTDataset rasterXSize="2" rasterYSize="2">
  <GeoTransform>0,1,0,2,0,-1</GeoTransform>
  <VRTRasterBand dataType="Byte" band="1"><SimpleSource>
    <SourceFilename relativeToVRT="1">inner.vrt</SourceFilename>
    <SourceBand>1</SourceBand>
    <SrcRect xOff="0" yOff="0" xSize="2" ySize="2"/>
    <DstRect xOff="0" yOff="0" xSize="2" ySize="2"/>
  </SimpleSource></VRTRasterBand>
</VRTDataset>''')
        zip_path = root / "source.zip"
        with ZipFile(zip_path, "w", compression=ZIP_STORED) as archive:
            archive.write(source, arcname="source.tif")
        zip_vrt = root / "zip.vrt"
        gdal.Translate(str(zip_vrt), f"/vsizip/{zip_path}/source.tif", format="VRT")
        records = {}
        for name, path in (("direct", source), ("inner_vrt", inner), ("nested_vrt", outer), ("local_zip_vrt", zip_vrt)):
            dataset = gdal.Open(str(path))
            files = dataset.GetFileList()
            dataset = None
            records[name] = {
                "files": [filename.replace(str(root), "<temporary>") for filename in files],
                "native_summary": identify_median_single_raster_key(
                    key_fn=str(keys), parameter_fn=str(path), band_indx=1
                ),
            }
        dataset = gdal.Open(str(outer))
        listed = dataset.GetFileList()
        dataset = None
        old_hashes = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in listed}
        before = source.stat()
        dataset = gdal.Open(str(source), gdal.GA_Update)
        dataset.GetRasterBand(1).Fill(75)
        dataset = None
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
        new_hashes = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in listed}
        records["nested_vrt_rewrite"] = {
            "source_size_preserved": source.stat().st_size == before.st_size,
            "source_mtime_preserved": source.stat().st_mtime_ns == before.st_mtime_ns,
            "flat_listed_hashes_unchanged": old_hashes == new_hashes,
            "native_summary_after": identify_median_single_raster_key(
                key_fn=str(keys), parameter_fn=str(outer), band_indx=1
            ),
        }
        print(json.dumps(records, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
