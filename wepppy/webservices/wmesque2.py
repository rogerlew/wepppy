# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""
WMSesque is a flask web application that provides an endpoint for acquiring
tiled raster datasets. The web application reprojects (warps) the map to UTM
based on the top left corner of the bounding box {bbox} provided to the
application. It also scales the map data based on arguments supplied in the
request {cellsize}. Returns GeoTiff. Header contains information related to
the request and the map processing.

The WMSesque server assumes that the datasets have been downloaded onto the
machine running EMSeque. The datasets should be in the {geodata_dir}. Each
should have its own directory with a subdirectory for each year. Tiles or
single maps should be combined as a gdal virtual dataset (vrt). WMSesque
looks for: {geodata_dir}/{dataset}/{year}/.vrt
"""

import subprocess
import os
import logging
import sys
from uuid import uuid4

from datetime import datetime

import utm
from flask import (
    Flask,
    jsonify,
    request,
    make_response,
    send_file,
    after_this_request,
)
from osgeo import gdal
import xml.etree.ElementTree as ET
import base64, json, hashlib
import zlib


import dotenv
dotenv.load_dotenv()

gdal.UseExceptions()

logging.basicConfig(
    level=logging.INFO,  # or DEBUG
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

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

resample_methods = (
    "near bilinear cubic cubicspline lanczos " "average mode max min med q1 q1".split()
)
resample_methods = tuple(resample_methods)

ext_d = {"GTiff": ".tif", "AAIGrid": ".asc", "PNG": ".png", "ENVI": ".raw"}

format_drivers = tuple(list(ext_d.keys()))

gdaldem_modes = (
    "hillshade slope aspect tri tpi roughnesshillshade "
    "slope aspect tri tpi roughness".split()
)
gdaldem_modes = tuple(gdaldem_modes)

_this_dir = os.path.dirname(__file__)
_catalog = os.path.join(_this_dir, "catalog")


SCRATCH = "/media/ramdisk"


def raster_stats(src):
    cmd = ["gdalinfo", src, "-stats"]

    res = subprocess.run(cmd, capture_output=True, text=True)
    output = (res.stdout or "") + (res.stderr or "")

    stat_fn = src + ".aux.xml"
    assert os.path.exists(stat_fn), (src, stat_fn)

    d = {}
    tree = ET.parse(stat_fn)
    root = tree.getroot()
    for stat in root.iter("MDI"):
        key = stat.attrib["key"]
        value = float(stat.text)
        d[key] = value

    return d


def format_convert(src, _format):
    dst = src[:-4] + ext_d[_format]
    if _format == "ENVI":
        stats = raster_stats(src)
        cmd = [
            "gdal_translate",
            "-of",
            _format,
            "-ot",
            "Uint16",
            "-scale",
            str(stats["STATISTICS_MINIMUM"]),
            str(stats["STATISTICS_MAXIMUM"]),
            "0",
            "65535",
            src,
            dst,
        ]
    else:
        cmd = ["gdal_translate", "-of", _format, src, dst]

    res = subprocess.run(cmd, capture_output=True, text=True)
    output = (res.stdout or "") + (res.stderr or "")

    if os.path.exists(dst):
        return dst, 200

    return output, 400


def determine_band_type(vrt):
    ds = gdal.Open(vrt)
    if ds == None:
        return None

    band = ds.GetRasterBand(1)
    return gdal.GetDataTypeName(band.DataType)


def load_maps(geodata):
    """
    recursively searches for .vrt files from the
    path speicified by {geodata_dir}
    """
    maps = open(_catalog).readlines()
    maps = [fn.strip() for fn in maps if fn.startswith(geodata)]

    return maps


def safe_float_parse(x):
    """
    Tries to parse {x} as a float. Returns None if it fails.
    """
    try:
        return float(x)
    except:
        return None


def parse_bbox(bbox):
    """
    Tries to parse the bbox argument supplied by the request
    in a fault tolerate manner
    """
    try:
        coords = bbox.split(",")
    except:
        return (None, None, None, None)

    n = len(coords)
    if n < 4:
        coords.extend([None for i in range(4 - n)])
    if n > 4:
        coords = coords[:4]

    return tuple(map(safe_float_parse, coords))


app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify("OK")


@app.route("/catalog")
def catalog():
    """
    Return a list of available maps
    """
    maps = load_maps(geodata_dir)
    return jsonify(maps)


@app.route("/retrieve/<path:dataset>", methods=["GET"])
def api_dataset_retrieve(dataset: str):
    """
    Build: {geodata_dir}/{dataset}/{subpath}/.vrt
    subpath is optional and may include multiple '/.../...' segments.
    """
    logging.info(f"api_dataset_retrieve({dataset})")

    # Build the VRT path safely
    parts = dataset.split("/")

    src = os.path.normpath(os.path.join(geodata_dir, *[p for p in parts if p], ".vrt"))
    base = os.path.normpath(geodata_dir)
    if not src.startswith(base + os.sep) and src != base:
        return jsonify({"Error": "Invalid path."}), 400

    # if the src file doesn't exist we can abort
    if not os.path.exists(src):
        return jsonify({"Error": f"Cannot find dataset: {src}"}), 404

    fn_uuid = str(uuid4().hex) + ".tif"
    dst = os.path.join(SCRATCH, fn_uuid)

    # if cellsize argument is not supplied assume 30m
    if "cellsize" not in request.args:
        cellsize = 30.0  # in meters
    else:
        cellsize = safe_float_parse(request.args["cellsize"])
        if cellsize == None:
            return jsonify({"Error": "Cellsize should be a float"}), 400

    if cellsize < 1.0:
        return jsonify({"Error": "Cellsize must be  > 1.0"}), 400

    # parse bbox
    if "bbox" not in request.args:
        return jsonify({"Error": "bbox is required (left, bottom, right, top)"}), 400

    bbox = request.args["bbox"]
    bbox = parse_bbox(bbox)

    if any([x == None for x in bbox]):
        return jsonify({"Error": "bbox contains non float values"}), 400

    if bbox[1] > bbox[3] or bbox[0] > bbox[2]:
        return jsonify({"Error": "Expecting bbox defined as: left, bottom, right, top"}), 400

    # determine UTM coordinate system of top left corner
    ul_x, ul_y, utm_number, utm_letter = utm.from_latlon(bbox[3], bbox[0])

    # bottom right
    lr_x, lr_y, _, _ = utm.from_latlon(bbox[1], bbox[2], force_zone_number=utm_number)

    # check size
    width_px = int((lr_x - ul_x) / cellsize)
    height_px = int((ul_y - lr_y) / cellsize)

    if height_px > 4096 or width_px > 4096:
        return jsonify({"Error:": "output size cannot exceed 4096 x 4096"}), 400

    proj4 = "+proj=utm +zone={zone} +{hemisphere} +datum=WGS84 +ellps=WGS84".format(
        zone=utm_number, hemisphere=("south", "north")[bbox[3] > 0]
    )

    # determine resample method
    if "resample" not in request.args:
        src_dtype = determine_band_type(src)
        resample = ("near", "bilinear")["float" in src_dtype.lower()]
    else:
        resample = request.args["resample"]
        if resample not in resample_methods:
            return jsonify({"Error": "resample method not valid"}), 400

    # determine output format
    if "format" not in request.args:
        _format = "GTiff"
    else:
        _format = request.args["format"]
        if _format not in format_drivers:
            return jsonify({"Error": "format driver not valid" + _format}), 400

    # build command to warp, crop, and scale dataset
    cmd = [
        "gdalwarp",
        "-t_srs",
        proj4,
        "-tr",
        str(cellsize),
        str(cellsize),
        "-te",
        str(ul_x),
        str(lr_y),
        str(lr_x),
        str(ul_y),
        "-r",
        resample,
        src,
        dst,
    ]

    # delete destination file if it exists
    if os.path.exists(dst):
        os.remove(dst)

    # run command, check_output returns standard output
    res = subprocess.run(cmd, capture_output=True, text=True)
    output = (res.stdout or "") + (res.stderr or "")

    # check to see if file was created
    if not os.path.exists(dst):
        return jsonify(
            {"Error": "gdalwarp failed unexpectedly", "cmd": ' '.join(cmd), "stdout": output}
        ), 400

    fn_list = []
    fn_list.append(dst)

    # gdaldem processing
    dst2 = None
    gdaldem = None
    if "gdaldem" in request.args:

        gdaldem = request.args["gdaldem"].lower()
        if gdaldem not in gdaldem_modes:
            return jsonify({"Error": "Invalid gdaldem mode: %s" % gdaldem})

        fn_uuid2 = str(uuid4().hex) + ".tif"
        dst2 = os.path.join(SCRATCH, fn_uuid2)

        cmd2 = ["gdaldem", gdaldem, dst, dst2]

        res = subprocess.run(cmd2, capture_output=True, text=True)
        output2 = (res.stdout or "") + (res.stderr or "")

        # check to see if file was created
        if not os.path.exists(dst2):
            return (
                jsonify(
                    {
                        "Error": "gdaldem failed unexpectedly",
                        "cmd2": ' '.join(cmd2),
                        "stdout2": output2,
                    }
                ),
                400,
            )

        fn_list.append(dst2)

    # build response
    dst_final = (dst, dst2)[dst2 != None]

    fname = "_".join(parts) + ext_d[_format]

    if _format != "GTiff":
        dst3, status_code = format_convert(dst, _format)
        if status_code != 200:
            return jsonify({"Error": f"failed to convert to output format {dst3}"}), 400
        else:
            dst_final = dst3
            fn_list.append(dst3)

    logging.info('build resposnse')
    response = send_file(dst_final)
    logging.info('post build resposnse')

    if _format == "AAIGrid":
        response.headers["Content-Type"] = "text/plain"
    elif _format == "PNG":
        response.headers["Content-Type"] = "image/png"
    elif _format == "ENVI":
        response.headers["Content-Type"] = "application/octet-stream"
    else:
        response.headers["Content-Type"] = "image/tiff"

    meta_fn = src.replace(".vrt", "metadata.json")

    meta = {}
    if os.path.exists(meta_fn):
        with open(meta_fn) as f:
            meta = json.load(f)

    meta["wmesque"] = {
        "bbox": bbox,
        "cache": dst,
        "dataset": dataset,
        "cellsize": cellsize,
        "ul": {
            "ul_x": ul_x,
            "ul_y": ul_y,
            "utm_number": utm_number,
            "utm_letter": utm_letter,
        },
        "proj4": proj4,
        "cmd": cmd,
        "stdout": output,
        "timestamp": datetime.now().isoformat(),
    }

    if gdaldem != None:
        meta["wmesque"]["gdaldem"] = {
            "mode": gdaldem,
            "cmd": cmd2,
            "stdout": output2,
            "cache": dst2,
        }

    response.headers["Content-Disposition"] = "attachment; filename=" + fname

    response.headers["WMesque-Meta"] = _b64url(meta)
    response.headers["Access-Control-Expose-Headers"] = "WMesque-Meta"

    logging.info(str(meta)) ## this isn't printing 

    # Define a function to delete the files
    def delete_files(response):
        for file in fn_list:
            try:
                os.remove(file)
            except OSError:
                pass
        return response

    # Register the delete_files function to be executed after the request is completed
    after_this_request(delete_files)

    # return response
    return response
