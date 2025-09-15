# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""
WMSesque is a high-performance FastAPI web service providing an endpoint for
on-the-fly acquisition and processing of tiled raster datasets.

The service reprojects (warps) source data to a UTM projection derived from a
request's bounding box (`bbox`) and scales it to a specified `cellsize`. It
returns the processed raster in various formats (e.g., GeoTiff, PNG) and
includes detailed processing metadata in a custom response header.

The service expects source data to be structured as GDAL Virtual Datasets (VRTs)
within a local directory, typically following a path like:
`{geodata_dir}/{dataset}/{...}/.vrt`
"""

import subprocess
import os
import logging
import sys
from uuid import uuid4
from datetime import datetime
from typing import List, Tuple, Optional, Any
import asyncio

import utm
from fastapi import (
    FastAPI,
    Query,
    Path,
    HTTPException,
    BackgroundTasks,
    Response,
    Request,
    Depends,
)
from fastapi.responses import FileResponse, JSONResponse

from osgeo import gdal
import xml.etree.ElementTree as ET
import base64, json, hashlib
import zlib

import dotenv
dotenv.load_dotenv()

gdal.UseExceptions()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

def _b64url(obj: dict) -> str:
    b = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")

def from_b64url(s: str) -> dict:
    s += "=" * ((4 - len(s) % 4) % 4)
    b = base64.urlsafe_b64decode(s)
    return json.loads(b.decode("utf-8"))

def b64url_compact(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    z = zlib.compress(raw, level=9)  # max compression
    return base64.urlsafe_b64encode(z).decode("ascii").rstrip("=")

def from_b64url_compact(s: str) -> dict:
    s += "=" * ((4 - len(s) % 4) % 4)
    z = base64.urlsafe_b64decode(s)
    raw = zlib.decompress(z)
    return json.loads(raw.decode("utf-8"))

geodata_dir = os.environ.get("GEODATA_DIR", "/geodata")
SCRATCH = "/media/ramdisk"
_this_dir = os.path.dirname(__file__)
_catalog = os.environ.get(
    'CATALOG_PATH', 
    os.path.join(_this_dir, "catalog"))

resample_methods = tuple("near bilinear cubic cubicspline lanczos average mode max min med q1 q1".split())
ext_d = {"GTiff": ".tif", "AAIGrid": ".asc", "PNG": ".png", "ENVI": ".raw"}
format_drivers = tuple(ext_d.keys())
gdaldem_modes = tuple("hillshade slope aspect tri tpi roughness".split())


def determine_band_type(vrt: str) -> Optional[str]:
    ds = gdal.Open(vrt)
    if ds is None:
        return None
    band = ds.GetRasterBand(1)
    return gdal.GetDataTypeName(band.DataType)

def load_maps(geodata: str) -> List[str]:
    with open(_catalog) as f:
        maps = f.readlines()
    return [fn.strip() for fn in maps if fn.strip().startswith(geodata)]

def raster_stats(src: str) -> dict:
    cmd = ["gdalinfo", src, "-stats"]
    subprocess.run(cmd, capture_output=True, check=True)
    stat_fn = src + ".aux.xml"
    if not os.path.exists(stat_fn):
        raise FileNotFoundError(f"Statistics file not created: {stat_fn}")

    d = {}
    tree = ET.parse(stat_fn)
    root = tree.getroot()
    for stat in root.iter("MDI"):
        key = stat.attrib["key"]
        value = float(stat.text)
        d[key] = value
    return d

def format_convert(src: str, _format: str) -> Tuple[str, str]:
    dst = src[:-4] + ext_d[_format]
    if _format == "ENVI":
        stats = raster_stats(src)
        cmd = [
            "gdal_translate", "-of", _format, "-ot", "Uint16",
            "-scale", str(stats["STATISTICS_MINIMUM"]), str(stats["STATISTICS_MAXIMUM"]), "0", "65535",
            src, dst,
        ]
    else:
        cmd = ["gdal_translate", "-of", _format, src, dst]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(dst):
        output = (res.stdout or "") + (res.stderr or "")
        raise RuntimeError(f"gdal_translate failed: {output}")
    
    return dst


def process_raster(
    dataset: str,
    bbox: Tuple[float, float, float, float],
    cellsize: float,
    resample: Optional[str],
    _format: str,
    gdaldem: Optional[str],
) -> Tuple[str, dict, List[str]]:
    """
    This is the main synchronous, blocking function that runs all the GDAL subprocesses.
    It is designed to be run in a separate thread via asyncio.to_thread.
    """
    # 1. Path validation and setup
    parts = dataset.split("/")
    src = os.path.normpath(os.path.join(geodata_dir, *[p for p in parts if p], ".vrt"))
    base = os.path.normpath(geodata_dir)
    if not src.startswith(base + os.sep) and src != base:
        raise HTTPException(status_code=400, detail="Invalid dataset path.")
    if not os.path.exists(src):
        raise HTTPException(status_code=404, detail=f"Cannot find dataset: {src}")

    fn_uuid = str(uuid4().hex)
    dst = os.path.join(SCRATCH, fn_uuid + ".tif")
    fn_list_to_cleanup = [dst]

    # 2. Determine UTM projection
    left, bottom, right, top = bbox
    ul_x, ul_y, utm_number, utm_letter = utm.from_latlon(top, left)
    lr_x, lr_y, _, _ = utm.from_latlon(bottom, right, force_zone_number=utm_number)

    width_px = int((lr_x - ul_x) / cellsize)
    height_px = int((ul_y - lr_y) / cellsize)
    if height_px > 4096 or width_px > 4096:
        raise HTTPException(status_code=400, detail="Output size cannot exceed 4096x4096 pixels")

    proj4 = f"+proj=utm +zone={utm_number} +{'south' if top < 0 else 'north'} +datum=WGS84 +ellps=WGS84"

    # 3. Determine resample method
    if resample is None:
        src_dtype = determine_band_type(src)
        resample = "near" if "float" not in (src_dtype or "").lower() else "bilinear"

    # 4. Build and run gdalwarp
    cmd_warp = [
        "gdalwarp", "-t_srs", proj4,
        "-tr", str(cellsize), str(cellsize),
        "-te", str(ul_x), str(lr_y), str(lr_x), str(ul_y),
        "-r", resample, src, dst,
    ]
    if os.path.exists(dst): os.remove(dst)
    
    res_warp = subprocess.run(cmd_warp, capture_output=True, text=True)
    out_warp = (res_warp.stdout or "") + (res_warp.stderr or "")
    if not os.path.exists(dst):
        raise HTTPException(status_code=400, detail={
            "Error": "gdalwarp failed unexpectedly", "cmd": ' '.join(cmd_warp), "stdout": out_warp
        })

    # 5. Handle metadata
    meta_fn = src.replace(".vrt", "metadata.json")
    meta = {}
    if os.path.exists(meta_fn):
        with open(meta_fn) as f:
            meta = json.load(f)
    
    meta["wmesque"] = {
        "bbox": bbox, "cache": dst, "dataset": dataset, "cellsize": cellsize,
        "ul": {"ul_x": ul_x, "ul_y": ul_y, "utm_number": utm_number, "utm_letter": utm_letter},
        "proj4": proj4, "cmd": cmd_warp, "stdout": out_warp, "timestamp": datetime.now().isoformat(),
    }
    
    # 6. Run optional gdaldem processing
    dst_current = dst
    if gdaldem:
        dst2 = os.path.join(SCRATCH, f"{fn_uuid}_dem.tif")
        fn_list_to_cleanup.append(dst2)
        cmd_dem = ["gdaldem", gdaldem, dst, dst2]
        res_dem = subprocess.run(cmd_dem, capture_output=True, text=True)
        out_dem = (res_dem.stdout or "") + (res_dem.stderr or "")
        
        if not os.path.exists(dst2):
            raise HTTPException(status_code=400, detail={
                "Error": "gdaldem failed unexpectedly", "cmd2": ' '.join(cmd_dem), "stdout2": out_dem,
            })
        
        meta["wmesque"]["gdaldem"] = {"mode": gdaldem, "cmd": cmd_dem, "stdout": out_dem, "cache": dst2}
        dst_current = dst2

    # 7. Handle final format conversion
    dst_final = dst_current
    if _format != "GTiff":
        try:
            dst3 = format_convert(dst_current, _format)
            fn_list_to_cleanup.append(dst3)
            dst_final = dst3
        except (RuntimeError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=f"Failed to convert to output format: {e}")

    return dst_final, meta, fn_list_to_cleanup


# --- FastAPI App and Endpoints ---
app = FastAPI(
    title="WMSesque Service",
    description="Provides tiled, reprojected raster datasets.",
)

def parse_bbox(bbox: str = Query(..., description="Bounding box: left,bottom,right,top")) -> Tuple[float, float, float, float]:
    try:
        coords = [float(c) for c in bbox.split(",")]
        if len(coords) != 4:
            raise ValueError
        left, bottom, right, top = coords
        if bottom > top or left > right:
            raise ValueError("Expecting bbox defined as: left,bottom,right,top")
        return (left, bottom, right, top)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox format. Use four comma-separated floats: left,bottom,right,top"
        )

def cleanup_files(files: List[str]):
    """Synchronous function to remove a list of files."""
    for file in files:
        try:
            os.remove(file)
            logger.info(f"Cleaned up {file}")
        except OSError:
            pass

@app.get("/health")
async def health():
    return {"status": "OK"}

@app.get("/catalog", response_model=List[str])
async def catalog():
    """Returns a list of available map datasets."""
    return load_maps(geodata_dir)

@app.get("/retrieve/{dataset:path}")
async def api_dataset_retrieve(
    background_tasks: BackgroundTasks,
    dataset: str = Path(..., description="Path to the dataset, e.g., 'fire/severity/2020'"),
    bbox: Tuple[float, float, float, float] = Depends(parse_bbox),
    cellsize: float = Query(30.0, gt=0, description="Output cell size in meters."),
    resample: Optional[str] = Query(None, enum=resample_methods),
    _format: str = Query("GTiff", enum=format_drivers, alias="format"),
    gdaldem: Optional[str] = Query(None, enum=gdaldem_modes),
):
    """
    Retrieves a reprojected and clipped raster dataset based on the provided parameters.
    """
    try:
        # Run the entire blocking process in a separate thread
        dst_final, meta, fn_list_to_cleanup = await asyncio.to_thread(
            process_raster, dataset, bbox, cellsize, resample, _format, gdaldem
        )
    except HTTPException as e:
        # If the blocking function raised an HTTP exception, re-raise it
        raise e
    except Exception as e:
        # Catch any other unexpected errors from the processing function
        logger.error(f"Unhandled exception during raster processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during processing.")

    # Schedule the temp files to be deleted after the response is sent
    background_tasks.add_task(cleanup_files, fn_list_to_cleanup)

    # Determine filename and content type for the response
    fname = "_".join(dataset.replace('/', '_').split()) + ext_d[_format]
    media_type_map = {
        "GTiff": "image/tiff",
        "AAIGrid": "text/plain",
        "PNG": "image/png",
        "ENVI": "application/octet-stream",
    }
    
    # Log metadata before returning response
    logger.info(json.dumps(meta, indent=2))

    # Return the file as a response
    return FileResponse(
        path=dst_final,
        media_type=media_type_map.get(_format, "application/octet-stream"),
        filename=fname,
        headers={
            "Content-Disposition": f"attachment; filename={fname}",
            "WMesque-Meta": _b64url(meta),
            "Access-Control-Expose-Headers": "WMesque-Meta",
        },
    )
 