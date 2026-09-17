"""Check real native auxiliaries hidden by the proposed sibling allowlist."""
import json
import os
from pathlib import Path

from osgeo import gdal
import pytest

from wepppy.all_your_base import raster_freshness as fresh


@pytest.fixture(autouse=True)
def amended_policy_seam(monkeypatch):
    if os.environ.get("RASTER_PROPOSED_COMPANIONS") != "1":
        return
    original = fresh._companions
    monkeypatch.setattr(fresh, "_OPAQUE", fresh._OPAQUE + (".rpb", "_rpc.txt", ".rpc.txt", ".imd", ".rrd"))

    def companions(path):
        found = dict(original(path))
        for source in {path, os.path.realpath(path)}:
            item = Path(source)
            suffix = item.suffix.lower()
            suffixes = {suffix + "w", ".wld"}
            if len(suffix) > 1:
                suffixes.add("." + suffix[1] + suffix[-1] + "w")
            targets = {item.stem.lower() + ending for ending in suffixes}
            for member in item.parent.iterdir():
                if member.name.lower() in targets:
                    found[str(member)] = ".wld"  # Ordinary world-file policy.
        return tuple(sorted(found.items()))

    monkeypatch.setattr(fresh, "_companions", companions)


@pytest.mark.parametrize("filename,suffix", [("source.tiff", ".tifw"), ("source.tiff", ".tiffw"),
                                             ("source.tiff", ".wld"), ("source.foo", ".foow"),
                                             ("source.foo", ".fow"), ("source.tiff", ".TIFFW")])
def test_native_world_file_visibility(tmp_path, filename, suffix):
    source = tmp_path / filename
    ds = gdal.GetDriverByName("GTiff").Create(str(source), 2, 2, 1, gdal.GDT_Byte)
    ds.GetRasterBand(1).Fill(1)
    ds = None
    world = tmp_path / ("source" + suffix)
    world.write_text("30\n0\n0\n-30\n500015\n4999985\n")
    siblings = [source.name, *[Path(path).name for path, kind in fresh._companions(str(source)) if kind in fresh._ORDINARY]]
    states = []
    for restricted in (False, True):
        kwargs = {"sibling_files": siblings} if restricted else {}
        ds = gdal.OpenEx(str(source), gdal.OF_RASTER | gdal.OF_READONLY,
                         allowed_drivers=["GTiff", "AAIGrid"], **kwargs)
        states.append({"restricted": restricted, "files": ds.GetFileList(), "transform": ds.GetGeoTransform()})
        ds = None
    record = {"suffix": suffix, "siblings": siblings, "states": states}
    Path(__file__).with_name("raster_sibling_unknown_" + suffix[1:] + ".json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    assert states[0]["transform"] == states[1]["transform"]
    assert states[0]["files"] == states[1]["files"]
    if os.environ.get("RASTER_IMPLEMENTED_COMPANIONS") == "1":
        initial = fresh.raster_dependency_signature(source)
        assert initial is not None
        assert set(states[0]["files"]) <= {row[0] for row in initial[-1]}
        if str(world) in states[0]["files"]:
            world.write_text("30\n0\n0\n-30\n600015\n4999985\n")
            assert fresh.raster_dependency_signature(source) != initial


def test_native_rpc_sidecar_visibility(tmp_path):
    source = tmp_path / "rpc.tif"
    ds = gdal.GetDriverByName("MEM").Create("", 2, 2, 1, gdal.GDT_Byte)
    coeff = " ".join(["1"] + ["0"] * 19)
    rpc = {name: "1" for name in ("LINE_OFF", "SAMP_OFF", "LAT_OFF", "LONG_OFF", "HEIGHT_OFF",
                                   "LINE_SCALE", "SAMP_SCALE", "LAT_SCALE", "LONG_SCALE", "HEIGHT_SCALE")}
    rpc.update({name: coeff for name in ("LINE_NUM_COEFF", "LINE_DEN_COEFF", "SAMP_NUM_COEFF", "SAMP_DEN_COEFF")})
    ds.SetMetadata(rpc, "RPC")
    output = gdal.GetDriverByName("GTiff").CreateCopy(str(source), ds, options=["RPB=YES", "PROFILE=BASELINE"])
    output = ds = None
    # BASELINE may emit unrelated PAM; remove it so the native RPB relationship
    # is isolated and no existing opaque-PAM guard decides this experiment.
    source.with_name(source.name + ".aux.xml").unlink(missing_ok=True)
    siblings = [source.name, *[Path(path).name for path, kind in fresh._companions(str(source)) if kind in fresh._ORDINARY]]
    states = []
    for restricted in (False, True):
        kwargs = {"sibling_files": siblings} if restricted else {}
        ds = gdal.OpenEx(str(source), gdal.OF_RASTER | gdal.OF_READONLY,
                         allowed_drivers=["GTiff", "AAIGrid"], **kwargs)
        states.append({"restricted": restricted, "files": ds.GetFileList(), "rpc": ds.GetMetadata("RPC")})
        ds = None
    record = {"siblings": siblings, "on_disk": sorted(p.name for p in tmp_path.iterdir()), "states": states}
    Path(__file__).with_name("raster_sibling_unknown_rpc.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    if (os.environ.get("RASTER_PROPOSED_COMPANIONS") == "1"
            or os.environ.get("RASTER_IMPLEMENTED_COMPANIONS") == "1"):
        assert fresh.raster_dependency_signature(source) is None
    else:
        assert states[0]["rpc"] == states[1]["rpc"]
        assert states[0]["files"] == states[1]["files"]
