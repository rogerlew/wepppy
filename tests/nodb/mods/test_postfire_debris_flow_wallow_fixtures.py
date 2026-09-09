"""Offline integrity and reader checks for the real Wallow final-severity bundle."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

from wepppy.nodb.mods.baer.sbs_map import SoilBurnSeverityMap, sbs_map_sanity_check

pytestmark = [pytest.mark.integration, pytest.mark.slow]
FIXTURES = Path(__file__).parent / 'fixtures/postfire_debris_flow_wallow'
MANIFEST = json.loads((FIXTURES / 'manifest.json').read_text())


@pytest.mark.parametrize('entry', MANIFEST['files'], ids=lambda entry: entry['path'])
def test_source_product_identity_and_grid(entry):
    path = FIXTURES / entry['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    with rasterio.open(path) as ds:
        assert ds.count == 1 and ds.driver == 'GTiff'
        assert list(ds.shape) == entry['shape']
        assert str(ds.crs) == entry['crs'] == 'EPSG:5070'
        assert list(ds.transform)[:6] == entry['transform']
        assert ds.dtypes == (entry['dtype'],) and ds.nodata is None
        samples = ds.read(1, masked=True)
        assert samples.count() == entry['valid_cells']
        assert [float(samples.min()),float(samples.max())] == entry['valid_range']
        if 'class_counts' in entry:
            values, counts = np.unique(samples.compressed(), return_counts=True)
            assert {str(v):int(n) for v,n in zip(values,counts)} == entry['class_counts']
            assert ds.colormap(1)[4][:3] == (255,0,0)


def test_final_classes_read_without_dnbr_reclassification():
    path = str(FIXTURES / 'wallow_20110623_barc4_alb.tif')
    assert sbs_map_sanity_check(path) == (0,'Map has valid color table')
    source = SoilBurnSeverityMap(path)
    # Check documented severity codes only; archive zero is unclassified.
    assert {str(k):source.class_pixel_map[str(k)] for k in (1,2,3,4)} == {
        '1':'130','2':'131','3':'132','4':'133'}


def test_original_metadata_retained():
    for entry in MANIFEST['metadata']:
        raw = (FIXTURES / entry['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry['sha256']
    assert MANIFEST['collection'] == 'FinalSoilBurnSeverity'
    assert (MANIFEST['prefire_date'],MANIFEST['postfire_date']) == ('2011-05-30','2011-06-23')
