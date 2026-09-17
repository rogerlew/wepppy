"""MOFE native counting, content freshness and failed-publication isolation."""
from contextlib import nullcontext
from copy import deepcopy
import errno
import logging
import jsonpickle
import os
from types import SimpleNamespace

import numpy as np
from osgeo import gdal, osr
import pytest

from wepppy.nodb.core import landuse as module
from wepppy.wepp.management import InvalidManagementKey, load_map

pytestmark = pytest.mark.integration


def raster(path, values):
    ds = gdal.GetDriverByName('GTiff').Create(str(path), 2, 2, 1, gdal.GDT_Int32)
    ds.SetGeoTransform((500000, 30, 0, 5000060, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    ds.SetProjection(spatial.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(np.array(values, dtype=np.int32))
    ds = None


@pytest.fixture
def owner(tmp_path, monkeypatch):
    subwta, mofe = tmp_path / 'subwta.tif', tmp_path / 'mofe.tif'
    raster(subwta, [[11, 11], [11, 11]])
    raster(mofe, [[1, 1], [1, 2]])
    watershed = SimpleNamespace(subwta=str(subwta), mofe_map=str(mofe), hillslope_area=lambda _: .36)
    monkeypatch.setattr(module.Landuse, 'watershed_instance', property(lambda self: watershed))
    monkeypatch.setattr(module.Landuse, 'ron_instance', property(lambda self: SimpleNamespace(cellsize=30.)))
    monkeypatch.setattr(module.Landuse, 'wepp_instance', property(lambda self: SimpleNamespace(_multi_ofe=True)))
    landuse = module.Landuse.__new__(module.Landuse)
    landuse.wd = str(tmp_path)
    landuse._mapping = None
    keys = list(load_map())[:2]
    landuse.domlc_d = {'11': keys[0]}
    landuse.domlc_mofe_d = {'11': {'1': keys[0], '2': keys[1]}}
    landuse.managements = None
    landuse.logger = logging.getLogger(__name__)
    landuse.locked = lambda: nullcontext()
    publications = []
    landuse.dump_landuse_parquet = lambda: publications.append(deepcopy(landuse.managements))
    landuse.trigger = lambda *args: None
    return landuse, subwta, mofe, keys, publications


def test_real_native_counts_change_with_restored_mtime_and_legacy_miss(owner, monkeypatch):
    landuse, _, mofe, keys, publications = owner
    native = module.count_intersecting_raster_key_pairs
    calls = []
    def count(**kwargs):
        result = native(**kwargs)
        calls.append(result)
        return result
    monkeypatch.setattr(module, 'count_intersecting_raster_key_pairs', count)
    landuse._mofe_pair_count_cache = {'11': {'1': 100}}
    landuse._mofe_pair_count_cache_signature = ('legacy',)
    landuse.build_managements()
    assert landuse.managements[keys[0]].area == pytest.approx(.27)
    landuse._mofe_pair_count_cache_signature = jsonpickle.decode(
        jsonpickle.encode(landuse._mofe_pair_count_cache_signature))
    os.utime(mofe, None)
    landuse.build_managements()
    assert len(calls) == 1
    previous = mofe.stat()
    raster(mofe, [[1, 2], [2, 2]])
    os.utime(mofe, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    assert mofe.stat().st_size == previous.st_size
    landuse.build_managements()
    assert len(calls) == 2
    assert landuse.managements[keys[0]].area == pytest.approx(.09)
    assert landuse.managements[keys[1]].area == pytest.approx(.27)
    assert publications[-1][keys[0]].area == pytest.approx(.09)


@pytest.mark.parametrize('during', ['native', 'cached_hit', 'structure', 'selection'])
def test_rejected_generation_preserves_prior_values_and_cache(owner, monkeypatch, during):
    landuse, _, mofe, keys, publications = owner
    landuse.build_managements()
    previous_managements = landuse.managements
    previous_values = [(m.area, m.pct_coverage) for m in previous_managements.values()]
    previous_cache = landuse._mofe_pair_count_cache
    previous_signature = landuse._mofe_pair_count_cache_signature
    # Exercise runtime-generated summaries reused after static-map lookup fails.
    def missing(*args):
        raise InvalidManagementKey('runtime-generated test summary')
    monkeypatch.setattr(module, 'get_management_summary', missing)
    if during == 'native':
        raster(mofe, [[1, 2], [2, 2]])
        native = module.count_intersecting_raster_key_pairs
        def mutate(**kwargs):
            result = native(**kwargs)
            raster(mofe, [[2, 2], [2, 2]])
            return result
        monkeypatch.setattr(module, 'count_intersecting_raster_key_pairs', mutate)
    else:
        observe = landuse._build_mofe_pair_count_signature
        calls = []
        def mutation(**kwargs):
            result = observe(**kwargs)
            calls.append(1)
            if len(calls) == 1:
                if during == 'structure':
                    landuse.domlc_mofe_d['11']['3'] = keys[0]
                elif during == 'selection':
                    landuse.watershed_instance.mofe_map = landuse.watershed_instance.subwta
                else:
                    raster(mofe, [[2, 2], [2, 2]])
            return result
        monkeypatch.setattr(landuse, '_build_mofe_pair_count_signature', mutation)
    with pytest.raises(OSError) as error:
        landuse.build_managements()
    assert error.value.errno == errno.ESTALE
    assert landuse.managements is previous_managements
    assert [(m.area, m.pct_coverage) for m in previous_managements.values()] == previous_values
    assert landuse._mofe_pair_count_cache is previous_cache
    assert landuse._mofe_pair_count_cache_signature == previous_signature
    assert len(publications) == 1


def test_unverified_does_not_reuse_old_missing_sentinel(owner, monkeypatch):
    landuse, _, _, _, publications = owner
    monkeypatch.setattr(module, 'observe_raster_dependencies', lambda paths: None)
    native = module.count_intersecting_raster_key_pairs
    calls = []
    def count(**kwargs):
        calls.append(1)
        return native(**kwargs)
    monkeypatch.setattr(module, 'count_intersecting_raster_key_pairs', count)
    landuse.build_managements()
    landuse.build_managements()
    assert len(calls) == len(publications) == 2
    assert landuse._mofe_pair_count_cache is None
    assert landuse._mofe_pair_count_cache_signature is None


def test_changed_then_restored_native_counts_preserve_prior_cache(owner, monkeypatch):
    landuse, _, mofe, _, publications = owner
    landuse.build_managements()
    old_cache = landuse._mofe_pair_count_cache
    old_signature = landuse._mofe_pair_count_cache_signature
    old_managements = landuse.managements
    # Force a legitimate miss, then expose transient different bytes to native.
    raster(mofe, [[1, 2], [2, 2]])
    accepted = mofe.read_bytes()
    version = mofe.stat()
    native = module.count_intersecting_raster_key_pairs
    def changed_then_restored(**kwargs):
        raster(mofe, [[2, 2], [2, 2]])
        counts = native(**kwargs)
        mofe.write_bytes(accepted)
        os.utime(mofe, ns=(version.st_atime_ns, version.st_mtime_ns))
        return counts
    monkeypatch.setattr(module, 'count_intersecting_raster_key_pairs', changed_then_restored)
    with pytest.raises(OSError) as error:
        landuse.build_managements()
    assert error.value.errno == errno.ESTALE
    assert landuse._mofe_pair_count_cache is old_cache
    assert landuse._mofe_pair_count_cache_signature == old_signature
    assert landuse.managements is old_managements
    assert len(publications) == 1
