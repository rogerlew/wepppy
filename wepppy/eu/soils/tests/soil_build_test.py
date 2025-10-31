import os

import pytest

ESDAC_RASTER_DIR = "/geodata/eu/ESDAC_ESDB_rasters"
ESDAC_STU_DIR = "/geodata/eu/ESDAC_STU_EU_Layers"

pytestmark = pytest.mark.skipif(
    not (os.path.isdir(ESDAC_RASTER_DIR) and os.path.isdir(ESDAC_STU_DIR)),
    reason="ESDAC rasters unavailable",
)


def collection_error(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("requests")
    from wepppy.eu.soils.esdac import ESDAC

    esd = ESDAC()
    esd.build_wepp_soil(-6.309, 43.140013, str(tmp_path))


test_collection_error = collection_error
