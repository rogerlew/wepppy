import os

import pytest

from wepppy.eu.soils.esdac import ESDAC

pytestmark = pytest.mark.skipif(
    not (
        os.path.isdir("/geodata/eu/ESDAC_ESDB_rasters")
        and os.path.isdir("/geodata/eu/ESDAC_STU_EU_Layers")
    ),
    reason="ESDAC rasters unavailable",
)


def test_collection_error():
    esd = ESDAC()
    esd.build_wepp_soil(-6.309, 43.140013)
