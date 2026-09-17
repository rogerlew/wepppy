"""Actual Omni SBS copy/delete branch and native destination-sidecar evidence.

No model, named run, queue or remote call. Only landuse/soils and directory-lock
boundaries are isolated; copy, unlink, selected name and native GDAL read run.
"""
from contextlib import nullcontext
import hashlib
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from osgeo import gdal, osr
import pytest

from wepppy.nodb.mods.omni.omni import OmniScenario
from wepppy.nodb.mods.omni import omni_mode_build_services as mode

pytestmark = pytest.mark.integration


def test_actual_copy_uses_destination_worldfile_and_consumes_upload(tmp_path, monkeypatch):
    root = tmp_path / 'run'
    source = root / 'omni/_limbo/00/sbs.tif'
    destination = root / '_pups/omni/scenarios/sbs_map_probe/disturbed/sbs.tif'
    source.parent.mkdir(parents=True)
    destination.parent.mkdir(parents=True)
    ds = gdal.GetDriverByName('GTiff').Create(str(source), 2, 2, 1, gdal.GDT_Byte)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(32611)
    ds.SetProjection(crs.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(np.full((2, 2), 3, dtype=np.uint8))
    ds = None
    source_sidecar = source.with_suffix('.tfw')
    destination_sidecar = destination.with_suffix('.tfw')
    source_sidecar.write_text('30\n0\n0\n-30\n500015\n5000045\n')
    destination_sidecar.write_text('10\n0\n0\n-10\n600005\n5000055\n')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    ds = gdal.Open(str(source))
    source_transform = ds.GetGeoTransform()
    ds = None
    observed = {}

    class Disturbed:
        disturbed_dir = str(destination.parent)

        def validate(self, filename, *, mode):
            assert filename == source.name and mode == 0
            dataset = gdal.Open(str(destination))
            observed.update(transform=dataset.GetGeoTransform(), members=dataset.GetFileList(),
                            values=dataset.ReadAsArray().tolist())
            dataset = None

    omni = SimpleNamespace(logger=logging.getLogger(__name__),
                           timed=lambda _: nullcontext(),
                           rq_job_pool_max_worker_per_scenario_task=1)
    monkeypatch.setattr(mode, '_run_with_directory_roots_lock',
                        lambda wd, roots, callback, **kwargs: callback())
    mode.OmniModeBuildServices().apply_scenario_mode(
        omni, scenario_name='sbs_map_probe', scenario=OmniScenario.SBSmap,
        scenario_def={'type': OmniScenario.SBSmap, 'sbs_file_path': str(source)},
        new_wd=str(destination.parent.parent), disturbed=Disturbed(),
        landuse=SimpleNamespace(build=lambda: None),
        soils=SimpleNamespace(build=lambda **kwargs: None), omni_base_scenario_name=None)
    result = dict(source_main_exists=source.exists(), source_worldfile_exists=source_sidecar.exists(),
                  source_transform=source_transform, destination_observation=observed,
                  copied_main_hash_matches=hashlib.sha256(destination.read_bytes()).hexdigest() == before)
    print('OMNI_COPY_BOUNDARY', json.dumps(result, sort_keys=True))
    Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    assert not source.exists() and source_sidecar.exists()
    assert result['copied_main_hash_matches']
    assert observed['transform'] != source_transform
    assert str(destination_sidecar) in observed['members']
    assert observed['values'] == [[3, 3], [3, 3]]
