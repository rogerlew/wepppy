"""Disposable native correctness probes; no named project reads or writes."""
from contextlib import nullcontext
from copy import deepcopy
import errno
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from osgeo import gdal

from wepppy.all_your_base import raster_freshness as fresh
from wepppy.nodb.core import landuse as lu
from wepppy.nodb.mods.baer import sbs_map as sbs
from wepppy.wepp.management import InvalidManagementKey


def raster(path, values):
    path = Path(path)
    ds = gdal.GetDriverByName("GTiff").Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((500000, 30, 0, 4500000, 0, -30))
    ds.GetRasterBand(1).WriteArray(np.asarray(values, dtype=np.uint8).reshape(2, 2))
    ds = None
    return str(path)


def replace(path, values):
    candidate = str(path) + ".candidate"
    raster(candidate, values)
    os.replace(candidate, path)


def test_joint_observation_rejects_first_source_changed_after_second_hash(tmp_path, monkeypatch):
    one = raster(tmp_path / "a.tif", [11] * 4)
    two = raster(tmp_path / "b.tif", [1, 1, 1, 2])
    real = fresh.sha256_file

    def digest(path):
        result = real(path)
        if str(path) == two:
            replace(one, [12] * 4)
        return result

    monkeypatch.setattr(fresh, "sha256_file", digest)
    with pytest.raises(OSError) as exc:
        fresh.raster_dependency_signatures((one, two))
    assert exc.value.errno == errno.ESTALE


def test_recorded_dependency_disappearance_is_changed_source(tmp_path, monkeypatch):
    path = raster(tmp_path / "disappearing.tif", [1] * 4)
    original = fresh.sha256_file

    def digest(source):
        result = original(source)
        os.unlink(source)
        return result

    monkeypatch.setattr(fresh, "sha256_file", digest)
    with pytest.raises(OSError) as exc:
        fresh.raster_dependency_signature(path)
    assert exc.value.errno == errno.ESTALE


def test_sbs_changed_native_result_not_admitted_to_old_key(tmp_path, monkeypatch):
    path = raster(tmp_path / "sbs.tif", [1] * 4)
    original = sbs._summarize_sbs_raster_rust
    sbs._summarize_sbs_raster_cached.cache_clear()

    def changing(source):
        result = original(source)
        replace(path, [3] * 4)
        return result

    monkeypatch.setattr(sbs, "_summarize_sbs_raster_rust", changing)
    with pytest.raises(OSError) as exc:
        sbs._summarize_sbs_raster(path)
    assert exc.value.errno == errno.ESTALE
    assert sbs._summarize_sbs_raster_cached.cache_info().currsize == 0
    monkeypatch.setattr(sbs, "_summarize_sbs_raster_rust", original)
    actual = sbs._summarize_sbs_raster(path)
    assert actual == original(path)
    print("post-rejection native SBS summary", actual)


def test_unverified_vrt_keeps_actual_native_changes_uncached(tmp_path, monkeypatch):
    path = raster(tmp_path / "source.tif", [1] * 4)
    vrt = str(tmp_path / "source.vrt")
    gdal.Translate(vrt, path, format="VRT")
    assert fresh.raster_dependency_signature(vrt) is None
    original = sbs._summarize_sbs_raster_rust
    calls = []

    def observed(source):
        calls.append(source)
        return original(source)

    monkeypatch.setattr(sbs, "_summarize_sbs_raster_rust", observed)
    before = sbs._summarize_sbs_raster(vrt)
    replace(path, [3] * 4)
    after = sbs._summarize_sbs_raster(vrt)
    assert before != after
    assert calls == [vrt, vrt]


def owner(tmp_path, monkeypatch):
    sub = raster(tmp_path / "sub.tif", [11] * 4)
    mofe = raster(tmp_path / "mofe.tif", [1, 1, 1, 2])
    watershed = SimpleNamespace(subwta=sub, mofe_map=mofe, hillslope_area=lambda _: 0.36)
    instance = lu.Landuse.__new__(lu.Landuse)
    instance.wd = str(tmp_path)
    instance.logger = logging.getLogger("raster-correctness-disposable")
    instance._mapping = "disturbed"
    instance._custom_mapping_relpath = None
    instance.domlc_d = {"11": "runtime-generated"}
    instance.domlc_mofe_d = {"11": {"1": "runtime-generated", "2": "ordinary"}}
    instance.managements = {"runtime-generated": SimpleNamespace(area=123, pct_coverage=45)}
    instance.locked = lambda: nullcontext()
    instance.dump_landuse_parquet = lambda: None
    instance.trigger = lambda *_: None
    monkeypatch.setattr(lu.Landuse, "watershed_instance", property(lambda _: watershed))
    monkeypatch.setattr(lu.Landuse, "ron_instance", property(lambda _: SimpleNamespace(cellsize=30)))
    monkeypatch.setattr(lu.Landuse, "wepp_instance", property(lambda _: SimpleNamespace(_multi_ofe=True)))

    def summary(key, *_):
        if key == "runtime-generated":
            raise InvalidManagementKey(key)
        return SimpleNamespace(area=0, pct_coverage=0)

    monkeypatch.setattr(lu, "get_management_summary", summary)
    return instance, watershed


@pytest.mark.parametrize("drift", ["bytes", "selection", "structure"])
def test_mofe_native_drift_preserves_prior_generated_summary_and_cache(tmp_path, monkeypatch, drift):
    instance, watershed = owner(tmp_path, monkeypatch)
    instance.build_managements()
    previous = instance.managements
    values = deepcopy(previous)
    signature = instance._mofe_pair_count_cache_signature
    counts = instance._mofe_pair_count_cache
    assert previous["runtime-generated"].area == pytest.approx(0.27)
    assert previous["ordinary"].area == pytest.approx(0.09)
    replace(watershed.mofe_map, [1, 2, 2, 2])
    original = lu.count_intersecting_raster_key_pairs

    def changing(**kwargs):
        result = original(**kwargs)
        if drift == "bytes":
            replace(watershed.mofe_map, [1, 1, 2, 2])
        elif drift == "selection":
            watershed.mofe_map = raster(tmp_path / "other.tif", [1, 1, 2, 2])
        else:
            instance.domlc_mofe_d["11"]["3"] = "ordinary"
        return result

    monkeypatch.setattr(lu, "count_intersecting_raster_key_pairs", changing)
    with pytest.raises(OSError) as exc:
        instance.build_managements()
    assert exc.value.errno == errno.ESTALE
    assert instance.managements is previous
    assert instance.managements == values
    assert instance._mofe_pair_count_cache is counts
    assert instance._mofe_pair_count_cache_signature == signature


def test_normal_native_coverage_to_real_generated_management_preparation(tmp_path, monkeypatch):
    from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
    from wepppy.wepp.management import get_management_summary, load_map
    from wepppy.wepp.soils.utils import SoilMultipleOfeSynth

    instance, watershed = owner(tmp_path, monkeypatch)
    monkeypatch.setattr(lu, "get_management_summary", get_management_summary)
    instance._mapping = None
    keys = list(load_map())[:2]
    instance.domlc_d = {"11": keys[0]}
    instance.domlc_mofe_d = {"11": {"1": keys[0], "2": keys[1]}}
    instance.managements = None
    runs = tmp_path / "wepp" / "runs"
    runs.mkdir(parents=True)
    land = tmp_path / "landuse"
    land.mkdir()
    slopes = tmp_path / "watershed" / "slope_files" / "hillslopes"
    slopes.mkdir(parents=True)
    (slopes / "hill_11.mofe.slp").write_text(
        "97.5\n2\n311.995 80\n2 40\n0, 0.1 1, 0.2\n2 90\n0, 0.2 1, 0.3\n")
    soils = tmp_path / "soils"
    soils.mkdir()
    source_soil = Path(__file__).resolve().parents[4] / "tests/omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs/p118.sol"
    SoilMultipleOfeSynth([str(source_soil), str(source_soil)]).write(str(soils / "hill_11.mofe.sol"))

    def prepare():
        instance.build_managements()
        plans = []
        for key in keys:
            summary = instance.managements[key]
            plans.append({name: getattr(summary, name) for name in ("key", "man_fn", "man_dir", "desc", "color")})
        lu._write_mofe_management_file_task(("11", str(land / "hill_11.mofe.man"), 2, plans))
        prep_multi_ofe_hillslope(("11", 7, str(tmp_path), str(runs), 3, None, .5,
                                False, 60., False, 1., False, 1.))
        return (runs / "p7.man").read_bytes()

    before = prepare()
    assert instance.managements[keys[0]].area == pytest.approx(.27)
    replace(watershed.mofe_map, [1, 2, 2, 2])
    after = prepare()
    assert instance.managements[keys[0]].area == pytest.approx(.09)
    assert before == after  # Assignments did not change; count areas are reporting values.
    assert len(after) > 1000
    print("real two-OFE / three-year generated p7.man bytes", len(after))


def restore_generation(path, payload):
    staged = Path(str(path) + ".restored")
    staged.write_bytes(payload)
    staged.replace(path)


def test_sbs_native_old_new_old_generations_reject_admission(tmp_path, monkeypatch):
    path = raster(tmp_path / "cycle.tif", [1] * 4)
    payload = Path(path).read_bytes()
    native = sbs._summarize_sbs_raster_rust
    sbs._summarize_sbs_raster_cached.cache_clear()
    seen = []

    def cycle(source):
        replace(source, [3] * 4)
        result = native(source)
        seen.append(result["unique_classes"])
        restore_generation(source, payload)
        return result

    monkeypatch.setattr(sbs, "_summarize_sbs_raster_rust", cycle)
    with pytest.raises(OSError) as exc:
        sbs._summarize_sbs_raster(path)
    assert exc.value.errno == errno.ESTALE
    assert seen == [[3]]
    assert Path(path).read_bytes() == payload
    assert sbs._summarize_sbs_raster_cached.cache_info().currsize == 0


def test_mofe_native_old_new_old_generations_preserve_prior(tmp_path, monkeypatch):
    instance, watershed = owner(tmp_path, monkeypatch)
    instance.build_managements()
    previous = instance.managements
    values = deepcopy(previous)
    counts = instance._mofe_pair_count_cache
    instance._mofe_pair_count_cache_signature = ("legacy-force-real-count",)
    native = lu.count_intersecting_raster_key_pairs
    payload = Path(watershed.mofe_map).read_bytes()
    seen = []

    def cycle(**kwargs):
        replace(watershed.mofe_map, [1, 2, 2, 2])
        result = native(**kwargs)
        seen.append(deepcopy(result))
        restore_generation(watershed.mofe_map, payload)
        return result

    monkeypatch.setattr(lu, "count_intersecting_raster_key_pairs", cycle)
    with pytest.raises(OSError) as exc:
        instance.build_managements()
    assert exc.value.errno == errno.ESTALE
    assert seen == [{"11": {"1": 1, "2": 3}}]
    assert Path(watershed.mofe_map).read_bytes() == payload
    assert instance.managements is previous and instance.managements == values
    assert instance._mofe_pair_count_cache is counts
    assert instance._mofe_pair_count_cache_signature == ("legacy-force-real-count",)


def test_mofe_private_observation_roundtrip_then_touch_reuses(tmp_path, monkeypatch):
    import jsonpickle

    instance, watershed = owner(tmp_path, monkeypatch)
    instance.build_managements()
    payload = {"counts": instance._mofe_pair_count_cache,
               "signature": instance._mofe_pair_count_cache_signature}
    restored = jsonpickle.decode(jsonpickle.encode(payload))
    assert restored["signature"] == payload["signature"]
    assert restored["signature"][0].read_guard == payload["signature"][0].read_guard
    instance._mofe_pair_count_cache = restored["counts"]
    instance._mofe_pair_count_cache_signature = restored["signature"]
    os.utime(watershed.mofe_map, None)

    def unexpected(**kwargs):
        pytest.fail("unchanged numerical content was recounted after private-state roundtrip")

    monkeypatch.setattr(lu, "count_intersecting_raster_key_pairs", unexpected)
    instance.build_managements()
    assert instance.managements["runtime-generated"].area == pytest.approx(.27)
